# Отчёт Java-эталона после снятия намеренных дефектов

Дата: 10.11.2026. Контракт: ТЗ 2.0, F01–F18. По решению пользователя F10/F16/Н1 удалены; шкала баллов не разрабатывалась. Работа остаётся в ветке `feat/final-reference-solutions`.

## Сборка и окружение

Стенд собран полным Temurin JDK 17.0.21+9, compiler release 17, Maven 3.10.0. Исполнение: macOS ARM64, Apple M4 Max; тот же JAR на Java 17.0.21 и Homebrew Java 21.0.13. SHA-256: `95af5243747a3849e6865ea2537e86abd8c62383d805fe50b4f15d8647875377`. [Манифест](../../../jury/stand-manifest.md), [версии и сводка](evidence/after-defect-removal/summary.json).

Комиссия рассчитывается с превышения бесплатного порога; FAILED возвращает сумму и комиссию одной проводкой REFUND. Искусственная задержка 25 мс и prefetch=1 удалены; обычный последовательный потребитель использует prefetch=10. Производительность заранее не задаётся как ожидаемое нарушение.

## Свежая проверка

| Проверка | Результат | Доказательства |
| --- | --- | --- |
| Полный Java-эталон, JDK 17 | 61 PASS, 0 failures/errors/skipped; Maven 0, анализатор 0 | [XML](evidence/after-defect-removal/java17-full/), [лог](evidence/after-defect-removal/java17-full.log) |
| Полный Java-эталон, JDK 21 | 61 PASS, 0 failures/errors/skipped; Maven 0, анализатор 0 | [XML](evidence/after-defect-removal/java21-full/), [лог](evidence/after-defect-removal/java21-full.log) |
| Повтор Java 21 без reset, случайный порядок seed20261110 | 61 PASS, 0 failures/errors/skipped | [XML](evidence/after-defect-removal/java21-random/) |
| Регресс исходников, Java 17 и 21 | 17 PASS на каждой JVM; до исправления две новые денежные проверки падали | [Java17 XML](evidence/after-defect-removal/TEST-stand.StandRegressionTest-java17.xml), [Java21 XML](evidence/after-defect-removal/TEST-stand.StandRegressionTest-java21.xml), [до исправления](evidence/after-defect-removal/red-finance.log) |
| Четыре готовые выдачи × Java17/21 | Все 8 запусков PASS: health, AMQP publish/read, PostgreSQL SELECT и запрет записи, H2/Qpid/Dojo, история30000, контрольные и денежные сценарии | [Матрица](evidence/after-defect-removal/summary.json), `*-probe.json`, `*-finance.json` рядом |
| Общие Python-инструменты | По22 unit-проверки на CPython3.11.14/3.12.12/3.13.12/3.14.3/3.15.2 | `python-*-unit.log` в [evidence](evidence/after-defect-removal/) |
| Четыре participant ZIP | Точный состав и байты проверены; по53 файла, без jury/кэшей/данных | [Архивы](evidence/after-defect-removal/archive-checks.json) |

XML-анализатор принимает только точный полный зелёный состав. Исключения KNOWN удалены. Прежние XML с двумя известными падениями, частичный набор59 и реальный старый прогон с suppressed cleanup HTTP500 теперь отвергаются с кодом1: [проверка](evidence/after-defect-removal/old-failures-rejected.json). Unit-регресс отдельно проверяет отказ при любом failure/error/skip, потере, дублировании или добавлении testcase.

Независимое статическое [ревью](evidence/after-defect-removal/review.md): Critical0, Important0; одно устаревшее описание исправлено. Ревьюер самостоятельно исполнил12 unit-проверок; перечисленные runtime-прогоны выполнены автором изменения, отдельного независимого runtime-повтора новой сборки не было.

## Короткая диагностика нагрузки

Сравнение одной и той же команды `load_check.py 60 10` на этом Mac, без прогрева; каждый раз reset и стандартная история30000. До исправления:600/600 приняты,25% завершились за2с, очередь после подачи266. После:600/600 приняты,100% завершились за2с, очередь0, ошибок и503нет, p95 принятого POST2,99мс. [До](evidence/after-defect-removal/before-load.json), [после](evidence/after-defect-removal/after-load.json); исходные JSONL лежат рядом.

Это подтверждает снятие искусственного торможения в коротком локальном прогоне. Нагрузочный эталон и полное подтверждение НФТ ещё не выполнены; результаты Mac не являются производительностью Windows/ВДИ.

## Ограничения и история

Намеренных дефектов больше нет; F10/F16 — обычные зелёные проверки. Зелёный F01–F18 не означает исчерпывающий аудит контракта: замечания о404 неизвестного клиента уведомлений и едином правиле повторов/DLQ остаются отдельно, см. [известные замечания](known-findings.md).

Windows/ВДИ, полный повтор ручного эталона и независимый runtime-повтор нового хеша остаются открытыми. Старые offline/LFS-клон, контрольная мутация, матрицы и результаты59/61с падениями относятся только к прежней сборке `73c7773c…13ecf`; [старый отчёт](evidence/before-defect-removal-report.md) сохранён как история и не используется для приёмки нового хеша. Все процессы свежей проверки остановлены. Нагрузочный и Python-эталоны по-прежнему ожидают своих планов; оценка — после всех четырёх эталонов.
