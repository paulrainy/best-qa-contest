import tempfile
import unittest
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree
from check_reference_results import validate_reports


class ResultChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.expected = {'ref.Test#ok', 'ref.Test#fee', 'ref.Test#refund'}
        self.known = {'ref.Test#fee': 'KNOWN:F10:COMMISSION', 'ref.Test#refund': 'KNOWN:F16:REFUND'}

    def write(self, mutations=None):
        suite = Element('testsuite')
        for name in ('ok', 'fee', 'refund'):
            case = SubElement(suite, 'testcase', classname='ref.Test', name=name)
            if name != 'ok':
                SubElement(case, 'failure', type='java.lang.AssertionError', message='[' + self.known['ref.Test#' + name] + '] expected money')
        if mutations:
            mutations(suite)
        ElementTree(suite).write(self.root / 'TEST-one.xml')

    def check(self):
        return validate_reports(self.root, self.expected, self.known)

    def test_exact_known_assertions_accepted(self):
        self.write()
        self.assertEqual([], self.check())

    def test_missing_test_rejected(self):
        self.write(lambda s: s.remove(s[1]))
        self.assertTrue(self.check())

    def test_unknown_timeout_rejected(self):
        self.write(lambda s: SubElement(s[0], 'failure', type='java.lang.AssertionError', message='timeout'))
        self.assertTrue(self.check())

    def test_skip_rejected(self):
        def mutate(s):
            s[2].remove(s[2][0]); SubElement(s[2], 'skipped')
        self.write(mutate)
        self.assertTrue(self.check())

    def test_infrastructure_error_in_known_test_rejected(self):
        def mutate(s):
            s[1][0].tag = 'error'
        self.write(mutate)
        self.assertTrue(self.check())

    def test_preparation_failure_in_known_test_rejected(self):
        self.write(lambda s: s[1][0].set('message', 'HTTP 503 during preparation'))
        self.assertTrue(self.check())

    def test_green_after_stand_change_rejected(self):
        def mutate(s):
            for c in s:
                for child in list(c): c.remove(child)
        self.write(mutate)
        self.assertTrue(self.check())

    def test_duplicate_results_rejected(self):
        self.write(); (self.root / 'TEST-copy.xml').write_bytes((self.root / 'TEST-one.xml').read_bytes())
        self.assertTrue(self.check())

    def test_empty_and_truncated_rejected(self):
        self.assertTrue(self.check())
        (self.root / 'TEST-bad.xml').write_text('<testsuite>')
        self.assertTrue(self.check())

    def test_pytest_assertion_format_accepted(self):
        def mutate(s):
            for c in list(s)[1:]:
                c[0].attrib.pop('type')
                c[0].set('message', 'AssertionError: ' + self.known['ref.Test#' + c.get('name')] + '\nassert wrong == expected')
        self.write(mutate)
        self.assertEqual([], self.check())

    def test_untyped_failure_without_assertion_evidence_rejected(self):
        self.write(lambda s: s[1][0].attrib.pop('type'))
        self.assertTrue(self.check())

    def test_marker_with_wrong_failure_type_rejected(self):
        self.write(lambda s: s[1][0].set('type', 'java.sql.SQLException'))
        self.assertTrue(self.check())


if __name__ == '__main__':
    unittest.main()
