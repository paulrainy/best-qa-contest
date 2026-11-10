import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path
from check_distribution import check_distribution, check_archive, DIRECTIONS


class DistributionChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        final = self.root / 'final-task'
        (final / 'jury/source').mkdir(parents=True)
        (final / 'jury/source/spec.md').write_text('contract')
        rows = []
        for direction in DIRECTIONS:
            p = final / direction / 'participant'
            (p / 'stand/lib').mkdir(parents=True)
            for name in ('README.md', 'spec.md'):
                (p / name).write_text('contract')
            for name in ('run.sh', 'run.cmd', 'stand.properties'):
                (p / 'stand' / name).write_text('launcher')
            for name in ('transfer-stand.jar', 'lib/dependency.jar', 'lib/dojo.zip'):
                f = p / 'stand' / name
                with zipfile.ZipFile(f, 'w') as z:
                    z.writestr(zipfile.ZipInfo('META-INF/MANIFEST.MF'), 'Manifest-Version: 1.0\nClass-Path: lib/dependency.jar\n\n' if name == 'transfer-stand.jar' else 'Manifest-Version: 1.0\n')
            for f in sorted(p.rglob('*')):
                if f.is_file(): rows.append('| ' + hashlib.sha256(f.read_bytes()).hexdigest() + ' | ' + f.relative_to(self.root).as_posix() + ' |')
        (final / 'jury/stand-manifest.md').write_text('\n'.join(rows))
        self.first = final / DIRECTIONS[0] / 'participant'

    def test_complete_distribution_accepted(self):
        self.assertEqual([], check_distribution(self.root))

    def test_missing_dependency_rejected(self):
        (self.first / 'stand/lib/dependency.jar').unlink()
        self.assertTrue(check_distribution(self.root))

    def test_missing_console_zip_rejected(self):
        (self.first / 'stand/lib/dojo.zip').unlink()
        self.assertTrue(check_distribution(self.root))

    def test_pointer_rejected(self):
        (self.first / 'stand/transfer-stand.jar').write_text('version https://git-lfs.github.com/spec/v1\noid sha256:test\nsize 123\n')
        self.assertTrue(check_distribution(self.root))

    def test_different_jar_rejected(self):
        with zipfile.ZipFile(self.first / 'stand/transfer-stand.jar', 'a') as z: z.writestr('changed', 'changed')
        self.assertTrue(check_distribution(self.root))

    def test_generated_data_can_exist_locally_but_cannot_enter_archive(self):
        data = self.first / 'stand/test-data/accounts.csv'
        data.parent.mkdir(); data.write_text('private runtime data')
        self.assertEqual([], check_distribution(self.root))
        archive = self.root / 'runtime.zip'
        with zipfile.ZipFile(archive, 'w') as z: z.write(data, 'participant/stand/test-data/accounts.csv')
        self.assertTrue(check_archive(archive, self.first))

    def test_jury_in_archive_rejected(self):
        archive = self.root / 'bad.zip'
        with zipfile.ZipFile(archive, 'w') as z: z.writestr('participant/jury/key.md', 'secret')
        self.assertTrue(check_archive(archive, self.first))

    def test_clean_archive_accepted(self):
        archive = self.root / 'good.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            for f in self.first.rglob('*'):
                if f.is_file(): z.write(f, 'participant/' + f.relative_to(self.first).as_posix())
        self.assertEqual([], check_archive(archive, self.first))


if __name__ == '__main__':
    unittest.main()
