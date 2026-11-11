"""Подготовка кольца OTHER из публичного CSV; без записи в БД."""
import argparse
import csv
import io
import math
from decimal import Decimal
from pathlib import Path

try:
    from .common import request
except ImportError:
    from common import request


def select_pairs(accounts, count=2000, max_requests=100000):
    if count < 2 or max_requests < 1:
        raise ValueError('Нужны хотя бы два клиента и положительный бюджет')
    # CSV читается по кругу; каждый источник используется не более ceil(N/count) раз.
    budget = Decimal(math.ceil(max_requests / count)) * Decimal('100.00')
    if budget > Decimal('100000.00'):
        raise ValueError('Бюджет исчерпает бесплатный месячный порог или дневной лимит')
    clients = {}
    for account in accounts:
        if account['status'] == 'ACTIVE' and Decimal(account['balance']) >= budget:
            clients.setdefault(account['client_id'], account)
    selected = [clients[key] for key in sorted(clients)][:count]
    if len(selected) != count:
        raise ValueError(f'Нужны {count} разных активных клиентов с остатком ≥ {budget}; найдено {len(selected)}')
    return [dict(fromAccount=source['account_number'], toAccount=selected[(i + 1) % count]['account_number'],
                 fromClient=source['client_id'], toClient=selected[(i + 1) % count]['client_id'])
            for i, source in enumerate(selected)]


def prepare(base, output):
    accounts = list(csv.DictReader(io.StringIO(request(base, '/api/test/accounts.csv'))))
    pairs = select_pairs(accounts)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['fromAccount', 'toAccount', 'fromClient', 'toClient'])
        writer.writeheader()
        writer.writerows(pairs)
    return pairs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://localhost:18400')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(f'Подготовлено {len(prepare(args.base_url, args.output))} пар OTHER')
