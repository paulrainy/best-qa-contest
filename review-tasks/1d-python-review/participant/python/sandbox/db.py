"""База сервиса брокерского обслуживания: SQLite-файл, который пересоздаётся при каждом запуске песочницы."""
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

SCHEMA = """
CREATE TABLE backoffice_user (
    login    TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    name     TEXT NOT NULL
);

CREATE TABLE client (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    login         TEXT NOT NULL UNIQUE,
    password      TEXT NOT NULL,
    last_name     TEXT NOT NULL,
    first_name    TEXT NOT NULL,
    middle_name   TEXT,
    phone         TEXT NOT NULL,
    tariff        TEXT NOT NULL,
    status        TEXT NOT NULL,
    failed_logins INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);

CREATE TABLE agreement (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    number    TEXT NOT NULL UNIQUE,
    type      TEXT NOT NULL,
    status    TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    closed_at TEXT
);

CREATE TABLE account (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    agreement_id INTEGER NOT NULL,
    currency     TEXT NOT NULL,
    balance      NUMERIC NOT NULL
);

CREATE TABLE money_order (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    agreement_id INTEGER NOT NULL,
    type         TEXT NOT NULL,
    amount       NUMERIC NOT NULL,
    commission   NUMERIC NOT NULL DEFAULT 0,
    status       TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    executed_at  TEXT
);

CREATE TABLE tax_report (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id     INTEGER NOT NULL,
    tax_period    INTEGER NOT NULL,
    status        TEXT NOT NULL,
    request_id    TEXT NOT NULL,
    file_name     TEXT,
    registered_at TEXT NOT NULL
);

CREATE TABLE incoming_payment (
    payment_id  TEXT PRIMARY KEY,
    order_id    INTEGER NOT NULL,
    received_at TEXT NOT NULL
);

CREATE TABLE tariff_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id  INTEGER NOT NULL,
    old_tariff TEXT NOT NULL,
    new_tariff TEXT NOT NULL,
    changed_at TEXT NOT NULL
);
"""

# Клиенты, которые есть на стенде всегда. Пароль у всех — Client#Playground.
SEED_CLIENTS = [
    ('ivanova_ma', 'Иванова', 'Мария', 'Андреевна', '+79161234501', 'INVESTOR'),
    ('petrov_sv', 'Петров', 'Сергей', 'Викторович', '+79161234502', 'TRADER'),
    ('smirnov_ap', 'Смирнов', 'Алексей', 'Павлович', '+79161234503', 'INVESTOR'),
    ('kuznetsova_ei', 'Кузнецова', 'Елена', 'Игоревна', '+79161234504', 'INVESTOR'),
    ('volkov_dn', 'Волков', 'Дмитрий', 'Николаевич', '+79161234505', 'TRADER'),
    ('inv_client_lock', 'Соколов', 'Игорь', 'Олегович', '+79161234506', 'INVESTOR'),
]
SEED_PASSWORD = 'Client#Playground'


def now() -> str:
    """Местное время сервера — так время пишет и настоящий сервис."""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


class Database:
    """Одно соединение на весь сервис, запросы под общей блокировкой."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        for suffix in ('', '-wal', '-shm'):
            Path(str(path) + suffix).unlink(missing_ok=True)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None, timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.executescript(SCHEMA)
        self._seed()

    def all(self, sql: str, *args) -> list:
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql, args).fetchall()]

    def one(self, sql: str, *args):
        rows = self.all(sql, *args)
        return rows[0] if rows else None

    def execute(self, sql: str, *args) -> int:
        with self.lock:
            return self.conn.execute(sql, args).lastrowid

    def _seed(self):
        self.execute("INSERT INTO backoffice_user VALUES ('bo_operator1', 'Oper1#Playground', 'Операционист бэк-офиса')")
        opened = (datetime.now() - timedelta(days=700)).strftime('%Y-%m-%d %H:%M:%S')
        for i, (login, last, first, middle, phone, tariff) in enumerate(SEED_CLIENTS, start=1):
            client_id = self.execute(
                'INSERT INTO client (login, password, last_name, first_name, middle_name, phone, tariff, status, created_at)'
                " VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)",
                login, SEED_PASSWORD, last, first, middle, phone, tariff, opened)
            agreement_id = self.execute(
                "INSERT INTO agreement (client_id, number, type, status, opened_at) VALUES (?, ?, 'BROKER', 'ACTIVE', ?)",
                client_id, f'БД-{1000000 + i:07d}', opened)
            self.execute("INSERT INTO account (agreement_id, currency, balance) VALUES (?, 'RUB', ?)",
                         agreement_id, 150000 + i * 25000)
            for days_ago, amount in ((300, 100000), (120, 50000), (30, 25000)):
                created = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M:%S')
                self.execute(
                    'INSERT INTO money_order (agreement_id, type, amount, status, created_at, executed_at)'
                    " VALUES (?, 'REFILL', ?, 'EXECUTED', ?, ?)",
                    agreement_id, amount, created, created)
