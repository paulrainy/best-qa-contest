"""CSV для сценариев 1c. Запуск из папки tools: .venv/bin/python ../1c-load-review/jury/source/scripts/make_data.py

Пишет participant/scripts/data/ и, где данные исправленной версии отличаются, jury/fixed/scripts/data/.
Данные вымышленные, генерация детерминирована (seed).
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

TASK = Path(__file__).resolve().parents[3]
OUT = TASK / 'participant' / 'scripts' / 'data'
FIXED = TASK / 'jury' / 'fixed' / 'scripts' / 'data'

# Учётки менеджеров: у каждого сценария свой диапазон, вдвое больше потоков (методика 5.1)
USERS = {'op01': 84, 'op02': 66, 'op03': 16, 'op04': 32, 'op06': 20, 'op07': 16, 'op10': 10}
PASSWORD = 'Nt-2026-Load'

SURNAMES = ['Иванов', 'Смирнов', 'Кузнецов', 'Попов', 'Васильев', 'Петров', 'Соколов', 'Михайлов', 'Новиков',
            'Фёдоров', 'Морозов', 'Волков', 'Алексеев', 'Лебедев', 'Семёнов', 'Егоров', 'Павлов', 'Козлов']
NAMES = ['Александр', 'Дмитрий', 'Максим', 'Сергей', 'Андрей', 'Алексей', 'Артём', 'Илья', 'Кирилл', 'Михаил']
PATRONYMICS = ['Александрович', 'Дмитриевич', 'Сергеевич', 'Андреевич', 'Алексеевич', 'Михайлович',
               'Николаевич', 'Владимирович', 'Игоревич', 'Олегович']


def write(path: Path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(header)
        writer.writerows(rows)


def users():
    first = 1
    for scenario, count in USERS.items():
        rows = [(f'nt_mgr{n:03d}', PASSWORD) for n in range(first, first + count)]
        write(OUT / f'users_{scenario}.csv', ['login', 'password'], rows)
        first += count
    assert first - 1 <= 300


def controllers():
    rows = [(f'nt_ctl{n:02d}', PASSWORD) for n in range(1, 13)]
    write(OUT / 'controllers.csv', ['login', 'password'], rows[:6])  # дефект 05.1: учёток на 100 %, не на 200 %
    write(FIXED / 'controllers.csv', ['login', 'password'], rows)


def passport(rng, used):
    while True:
        value = f'{rng.randint(4500, 4599)} {rng.randint(100000, 999999)}'
        if value not in used:
            used.add(value)
            return value


def clients(rng, used):
    rows = []
    for n in range(50_000):
        client_id = f'CL{rng.randint(10_000_000, 99_999_999)}{n:05d}'
        rows.append((client_id, passport(rng, used)))
    write(OUT / 'clients.csv', ['clientId', 'passport'], rows)


def new_clients(rng, used):
    rows = []
    for _ in range(14_000):
        birth = date(1950, 1, 1) + timedelta(days=rng.randint(0, 365 * 55))
        rows.append((rng.choice(SURNAMES), rng.choice(NAMES), rng.choice(PATRONYMICS), birth.isoformat(),
                     passport(rng, used), '+7 9' + ''.join(str(rng.randint(0, 9)) for _ in range(9))))
    header = ['lastName', 'firstName', 'middleName', 'birthDate', 'passport', 'phone']
    write(OUT / 'new_clients.csv', header, rows[:5_000])  # дефект 03.1: нужно не меньше 13 824
    write(FIXED / 'new_clients.csv', header, rows)


def accounts(rng):
    rows = []
    for n in range(20_000):
        rows.append((f'AC{n + 1:07d}', f'40817810{rng.randint(10**11, 10**12 - 1)}'))
    write(OUT / 'accounts.csv', ['accountId', 'accountNumber'], rows)


def deposits(rng):
    rows = [(f'DP{n + 1:08d}',) for n in rng.sample(range(10_000_000), 18_000)]
    write(OUT / 'deposits_to_close.csv', ['depositId'], rows)


def branches():
    write(OUT / 'branches.csv', ['branch_id'], [(n,) for n in range(101, 221)])


if __name__ == '__main__':
    generator, used_passports = random.Random(1911), set()
    users()
    controllers()
    clients(generator, used_passports)
    new_clients(generator, used_passports)
    accounts(generator)
    deposits(generator)
    branches()
    print('Готово:', ', '.join(sorted(p.name for p in OUT.glob('*.csv'))))
