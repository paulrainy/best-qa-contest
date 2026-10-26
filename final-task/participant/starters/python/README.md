# Каркас автотестов на Python

pytest + requests + pika (клиент RabbitMQ) + psycopg (БД стенда по протоколу PostgreSQL). Python 3.10+.

```
python -m venv .venv
.venv\Scripts\activate          # Windows; на Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
pytest
```

Стенд должен быть запущен. Адреса — в `stand.ini`.

- `stand.py` — подключения к API, брокеру и БД, подписка на события брокера.
- `tests/test_smoke.py` — пример: перевод между своими счетами, событие `TransferCreated`, проводки в БД.

Каркас — только отправная точка. Структуру, библиотеки и подход выбираете сами.
