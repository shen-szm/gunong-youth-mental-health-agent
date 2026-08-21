import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from api.teacher import router as teacher_router
from api.user import router as user_router
from api.admin import router as admin_router
from api.chat import router as chat_router
from api.mood import router as mood_router
from database import Base, get_db
from models import ChatMessage, MoodRecord, SensitiveAccessLog, StudentCaseAccessRequest, TeacherStudentAssignment, User
from security import get_password_hash


class TeacherCaseAccessTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        db = self.Session()
        try:
            self.student = User(username="student_a", password_hash=get_password_hash("StudentPassword12"), nickname="合成学生A", is_admin=0)
            self.teacher = User(username="teacher_a", password_hash=get_password_hash("TeacherPassword12"), nickname="普通教师A", is_admin=1)
            self.admin = User(username="admin_a", password_hash=get_password_hash("AdminTeacherPassword12"), nickname="管理员教师A", is_admin=2)
            db.add_all([self.student, self.teacher, self.admin])
            db.commit()
            for item in (self.student, self.teacher, self.admin):
                db.refresh(item)
            self.student_id, self.teacher_id, self.admin_id = self.student.id, self.teacher.id, self.admin.id
            db.add(TeacherStudentAssignment(teacher_user_id=self.teacher.id, student_user_id=self.student.id, assigned_by_user_id=self.admin.id, active=1))
            db.add(MoodRecord(user_id=self.student.id, mood_score=3, mood_label="难过", content="最近早上不太想去学校"))
            db.add(ChatMessage(user_id=self.student.id, role="user", content="我和同学相处得有点累", emotion="难过"))
            db.commit()
        finally:
            db.close()

        app = FastAPI()
        app.include_router(user_router)
        app.include_router(teacher_router)
        app.include_router(admin_router)
        app.include_router(chat_router)
        app.include_router(mood_router)

        def override_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        self.teacher_client = TestClient(app)
        self.admin_client = TestClient(app)
        self.teacher_client.post("/api/user/login", json={"username": "teacher_a", "password": "TeacherPassword12"})
        self.admin_client.post("/api/user/login", json={"username": "admin_a", "password": "AdminTeacherPassword12"})

    def tearDown(self):
        self.teacher_client.close()
        self.admin_client.close()
        self.engine.dispose()

    def test_teacher_requires_approval_before_original_text(self):
        denied = self.teacher_client.get(f"/api/teacher/students/{self.student_id}/case-context")
        self.assertEqual(denied.status_code, 403)

        submitted = self.teacher_client.post(
            f"/api/teacher/students/{self.student_id}/access-requests",
            json={"reason": "近期到校困难，需要结合自愿记录制定线下关怀计划", "scope": "recent_30_days"},
        )
        self.assertEqual(submitted.status_code, 201)
        request_id = submitted.json()["request_id"]
        still_denied = self.teacher_client.get(f"/api/teacher/students/{self.student_id}/case-context", params={"request_id": request_id})
        self.assertEqual(still_denied.status_code, 403)

        approved = self.admin_client.post(
            f"/api/teacher/access-requests/{request_id}/decision",
            json={"decision": "approved", "note": "符合最小必要范围"},
        )
        self.assertEqual(approved.status_code, 200)
        allowed = self.teacher_client.get(f"/api/teacher/students/{self.student_id}/case-context", params={"request_id": request_id})
        self.assertEqual(allowed.status_code, 200)
        contents = [item["content"] for item in allowed.json()["records"]]
        self.assertIn("最近早上不太想去学校", contents)
        self.assertIn("我和同学相处得有点累", contents)

        db = self.Session()
        try:
            db.add(ChatMessage(user_id=self.student_id, role="user", content="审批之后新增的内容", emotion="平静", created_at=datetime.now() + timedelta(seconds=1)))
            db.commit()
        finally:
            db.close()
        fixed_snapshot = self.teacher_client.get(f"/api/teacher/students/{self.student_id}/case-context", params={"request_id": request_id})
        self.assertNotIn("审批之后新增的内容", [item["content"] for item in fixed_snapshot.json()["records"]])

        db = self.Session()
        try:
            self.assertEqual(db.query(StudentCaseAccessRequest).filter_by(id=request_id, status="approved").count(), 1)
            self.assertGreaterEqual(db.query(SensitiveAccessLog).filter_by(action="view_student_original_content", actor_user_id=self.teacher_id).count(), 1)
            request = db.query(StudentCaseAccessRequest).filter_by(id=request_id).one()
            request.expires_at = datetime.now() - timedelta(seconds=1)
            db.commit()
        finally:
            db.close()
        self.assertEqual(self.teacher_client.get(f"/api/teacher/students/{self.student_id}/case-context", params={"request_id": request_id}).status_code, 403)

    def test_admin_teacher_can_view_directly_and_teacher_cannot_approve(self):
        direct = self.admin_client.get(f"/api/teacher/students/{self.student_id}/case-context")
        self.assertEqual(direct.status_code, 200)
        self.assertEqual(direct.json()["access_basis"], "admin_direct")

        submitted = self.teacher_client.post(
            f"/api/teacher/students/{self.student_id}/access-requests",
            json={"reason": "需要核对近期记录以制定支持计划", "scope": "recent_30_days"},
        )
        request_id = submitted.json()["request_id"]
        forbidden = self.teacher_client.post(
            f"/api/teacher/access-requests/{request_id}/decision",
            json={"decision": "approved", "note": "越权尝试"},
        )
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(self.teacher_client.get(f"/api/admin/user-detail/{self.student_id}").status_code, 403)
        self.assertEqual(self.teacher_client.get("/api/admin/chats").status_code, 403)
        self.assertEqual(self.teacher_client.post(f"/api/admin/set-admin/{self.student_id}").status_code, 403)
        self.assertEqual(self.teacher_client.get("/api/chat/history", params={"user_id": self.student_id}).status_code, 403)
        self.assertEqual(self.teacher_client.get("/api/mood/list", params={"user_id": self.student_id}).status_code, 403)
        self.assertEqual(self.teacher_client.post("/api/mood/record", json={"user_id": self.student_id, "label": "平静", "score": 6, "content": "越权写入"}).status_code, 403)
        # 管理员教师的直达读取也必须走带审计的 case-context，不能绕用学生旧接口读写。
        self.assertEqual(self.admin_client.get("/api/chat/history", params={"user_id": self.student_id}).status_code, 403)
        self.assertEqual(self.admin_client.get("/api/mood/list", params={"user_id": self.student_id}).status_code, 403)
        self.assertEqual(self.admin_client.post("/api/chat/send", json={"user_id": self.student_id, "message": "伪造学生消息"}).status_code, 403)
        self.assertEqual(self.admin_client.post("/api/mood/record", json={"user_id": self.student_id, "label": "平静", "score": 6, "content": "伪造记录"}).status_code, 403)

    def test_unassigned_teacher_cannot_enumerate_or_request_student(self):
        db = self.Session()
        try:
            db.query(TeacherStudentAssignment).delete()
            db.commit()
        finally:
            db.close()
        roster = self.teacher_client.get("/api/teacher/student-list")
        self.assertEqual(roster.status_code, 200)
        self.assertEqual(roster.json()["students"], [])
        request = self.teacher_client.post(
            f"/api/teacher/students/{self.student_id}/access-requests",
            json={"reason": "尝试申请职责范围之外的学生个案", "scope": "recent_30_days"},
        )
        self.assertEqual(request.status_code, 403)

    def test_role_change_revokes_existing_session(self):
        student_client = TestClient(self.teacher_client.app)
        try:
            logged_in = student_client.post(
                "/api/user/login",
                json={"username": "student_a", "password": "StudentPassword12"},
            )
            self.assertEqual(logged_in.status_code, 200)
            self.assertEqual(student_client.get("/api/user/me").status_code, 200)

            promoted = self.admin_client.patch(
                f"/api/teacher/accounts/{self.student_id}",
                json={"is_admin": True},
            )
            self.assertEqual(promoted.status_code, 200)
            self.assertEqual(student_client.get("/api/user/me").status_code, 401)
        finally:
            student_client.close()

    def test_hard_delete_is_disabled(self):
        response = self.admin_client.delete(f"/api/admin/users/{self.student_id}")
        self.assertEqual(response.status_code, 410)
        db = self.Session()
        try:
            self.assertIsNotNone(db.query(User).filter(User.id == self.student_id).first())
        finally:
            db.close()

    def test_mood_note_crisis_forces_high_and_immediate_action(self):
        db = self.Session()
        try:
            db.add(MoodRecord(user_id=self.student_id, mood_score=9, mood_label="平静", content="我想死，不想再继续了"))
            db.commit()
        finally:
            db.close()

        warnings = self.teacher_client.get("/api/teacher/warning-list")
        self.assertEqual(warnings.status_code, 200)
        warning = next(item for item in warnings.json()["warnings"] if item["student_id"] == self.student_id)
        self.assertEqual(warning["risk_level"], "high")
        self.assertTrue(warning["urgent"])
        self.assertIn("立即核实安全", warning["reason"])

        detail = self.teacher_client.get(f"/api/teacher/warning/{self.student_id}/detail")
        self.assertEqual(detail.status_code, 200)
        self.assertTrue(detail.json()["urgent"])
        self.assertIn("不等待原文审批", detail.json()["detail"])
        self.assertIn("12356", detail.json()["suggestion"])
        self.assertIn("110", detail.json()["suggestion"])
        self.assertIn("120", detail.json()["suggestion"])

    def test_student_chat_uses_unified_crisis_gate(self):
        student_client = TestClient(self.teacher_client.app)
        try:
            logged_in = student_client.post(
                "/api/user/login",
                json={"username": "student_a", "password": "StudentPassword12"},
            )
            self.assertEqual(logged_in.status_code, 200)
            for message in ("我想死", "我想结束生命", "我准备烧炭", "不是我想这样，但我不想活了"):
                response = student_client.post(
                    "/api/chat/send",
                    json={"user_id": self.student_id, "message": message},
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn("12356", response.json()["reply"])
                self.assertIn("110", response.json()["reply"])
                self.assertEqual(response.json()["emotion"], "需要立即协助")
        finally:
            student_client.close()


if __name__ == "__main__":
    unittest.main()
