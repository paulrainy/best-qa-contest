# Нагрузочный эталон сервиса переводов

Только для жюри. [Методика](methodology.md), [ТЗ](../../../jury/source/spec.md), [выдача участника](../../participant/README.md). Участник выбирает собственные инструменты и структуру; этот JMX в выдачу не входит.

## Подготовка

Нужны JMeter5.6.3 без плагинов, Java17 (дополнительно21), Python3.11+ и зависимости графиков. Можно использовать JMeter из `review-tasks/1c-load-review/participant/1-scripts/tools/apache-jmeter-5.6.3/`; это путь организатора, не зависимость выдачи. Готовый стенд запускается без Maven и сети. JVM выбирается через JAVA_HOME, её версия должна соответствовать платформе.

На выделенном стенде запустите `bash final-task/1c-load/participant/stand/run.sh` из корня репозитория. Другие эталоны одновременно не запускать: каждый нагрузочный прогон выполняет reset. По умолчанию все подключения локальные.

Из этого каталога:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/run.py --profile smoke --jmeter /абсолютный/путь/apache-jmeter-5.6.3/bin/jmeter --base-url http://localhost:18400 --output build/smoke-01
```

Windows: `.venv\Scripts\python.exe` и `jmeter.bat`. Для старшего Python создайте новое окружение именно этим интерпретатором, например `python3.15 -m venv .venv315`; проверьте `.venv315/bin/python --version`, установите тот же requirements и повторите smoke. Фактически подтверждённые сочетания будут перечислены в отчёте; Mac не заменяет целевой Windows/ВДИ-пилот.

`run.py` сам проверяет health, сбрасывает данные, проверяет30000 строк истории, готовит CSV, запускает сбор метрик и JMeter CLI, собирает все принятые статусы с drain≤120с, анализирует и строит графики. Каталог `--output` обязан быть новым. Ошибка запуска не скрывается старым XML/JTL. Результат содержит команды, окружение и коды завершения. `--java-home` позволяет явно выбрать JVM генератора; JVM стенда выбирается при его отдельном запуске. При наличии PID стенда передайте `--stand-pid` для фиксации команды процесса.

## Исполнение

После успешного smoke выполните `steps`, `confirmation`, `stability` той же командой с новыми каталогами. Профили задаются в `profiles/`; переопределять измерительные интервалы без сохранения изменённого профиля нельзя. Каждое исполнение отдельно, с новым reset. Команда возвращает0 при собранном достоверном измерении, даже если НФТ FAIL;2 означает недоказанное измерение (например, недодачу),1 — ошибку инструмента. Проверяйте `summary.json`, а не только код JMeter.

Для низкоуровневого smoke сначала самостоятельно сбросьте стенд, подготовьте данные и новый каталог:

```bash
curl -f -X POST http://localhost:18400/api/test/reset
python tools/prepare_data.py --output build/raw/accounts.csv
mkdir -p build/raw/smoke
jmeter -n -t transfers.jmx -q profiles/smoke.properties -Jaccounts.file=build/raw/accounts.csv -l build/raw/smoke/samples.jtl -e -o build/raw/smoke/html
```

Этот raw CLI проверяет загрузку JMX и дополнительный HTML; для полного комплекта статусов и метрик используйте run.py. Готовый `test-data/accounts.csv` — пример2000 валидных пар стандартной выдачи; runner каждый раз получает актуальный CSV после reset. Файлы JTL, metrics.csv, transfers.jsonl и сохранённый profile.properties позволяют пересчитать summary без стенда:

```bash
python tools/analyse.py --jtl build/smoke-01/samples.jtl --metrics build/smoke-01/metrics.csv --transfers build/smoke-01/transfers.jsonl --profile build/smoke-01/profile.properties --output build/smoke-01/recalculated.json
python tools/plot.py --summary build/smoke-01/summary.json --metrics build/smoke-01/metrics.csv --output build/smoke-01/recalculated-plots
```

Рабочие запуски — в ignored `build/`, отобранные реальные доказательства — в `evidence/`. Кэши, локальные окружения и исходники эталона участникам не передаются. Баллы и штрафы здесь не назначаются.
