#!/usr/bin/env python3
"""Контроль новой версии стенда. Сбрасывает данные; режим controls — исправленные правила."""
import json
import sys
from stand_client import Client


def verify(base='http://localhost:18400', controls=False):
    api = Client(base)
    api.call('POST', '/api/test/reset', {})
    result = {}
    if controls:
        a = api.account(); own = api.account(a['clientId'])
        t = api.final(api.transfer(a, own, 100))
        assert t['status'] == 'COMPLETED' and t['commission'] == 0
        assert api.balance(a) == 999900 and api.balance(own) == 1000100
        result['F02'] = 'COMPLETED, one debit/credit'
        a = api.account(); b = api.account()
        assert api.final(api.transfer(a, b, 150000))['status'] == 'COMPLETED'
        result['F08'] = '150000 inclusive'
        a = api.account(); b = api.account()
        api.call('PUT', '/api/test/accounts/' + b['accountNumber'] + '/status', {'status': 'BLOCKED'})
        assert api.final(api.transfer(a, b, 100))['status'] == 'COMPLETED'
        result['F06'] = 'BLOCKED accepts credit'
    else:
        a = api.account(); b = api.account()
        api.final(api.transfer(a, b, 90000))
        crossing = api.final(api.transfer(a, b, 20000))
        assert crossing['commission'] == 200, crossing
        result['F10'] = {'expected': '100.00', 'actual': str(crossing['commission']), 'transferId': crossing['transferId']}
        a = api.account(); b = api.account()
        api.final(api.transfer(a, b, 100000))
        before = api.balance(a)
        try:
            api.call('POST', '/api/test/consumers/accounting/pause', {})
            t = api.transfer(a, b, 40000)
            assert t['commission'] == 400
            api.call('PUT', '/api/test/accounts/' + b['accountNumber'] + '/status', {'status': 'CLOSED'})
        finally:
            api.call('POST', '/api/test/consumers/accounting/resume', {})
        failed = api.final(t)
        assert failed['status'] == 'FAILED', failed
        after = api.balance(a)
        assert before - after == 400, (before, after)
        result['F16'] = {'expected_balance': str(before), 'actual_balance': str(after), 'transferId': t['transferId']}
    return result


if __name__ == '__main__':
    print(json.dumps(verify(controls='controls' in sys.argv), ensure_ascii=False, indent=2))
