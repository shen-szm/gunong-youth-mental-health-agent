import hashlib
import importlib.util
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('release', Path(__file__).with_name('release-alpha37.py'))
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.env = self.root / 'backend/.env'
        self.env.parent.mkdir()
        self.env.write_bytes(b'# RELEASE_VERSION=5.1.0-alpha.36\r\nRELEASE_VERSION=5.1.0-alpha.36\r\nPRIVATE=unchanged\r\n')
        self.patch = patch.object(release, 'ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_only_active_version_changes(self):
        before = self.env.read_bytes()
        with patch.object(release.os, 'fchmod', create=True), patch.object(release.os, 'fchown', create=True):
            release.version('5.1.0-alpha.36', '5.1.0-alpha.37')
        self.assertEqual(self.env.read_bytes(), before.replace(b'\nRELEASE_VERSION=5.1.0-alpha.36', b'\nRELEASE_VERSION=5.1.0-alpha.37'))

    def test_enabled_pilot_aborts(self):
        self.env.write_bytes(self.env.read_bytes() + b'ENABLE_TEACHER_DURABLE_PLANS=true\n')
        with self.assertRaises(AssertionError):
            release.check_environment('5.1.0-alpha.36')

    def test_failed_start_restores_code_frontend_and_version(self):
        stage = self.root / 'releases/alpha37-test'
        baseline = {}
        for name in release.BASELINES:
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b'# original\n')
            baseline[name] = hashlib.sha256(dest.read_bytes()).hexdigest()
        for base in (self.root / 'frontend/dist', stage / 'dist'):
            (base / 'assets').mkdir(parents=True)
            for name in ('index.html', 'third-party-agent.txt', 'third-party-icons.txt', 'third-party-audio.txt'):
                (base / name).write_text('original' if base.parent.name == 'frontend' else 'new')
        with tarfile.open(stage / 'backend.tar', 'w') as archive:
            source = self.root / 'new.py'
            source.write_text('# new\n')
            for name in release.FILES:
                archive.add(source, arcname=name)
        calls = []

        def command(*args):
            calls.append(args)
            if args[0] == 'install':
                shutil.copy2(args[-2], args[-1])
            if args[:2] == ('systemctl', 'start') and sum(c[:2] == args[:2] for c in calls) == 1:
                raise RuntimeError('start failed')

        with patch.object(release, 'BASELINES', baseline), patch.object(release, 'healthy', return_value=True), patch.object(release, 'run', side_effect=command), patch.object(release.subprocess, 'run'), patch.object(release.os, 'fchmod', create=True), patch.object(release.os, 'fchown', create=True):
            with self.assertRaisesRegex(RuntimeError, 'start failed'):
                release.main('alpha37-test', True)
        for name in baseline:
            self.assertEqual((self.root / name).read_bytes(), b'# original\n')
        self.assertTrue(all(not (self.root / name).exists() for name in release.NEW))
        self.assertEqual((self.root / 'frontend/dist/index.html').read_text(), 'original')
        self.assertIn(b'\nRELEASE_VERSION=5.1.0-alpha.36', self.env.read_bytes())
        self.assertEqual(sum(c[:2] == ('systemctl', 'start') for c in calls), 2)


if __name__ == '__main__':
    unittest.main()
