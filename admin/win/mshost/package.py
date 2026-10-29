# SPDX-FileCopyrightText: 2026 MSHost contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build the standalone Windows payload and the per-user NSIS installer."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[3]


def pe_imports(path: Path) -> set[str]:
    data = path.read_bytes()
    if data[:2] != b"MZ":
        raise ValueError(f"Not a PE executable: {path}")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError(f"Invalid PE signature: {path}")
    machine, sections = struct.unpack_from("<HH", data, pe + 4)
    if machine != 0x8664:
        raise ValueError(f"Non-x64 binary in payload: {path}")
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    optional = pe + 24
    if struct.unpack_from("<H", data, optional)[0] != 0x20B:
        raise ValueError(f"Expected PE32+ executable: {path}")
    section_table = optional + optional_size

    def offset(rva: int) -> int:
        for index in range(sections):
            start = section_table + index * 40
            size, address, raw_size, raw_offset = struct.unpack_from("<IIII", data, start + 8)
            if address <= rva < address + max(size, raw_size):
                return raw_offset + rva - address
        raise ValueError(f"Unmapped import RVA {rva:x}: {path}")

    imports = set()
    for directory_index, descriptor_size, name_offset in [(1, 20, 12), (13, 32, 4)]:
        rva, _ = struct.unpack_from("<II", data, optional + 112 + directory_index * 8)
        if not rva:
            continue
        cursor = offset(rva)
        for _ in range(4096):
            descriptor = data[cursor:cursor + descriptor_size]
            if not any(descriptor):
                break
            name_rva = struct.unpack_from("<I", descriptor, name_offset)[0]
            if directory_index == 13 and not (struct.unpack_from("<I", descriptor)[0] & 1):
                raise ValueError(f"Unsupported non-RVA delay import: {path}")
            name_start = offset(name_rva)
            imports.add(data[name_start:data.index(b"\0", name_start)].decode("ascii"))
            cursor += descriptor_size
        else:
            raise ValueError(f"Unterminated PE import table: {path}")
    return imports


def deploy_dependencies(payload: Path, qt_root: Path) -> None:
    sources = {p.name.casefold(): p for p in (qt_root / "bin").glob("*.dll")}
    queue = [p for p in payload.rglob("*") if p.suffix.lower() in {".dll", ".exe"}]
    available = {p.name.casefold() for p in queue}
    system32 = Path(os.environ["SystemRoot"]) / "System32"
    missing = set()
    for binary in queue:
        for dependency in pe_imports(binary):
            name = dependency.casefold()
            if name in available or name.startswith(("api-ms-win-", "ext-ms-win-")):
                continue
            if name in sources:
                target = payload / sources[name].name
                shutil.copy2(sources[name], target)
                available.add(name)
                queue.append(target)
            elif not (system32 / dependency).exists():
                missing.add(f"{binary.name}: {dependency}")
    if missing:
        raise RuntimeError("Unresolved DLL imports:\n" + "\n".join(sorted(missing)))


def nsis_string(value: str | Path) -> str:
    return str(value).replace("$", "$$").replace('"', '$\\"')


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_payload(payload: Path, qt_root: Path) -> None:
    deploy_dependencies(payload, qt_root)
    required = ["mshost-cloud.exe", "mshost-cloudsync.dll", "mshost-cloud_csync.dll",
                "mshost-cloudsync_vfs_cfapi.dll", "Qt6Core.dll", "Qt6Quick.dll", "qt.conf",
                "plugins/platforms/qwindows.dll", "i18n/client_ru.qm", "LICENSE.txt",
                "vcruntime140.dll", "msvcp140.dll"]
    for relative in required:
        if not (payload / relative).is_file():
            raise RuntimeError(f"Missing payload file: {relative}")
    for path in payload.rglob("*"):
        if path.is_file() and (path.suffix.lower() in {".pdb", ".ilk", ".cfg", ".db"}
                               or "privatekey" in path.name.lower()
                               or path.name in {"ThemeTest.exe", "NavigationPaneHelperTest.exe"}):
            raise RuntimeError(f"Developer or private file in payload: {path}")


