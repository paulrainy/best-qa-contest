-- Артефакты теста стабильности 10.11.2026 и данные для следующего прогона
-- БД efr на efr-nt-db01, PostgreSQL 15, расширение pg_profile в схеме profile.
-- Тест: прогрев 22:00–22:10 МСК, измерение 22:10–06:10 МСК.

-- 1. Ручной снимок в конце измерения (в начале снят так же в 22:10)
SELECT profile.take_sample();

-- 2. Снимки PWR за интервал теста
SELECT sample, sample_time
FROM profile.show_samples()
WHERE sample_time >= '2026-11-10 22:10:00+03'
  AND sample_time <= '2026-11-11 06:10:00+03'
ORDER BY sample;

-- 3. Отчёт PWR между первым и последним снимком из запроса 2
SELECT profile.get_report(:start_sample, :end_sample, 'Стабильность ЕФР 2026.11');

-- 4. Ошибки из лога БД. Сервер в UTC: тест 19:00–03:10 UTC, это файлы за 10 и 11 ноября.
--    Читаем файлы целиком: третий аргумент pg_read_file — длина в байтах, а не число строк.
SELECT line
FROM unnest(ARRAY['log/postgresql-2026-11-10.log', 'log/postgresql-2026-11-11.log']) AS f(name),
     regexp_split_to_table(pg_read_file(f.name), E'\n') AS line
WHERE line ~ '(ERROR|FATAL|PANIC):';

-- 5. Выборка клиентов для clients.csv (ОП-01, ОП-02, ОП-10): 50 000 случайных
\copy (SELECT c.client_id AS "clientId", d.series || ' ' || d.number AS passport FROM efr.clients c JOIN efr.client_documents d ON d.client_id = c.client_id WHERE d.doc_type = 'PASSPORT_RF' AND d.is_valid AND c.status = 'ACTIVE' AND c.deleted = false ORDER BY random() LIMIT 50000) TO 'clients.csv' WITH (FORMAT csv, HEADER)
