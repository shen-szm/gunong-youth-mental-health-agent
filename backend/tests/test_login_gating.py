import asyncio
import sys
import unittest
from pathlib import Path

from fastapi import HTTPException, Response
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from api.user import RegisterReq, _payload, register
from auth import require_real_user
from database import Base
from models import User


class LoginGatingTests(unittest.TestCase):
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

    def _user(self, username, is_admin=0):
        user = User(username=username, password_hash="x", nickname=username, is_admin=is_admin)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def test_payload_marks_guests(self):
        guest = self._user("guest_abc123")
        student = self._user("student01")

        self.assertTrue(_payload(guest)["is_guest"])
        self.assertFalse(_payload(student)["is_guest"])

    def test_require_real_user_rejects_guests(self):
        guest = self._user("guest_abc123")
        student = self._user("student01")

        with self.assertRaises(HTTPException) as ctx:
            require_real_user(guest)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail["code"], "login_required")

        self.assertEqual(require_real_user(student).id, student.id)

    def test_register_rejects_reserved_guest_prefix(self):
        req = RegisterReq(
            username="guest_hacker",
            password="1234567890",
            real_name="张三",
            class_name="初二（3）班",
            student_no="2026001",
        )
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(register(req, Response(), self.db))
        self.assertEqual(ctx.exception.status_code, 400)

    def test_register_creates_real_student(self):
        req = RegisterReq(
            username="student02",
            password="1234567890",
            real_name="李四",
            class_name="初二（3）班",
            student_no="2026002",
        )
        payload = asyncio.run(register(req, Response(), self.db))
        self.assertFalse(payload["is_guest"])
        self.assertFalse(payload["is_admin"])
        self.assertEqual(payload["real_name"], "李四")
        self.assertEqual(payload["class_name"], "初二（3）班")
        self.assertEqual(payload["student_no"], "2026002")
        self.assertEqual(payload["nickname"], "李四")

    def test_register_rejects_duplicate_student_no(self):
        asyncio.run(register(RegisterReq(
            username="student03",
            password="1234567890",
            real_name="王五",
            class_name="初二（3）班",
            student_no="2026003",
        ), Response(), self.db))

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(register(RegisterReq(
                username="student04",
                password="1234567890",
                real_name="赵六",
                class_name="初二（4）班",
                student_no="2026003",
            ), Response(), self.db))
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
