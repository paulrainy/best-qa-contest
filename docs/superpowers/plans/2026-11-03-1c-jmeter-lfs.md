# Загрузка комплекта JMeter 1c через Git LFS — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать отдельную ветку, настроить Git LFS и загрузить на GitHub самодостаточный комплект JMeter и Java для задания 1c.

**Architecture:** Сохранить распакованные дистрибутивы в `participant/1-scripts/tools/`. Библиотеки JMeter и исполняемые части Java хранить в Git LFS; документы, лицензии и материалы задания — обычными файлами Git. После push проверить восстановление полного комплекта в свежем клоне с пустым локальным хранилищем LFS.

**Tech Stack:** Git, Git LFS, GitHub, Apache JMeter 5.6.3, Eclipse Temurin JRE 17.0.21+9, существующие Python-проверки материалов.

**Spec:** Требования согласованы в разговоре: новая ветка обязательна; дистрибутивы остаются в репозитории; Windows Server 2016 x64 и macOS только Apple Silicon; запуск без установки и интернета; памятка только для жюри.

## Ограничения и исходное состояние

- Ветка сейчас `main`, HEAD `bd87638`; имеются незакоммиченные изменения комплекта и документации. Сохранить их при создании ветки.
- Рабочая ветка: `feature/1c-jmeter-lfs`.
- Git LFS локально не установлен, Homebrew доступен. Настройка Git LFS — локальная для этого репозитория.
- Около 398 МиБ, 3201 файл в `tools/`; крупнейшие файлы `lib/modules` — около 80 МиБ. Эти дистрибутивы ещё не попадали в коммиты: миграция истории не нужна.
- Не менять JMX, CSV, ключ, ловушки и оценивание. Не добавлять Intel-версию Java.
- Не открывать MR и не сливать ветку в рамках этого плана: результат — проверенная ветка на GitHub.
- Не менять платёжные настройки GitHub. Если квота LFS не позволяет загрузку, сохранить результат локально и сообщить фактическую ошибку.

## На что обратить внимание при проверке

- `lib/modules`, исполняемые файлы без расширения и `bin/ApacheJMeter.jar` тоже должны попадать в LFS — проверить атрибуты и индекс.
- После клонирования должны восстановиться реальные бинарники, права запуска и ссылки — проверить свежий клон с отдельным хранилищем LFS и запуск на Mac.
- Пути с пробелами и кириллицей, отсутствие системной Java — проверить запуск комплектной Java через Mac launcher в этих условиях.
- Архивы GitHub по умолчанию содержат указатели LFS — включить нужную настройку, проверить скачанный архив; архив участника собирать отдельно только из `participant/`.
- Windows Server 2016 пока не проверен запуском — сохранить это ограничение в отчёте; на ВДИ проверить запуск без установленной Java и открытия внешних сервисов.

## Файлы

- Создать `.gitattributes`: границы LFS, сохранение байтов дистрибутивов и окончания строк launchers.
- Сохранить и включить текущие изменения `.gitignore`, `review-tasks/README.md`, `review-tasks/1c-load-review/participant/task.md`.
- Добавить существующие новые `participant/1-scripts/open-jmeter.bat`, `open-jmeter.command` и `tools/`.
- Добавить `jury/jmeter-viewing-guide.md`, `jury/runtime-downloads.json`.
- Дополнить README инструкцией установки Git LFS для сопровождающих и получения файлов перед упаковкой. Участникам Git LFS не нужен: они получают готовый архив.
- Включить этот план в коммит.

## Задача 1. Отдельная ветка и настройка LFS до добавления бинарников

- [x] Сверить `git status --short --branch`, список изменений и отсутствие дистрибутивов в истории. Создать `git switch -c feature/1c-jmeter-lfs`, сохранив текущие файлы. Если имя уже занято, сначала проверить ветку, не перезаписывать её.
- [x] Установить `brew install git-lfs`. Проверить `git lfs version`.
- [x] Выполнить `git lfs install --local`; проверить `git lfs env` и подключение pre-push hook. Существующий hook не перезаписывать принудительно: при его наличии объединить вызовы.
- [x] Создать `.gitattributes` с точными правилами ниже. Первое правило сохраняет исходные окончания строк всех файлов поставщика, включая подписанный Mac runtime. Правила не затрагивают другие задания.

```gitattributes
review-tasks/1c-load-review/participant/1-scripts/tools/** -text
review-tasks/1c-load-review/participant/1-scripts/tools/**/*.jar filter=lfs diff=lfs merge=lfs -text
review-tasks/1c-load-review/participant/1-scripts/tools/java/**/bin/** filter=lfs diff=lfs merge=lfs -text
review-tasks/1c-load-review/participant/1-scripts/tools/java/**/lib/** filter=lfs diff=lfs merge=lfs -text
review-tasks/1c-load-review/participant/1-scripts/tools/java/**/MacOS/** filter=lfs diff=lfs merge=lfs -text
review-tasks/1c-load-review/participant/1-scripts/open-jmeter.bat text eol=crlf
review-tasks/1c-load-review/participant/1-scripts/open-jmeter.command text eol=lf
```

- [x] Через `git check-attr filter text -- <пути>` подтвердить `filter: lfs` у обоих `lib/modules`, Mac `bin/java`, Windows `bin/java.exe`, `Contents/MacOS/libjli.dylib` и `bin/ApacheJMeter.jar`. У `task.md` и лицензий вне `bin/`/`lib/` фильтр должен остаться неопределённым.