def main() -> None:
    build = ARGS.build_dir.resolve()
    output = ARGS.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="stage-", dir=output)).resolve()
    if not stage.is_relative_to(output):
        raise RuntimeError("Staging directory escaped the output directory")
    payload = stage / "payload"
    assets = stage / "assets"
    payload.mkdir()
    assets.mkdir()
    print(f"Staging payload in {payload}", flush=True)
    for name in ["mshost-cloud.exe", "mshost-cloudsync.dll", "mshost-cloud_csync.dll", "mshost-cloudsync_vfs_cfapi.dll", "sync-exclude.lst"]:
        shutil.copy2(build / "bin" / name, payload / name)
    (payload / "i18n").mkdir()
    for path in (build / "src/gui").glob("client_*.qm"):
        shutil.copy2(path, payload / "i18n" / path.name)
    deploy = ARGS.qt_root / "bin/windeployqt.exe"
    command = [str(deploy), "--release", "--no-compiler-runtime", "--qmldir", str(ROOT / "src/gui"),
               "--dir", str(payload), "--plugindir", str(payload / "plugins"),
               "--qml-deploy-dir", str(payload / "qml"), "--translationdir", str(payload / "i18n"),
               str(payload / "mshost-cloud.exe")]
    with (stage / "windeployqt.log").open("wb") as log:
        subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
    for path in (ARGS.qt_root / "translations").glob("qtkeychain_*.qm"):
        shutil.copy2(path, payload / "i18n" / path.name)
    (payload / "qt.conf").write_text("[Paths]\nPrefix=.\nPlugins=plugins\nQmlImports=qml\nTranslations=i18n\n", encoding="utf-8")
    shutil.copy2(ROOT / "COPYING", payload / "LICENSE.txt")
    (payload / "licenses").mkdir()
    for name, url in {
        "Qt-LGPL-3.0.txt": "https://raw.githubusercontent.com/qt/qtbase/v6.11.2/LICENSES/LGPL-3.0-only.txt",
        "GPL-3.0.txt": "https://raw.githubusercontent.com/qt/qtbase/v6.11.2/LICENSES/GPL-3.0-only.txt",
        "OpenSSL-LICENSE.txt": "https://raw.githubusercontent.com/openssl/openssl/openssl-3.6.4/LICENSE.txt",
    }.items():
        with urllib.request.urlopen(url, timeout=60) as response:
            (payload / "licenses" / name).write_bytes(response.read())
    (payload / "THIRD-PARTY-NOTICES.txt").write_text(
        "MSHost-Cloud is based on Nextcloud Desktop (GPL-2.0-or-later).\n"
        "Copyright Nextcloud GmbH, ownCloud GmbH and contributors.\n"
        "Qt 6.11.2 is dynamically linked; see licenses/Qt-LGPL-3.0.txt and licenses/GPL-3.0.txt.\n"
        "OpenSSL license: licenses/OpenSSL-LICENSE.txt.\n"
        "The payload also contains QtKeychain, KDE KArchive and their runtime dependencies.\n"
        "Application source: https://github.com/BigShiShKa/mshost-desktop\n", encoding="utf-8")
    versions = (ROOT / "VERSION.cmake").read_text(encoding="utf-8")
    numbers = [int(re.search(rf"set\(MIRALL_VERSION_{key}\s+(\d+)\)", versions)[1]) for key in ["MAJOR", "MINOR", "PATCH"]]
    numeric = ".".join(map(str, [*numbers, 0]))
    version = numeric + ("-alpha" if numbers[2] >= 50 else "")
    brand = (ROOT / "NEXTCLOUD.cmake").read_text(encoding="utf-8")
    product_id = re.search(r'set\(\s*WIN_MSI_UPGRADE_CODE\s+"([A-F0-9-]+)"', brand)[1]
    (payload / ".mshost-cloud-owned").write_text(product_id, encoding="ascii")
    metadata = {"product": "MSHost-Cloud", "version": version, "architecture": "x64",
                "source_revision": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
                "source_modified": bool(subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True)),
                "source_url": "https://github.com/BigShiShKa/mshost-desktop"}
    (payload / "BUILD-INFO.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    validate_payload(payload, ARGS.qt_root)
    files = sorted(p for p in payload.rglob("*") if p.is_file())
    manifest = {p.relative_to(payload).as_posix(): sha256(p) for p in files}
    (payload / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    files.append(payload / "manifest.json")
    for name in ["header", "welcome"]:
        subprocess.run([str(ARGS.inkscape), str(ROOT / f"admin/win/mshost/assets/{name}.svg"), "-o", str(assets / f"{name}.png")], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "admin/win/mshost/prepare-assets.ps1"), "-AssetDirectory", str(assets)], check=True)
    installer = output / f"MSHost-Cloud-{version}-win64-setup.exe"
    portable = output / f"MSHost-Cloud-{version}-win64-portable.zip"
    config = {"PACKAGE_VERSION": version, "NUMERIC_VERSION": numeric, "PRODUCT_ID": product_id,
              "OUTPUT_FILE": installer, "PAYLOAD_DIR": payload, "ASSET_DIR": assets,
              "APP_ICON": build / "src/gui/MSHost-Cloud.ico"}
    lines = [f'!define {key} "{nsis_string(value)}"' for key, value in config.items()]
    lines.append(f"!define INSTALLED_SIZE_KB {(sum(p.stat().st_size for p in files) + 1023) // 1024}")
    (stage / "package-config.nsh").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    remove = [f'Delete "$INSTDIR\\{nsis_string(p.relative_to(payload))}"' for p in files]
    directories = sorted((p for p in payload.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True)
    remove += [f'RMDir "$INSTDIR\\{nsis_string(p.relative_to(payload))}"' for p in directories]
    (stage / "payload-uninstall.nsh").write_text("\n".join(remove) + "\n", encoding="utf-8-sig")
    makensis = ARGS.nsis_dir / "makensis.exe"
    with (stage / "nsis.log").open("wb") as log:
        subprocess.run([str(makensis), "/WX", f'/X!addincludedir "{stage}"', str(ROOT / "admin/win/mshost/installer.nsi")], check=True, cwd=stage, stdout=log, stderr=subprocess.STDOUT)
    with zipfile.ZipFile(portable, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            archive.write(path, path.relative_to(payload).as_posix())
    checksums = {p.name: sha256(p) for p in [installer, portable]}
    (output / "SHA256SUMS.txt").write_text("".join(f"{digest}  {name}\n" for name, digest in checksums.items()), encoding="ascii")
    result = {**metadata, "installer": str(installer), "portable": str(portable), "payload": str(payload),
              "file_count": len(files), "sha256": checksums}
    (output / "package-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ["build-dir", "qt-root", "output-dir", "nsis-dir", "inkscape"]:
        parser.add_argument("--" + key, required=True, type=Path)
    ARGS = parser.parse_args()
    main()
