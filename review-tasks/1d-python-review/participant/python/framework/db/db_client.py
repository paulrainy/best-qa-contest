"""Подключение к БД сервиса. Строки возвращаются словарями: {'колонка': значение}."""
import logging
import sqlite3

import allure

from framework.config import Config

log = logging.getLogger('db')


class DbClient:
    _connections = {}

    def __init__(self, path=None):
        path = str(path or Config.db_path())
        if path not in DbClient._connections:
            # одно соединение на файл БД на весь прогон
            conn = sqlite3.connect(path, check_same_thread=False, timeout=10)
            conn.row_factory = sqlite3.Row
            DbClient._connections[path] = conn
        self.conn = DbClient._connections[path]

    def query(self, sql: str, *args, fetch_one: bool = False):
        rows = [dict(r) for r in self.conn.execute(sql, args).fetchall()]
        log.info('%s %s -> %s', ' '.join(sql.split()), args, rows[:5])
        allure.attach(f'{sql.strip()}\n\nПараметры: {args}\n\nРезультат: {rows[:20]}', name='SQL',
                      attachment_type=allure.attachment_type.TEXT)
        if fetch_one:
            return rows[0] if rows else None
        return rows

    def execute(self, sql: str, *args) -> int:
        cursor = self.conn.execute(sql, args)
        self.conn.commit()
        log.info('%s %s -> изменено строк: %s', ' '.join(sql.split()), args, cursor.rowcount)
        return cursor.rowcount
