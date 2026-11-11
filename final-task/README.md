# Финальное задание «Сервис переводов»

Четыре самостоятельные выдачи для построения тестирования с нуля. Общий продукт и контракт, собственная работа по направлению. Эталоны жюри создаются до разработки шкалы оценки; прежние баллы и ключ охоты за дефектами удалены.

| Направление | Выдача участнику | Эталон жюри |
| --- | --- | --- |
| Java | [1a-java/participant](1a-java/participant/README.md) | [Проект Java](1a-java/jury/reference/README.md) |
| Ручное | [1b-manual/participant](1b-manual/participant/README.md) | [Исполненный ручной проект](1b-manual/jury/reference/README.md) |
| Нагрузка | [1c-load/participant](1c-load/participant/README.md) | Ожидает исполнения отдельного плана |
| Python | [1d-python/participant](1d-python/participant/README.md) | [Проект Python](1d-python/jury/reference/README.md), [результаты и ограничения](1d-python/jury/reference/report.md) |

Намеренно внедрённых дефектов в стенде больше нет. Оценивается построение тестирования и обоснованность результатов; обязательного числа находок нет. Полные Java- и Python-эталоны должны проходить целиком.

## Общая основа жюри

- [Канонический контракт](jury/source/spec.md), [каталог F01–F18](jury/coverage-catalog.md), [известные отклонения](jury/stand-findings.md).
- `jury/stand-src/` — единственные исходники стенда; участникам их не передавать. Сборка обфусцирована; декомпиляция запрещена условием.
- [Манифест](jury/stand-manifest.md) — SHA-256 исходников, конфигурации и четырёх физических runtime-копий.
- Информация участнику находится в README и ТЗ Markdown; готовые тесты и starters не выдаются.
- Java 17 — базовая версия, Java 21 — обязательная проверка совместимости. Служебные Python-инструменты — 3.11+, проверенная матрица и ограничения указываются в отчёте. Python не нужен участнику ручного направления.

## Подготовка и контроль

Готовые JAR/библиотеки/ZIP консоли хранятся через Git LFS. После установки Git LFS один раз для клона выполнить `git lfs install --local`, затем `git lfs pull`. Для запуска готовой выдачи нужны только соответствующая платформе Java 17/21 и локальные свободные порты. Maven и сеть при запуске стенда не нужны. Все четыре стенда имеют одинаковые порты, запускаются последовательно.

Из корня репозитория:

```bash
# Только для изменения и пересборки стенда: полный JDK 17 с jmods, Maven, Python 3.11+.
# JAVA_HOME должен указывать на JDK 17.
bash final-task/jury/build-stand.sh
python3 final-task/jury/verify/check_distribution.py --check
git lfs fsck

bash final-task/1a-java/participant/stand/run.sh
# Следующие команды — в другом терминале. Они сбрасывают данные стенда.
python3 final-task/jury/verify/verify_defects.py controls
python3 final-task/jury/verify/verify_defects.py
# Короткая диагностика нагрузки; не заменяет нагрузочный эталон и проверку НФТ.
python3 final-task/jury/verify/load_check.py 60 10

python3 -m unittest discover -s final-task/jury/tools
python3 -m unittest discover -s final-task/jury/verify
```

`probe_runtime.py` дополнительно проверяет AMQP, PostgreSQL и обе веб-консоли, включая Dojo. Зависимости: `jury/verify/requirements.txt`; установить их в отдельное виртуальное окружение выбранного Python (`python -m pip install -r ...`). H2 JDBC и запрет записи дополнительно проверяются Java-эталоном. Команды запуска и подключения участника находятся только в README его выдачи.

## Упаковка

Архивировать только `final-task/<направление>/participant/`: README, spec и stand с библиотеками. Исключить `stand/test-data/`, логи и файлы блокировки. Эталон, `jury/`, исходники стенда, Maven-кэш, target и Python-окружения в архив не включать. Проверка готового архива:

```bash
python3 final-task/jury/verify/check_distribution.py --check --archive /путь/participant.zip --direction 1a-java
```

В архиве допускается корень `participant/` либо его содержимое без обёртки. Проверка сверяет полный набор файлов и содержимое с выдачей. Независимый локальный клон с LFS и запуск без пересборки проверяются до приёмки. Windows/ВДИ требуют отдельного пилота на целевом окружении; Mac его не заменяет.

Срок сдачи — пять рабочих дней до финала, защита 7+3 минуты. Шкала оценки будет отдельной работой после приёмки всех четырёх эталонов. Java-план включает общую подготовку; ручной и Python-планы также завершены. Нагрузочный план отложен пользователем.
