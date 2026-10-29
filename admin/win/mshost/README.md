<!--
SPDX-FileCopyrightText: 2026 MSHost contributors
SPDX-License-Identifier: GPL-2.0-or-later
-->
# MSHost-Cloud Windows packages

`package.py` prepares a standalone x64 payload with Qt, Russian/client
translations, the CfAPI virtual-files plugin, runtime DLLs and license texts.
It builds a per-user NSIS installer and a portable ZIP with SHA-256 manifests.
The application version is read from VERSION.cmake; prerelease builds retain
an `alpha` marker. No account settings, sync databases or private test keys
are included.

Build from a configured Craft environment:

```powershell
python admin/win/mshost/package.py `
  --build-dir D:\MSHost-Desktop-Build\client `
  --qt-root D:\MSHost-Desktop-Build\windows-msvc2022_64-cl `
  --output-dir D:\MSHost-Desktop-Build\dist `
  --nsis-dir D:\MSHost-Desktop-Build\packaging-tools\nsis-3.09 `
  --inkscape D:\MSHost-Desktop-Build\Inkscape\PFiles64\Inkscape\bin\inkscape.com
```

The installer targets the current user's `%LOCALAPPDATA%\Programs\MSHost-Cloud`,
creates Start menu entries and offers a desktop shortcut. It refuses nonempty
unrelated target directories. Updating a locked application prompts the user
to close it. Uninstall removes only files listed in the package manifest and
preserves profile/sync data and other files. This package does not register
new Explorer COM extensions or take over the ordinary Nextcloud `nc:` handler.
The client and its virtual-files runtime are included.

Run package verification:

```powershell
python admin/win/mshost/verify.py D:\MSHost-Desktop-Build\dist\package-result.json
```

Adding `--install-test` installs and uninstalls in a newly created test folder.
It refuses to run if an existing MSHost installation or conflicting shortcuts
would be overwritten. It verifies installed file hashes, the uninstaller
command, clean-environment GUI startup and preservation of an unowned file.
The startup check opens and closes only the version dialog; it does not sign
in or start syncing. Compiler warnings fail the installer build (`/WX`).

The initial local packages are unsigned. Staging logs and verification reports
are kept beside the artifacts. The application source remains in the local
fork; packaging does not publish a release or change the server VM.
