<!--
SPDX-FileCopyrightText: 2026 MSHost contributors
SPDX-License-Identifier: GPL-2.0-or-later
-->
# Проверки и сборки Desktop

Результаты относятся к локальному окружению 27–28 октября 2026, а не к неизвестному CI.

| Проверка | Наблюдавшийся результат |
| --- | --- |
| Сборка клиента и двух выбранных test targets | Успех |
| ThemeTest | 50 случаев в проверке брендинга; suite повторно прошёл после смены домена |
| NavigationPaneHelperTest | Успех; включает регрессию владения Explorer namespace |
| MSHostBrandingConfig / DevConfig / CustomServer | Все три прошли |
| clang-tidy затронутых translation units до смены домена | Прошёл; финальный прогон не менял исходники |
| git diff --check | Прошёл на подготовленных изменениях |
| Итоговый default в упакованной библиотеке | https://cloud.mshostcloud.org |
| Хеши пакетов и файлов portable | Прошли; 1554 payload-файла проверены |
| Запуск с чистым окружением | Прошёл; используется собственный Qt platform plugin |
| Install/uninstall и чужой файл | Прошли на предыдущем пакете; для domain-пакета отдельно не повторялись |

## Артефакты с новым доменом

Версия 35.0.50.0-alpha, Windows x64. Локальная папка выпуска:
D:\MSHost-Desktop-Build\dist\domain-20261028.
Бинарники не входят в это обновление Git и не считаются опубликованным GitHub Release.
Сборка выполнялась на базовой ревизии c6461d9a8088100ff12bd849d676e29928b86eaa
с незакоммиченными на тот момент изменениями.

```text
42147485444cd31eb75b014bde86e74d4adc7defbca2cf0cf71e80c8084b718e  MSHost-Cloud-35.0.50.0-alpha-win64-setup.exe
0a9c2741ee1da5b2804c2b4f383d1ef75c29102c210e5901957c3b7dafc6ad04  MSHost-Cloud-35.0.50.0-alpha-win64-portable.zip
```

Известные ограничения: alpha upstream, отсутствие цифровой подписи,
отсутствие установки Explorer COM extensions, отключённое автообновление,
неполная матрица обновлений/параллельных установок и ручной live-синхронизации.
