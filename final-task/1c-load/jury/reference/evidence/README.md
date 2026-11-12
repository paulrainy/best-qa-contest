# Происхождение измерений

Основные и совместимые запуски выполнены 11.11.2026. Файлы скопированы из одноимённых build-каталогов без изменения содержания. Абсолютные пути environment.json — фактически выполненные команды до отбора, а не команды запуска из evidence. `.gitattributes` сохраняет исходные байты CSV/JTL/JSONL при checkout на другой платформе.

- `main-java17/{steps,confirmation,stability}` — три основных профиля, базовые Java 17/Python 3.11.
- `matrix-java17/python311` … `python315` — отдельные чистые установки и реальные smoke с PNG. install.log содержит установку и unit-тесты; environment.json — фактические пакеты и версии.
- `matrix-java21/python311` — smoke со стендом и генератором на Java 21, базовый Python.
- `control/dispatch-stall` — ожидаемо недоказанный прогон с задержкой отправки; `control/restored-smoke` — повтор без неё.
- `control/slow-dispatch-jmeter` и `slow-dispatch-control.jmx` — реальный wrapper и фактически загруженная копия JMX. Путь `real` в wrapper нужно заменить, если воспроизводить контроль на другой машине. Его environment.json хранит SHA входного штатного JMX, а не подменённой копии; отдельные файлы различаются в SHA256SUMS.
- `raw-cli` — пробный низкоуровневый запуск и дополнительный HTML, 60 строк JTL. Без статусов и метрик он не доказывает SLO.
- `tool-guards` — отрицательные проверки отказа от перезаписи/ошибки процесса.
- `independent-recount.json` — отдельный пересчёт количества, ключей, ID, p95 и SLO по каждой измерительной когорте; не усредняет p95.
- `review-fixes-2026-11-12/{smoke,confirmation}` — повтор 12.11.2026 на JAR `220d02c8…` после исправлений по ревью. Стенд на Java 17, генератор на JRE 17 из комплекта JMeter, Windows 11; JMX уже с классификацией 422. Состав файлов тот же, что у основных прогонов, без HTML и INFO-лога.
- `independent-acceptance/windows-java25` — независимый повтор smoke, confirmation и raw CLI на Windows 11 12.11.2026 (стенд на Java 25, генератор на Java 17), отдельный пересчёт и неудавшийся генератор на Java 25. Заключение — в его [README](independent-acceptance/windows-java25/README.md). Файлы созданы на Windows и сохраняют CRLF там, где их так записали Python и JMeter.

В каждой полной записи: samples.jtl, metrics.csv и исходный Prometheus в metrics.jsonl, transfers.jsonl с ответами API и временем наблюдения, transfers.survey.json с deadline опроса, profile.properties, accounts.csv, initial/reset/environment JSON, консоль JMeter, результат построения и четыре PNG. Полные INFO-логи/HTML основных запусков не отбираются: это вспомогательная диагностика, первичные измерения сохраняются полностью. Для raw CLI на Mac сохранены HTML и JTL; его INFO-лог был указан в первой версии SHA256SUMS, но правило `jmeter.log` в `.gitignore` не пустило файл в Git. 12.11.2026 строка удалена из SHA256SUMS, а для отобранных логов добавлено исключение `!evidence/**/jmeter.log`; исходный лог остался только на машине автора.

В SHA256SUMS включаются все файлы evidence, кроме самого SHA256SUMS. Проверка из каталога эталона на macOS/Linux:

```bash
shasum -a 256 -c evidence/SHA256SUMS
```

Для пересчёта без стенда используйте команды analyse.py/plot.py из README, подставив соответствующий каталог evidence и новый output в build. Сохранённый summary не редактируется при пересчёте. Если меняется код анализа, происхождение и различия старого/нового результата фиксируются явно.
