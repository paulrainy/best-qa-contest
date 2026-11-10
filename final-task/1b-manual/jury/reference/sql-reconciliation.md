# SQL-сверка: запросы, факты, интерпретация

Запросы повторно исполнены на текущем JAR `95af5243…875377`, собственные данные нового полного прогона. Старые результаты корня evidence сохранены как история; актуальные ответы находятся в `evidence/current-build/`.

Только чтение, H2 driver2.5.252, `jdbc:h2:tcp://localhost:19400/mem:stand`, `qa/qa`. Использован стандартный H2 Shell из runtime выдачи; те же SQL можно выполнить в H2-консоли/DBeaver. БД не изменялась. [Данные](evidence/current-build/data-register.md). Пустой ответ означает отсутствие данного нарушения в проверенной области, не отсутствие всех ошибок.

## SQL00-scope — Область своих данных

**Подготовка и назначение:** Нижний/верхний счёт получены нами в M02/EX02. На выделенном стенде между ними только83 своих счёта и49 переводов:46 COMPLETED/3 FAILED. При повторении подставить свои границы или явный IN-список, не копировать числа автора.

```sql
SELECT COUNT(*) AS OWN_ACCOUNTS
FROM accounts
WHERE account_number BETWEEN '40817810000000020061' AND '40817810000000020143';
SELECT status,COUNT(*) AS N
FROM transfers
WHERE from_account BETWEEN '40817810000000020061' AND '40817810000000020143'
GROUP BY status ORDER BY status;
```

**Фактически:** 83/46/3 подтверждают непустую область, без сидовой истории.

[Сырой результат](evidence/current-build/SQL00-scope.txt).

## SQL01-balance — Остаток и проводки

**Подготовка и назначение:** Свои счета, включая отказные кейсы и F16. LEFT JOIN сохраняет счёт без проводок.

```sql
SELECT a.account_number,a.balance,COALESCE(SUM(CASE WHEN p.direction='CREDIT' THEN p.amount ELSE -p.amount END),0) AS BY_POSTINGS
FROM accounts a
LEFT JOIN postings p ON p.account_number=a.account_number
WHERE a.account_number BETWEEN '40817810000000020061' AND '40817810000000020143'
GROUP BY a.account_number,a.balance
HAVING a.balance<>COALESCE(SUM(CASE WHEN p.direction='CREDIT' THEN p.amount ELSE -p.amount END),0);
```

**Фактически:** 0 строк: остатки совпали с проводками. Это не доказывает правильность формулы комиссии/возврата: они могут быть одинаково неверны в двух представлениях.

[Сырой результат](evidence/current-build/SQL01-balance.txt).

## SQL02-negative — Отрицательные остатки

**Подготовка и назначение:** Отдельный денежный инвариант своих счетов.

```sql
SELECT account_number,balance
FROM accounts
WHERE account_number BETWEEN '40817810000000020061' AND '40817810000000020143' AND balance<0;
```

**Фактически:** 0 строк: в области нет отрицательных остатков.

[Сырой результат](evidence/current-build/SQL02-negative.txt).

## SQL03-credit — Одно точное зачисление COMPLETED

**Подготовка и назначение:** Свои transferId, правильный to_account, CREDIT/AMOUNT; OPENING исключён.

```sql
SELECT t.transfer_id,t.amount,COUNT(p.posting_id) AS CREDIT_COUNT,COALESCE(SUM(p.amount),0) AS CREDITED
FROM transfers t
LEFT JOIN postings p ON p.transfer_id=t.transfer_id AND p.account_number=t.to_account AND p.direction='CREDIT' AND p.posting_type='AMOUNT'
WHERE t.status='COMPLETED' AND t.from_account BETWEEN '40817810000000020061' AND '40817810000000020143'
GROUP BY t.transfer_id,t.amount
HAVING COUNT(p.posting_id)<>1 OR COALESCE(SUM(p.amount),0)<>t.amount;
```

**Фактически:** 0 строк: у завершённых ровно одно точное зачисление получателю.

[Сырой результат](evidence/current-build/SQL03-credit.txt).

## SQL04-refund — Полный возврат FAILED

**Подготовка и назначение:** Три своих FAILED: M16 с комиссией400; M17/M18 без комиссии.

```sql
SELECT t.transfer_id,t.amount,t.commission,t.amount+t.commission AS EXPECTED_REFUND,COALESCE(SUM(p.amount),0) AS ACTUAL_REFUND
FROM transfers t
LEFT JOIN postings p ON p.transfer_id=t.transfer_id AND p.account_number=t.from_account AND p.direction='CREDIT' AND p.posting_type='REFUND'
WHERE t.status='FAILED' AND t.from_account BETWEEN '40817810000000020061' AND '40817810000000020143'
GROUP BY t.transfer_id,t.amount,t.commission
HAVING COALESCE(SUM(p.amount),0)<>t.amount+t.commission;
```

