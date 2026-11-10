# Трассировка F01–F18

[Контракт](../../../jury/source/spec.md), [общий каталог](../../../jury/coverage-catalog.md). Пути классов ниже — `src/test/java/reference/`. Варианты параметризованных методов входят в [точный каталог XML](../../../jury/tools/reference-test-catalog.json); всего 61 testcase, включая 3 проверки поддержки. Это состав эталона, а не квота для участника.

| ID | Методы | Проверяемый результат |
| --- | --- | --- |
| F01 | `TransferTest.readinessAndReadOnlyConnections` | health UP, AMQP, SELECT H2, запрет UPDATE |
| F02 | `TransferTest.ownTransferCompletesWithExactBalances` | OWN, нулевая комиссия, точные остатки и две проводки |
| F03 | `TransferTest.otherTransferWithinFreeThreshold` | OTHER, нулевая комиссия, сохранение копейки |
| F04 | `ValidationTest.amountBoundaries` (5 вариантов) | 9,99 и 300 000,01/10,001 отклонены без движения; 10,00 и 300 000,00 OWN приняты |
| F05 | `ValidationTest.invalidPayloadLeavesMoneyUntouched` (7), `unknownAccountIs404` (2), `invalidKeyIs400` (2); `TransferTest.insufficientFundsLeaveNoTransfer` | Структурные ошибки, неизвестные счета, ключ, недостаток денег; код/тело и отсутствие побочных переводов |
| F06 | `ValidationTest.accountStatusMatrix` (18) | Все сочетания ACTIVE/BLOCKED/CLOSED для OWN и OTHER, деньги при отказе не меняются |
| F07 | `ValidationTest.selfTransferIsValidationError` | 400 VALIDATION_ERROR, без перевода и списания |
| F08 | `LimitsTest.dailyLimitBoundaries` (3), `failedTransferReleasesUsage` | 149 999,99 / 150 000,00 приняты, 150 000,01 отклонён; FAILED освобождает использование. Бесплатный порог исчерпан предыдущим днём, F10 не влияет |
| F09 | `LimitsTest.moscowMidnightResetsDailyLimit` | 23:59 → 00:01 МСК обнуляет дневное использование |
| F10 | `CommissionTest.thresholdCrossingChargesOnlyExcess` | Требование комиссии 100,00 после 90 000 + 20 000; обычная проверка корректного поведения |
| F11 | `CommissionTest.minimumAndHalfUpAfterThreshold` (2), `LimitsTest.calendarMonthResetsFreeThreshold` | Минимум 30,00; 34,5678 → 34,57; новый месяц обнуляет бесплатный порог |
| F12 | `IdempotencyTest.sameBodyReturnsOriginalWithoutSecondDebit` | 100 и 100,00 равнозначны; один transferId, одна строка и две проводки, одно списание |
| F13 | `IdempotencyTest.differentBodyReturns409`, `keyIsGlobalAcrossClients`, `expiredKeyCreatesNewOperation` | Конфликт до истечения; область всех клиентов; новая операция через 24 ч, история сохранена |
| F14 | `EventsTest.createdEventAndPostingsMatchOwnTransfer` | Подписка до запроса, eventId/transferId/поля/денежные суммы, проводки по своему ID |
| F15 | `AsyncTest.processingOnPauseCompletesAfterResume` | PROCESSING без зачисления на паузе; после resume — COMPLETED и одно зачисление |
| F16 | `AsyncTest.failedTransferRefundsAmountAndCommission` | Изолированная подготовка 100 000 + 40 000, комиссия 400, FAILED, требование полного возврата; обычная проверка корректного поведения |
| F17 | `NotificationsTest.completedNotificationHasCorrectRecipientAndFormat`, `failedNotificationReportsFailure` | Уведомление отправителю, точные формат/счета/статус, ожидание по transferId |
| F18 | `TurnoverTest.turnoverIncludesOnlyCompletedOnSelectedMoscowDate` | Две свободные даты, выбор по completedAt МСК, исключены FAILED/PROCESSING и соседняя дата |

`SupportTest`: ограниченные таймауты с transferId; временная очередь привязана до действия и удалена; после исключения восстановлены часы и оба потребителя. SQL параметризован и использует собственные ID; подключения закрываются. Глобальные сценарии выполняются последовательно, scope восстанавливает исходные настройки, обычные сценарии не делают reset.

F10/F16 входят в полный зелёный набор. Нет разрешённых падений, skip/xfail и фильтрации known_issue; анализатор отвергает любое падение и неполный состав.
