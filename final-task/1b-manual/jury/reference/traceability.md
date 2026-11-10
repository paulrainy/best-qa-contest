# Трассировка требований и исполнения

[Общий каталог F01–F18](../../../jury/coverage-catalog.md). Каждая карточка содержит подготовку, ожидания, очистку, фактическое и все ссылки вариантов. Статусы ниже отражают конкретную сборку, не квоту качества участника.

| ТЗ | F | Кейс | Факт | Доказательства |
| --- | --- | --- | --- | --- |
| 10,12 | F01 | [M01](test-cases.md#m01) | PASS | [Java17](evidence/M01-java17.jsonl), [Java21](evidence/M01-java21.jsonl) |
| 2–3 | F02 | [M02](test-cases.md#m02) | PASS | [HTTP](evidence/M02.jsonl), [SQL кредитов](evidence/SQL03-credit.txt) |
| 3–5 | F03 | [M03](test-cases.md#m03) | PASS | [HTTP](evidence/M03.jsonl) |
| 3.2,10.1 | F04 | [M04](test-cases.md#m04) | PASS | [9,99](evidence/M04-a.jsonl), [10](evidence/M04-b.jsonl), [300000](evidence/M04-c.jsonl), [300000,01](evidence/M04-d.jsonl), [точность](evidence/M04-e.jsonl) |
| 10.1–10.2 | F05 | [M05](test-cases.md#m05) | PASS | Все12 вариантов связаны в карточке; [данные](evidence/M05-data.jsonl), [SQL отказов](evidence/SQL-early-controls.txt) |
| 2 | F06 | [M06](test-cases.md#m06) | PASS | Все18 вариантов связаны в карточке; [данные/проводки](evidence/M06-data.jsonl), [SQL](evidence/SQL-early-controls.txt) |
| 3.3 | F07 | [M07](test-cases.md#m07) | PASS | [HTTP](evidence/M07.jsonl), [SQL](evidence/SQL-early-controls.txt) |
| 4 | F08 | [M08](test-cases.md#m08) | PASS | [149999,99](evidence/M08-a.jsonl), [150000](evidence/M08-b.jsonl), [150000,01](evidence/M08-c.jsonl) |
| 4,12 | F09 | [M09](test-cases.md#m09) | PASS | [HTTP](evidence/M09.jsonl), [очистка](evidence/C01-M09.jsonl) |
| 5 | F10 | [M10](test-cases.md#m10) | FAIL: денежное отклонение | [HTTP/проводки](evidence/M10.jsonl), [повтор](evidence/R-M10.jsonl) |
| 5 | F11 | [M11](test-cases.md#m11) | PASS | [минимум](evidence/M11-min.jsonl), [округление](evidence/M11-round.jsonl), [месяц](evidence/M11-month.jsonl) |
| 6 | F12 | [M12](test-cases.md#m12) | PASS | [HTTP](evidence/M12.jsonl), [SQL1 строка/2 проводки](evidence/SQL-early-controls.txt) |
| 6 | F13 | [M13](test-cases.md#m13) | PASS | [HTTP](evidence/M13.jsonl) |
| 3.4,8,12 | F14 | [M14](test-cases.md#m14) | PASS | [продукт](evidence/M14.jsonl), [своя очередь/событие/очистка](evidence/M14-broker.jsonl), [SQL](evidence/M14-postings.txt) |
| 3.4 | F15 | [M15](test-cases.md#m15) | PASS | [HTTP](evidence/M15.jsonl), [очередь](evidence/M15-paused-metrics.txt), [C01](evidence/C01-M15.jsonl) |
| 3.4 | F16 | [M16](test-cases.md#m16) | FAIL: денежное отклонение | [HTTP](evidence/M16.jsonl), [REFUND](evidence/SQL04-refund.txt), [C01](evidence/C01-M16.jsonl) |
| 7 | F17 | [M17](test-cases.md#m17) | PASS | [успех](evidence/M17-success.jsonl), [отказ](evidence/M17-failed.jsonl) |
| 9 | F18 | [M18](test-cases.md#m18) | PASS | [HTTP](evidence/M18.jsonl), [ранний SQL](evidence/M18-before-cleanup-sql.txt), [поздний SQL](evidence/SQL07-turnover.txt) |

Дополнительно: [EX01/EX02](exploratory-sessions.md), [SQL и его контроли](sql-reconciliation.md), [собственные данные](evidence/data-register.md). C01-доказательства находятся в ссылках соответствующих календарных/асинхронных карточек.
