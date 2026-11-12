import sys
import os
import tempfile
import unittest
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.collect_metrics import parse_metrics, generator_stats, java_child
from tools.collect_transfers import collect
from test_analysis import row, final


class CollectorTests(unittest.TestCase):
    def test_java_child_is_found_by_process_name_on_linux_and_macos(self):
        linux = ['  100     1 bash', '  200   100 java', '  300   200 java']
        macos = ['  100     1 /bin/sh', '  200   100 /Library/Java/jdk-17/Contents/Home/bin/java']
        self.assertEqual(java_child(linux, 100), 200)
        self.assertEqual(java_child(macos, 100), 200)
        self.assertEqual(java_child(['  200   100 javac'], 100), 100)
        self.assertEqual(java_child([], 100), 100)

    def test_real_local_process_resources_are_readable(self):
        result = generator_stats(os.getpid())
        self.assertNotIn('generatorError', result)
        self.assertGreater(result['generatorRssKiB'], 0)
        self.assertGreaterEqual(result['generatorThreads'], 1)

    @unittest.skipUnless(os.name == 'nt', 'интервальный CPU через WinAPI считается только в Windows')
    def test_windows_cpu_is_share_since_previous_sample(self):
        generator_stats(os.getpid())
        deadline = time.perf_counter() + .3
        while time.perf_counter() < deadline:
            pass
        busy = generator_stats(os.getpid())
        self.assertGreater(busy['generatorCpuPercent'], 20)
        time.sleep(.3)
        idle = generator_stats(os.getpid())
        self.assertLess(idle['generatorCpuPercent'], busy['generatorCpuPercent'])

    def test_absent_metric_is_a_gap_not_zero(self):
        values = parse_metrics('stand_db_transfers_rows 30000\n# comment\njvm_memory_heap_used_bytes 123\n')
        self.assertEqual(values['dbTransfers'], 30000)
        self.assertIsNone(values['accountingQueue'])
        self.assertIsNone(values['accountingProcessed'])

    def test_terminal_and_unfinished_are_both_saved(self):
        rows = [row(1), row(2), row(3, code='503')]
        def fetch(transfer_id):
            return final(rows[0]) if transfer_id == rows[0]['transferId'] else final(rows[1], status='PROCESSING')
        with tempfile.TemporaryDirectory() as directory:
            result = collect(rows, '', Path(directory) / 'states.jsonl', drain_s=.01, fetch=fetch)
        self.assertEqual(len(result), 2)
        self.assertEqual({r['status'] for r in result}, {'COMPLETED', 'PROCESSING'})

    def test_fetch_failure_is_retained_and_not_a_product_result(self):
        def fetch(transfer_id):
            raise OSError('connection refused')
        with tempfile.TemporaryDirectory() as directory:
            result = collect([row(1)], '', Path(directory) / 'states.jsonl', drain_s=.01, fetch=fetch)
        self.assertEqual(len(result), 1)
        self.assertIn('connection refused', result[0]['error'])
        self.assertEqual(result[0]['status'], 'UNKNOWN')

    def test_drain_deadline_does_not_issue_the_whole_unvisited_backlog(self):
        calls = []
        def fetch(transfer_id):
            calls.append(transfer_id)
            time.sleep(.02)
            raise OSError('slow endpoint')
        with tempfile.TemporaryDirectory() as directory:
            result = collect([row(i) for i in range(100)], '', Path(directory) / 'states.jsonl', drain_s=.005, fetch=fetch)
        self.assertEqual(len(result), 100)
        self.assertLessEqual(len(calls), 8)


if __name__ == '__main__':
    unittest.main()
