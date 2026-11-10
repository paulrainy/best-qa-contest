import unittest
from load_check import summarize


class LoadSummaryChecks(unittest.TestCase):
    def test_p95_uses_all_accepted_and_unfinished_stay_in_denominator(self):
        rows = [{'code': 202, 'elapsed_ms': x * 100, 'final_ms': (1000 if x <= 14 else 3000 if x <= 18 else None)} for x in range(1, 21)]
        rows.append({'code': 503, 'elapsed_ms': 90000, 'final_ms': None})
        result = summarize(rows)
        self.assertEqual(1900, result['accepted_post_p95_ms'])
        self.assertEqual(70, result['within_2s_percent'])
        self.assertEqual(2, result['unfinished'])
        self.assertEqual(1, result['http_503'])

    def test_empty_has_no_fabricated_percentiles(self):
        result = summarize([])
        self.assertIsNone(result['accepted_post_p95_ms'])
        self.assertIsNone(result['within_2s_percent'])


if __name__ == '__main__': unittest.main()