**Фактически:** 0 строк: все три FAILED возвращены полностью. Отдельный [срез M16](evidence/current-build/M16-refund.txt) содержит ровно одну REFUND40400 при amount40000/commission400. Отсутствие нарушения дополнено отрицательным контролем SQLC04 ниже.

[Сырой результат](evidence/current-build/SQL04-refund.txt).

## SQL05-debit — Сумма и записанная комиссия списаны

**Подготовка и назначение:** LEFT JOIN/COALESCE видят и отсутствие дебета. Проводки принадлежат from_account.

```sql
SELECT t.transfer_id,t.amount+t.commission AS EXPECTED_DEBIT,COALESCE(SUM(p.amount),0) AS ACTUAL_DEBIT
FROM transfers t
LEFT JOIN postings p ON p.transfer_id=t.transfer_id AND p.account_number=t.from_account AND p.direction='DEBIT'
WHERE t.from_account BETWEEN '40817810000000020061' AND '40817810000000020143'
GROUP BY t.transfer_id,t.amount,t.commission
HAVING COALESCE(SUM(p.amount),0)<>t.amount+t.commission;
```

**Фактически:** 0 строк: суммы согласованы с amount+commission записи. Бизнес-формула M10 проверяется отдельно.

[Сырой результат](evidence/current-build/SQL05-debit.txt).

## SQL06-pending — PROCESSING старше10с

**Подготовка и назначение:** Часы реальные, оба RUNNING. При сдвинутых часах заменить CURRENT_TIMESTAMP явным временем стенда.

```sql
SELECT transfer_id,status,created_at
FROM transfers
WHERE from_account BETWEEN '40817810000000020061' AND '40817810000000020143' AND status='PROCESSING' AND created_at<DATEADD('SECOND',-10,CURRENT_TIMESTAMP);
```

**Фактически:** 0 строк после очистки. В EX01 та же логика нашла намеренно приостановленный перевод возраста37с; после resume он завершился. Это диагностический отбор, не автоматический баг.

[Сырой результат](evidence/current-build/SQL06-pending.txt).

## SQL07-turnover — Оборот по completed_at МСК

**Подготовка и назначение:** Собственные данные двух свободных дат M18; этот срез после завершения400.

```sql
SELECT CAST((completed_at AT TIME ZONE 'Europe/Moscow') AS DATE) AS DAY_MSK,COUNT(*) AS N,COALESCE(SUM(amount),0) AS TOTAL,COALESCE(SUM(commission),0) AS FEE
FROM transfers
WHERE from_account BETWEEN '40817810000000020061' AND '40817810000000020143' AND status='COMPLETED' AND completed_at>=TIMESTAMP WITH TIME ZONE '2051-07-10 00:00:00+03' AND completed_at<TIMESTAMP WITH TIME ZONE '2051-07-12 00:00:00+03'
GROUP BY DAY_MSK ORDER BY DAY_MSK;
```

**Фактически:** D=1/100/0,D+1=2/600/0. Ранний срез до resume400 был1/100/0 и1/200/0; каждый совпал с API в свой момент.

[Сырой результат](evidence/current-build/SQL07-turnover.txt).

## Способность обнаруживать нарушения

Контроли VALUES/CTE ниже — синтетические данные только в памяти read-only запроса. Это не реальные дефекты и не изменения БД. Логика JOIN/HAVING соответствует основной проверке; контроли не заменяют исполнение основных SQL.

### SQLC01-balance

```sql
WITH a(n,balance) AS (VALUES('control',101.00)), p(n,direction,amount) AS (VALUES('control','CREDIT',100.00)) SELECT a.n,a.balance,COALESCE(SUM(CASE WHEN p.direction='CREDIT' THEN p.amount ELSE -p.amount END),0) AS BY_POSTINGS FROM a LEFT JOIN p ON p.n=a.n GROUP BY a.n,a.balance HAVING a.balance<>COALESCE(SUM(CASE WHEN p.direction='CREDIT' THEN p.amount ELSE -p.amount END),0);
```

101 против100:1 строка нарушения. [Вывод](evidence/current-build/SQLC01-balance.txt).

### SQLC02-negative

```sql
WITH a(n,balance) AS (VALUES('negative',-1.00),('zero',0.00)) SELECT n,balance FROM a WHERE balance<0;
```

Найден -1;0 не помечен. [Вывод](evidence/current-build/SQLC02-negative.txt).

### SQLC03-credit

