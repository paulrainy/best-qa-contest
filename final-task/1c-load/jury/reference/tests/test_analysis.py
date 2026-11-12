import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.analyse import analyse_rows, counter_rates, metric_summary


ORIGIN = 1900000000000


def row(i, elapsed=100, start=31, code='202', status='PROCESSING'):
    return dict(timeStamp=str(ORIGIN + int(start * 1000)), elapsed=str(elapsed),
                label='POST transfer', success=str(code == '202').lower(), responseCode=code,
                transferId=f'00000000-0000-0000-0000-{i:012d}',
                createdAt=datetime.fromtimestamp((ORIGIN + start * 1000) / 1000, timezone.utc).isoformat(),
                apiStatus=status, originMs=str(ORIGIN), category='accepted')


def final(r, delay=1, status='COMPLETED'):
    created = datetime.fromisoformat(r['createdAt'])
    return dict(transferId=r['transferId'], createdAt=r['createdAt'], status=status,
                completedAt=(created + timedelta(seconds=delay)).isoformat() if status != 'PROCESSING' else None,
                observedAtMs=int(created.timestamp() * 1000) + 130000)


class AnalysisTests(unittest.TestCase):
    def summary(self, rows, statuses, windows=((30, 180, 50),)):
        return analyse_rows(rows, statuses, windows)

    def test_full_population_nearest_rank_excludes_errors_get_and_warmup(self):
        rows = [row(i, elapsed=i * 100) for i in range(1, 21)]
        extras = [row(21, 99999, code='Non HTTP response code: SocketTimeoutException'),
                  dict(row(22, 99999), label='GET status'), row(23, 99999, start=1)]
        summary = self.summary(rows + extras, [final(r) for r in rows + extras if r['responseCode'] == '202' and r['label'] == 'POST transfer'])
        self.assertEqual(summary['measured']['accepted_post_p95_ms'], 1900)
        self.assertEqual(summary['measured']['accepted'], 20)
        self.assertEqual(summary['excluded']['service_samples'], 1)
        self.assertEqual(summary['excluded']['outside_measurement_posts'], 1)
        self.assertEqual(summary['measured']['categories']['timeout'], 1)

    def test_unfinished_stays_in_denominator(self):
        rows = [row(i) for i in range(10)]
        statuses = [final(r, 1 if i < 7 else 3) for i, r in enumerate(rows[:9])]
        statuses.append(final(rows[9], status='PROCESSING'))
        summary = self.summary(rows, statuses)['measured']
        self.assertEqual(summary['within_2s_percent'], 70)
        self.assertEqual(summary['unfinished'], 1)
        self.assertEqual(summary['accepted'], 10)

    def test_missing_or_immature_final_data_does_not_prove_slo(self):
        r = row(1)
        for statuses in ([], [dict(final(r, status='PROCESSING'), observedAtMs=ORIGIN + 31001)]):
            summary = self.summary([r], statuses)
            self.assertFalse(summary['data_complete'])
            self.assertIsNone(summary['measured']['within_2s_percent'])

    def test_response_categories_are_separate(self):
        rows = [row(1), row(2, code='422', status=''), row(3, code='503'),
                row(4, code='Non HTTP response code: SocketTimeoutException'), dict(row(5), transferId=''),
                row(6, code='200'), row(7, code='409', status='')]
        summary = self.summary(rows, [final(rows[0])])
        # 422 — прикладной отказ по ТЗ; 200 означает повтор по ключу и при уникальных ключах неожидан.
        self.assertEqual(summary['measured']['categories'],
                         dict(accepted=1, application_rejection=1, overload_503=1, timeout=1, invalid_202=1,
                              http_or_transport_error=2))
        self.assertEqual(summary['measured']['accepted'], 1)

    def test_step_half_open_boundaries_and_late_completion(self):
        rows = [row(i, start=t) for i, t in enumerate((14.999, 15, 59.999, 60, 74.999, 75, 119.999, 120), 1)]
        summary = self.summary(rows, [final(r, delay=3) for r in rows], ((15, 60, 10), (75, 120, 20)))
        self.assertEqual([s['posts'] for s in summary['intervals']], [2, 2])
        self.assertEqual(summary['measured']['accepted'], 4)
        self.assertEqual(summary['measured']['within_2s_percent'], 0)

    def test_duplicate_and_missing_accepted_ids_invalidate_evidence(self):
        r = row(1)
        self.assertFalse(self.summary([r, r], [final(r)])['data_complete'])
        self.assertFalse(self.summary([r], [final(r), final(r)])['data_complete'])

    def test_counter_reset_starts_new_segment_not_negative_rate(self):
        rates = counter_rates([(0, 100), (5, 130), (10, 4), (15, 14)])
        self.assertEqual([r['rate'] for r in rates], [6, None, 2])
        self.assertEqual([r['reset'] for r in rates], [False, True, False])

    def test_slo_exact_two_seconds_is_inclusive(self):
        rows = [row(1), row(2)]
        summary = self.summary(rows, [final(rows[0], 2), final(rows[1], 2.000001)])
        self.assertEqual(summary['measured']['within_2s_percent'], 50)

    def test_generator_underdelivery_is_not_service_capacity(self):
        rows = [row(i) for i in range(100)]
        summary = self.summary(rows, [final(r) for r in rows])
        self.assertFalse(summary['load_valid'])
        self.assertEqual(summary['nft_verdict'], 'UNPROVEN')

    def test_metric_gaps_and_missing_resource_evidence_are_visible(self):
        rows = [dict(timestampMs=str(ORIGIN + s * 1000), error='', accountingQueue='0',
                     accountingProcessed=str(s), generatorRssKiB='100', generatorThreads='5', generatorCpuPercent='1')
                for s in range(0, 31, 5)]
        self.assertTrue(metric_summary(rows, ORIGIN, 30)['complete'])
        self.assertFalse(metric_summary(rows[:-1], ORIGIN, 30)['complete'])
        broken = [dict(r, error='network failed', accountingQueue='', accountingProcessed='') for r in rows]
        self.assertFalse(metric_summary(broken, ORIGIN, 30)['complete'])


if __name__ == '__main__':
    unittest.main()
