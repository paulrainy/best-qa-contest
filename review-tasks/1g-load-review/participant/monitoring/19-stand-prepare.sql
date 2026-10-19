-- Подготовка стенда EFR-NT к тесту стабильности 10.11.2026 (старт прогрева 22:00 МСК)
-- БД efr на efr-nt-db01, PostgreSQL 15. Выполняет инженер НТ под efr_admin.

-- 1. Ночью перед тестом, по расписанию, с 01:00 МСК: перестроить раздутые таблицы
--    (после прошлого теста client_documents вырос в 2,5 раза). Закончить до 05:00.
VACUUM FULL client_documents;
ANALYZE client_documents;

-- 2. За 10 минут до старта прогрева: свежая статистика по таблицам, которые пишет тест
VACUUM (ANALYZE) operations;
VACUUM (ANALYZE) deposits;
VACUUM (ANALYZE) tasks;

-- 3. Объём критичных таблиц против прома (выгрузка из прома от 01.11.2026)
WITH prod(table_name, prod_rows) AS (
    VALUES ('clients', 12000000),
           ('client_documents', 18000000),
           ('accounts', 30000000),
           ('deposits', 6000000),
           ('operations', 450000000)
),
nt AS (
    SELECT relname AS table_name, n_live_tup AS nt_rows
    FROM pg_stat_user_tables
    WHERE schemaname = 'efr'
)
SELECT p.table_name,
       p.prod_rows,
       nt.nt_rows,
       round(nt.nt_rows::numeric / p.prod_rows, 2) AS share,
       nt.nt_rows >= p.prod_rows * 0.7 AS ok
FROM prod p
JOIN nt USING (table_name)
ORDER BY p.table_name;

-- 4. Чтобы автовакуум не влиял на результаты, отключаем его на время теста на самой большой таблице
ALTER TABLE operations SET (autovacuum_enabled = off);

-- 5. Очередь задач для ОП-05: задачи в статусе NEW
SELECT count(*) AS new_tasks,
       count(*) >= 1000 AS ok
FROM tasks
WHERE status = 'NEW';

-- 6. Проверка, что efr-api пишет операции: записи за последние 10 минут смоук-прогона
SELECT count(*) AS written,
       count(*) FILTER (WHERE status IS NULL OR amount IS NULL OR branch_id IS NULL) AS incomplete
FROM operations
WHERE created_at >= now() - interval '10 minutes';
