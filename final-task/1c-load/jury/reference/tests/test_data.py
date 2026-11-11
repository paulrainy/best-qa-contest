import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.prepare_data import select_pairs


class DataTests(unittest.TestCase):
    def test_ring_pairs_different_active_clients_and_budget(self):
        accounts = [dict(account_number=str(i).zfill(20), client_id=f'C{i}', status='ACTIVE', balance='50000.00') for i in range(4)]
        pairs = select_pairs(accounts, count=4, max_requests=1200)
        self.assertEqual(len(pairs), 4)
        self.assertEqual(len({r['fromAccount'] for r in pairs}), 4)
        self.assertTrue(all(r['fromClient'] != r['toClient'] for r in pairs))

    def test_rejects_insufficient_pairs_or_daily_budget(self):
        rows = [dict(account_number=str(i).zfill(20), client_id=f'C{i}', status='ACTIVE', balance='1000000') for i in range(4)]
        with self.assertRaises(ValueError):
            select_pairs(rows, count=5, max_requests=100)
        with self.assertRaises(ValueError):
            select_pairs(rows, count=4, max_requests=12000)


if __name__ == '__main__':
    unittest.main()
