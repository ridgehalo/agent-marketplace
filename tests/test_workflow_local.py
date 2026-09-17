"""参照元の固定と変更検出を実Gitリポジトリで確認する。"""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'plugins/engineering-delivery/skills/workflow-local/scripts/source_snapshot.py'
spec = importlib.util.spec_from_file_location('source_snapshot', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SourceSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Test')
        (self.root / '.github/workflows').mkdir(parents=True)
        self.workflow = '.github/workflows/test.yml'
        (self.root / self.workflow).write_text('jobs:\n  check:\n    steps:\n      - run: python3 check.py\n')
        (self.root / 'check.py').write_text('print("checked")\n')
        self.commit()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.PIPE).decode().strip()

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'test')
        self.sha = self.git('rev-parse', 'HEAD')

    def capture(self):
        return module.snapshot(self.root, self.sha, self.workflow, ['check.py'])

    def test_matching_source_and_no_execution(self):
        record = self.capture()
        self.assertEqual(module.verify(self.root, record)['status'], 'matched')
        self.assertNotIn('print', str(record))

    def test_workflow_update_is_observed_and_old_snapshot_rejected(self):
        old = self.capture()
        (self.root / self.workflow).write_text('jobs: {new: {steps: [{run: echo updated}]}}\n')
        with self.assertRaisesRegex(ValueError, 'working tree changed'):
            module.verify(self.root, old)
        self.commit()
        new = self.capture()
        self.assertNotEqual(old['files'], new['files'])
        with self.assertRaisesRegex(ValueError, 'HEAD changed'):
            module.verify(self.root, old)
        self.assertEqual(module.verify(self.root, new)['status'], 'matched')

    def test_referenced_script_change_rejected(self):
        record = self.capture()
        (self.root / 'check.py').write_text('raise RuntimeError()\n')
        with self.assertRaisesRegex(ValueError, 'working tree changed'):
            module.verify(self.root, record)

    def test_tampered_record_rejected(self):
        record = self.capture()
        record['files']['check.py'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'committed source'):
            module.verify(self.root, record)

    def test_unsafe_paths_and_non_commit_rejected(self):
        for path in ['../secret', '/secret', './check.py', 'a/../check.py', '-x', 'a\\b']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                module.snapshot(self.root, self.sha, self.workflow, [path])
        with self.assertRaisesRegex(ValueError, 'full commit'):
            module.snapshot(self.root, 'HEAD', self.workflow, [])

    def test_symlink_rejected(self):
        (self.root / 'link.py').symlink_to('check.py')
        self.commit()
        with self.assertRaisesRegex(ValueError, 'regular file'):
            module.snapshot(self.root, self.sha, self.workflow, ['link.py'])
        record = self.capture()
        (self.root / 'check.py').unlink()
        (self.root / 'check.py').symlink_to(self.workflow)
        with self.assertRaisesRegex(ValueError, 'regular checkout'):
            module.verify(self.root, record)

    def test_cli_refuses_overwriting_evidence(self):
        record = self.root / 'record.json'
        args = ['python3', str(SCRIPT), 'capture', '--root', str(self.root),
                '--revision', self.sha, '--workflow', self.workflow, '--record', str(record)]
        first = subprocess.run(args, capture_output=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        original = record.read_bytes()
        second = subprocess.run(args, capture_output=True)
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(record.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
