from contextlib import AbstractContextManager

import psycopg
from psycopg.rows import dict_row


class Db(AbstractContextManager):
    def __init__(self, config, *, connect=psycopg.connect):
        self.config = config
        self.connect = connect
        self.connection = None

    def __enter__(self):
        try:
            self.connection = self.connect(**self.config.database, sslmode="disable",
                                           autocommit=True, prepare_threshold=None,
                                           row_factory=dict_row)
        except psycopg.Error as exc:
            endpoint = self.config.database
            raise RuntimeError(f"БД недоступна {endpoint['host']}:{endpoint['port']}/{endpoint['dbname']}: {exc}") from exc
        return self

    def __exit__(self, *args):
        self.connection.close()

    def select(self, sql, params=()):
        if not sql.lstrip().upper().startswith("SELECT ") or ";" in sql:
            raise ValueError("Разрешён один SELECT с параметрами")
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return [{key.lower(): value for key, value in row.items()} for row in cursor.fetchall()]

    def postings(self, transfer_id):
        return self.select("SELECT * FROM postings WHERE transfer_id = %s ORDER BY posting_id", (transfer_id,))
