import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from api.user import _create_isolated_guest_user, get_demo_session
from database import Base
from models import User


class DemoSessionTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()

    def tearDown(self):
        self.db.close()

    def test_reuses_one_non_teacher_demo_user(self):
        first = get_demo_session(self.db)
        second = get_demo_session(self.db)

        self.assertEqual(first["user_id"], second["user_id"])
        self.assertEqual(first["nickname"], "演示访客")
        self.assertFalse(first["is_admin"])
        self.assertEqual(
            self.db.query(User).filter(User.username == "demo_guest").count(),
            1,
        )

    def test_guest_users_are_isolated_and_never_teachers(self):
        first = _create_isolated_guest_user(self.db)
        second = _create_isolated_guest_user(self.db)
        self.assertNotEqual(first.id, second.id)
        self.assertNotEqual(first.username, second.username)
        self.assertTrue(first.username.startswith("guest_"))
        self.assertEqual(first.nickname, "新朋友")
        self.assertEqual(first.is_admin, 0)


if __name__ == "__main__":
    unittest.main()
