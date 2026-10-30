#!/usr/bin/env python3
"""Приёмка правильных веток 900401–900420. Только для жюри; сбрасывает стенд.

Запуск: python3 sandbox_check.py [http://localhost:18081/efr/]
Не исполняет намеренно неверные ожидания participant/testcases.xlsx.
"""
import json
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta


class Stand:
    def __init__(self, url):
        self.url = url.rstrip('/') + '/api/'
        self.token = ''

    def request(self, path, body):
        request = urllib.request.Request(self.url + path, json.dumps(body).encode(),
            {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.token})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise AssertionError(f'{error.code}: {json.load(error)["error"]}') from error

    def login(self, user='tst_oper01'):
        self.token = self.request('login', {'login': user, 'password': 'Test123!'})['token']

    def reset(self):
        self.login()
        self.request('reset', {})
        self.login()
        self.today = date.fromisoformat(self.call('bootstrap')['today'])

    def call(self, action, **data):
        return self.request('action', {'action': action, **data})

    def client(self, **extra):
        values = dict(entity='client', surname='Проверочный', name='Иван', patronymic='Иванович',
            passport='4500999001', birthDate='1990-01-01', fatca='NON_US', dbo='FULL')
        values.update(extra)
        return self.call('prepare', **values)

    def product(self, c, kind='Текущий', amount='0', **extra):
        values = dict(entity='product', clientId=c['id'], type='account', kind=kind, amount=amount)
        values.update(extra)
        return self.call('prepare', **values)

    def deposit(self, c, amount='100000', days=30, kind='Надёжный'):
        return self.product(c, kind, amount, type='deposit', opened=str(self.today-timedelta(days=days)), term='181')

    def opening(self, c, amount='1000', kind='Пополняемый', **extra):
        values = dict(clientId=c['id'], amount=amount, kind=kind, term='181', funding='Наличными через кассу')
        values.update(extra)
        return self.call('open-deposit', **values)

    def paper(self, op, **extra):
        self.call('update-operation', id=op['id'], bankOfficer='Ирина Соловьёва', **extra)
        self.call('print', id=op['id'])
        return self.call('sign', id=op['id'])

    def electronic(self, op):
        self.call('send-sms', id=op['id'])
        messages = self.call('sms')['messages']
        return self.call('sign', id=op['id'], code=messages[-1]['code'])

    def decide(self, op, approve=True):
        self.login('tst_contr01')
        self.call('take', id=op['id'])
        result = self.call('decide', id=op['id'], approve=approve, comment='Решение по проверке')
        self.login()
        return result

    def form(self, **extra):
        values = dict(surname='Новый', name='Павел', patronymic='Ильич', birthDate='1991-01-01',
            gender='Мужской', passport='4500999002', issued='2015-01-01', division='770-001',
            issuer='МВД', phone='+79000000001', address='Москва', citizenship='РФ')
        values.update(extra)
        return self.call('create-client', **values)


def fails(fn, text):
    try:
        fn()
    except AssertionError as error:
        assert text in str(error), str(error)
    else:
        raise AssertionError('Ожидался отказ: ' + text)