```sql
WITH t(id,to_account,amount,status) AS (VALUES('short','B',100.00,'COMPLETED'),('double','B',100.00,'COMPLETED'),('missing','B',100.00,'COMPLETED')), p(posting_id,transfer_id,account_number,direction,posting_type,amount) AS (VALUES(1,'short','B','CREDIT','AMOUNT',99.00),(2,'double','B','CREDIT','AMOUNT',50.00),(3,'double','B','CREDIT','AMOUNT',50.00)) SELECT t.id,t.amount,COUNT(p.posting_id) AS CREDIT_COUNT,COALESCE(SUM(p.amount),0) AS CREDITED FROM t LEFT JOIN p ON p.transfer_id=t.id AND p.account_number=t.to_account AND p.direction='CREDIT' AND p.posting_type='AMOUNT' WHERE t.status='COMPLETED' GROUP BY t.id,t.amount HAVING COUNT(p.posting_id)<>1 OR COALESCE(SUM(p.amount),0)<>t.amount;
```

Найдены3 нарушения: short99 вместо100; double2 кредита общей суммой100; missing0 кредитов. [Вывод](evidence/current-build/SQLC03-credit.txt).

### SQLC04-refund

```sql
WITH t(id,from_account,amount,commission,status) AS (VALUES('short','A',40000.00,400.00,'FAILED'),('missing','A',100.00,0.00,'FAILED'),('double','A',100.00,0.00,'FAILED'),('correct','A',40000.00,400.00,'FAILED')), p(transfer_id,account_number,direction,posting_type,amount) AS (VALUES('short','A','CREDIT','REFUND',40000.00),('double','A','CREDIT','REFUND',100.00),('double','A','CREDIT','REFUND',100.00),('correct','A','CREDIT','REFUND',40400.00)) SELECT t.id,t.amount+t.commission AS EXPECTED_REFUND,COALESCE(SUM(p.amount),0) AS ACTUAL_REFUND FROM t LEFT JOIN p ON p.transfer_id=t.id AND p.account_number=t.from_account AND p.direction='CREDIT' AND p.posting_type='REFUND' WHERE t.status='FAILED' GROUP BY t.id,t.amount,t.commission HAVING COALESCE(SUM(p.amount),0)<>t.amount+t.commission ORDER BY t.id;
```

Найдены3 нарушения: short40000 вместо40400; missing0 вместо100; double200 вместо100. Корректный полный возврат40400 не помечен. [Вывод](evidence/current-build/SQLC04-refund.txt).

### SQLC05-debit

```sql
WITH t(id,from_account,amount,commission) AS (VALUES('short','A',100.00,30.00),('missing','A',100.00,0.00)), p(transfer_id,account_number,direction,amount) AS (VALUES('short','A','DEBIT',100.00)) SELECT t.id,t.amount+t.commission AS EXPECTED_DEBIT,COALESCE(SUM(p.amount),0) AS ACTUAL_DEBIT FROM t LEFT JOIN p ON p.transfer_id=t.id AND p.account_number=t.from_account AND p.direction='DEBIT' GROUP BY t.id,t.amount,t.commission HAVING COALESCE(SUM(p.amount),0)<>t.amount+t.commission;
```

Найдены оба: short100 вместо130; missing0 вместо100. [Вывод](evidence/current-build/SQLC05-debit.txt).

SQL04 проверен на трёх корректных реальных FAILED и на синтетических нарушениях SQLC04. SQL06 проверен на [намеренной паузе EX01](evidence/current-build/EX01-pending-sql.txt) и после восстановления. SQL07 проверен на COMPLETED/FAILED/PROCESSING и переносе даты в [M18](evidence/current-build/M18-before-cleanup-sql.txt). Пустые результаты не приняты без контроля чувствительности.

## Повтор порядка и финальный срез

Обычные карточки повторены без reset в порядке M12→M10→M07→M06→M05→M04→M03→M02. M04: верхняя граница300000; M05: неизвестный получатель; M06: OWN с заблокированным отправителем и OTHER с заблокированным получателем. Остальные параметры полностью исполнены в основной сессии, их второе полное исполнение не заявляется. Все выбранные факты совпали с ожидаемыми.

[SQL-reorder](evidence/current-build/SQL-reorder.txt) подтверждает по одной строке каждого из7 новых принятых ключей и ровно2 проводки по повторённому ключу M12. Отказные ключи не создали переводов.

[Финальная сверка](evidence/current-build/SQL-final-reconciliation.txt) повторяет SQL00–07 с верхней границей `40817810000000020161`:101 счёт,56 переводов (53 COMPLETED/3 FAILED). Денежные запросы и PROCESSING дали0 нарушений; оборот остался1/100 и2/600. Эта область шире исходных83 счетов; срезы не смешиваются.
