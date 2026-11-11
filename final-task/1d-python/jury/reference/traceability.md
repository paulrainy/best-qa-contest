# Трассировка Python-эталона

Источник ожиданий — [ТЗ2.0](../../../jury/source/spec.md) и [F01–F18](../../../jury/coverage-catalog.md). Пути ниже относительно этого проекта; точные XML ID, включая параметры, закреплены в [общем каталоге](../../../jury/tools/reference-test-catalog.json). Полный интеграционный состав —64 testcase, помощники проверяются отдельно. Это не квота для участника.

| ID | Тесты (`tests/`) | Проверяемый результат |
| --- | --- | --- |
| F01 | `test_transfers::test_readiness_and_read_only_connections`; AMQP также в F02/F14 | HTTP UP, SELECT по PostgreSQL, реальное подключение к брокеру; `Db` разрешает только SELECT, серверные права ранее проверены общим инструментом |
| F02 | `test_transfers::test_own_transfer_completes_with_exact_balances` | OWN100, комиссия0,999900/100, своё событие, ровно2 проводки |
| F03 | `test_transfers::test_other_transfer_within_free_threshold` | OTHER123,45, комиссия0, сохранена копейка |
| F04 | `test_validation::test_amount_boundaries` (5) |9,99/300000,01/10,001 отклонены;10/300000 OWN приняты |
| F05 | `test_validation::test_invalid_payload_leaves_money_untouched` (7), `test_unknown_account_is_404` (2), `test_invalid_key_is_400` (2); `test_transfers::test_insufficient_funds_leave_no_transfer` | Структура/тип/формат/неизвестный счёт/ключ/нехватка денег; код/тело, без переводов и денежных проводок |
| F06 | `test_validation::test_account_status_matrix` (18) | Все9 сочетаний статусов для OWN и OTHER; блокировка списания, закрытие обоих направлений, разрешённый кредит BLOCKED |
| F07 | `test_validation::test_self_transfer_is_validation_error` |400, без списания и перевода |
| F08 | `test_limits::test_daily_limit_boundaries` (3), `test_failed_transfer_releases_usage` |149999,99/150000 приняты;150000,01 отклонён; FAILED освобождает дневное и месячное использование |
| F09 | `test_limits::test_moscow_midnight_resets_daily_limit` |23:59→00:01 МСК, новый дневной лимит |
| F10 | `test_commission::test_threshold_crossing_charges_only_excess` |90000+20000: комиссия100, остатки889900/110000 |
| F11 | `test_commission::test_minimum_half_up_and_maximum_after_threshold` (4), `test_limits::test_calendar_month_resets_free_threshold` | Минимум30;34,5678→34,57; точная половина30,005→30,01; верхняя граница1500; сброс месячного порога |
| F12 | `test_idempotency::test_same_body_returns_original_without_second_debit` |100 и100,00 нормализованы,200/один ID, одна строка/две проводки |
| F13 | `test_idempotency::test_different_body_returns_409`, `test_key_is_global_across_clients`, `test_expired_key_creates_new_operation` | Конфликт тела и глобальная область; новый ID после собственного createdAt+24ч+1мин, история сохранена |
| F14 | `test_events::test_created_event_and_postings_match_own_transfer` | Очередь привязана до POST; собственные ID/тип/поля/суммы/время, точные проводки |
| F15 | `test_async::test_processing_on_pause_completes_after_resume` |PROCESSING без кредита на паузе, после resume один кредит |
| F16 | `test_async::test_failed_transfer_refunds_amount_and_commission` |100000 подготовки,40000+400, FAILED, REFUND40400 ровно один, нет кредита получателю |
| F17 | `test_notifications::test_completed_notification_has_correct_recipient_and_format`, `test_failed_notification_reports_failure` | Точные русские тексты, комиссия/возврат, отправитель в API и SQL, получатель без уведомлений |
| F18 | `test_turnover::test_turnover_includes_only_completed_on_selected_moscow_date` | Две свободные даты; отбор по completedAt МСК; FAILED/PROCESSING исключены, SQL совпадает |

`tests/test_support.py` содержит3 реальных проверки: таймаут с собственным ID, удаление очереди после события, восстановление часов/обоих потребителей и закрытие PostgreSQL/AMQP после исключения. После очистки выполняется контрольный перевод. `tests_support/` проверяет помощники на управляемых ответах: ожидание, cleanup при ошибке, фильтрацию чужого события, точное числовое JSON и защиту от повторного использования файла отчёта.

Дополнительно проверяется закрытый MF01: неизвестный клиент уведомлений→404 CLIENT_NOT_FOUND; существующий без уведомлений→200[]. По сравнению с [Java](../../../1a-java/jury/reference/traceability.md) общий каталог покрыт; дополнительные варианты комиссии1500, точной половины копейки и MF01 дают64 вместо61 testcase. Ручной эталон покрывает те же бизнес-группы, средства и число шагов различаются.

При одновременном BLOCKED отправителя и CLOSED получателя ТЗ не задаёт приоритет: допускаются оба применимых кода422, но отсутствие движения обязательно. JSON уведомления не обязан содержать clientId: адресат проверяется URL клиента и SQL. Ожидания не берутся из исходников стенда.