def case(s, n):
    c = s.client()
    if n == 401:
        c = s.client(id=c['id'], fatca='NONE')
        fails(lambda: s.opening(c), 'не определён FATCA')
        assert s.call('set-fatca', clientId=c['id'], fatca='NON_US')['fatca'] == 'NON_US'
    elif n == 402:
        a = s.product(c, amount='10000')
        op = s.opening(c, '10000', 'Надёжный', funding='Со счёта или карты в Банке', sourceId=a['id'])
        assert op['fields']['rate'] == '16,0'
        assert s.paper(op)['status'] == 'Исполнена'
    elif n == 403:
        fails(lambda: s.opening(c, '999.99'), 'Минимальная сумма')
        assert s.opening(c, '1000')['status'] == 'Черновик'
    elif n == 404:
        assert s.paper(s.opening(c, '1000000'))['status'] == 'Исполнена'
        op = s.paper(s.opening(c, '1000000.01'))
        assert op['status'] == 'На подтверждении'
        assert s.decide(op)['status'] == 'Исполнена'
    elif n == 405:
        c = s.client(id=c['id'], fatca='US')
        op = s.opening(c, '50000', funding='Из другого банка')
        assert op['fields']['rate'] == '14,5'
        assert s.paper(op)['status'] == 'На подтверждении'
        assert s.decide(op)['status'] == 'Исполнена'
    elif n == 406:
        op = s.opening(c, '10', 'До востребования')
        assert op['fields']['term'] == '0' and op['fields']['rate'] == '0,01'
        assert s.paper(op)['status'] == 'Исполнена'
    elif n == 407:
        op = s.paper(s.opening(c, '2500000', 'Надёжный'))
        assert s.decide(op, False)['status'] == 'Отклонена'
        assert not s.call('client', id=c['id'])['deposits']
    elif n == 408:
        c = s.client(id=c['id'], dbo='NONE')
        a = s.product(c, amount='0.01')
        fails(lambda: s.call('begin-close', productId=a['id']), 'Текущий остаток: 0,01')
        b = s.product(c)
        op = s.call('begin-close', productId=b['id'])
        assert s.paper(op, continuePaper=True)['status'] == 'Исполнена'
    elif n == 409:
        s.product(c, currency='USD')
        d = s.deposit(c)
        fails(lambda: s.call('begin-close', productId=d['id']), 'нет открытого текущего счёта в рублях')
    elif n in (410, 411, 412, 413):
        if n == 411:
            c = s.client(id=c['id'], birthDate=str(s.today.replace(year=s.today.year-16)))
        if n == 412:
            c = s.client(id=c['id'], birthDate=str(s.today.replace(year=s.today.year-18)))
        if n == 413:
            c = s.client(id=c['id'], dbo='LIMITED')
        a = s.product(c, amount='5000' if n == 410 else '0')
        d = s.deposit(c, amount='50000' if n == 413 else '100000', days=73 if n == 413 else 30,
            kind='До востребования' if n in (411, 412) else 'Пополняемый')
        op = s.call('begin-close', productId=d['id'])
        extra = dict(targetId=a['id'])
        if n == 411:
            representative = s.client(passport='4500999003', surname='Представитель')
            extra['representativeId'] = representative['id']
        if n == 413:
            extra['continuePaper'] = True
        s.call('update-operation', id=op['id'], **extra)
        if n in (411, 413):
            op = s.paper(op)
            assert op['status'] == 'На подтверждении'
            assert s.decide(op)['status'] == 'Исполнена'
        else:
            if n == 412:
                s.call('send-sms', id=op['id'])
                assert s.call('sign', id=op['id'], code='000000')['attempts'] == 2
            assert s.electronic(op)['status'] == 'Исполнена'
        snapshot = s.call('client', id=c['id'])
        assert snapshot['deposits'][0]['status'] == 'Закрыт'
        assert snapshot['accounts'][0]['amount'] == ('105000.82' if n == 410 else '50001.00' if n == 413 else '100000.00')
    elif n == 414:
        a = s.product(c)
        assert s.electronic(s.call('begin-close', productId=a['id']))['status'] == 'Исполнена'
    elif n in (415, 416, 420):
        c = s.client(id=c['id'], surname='Семёнова', name='Алёна', patronymic='Игоревна', previousPassports='4500999004')
        if n == 420:
            s.call('prepare', entity='finmon', passport='4500999002', list='Решения межведомственной комиссии')
        op = s.form(surname='СЕМЕНОВА', name='АЛЕНА', patronymic='ИГОРЕВНА', birthDate='1990-01-01')
        assert op['stage'] == 'DUPLICATE'
        op = s.call('continue-client', id=op['id'], choice='previous' if n == 416 else 'noPrevious', passport='4500999004')
        if n == 416:
            assert op['existingId'] == c['id'] and op['stage'] == 'EXISTING'
        else:
            if n == 420:
                assert op['stage'] == 'FINMON'
                op = s.call('continue-client', id=op['id'], choice='continue')
            assert op['status'] == 'На подтверждении'
            fails(lambda: s.call('search', passport='4500999002'), 'Клиент не найден')
            assert s.decide(op, n == 415)['status'] == ('Исполнена' if n == 415 else 'Отменена')
    elif n == 417:
        s.call('prepare', entity='finmon', passport='4500999002', list='Решения межведомственной комиссии')
        op = s.form()
        assert op['stage'] == 'FINMON'
        op = s.call('continue-client', id=op['id'], choice='continue')
        assert op['status'] == 'Исполнена'
        assert 'Передано в финмониторинг' in s.call('client', id=op['clientId'])['history']
    elif n == 418:
        boundary = s.today.replace(year=s.today.year-14)
        fails(lambda: s.form(birthDate=str(boundary+timedelta(days=1))), 'Клиенту меньше 14 лет')
        assert s.form(birthDate=str(boundary))['status'] == 'Исполнена'
    elif n == 419:
        op = s.form(passport=c['passport'])
        assert op['message'] == 'Клиент с таким паспортом уже существует'
        assert op['existingId'] == c['id']


if __name__ == '__main__':
    stand = Stand(sys.argv[1] if len(sys.argv)>1 else 'http://localhost:18081/efr/')
    for number in range(401, 421):
        stand.reset()
        case(stand, number)
        print(f'900{number}: OK')
    print('20/20 правильных веток пройдены. Стенд содержит данные последней проверки.')
