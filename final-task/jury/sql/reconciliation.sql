-- Эталонные сверочные запросы (ключ раздела «SQL-сверка»). Синтаксис H2; через протокол PostgreSQL работают так же.
-- Каждый запрос возвращает строки-нарушения: пустой результат — нарушений нет.

-- С1. Остаток счёта равен сумме проводок (ловит А1 — затёртые списания)
SELECT a.account_number, a.balance,
       SUM(CASE WHEN p.direction = 'CREDIT' THEN p.amount ELSE -p.amount END) AS by_postings
FROM accounts a
JOIN postings p ON p.account_number = a.account_number
GROUP BY a.account_number, a.balance
HAVING a.balance <> SUM(CASE WHEN p.direction = 'CREDIT' THEN p.amount ELSE -p.amount END);

-- С2. Отрицательные остатки. При А1 остаток не уходит в минус — списания «затирают» друг друга, в минус уходит сумма проводок (С1)
SELECT account_number, balance FROM accounts WHERE balance < 0;

-- С3. У завершённого перевода ровно одно зачисление на сумму перевода (ловит А2 — повторное зачисление, А3 — недостача копейки)
SELECT t.transfer_id, t.amount, COUNT(p.posting_id) AS credits, SUM(p.amount) AS credited
FROM transfers t
LEFT JOIN postings p ON p.transfer_id = t.transfer_id AND p.direction = 'CREDIT' AND p.posting_type = 'AMOUNT'
WHERE t.status = 'COMPLETED'
GROUP BY t.transfer_id, t.amount
HAVING COUNT(p.posting_id) <> 1 OR SUM(p.amount) <> t.amount;

-- С4. Неуспешному переводу вернули всё списанное: сумму и комиссию (ловит Р2)
SELECT t.transfer_id, t.amount, t.commission, COALESCE(SUM(p.amount), 0) AS refunded
FROM transfers t
LEFT JOIN postings p ON p.transfer_id = t.transfer_id AND p.posting_type = 'REFUND'
WHERE t.status = 'FAILED'
GROUP BY t.transfer_id, t.amount, t.commission
HAVING COALESCE(SUM(p.amount), 0) <> t.amount + t.commission;

-- С5. Списание по переводу равно сумме и комиссии
SELECT t.transfer_id, t.amount, t.commission, SUM(p.amount) AS debited
FROM transfers t
JOIN postings p ON p.transfer_id = t.transfer_id AND p.direction = 'DEBIT'
GROUP BY t.transfer_id, t.amount, t.commission
HAVING SUM(p.amount) <> t.amount + t.commission;

-- С6. Зависшие переводы: в PROCESSING дольше минуты (ловит Б1 и Н1)
SELECT transfer_id, status, created_at
FROM transfers
WHERE status = 'PROCESSING' AND created_at < DATEADD('MINUTE', -1, CURRENT_TIMESTAMP);

-- С7. Оборот за дату по правилу ТЗ — сравнить с GET /api/v1/reports/turnover?date=... (ловит О5)
SELECT COUNT(*) AS transfers_count, COALESCE(SUM(amount), 0) AS total_amount,
       COALESCE(SUM(commission), 0) AS total_commission
FROM transfers
WHERE status = 'COMPLETED'
  AND CAST((completed_at AT TIME ZONE 'Europe/Moscow') AS DATE) = CURRENT_DATE;
