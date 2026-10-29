<!--
SPDX-FileCopyrightText: 2026 MSHost contributors
SPDX-License-Identifier: GPL-2.0-or-later
-->
# Сборка Desktop на Windows

Проверенное локальное окружение: Visual Studio 2026 с toolset MSVC v143 14.44,
Qt 6.11.2 и зависимости Craft, CMake/Ninja, Python 3.12, Inkscape, NSIS 3.09.
Путь ниже — пример отдельного каталога сборки, не синхронизируемая папка.
Craft и установленный SDK не входят в Git. Их локальные исправления также
не следует считать автоматически воспроизведёнными одним clone.

```powershell
$root = 'D:/MSHost-Desktop-Build'
$qt = "$root/windows-msvc2022_64-cl"
. "$qt/craft/craftenv.ps1"
$env:SVG_CONVERTER_DIR = "$root/Inkscape/PFiles64/Inkscape/bin"
$env:PATH = "$env:SVG_CONVERTER_DIR;$env:PATH"
cmake -S . -B "$root/client" -G Ninja `
  -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_EXPORT_COMPILE_COMMANDS=ON `
  "-DCMAKE_PREFIX_PATH=$qt" "-DOPENSSL_ROOT_DIR=$qt" `
  "-DCMAKE_INSTALL_PREFIX=$root/runtime" `
  -DBUILD_TESTING=ON -DBUILD_UPDATER=OFF -DWITH_PROVIDERS=OFF `
  -DWIZARD_HIDE_SIGNUP_BUTTON=ON -DWIZARD_HIDE_SELF_HOST_BUTTON=ON `
  -DDISABLE_ACCOUNT_MIGRATION=ON -DBUILD_WIN_MSI=OFF -DBUILD_WIN_TOOLS=OFF `
  -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=cl -DCMAKE_CXX_CLANG_TIDY= `
  -DAPPLICATION_SERVER_URL=https://cloud.mshostcloud.org
cmake --build "$root/client" --parallel 4 `
  --target nextcloud ThemeTest NavigationPaneHelperTest
ctest --test-dir "$root/client" --output-on-failure `
  -R 'ThemeTest|NavigationPaneHelperTest|MSHostBranding'
```

Проверяйте LASTEXITCODE после каждой стадии. В существующем CMake CACHE явно
замените APPLICATION_SERVER_URL: изменение default в исходнике не заменяет cache.
На локальной Windows-сборке после изменения config.h сохранились три старых объекта.
Для смены домена принудительно пересобрали theme.cpp, nextcloudtheme.cpp и testtheme.cpp.
Проверяйте реальный runtime/default, а не только config.h и успешный link.

## Установщик и portable

```powershell
python admin/win/mshost/package.py `
  --build-dir "$root/client" --qt-root $qt `
  --output-dir "$root/dist/domain-20261028" `
  --nsis-dir "$root/packaging-tools/nsis-3.09" `
  --inkscape "$root/Inkscape/PFiles64/Inkscape/bin/inkscape.com"
python admin/win/mshost/verify.py `
  "$root/dist/domain-20261028/package-result.json"
```

Упаковщик скачивает тексты лицензий из указанных upstream-источников;
для этого нужен доступ к сети. Он создаёт setup.exe, portable.zip,
SHA256SUMS.txt, package-result.json и временный payload.
verify.py требует существующий payload: после его очистки сначала повторите упаковку.

Опция verify.py --install-test выполняет установку/удаление в тестовом каталоге
и отказывается затрагивать существующую установку/ярлыки MSHost.
Не удаляйте рабочую установку только ради прохождения этого теста.
Используйте отдельный профиль и одноразовую папку для ручной проверки синхронизации.
[Подробности упаковщика](../../admin/win/mshost/README.md).

## Pre-commit hook форматирования

CMake устанавливает штатный hook git-clang-format. Если git не находит эту команду,
добавьте bin установленного Craft в PATH. На локальном окружении Craft содержал
clang-format 20.1.7, а Visual Studio — 22.1.3. Проверка через LLVM 22.1.3 распознала
конфигурацию репозитория и не изменила ни одного staged C++-файла.
Например, git -c clangFormat.binary=<путь-к-совместимому-clang-format.exe> clang-format
--staged --diff позволяет явно выбрать бинарник. Ту же настройку можно передать
команде commit; hook при этом продолжает выполняться. Не отключайте hook из-за отсутствия PATH.