## Задача 2. Подготовка и локальная проверка коммита

- [x] Дополнить `review-tasks/README.md`: сопровождающим нужен Git LFS; перед упаковкой выполнить `git lfs pull` и `git lfs fsck`; участников это не касается. Указать, что runtime хранятся через LFS.
- [x] Снять временный манифест SHA-256 всех обычных файлов `tools/`, а также целей символических ссылок и исполняемых битов. Он понадобится для сравнения со свежим клоном; хранить его вне участника, например в `/private/tmp/`.
- [x] Добавить в индекс `.gitattributes` и перечисленные в разделе «Файлы» изменения. Не использовать глобальное `git add .`, не добавлять журнал `.jmeter/`, временные архивы и результаты проверок.
- [x] Проверить `git lfs ls-files --size` и `git lfs status`. У каждого файла, покрытого LFS, содержимое в индексе должно быть корректным LFS-указателем, а рабочий файл — полным бинарником. Проверить это через `git show :<путь>` и `git lfs pointer --check --strict`.
- [x] Проверить, что среди новых обычных Git-блобов нет файлов больше 50 МиБ; `git ls-files -s` показывает режим `100755` у `open-jmeter.command`; реальные байты и ссылки дистрибутивов совпадают с временным манифестом. Существующие файлы упражнений не изменились, кроме строки о запуске в `task.md`.
- [x] Выполнить `git diff --cached --check`. Исходное форматирование файлов поставщика не исправлять; проверять whitespace в собственных документах, launchers и конфигурации отдельно, если поставка даёт замечания.
- [x] Запустить существующую полную проверку с комплектным runtime:

```bash
export JMETER_HOME="$PWD/review-tasks/1c-load-review/participant/1-scripts/tools/apache-jmeter-5.6.3"
export JAVA="$PWD/review-tasks/1c-load-review/participant/1-scripts/tools/java/macos-aarch64/Contents/Home/bin/java"
review-tasks/tools/.venv/bin/python -m pytest review-tasks/tools -q
review-tasks/tools/.venv/bin/python review-tasks/tools/build_jmx.py review-tasks/1c-load-review --check
```

Ожидается: 100 тестов прошли без пропусков, все 20 JMX загружены и прошли проверку GUI-классов. Нагрузку не запускать.

- [x] Проверить `open-jmeter.command --version` из пути с пробелами и кириллицей, с недействительными внешними `JAVA_HOME`/`JRE_HOME` и `PATH=/usr/bin:/bin`. Ожидается JMeter 5.6.3 и код 0; используется комплектная Java.
- [x] Проверить состав архива участника: только `participant/`, реальные runtime, никакой памятки, ключа или `jury/`. Памятка остаётся в `jury/`.
- [x] Сделать один сфокусированный коммит: `feat(1c): добавить комплект JMeter и Java через Git LFS`. Правила LFS и указатели должны попасть в него одновременно. Выполнить `git lfs fsck` для созданного коммита.

## Задача 3. Загрузка и проверка GitHub

- [ ] Проверить авторизацию к `origin` и доступный LFS-бюджет/квоту в настройках GitHub. Не считать общий бесплатный лимит свободным остатком аккаунта.
- [ ] Выполнить `git push -u origin feature/1c-jmeter-lfs`. Pre-push hook должен загрузить объекты LFS до завершения push. Не отключать hook и проверку целостности ради обхода ошибки.
- [ ] Клонировать именно эту ветку из URL `origin` в новую временную папку с `GIT_LFS_SKIP_SMUDGE=1`. Настроить там `git lfs install --local`, затем `git lfs pull` и `git lfs fsck`. Не переиспользовать `.git/lfs` рабочего репозитория.
- [ ] Сравнить каждый файл, цель ссылки и исполняемый бит с манифестом из задачи 2. Убедиться, что runtime восстановлены, а вместо бинарников не остались LFS-указатели. Запустить Mac launcher со `--version` из свежего клона.
- [ ] В GitHub Settings → Archives включить **Include Git LFS objects in archives**, если настройка ещё выключена и есть права администратора. Скачать исходный ZIP именно этой ветки, проверить реальные размеры и SHA-256 обоих `lib/modules` и `ApacheJMeter.jar`. Отсутствие доступа к настройке явно отразить в отчёте; локальная упаковка после `git lfs pull` остаётся рабочим способом выдачи.
- [ ] Собрать пробный архив только из `participant/` свежего клона, исключив `.DS_Store` и `.jmeter/`; проверить его состав. Полный исходный архив репозитория с GitHub участникам не выдавать: в нём есть жюрийные материалы.
- [ ] Завершить отчётом: имя ветки, commit SHA, результат push и проверки свежего клона, состояние включения LFS в архивы, оставшаяся проверка на Windows Server 2016. MR и merge — отдельное последующее действие.

## Документация

- [Установка Git LFS](https://docs.github.com/en/repositories/working-with-files/managing-large-files/installing-git-large-file-storage)
- [Настройка LFS и `.gitattributes`](https://docs.github.com/en/repositories/working-with-files/managing-large-files/configuring-git-large-file-storage)
- [Включение LFS в архивы GitHub](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/managing-git-lfs-objects-in-archives-of-your-repository)
