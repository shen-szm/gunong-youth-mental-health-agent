import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class ReleaseVersionScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env_path = Path(self.temp.name) / '.env'
        script = (Path(__file__).resolve().parents[2] / 'deploy' / 'release-alpha34.sh').read_text(encoding='utf-8')
        self.code = script.split("<<'PY'\n", 1)[1].split('\nPY\n', 1)[0]
        self.code = self.code.replace("'/opt/shengyu/backend/.env'", repr(str(self.env_path)))
        if os.name == 'nt':
            # The deployed script uses Unix owner/mode APIs. Exercise content on Windows.
            self.code = 'import os\nos.fchmod = lambda *args: None\nos.fchown = lambda *args: None\n' + self.code

    def tearDown(self):
        self.temp.cleanup()

    def run_version(self, before, after):
        return subprocess.run([sys.executable, '-c', self.code, before, after], capture_output=True)

    def test_only_public_version_changes_and_rollback_preserves_all_other_bytes(self):
        original = b'# local config\r\nKEY=not-a-real-key\r\nRELEASE_VERSION=5.1.0-alpha.32\r\nFLAG=true\r\n'
        self.env_path.write_bytes(original)
        self.assertEqual(self.run_version('5.1.0-alpha.32', '5.1.0-alpha.34').returncode, 0)
        self.assertEqual(self.env_path.read_bytes(), original.replace(b'alpha.32', b'alpha.34'))
        self.assertEqual(self.run_version('5.1.0-alpha.34', '5.1.0-alpha.32').returncode, 0)
        self.assertEqual(self.env_path.read_bytes(), original)

    def test_unexpected_version_refuses_to_overwrite(self):
        original = b'RELEASE_VERSION=5.1.0-alpha.99\nKEY=not-a-real-key\n'
        self.env_path.write_bytes(original)
        result = self.run_version('5.1.0-alpha.32', '5.1.0-alpha.34')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(b'not-a-real-key', result.stdout + result.stderr)
        self.assertEqual(self.env_path.read_bytes(), original)

    def test_ambiguous_duplicate_configuration_is_not_rewritten(self):
        original = b'RELEASE_VERSION=5.1.0-alpha.32\nRELEASE_VERSION=5.1.0-alpha.32\n'
        self.env_path.write_bytes(original)
        self.assertNotEqual(self.run_version('5.1.0-alpha.32', '5.1.0-alpha.34').returncode, 0)
        self.assertEqual(self.env_path.read_bytes(), original)
