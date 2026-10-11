import asyncio
import unittest
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import settings
from main import health, root


class ReleaseHealthTests(unittest.TestCase):
    def test_release_version_is_synchronized(self):
        self.assertEqual(settings.RELEASE_VERSION, "5.1.0-alpha.41")
        self.assertEqual(asyncio.run(root())["version"], settings.RELEASE_VERSION)
        self.assertEqual(asyncio.run(health())["version"], settings.RELEASE_VERSION)


if __name__ == "__main__":
    unittest.main()
