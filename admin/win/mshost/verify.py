# SPDX-FileCopyrightText: 2026 MSHost contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify package hashes, clean-environment startup and optional install/uninstall."""
from __future__ import annotations
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tempfile
import time
import winreg
import zipfile

UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\MSHost-Cloud"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def registry_value(path: str, name: str):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            return winreg.QueryValueEx(key, name)
    except FileNotFoundError:
        return None


def clean_environment() -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items()
                   if not key.upper().startswith(("QT_", "QML_", "CRAFT", "KDEROOT", "QTDIR", "CMAKE_", "QSG_"))}
    environment["PATH"] = os.path.join(os.environ["SystemRoot"], "System32") + os.pathsep + os.environ["SystemRoot"]
    environment["QT_QPA_PLATFORM"] = "windows"
    environment["QT_DEBUG_PLUGINS"] = "1"
    environment["QT_FORCE_STDERR_LOGGING"] = "1"
    return environment


def gui_smoke(executable: Path, log: Path) -> None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    ctypes.WinDLL("kernel32").SetErrorMode(0x0001 | 0x0002 | 0x8000)
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    stream = log.open("wb")
    process = subprocess.Popen([str(executable), "--version"], cwd=executable.parent,
                               env=clean_environment(), startupinfo=startup,
                               stdout=stream, stderr=subprocess.STDOUT)
    window = []

    @callback_type
    def visit(handle, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        if pid.value == process.pid:
            title = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(handle, title, len(title))
            if title.value == "MSHost-Cloud":
                window.append(handle)
                return False
        return True

    deadline = time.monotonic() + 30
    while process.poll() is None and time.monotonic() < deadline and not window:
        user32.EnumWindows(visit, 0)
        time.sleep(0.1)
    if window:
        user32.PostMessageW(window[0], 0x0010, 0, 0)
    else:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=10)
        stream.close()
        raise RuntimeError(f"Standalone version dialog did not open; exit={process.returncode}; log={log}")
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
        stream.close()
        raise RuntimeError("Standalone version dialog did not exit cleanly")
    stream.close()
    output = log.read_bytes()
    if process.returncode != 0:
        raise RuntimeError(f"Standalone startup failed: {process.returncode}; log={log}")
    expected = str(executable.parent / "plugins/platforms/qwindows.dll").replace("\\", "/").lower()
    if expected not in output.decode("utf-8", errors="replace").replace("\\", "/").lower():
        raise RuntimeError("Qt platform plugin was not found in the bundled directory")


def install_roundtrip(result: dict, manifest: dict[str, str], output: Path) -> dict:
    if registry_value(UNINSTALL_KEY, "InstallLocation") is not None:
        raise RuntimeError("An MSHost-Cloud installation already exists; install test was not started")
    install_key = r"Software\MSHost\MSHost-Cloud"
    if registry_value(install_key, "InstallDir") is not None:
        raise RuntimeError("An existing MSHost install registration would be overwritten")
    desktop_value = registry_value(r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders", "Desktop")
    desktop = Path(os.path.expandvars(desktop_value[0])) if desktop_value else Path(os.environ["USERPROFILE"]) / "Desktop"
    programs = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/MSHost-Cloud"
    shortcut = desktop / "MSHost-Cloud.lnk"
    if shortcut.exists() or programs.exists():
        raise RuntimeError("Existing MSHost shortcuts would be overwritten; install test was not started")
    autostart = registry_value(RUN_KEY, "MSHost-Cloud")
    target = Path(tempfile.mkdtemp(prefix="installer-test-", dir=output.parent)).resolve()
    if not target.is_relative_to(output.parent.resolve()):
        raise RuntimeError("Unexpected installer test path")
    print(f"Testing installer in {target}", flush=True)
    subprocess.run([result["installer"], "/S", f"/D={target}"], check=True, timeout=180)
    for name, digest in manifest.items():
        path = target / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"Installed file differs from package: {name}")
    if registry_value(UNINSTALL_KEY, "InstallLocation")[0] != str(target):
        raise RuntimeError("Incorrect installed application path")
    uninstall = target / "Uninstall.exe"
    if registry_value(UNINSTALL_KEY, "UninstallString")[0] != f'"{uninstall}"':
        raise RuntimeError("Uninstaller command is incorrectly quoted")
    gui_smoke(target / "mshost-cloud.exe", output / "installed-startup.log")
    sentinel = target / "KEEP-UNOWNED-FILE.txt"
    sentinel.write_text("This file must survive application uninstall.\n", encoding="utf-8")
    print("Installed runtime passed; testing uninstall", flush=True)
    subprocess.run([str(uninstall), "/S"], check=True, timeout=60)
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if registry_value(UNINSTALL_KEY, "DisplayName") is None and not (target / "mshost-cloud.exe").exists():
            break
        time.sleep(0.2)
    if any((target / name).exists() for name in manifest):
        raise RuntimeError("Uninstaller left packaged files behind")
    if not sentinel.is_file() or sentinel.read_text() != "This file must survive application uninstall.\n":
        raise RuntimeError("Uninstaller removed an unowned file")
    if registry_value(UNINSTALL_KEY, "DisplayName") is not None or registry_value(install_key, "InstallDir") is not None:
        raise RuntimeError("Uninstaller left install registration behind")
    if shortcut.exists() or programs.exists() or registry_value(RUN_KEY, "MSHost-Cloud") != autostart:
        raise RuntimeError("Uninstall did not restore shortcut/autostart state")
    return {"install_uninstall": "passed", "test_directory": str(target), "unowned_file_preserved": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("--install-test", action="store_true")
    args = parser.parse_args()
    result = json.loads(args.result.read_text(encoding="utf-8"))
    output = args.result.parent.resolve()
    for name, digest in result["sha256"].items():
        if hashlib.sha256((output / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"Artifact checksum differs: {name}")
    with zipfile.ZipFile(result["portable"]) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or any(PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts for name in names):
            raise RuntimeError("Invalid portable archive paths")
        manifest = json.loads(archive.read("manifest.json"))
        if set(names) != set(manifest) | {"manifest.json"}:
            raise RuntimeError("Portable manifest and archive file list differ")
        for name, digest in manifest.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise RuntimeError(f"Portable file checksum differs: {name}")
    gui_smoke(Path(result["payload"]) / "mshost-cloud.exe", output / "standalone-startup.log")
    report = {"artifact_hashes": "passed", "portable_file_hashes": len(manifest), "clean_environment_startup": "passed"}
    if args.install_test:
        report.update(install_roundtrip(result, manifest, output))
    (output / "verification-result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
