-- Дополнительные сверки жюри, без баллов. Синтаксис H2; через протокол PostgreSQL работают так же.
-- Каждый запрос возвращает строки-нарушения: пустой результат — нарушений нет.

-- С1. Остаток счёта равен сумме проводок; счёт без проводок тоже попадает в сверку
SELECT a.account_number, a.balance,
       COALESCE(SUM(CASE WHEN p.direction = 'CREDIT' THEN p.amount ELSE -p.amount END), 0) AS by_postings
FROM accounts a
LEFT JOIN postings p ON p.account_number = a.account_number
GROUP BY a.account_number, a.balance
HAVING a.balance <> COALESCE(SUM(CASE WHEN p.direction = 'CREDIT' THEN p.amount ELSE -p.amount END), 0);

-- С2. Отрицательные остатки (отдельно от сверки проводок).
SELECT account_number, balance FROM accounts WHERE balance < 0;

-- С3. У завершённого перевода ровно одно зачисление на сумму перевода
SELECT t.transfer_id, t.amount, COUNT(p.posting_id) AS credits, SUM(p.amount) AS credited
FROM transfers t
LEFT JOIN postings p ON p.transfer_id = t.transfer_id AND p.direction = 'CREDIT' AND p.posting_type = 'AMOUNT'
WHERE t.status = 'COMPLETED'
GROUP BY t.transfer_id, t.amount
HAVING COUNT(p.posting_id) <> 1 OR SUM(p.amount) <> t.amount;

-- С4. Неуспешному переводу вернули всё списанное: сумму и комиссию
SELECT t.transfer_id, t.amount, t.commission, COALESCE(SUM(p.amount), 0) AS refunded
FROM transfers t
LEFT JOIN postings p ON p.transfer_id = t.transfer_id AND p.posting_type = 'REFUND'
WHERE t.status = 'FAILED'
GROUP BY t.transfer_id, t.amount, t.commission
HAVING COALESCE(SUM(p.amount), 0) <> t.amount + t.commission;

-- С5. Списание по переводу равно сумме и комиссии; перевод без списания тоже нарушение
SELECT t.transfer_id, t.amount, t.commission, COALESCE(SUM(p.amount), 0) AS debited
FROM transfers t
LEFT JOIN postings p ON p.transfer_id = t.transfer_id AND p.direction = 'DEBIT'
GROUP BY t.transfer_id, t.amount, t.commission
HAVING COALESCE(SUM(p.amount), 0) <> t.amount + t.commission;

-- С6. Длительное PROCESSING по реальным часам БД; не применять при сдвинутых тестовых часах
SELECT transfer_id, status, created_at
FROM transfers
WHERE status = 'PROCESSING' AND created_at < DATEADD('MINUTE', -1, CURRENT_TIMESTAMP);

-- С7. Подставить те же сутки МСК, что переданы API; пример 2027-03-15. Оборот по правилу ТЗ — сравнить с GET /api/v1/reports/turnover?date=...
-- Границы заданы со смещением +03:00: CAST(... AS DATE) в H2 зависит от часового пояса сервера.
SELECT COUNT(*) AS transfers_count, COALESCE(SUM(amount), 0) AS total_amount,
       COALESCE(SUM(commission), 0) AS total_commission
FROM transfers
WHERE status = 'COMPLETED'
  AND completed_at >= TIMESTAMP WITH TIME ZONE '2027-03-15 00:00:00+03:00'
  AND completed_at <  TIMESTAMP WITH TIME ZONE '2027-03-16 00:00:00+03:00';
