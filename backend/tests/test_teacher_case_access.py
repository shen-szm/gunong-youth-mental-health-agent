import sys
import unittest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep

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
from models import ChatMessage, MoodRecord, SensitiveAccessLog, StudentCaseAccessRequest, StudentExternalAiAuthorization, StudentWellbeingAssessment, TeacherReviewReport, TeacherReviewReportDecision, TeacherStudentAssignment, TeacherWorkProductSnapshot, User
from security import get_password_hash
from teacher_review_engine import NarrativeOutput, _safe_model_narrative


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
            self.unassigned_student = User(username="student_b", password_hash=get_password_hash("StudentPassword12"), nickname="未分配学生B", is_admin=0)
            db.add_all([self.student, self.teacher, self.admin, self.unassigned_student])
            db.commit()
            for item in (self.student, self.teacher, self.admin):
                db.refresh(item)
            self.student_id, self.teacher_id, self.admin_id = self.student.id, self.teacher.id, self.admin.id
            self.unassigned_student_id = self.unassigned_student.id
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
        self.student_client = TestClient(app)
        self.teacher_client.post("/api/user/login", json={"username": "teacher_a", "password": "TeacherPassword12"})
        self.admin_client.post("/api/user/login", json={"username": "admin_a", "password": "AdminTeacherPassword12"})
        self.student_client.post("/api/user/login", json={"username": "student_a", "password": "StudentPassword12"})

    def tearDown(self):
        self.teacher_client.close()
        self.admin_client.close()
        self.student_client.close()
        self.engine.dispose()

    def test_teacher_manages_external_ai_authorization_with_scope_attestation_and_audit(self):
        missing_attestation = self.teacher_client.post(
            f"/api/teacher/students/{self.student_id}/external-ai-authorization",
            json={"active": True, "authority_confirmed": False, "expires_days": 90},
        )
        self.assertEqual(missing_attestation.status_code, 400)

        enabled = self.teacher_client.post(
            f"/api/teacher/students/{self.student_id}/external-ai-authorization",
            json={"active": True, "authority_confirmed": True, "expires_days": 90},
        )
        self.assertEqual(enabled.status_code, 200)
        self.assertTrue(enabled.json()["active"])
        self.assertEqual(enabled.json()["basis"], "school_guardian_authority")
        self.assertEqual(enabled.json()["statement_version"], "teacher-ai-authorization-v1")
        listed = self.teacher_client.get("/api/teacher/student-list").json()["students"]
        self.assertTrue(next(item for item in listed if item["id"] == self.student_id)["external_ai_authorization"]["active"])

        self.assertEqual(self.teacher_client.post(
            f"/api/teacher/students/{self.unassigned_student_id}/external-ai-authorization",
            json={"active": True, "authority_confirmed": True, "expires_days": 30},
        ).status_code, 403)
        admin_enabled = self.admin_client.post(
            f"/api/teacher/students/{self.unassigned_student_id}/external-ai-authorization",
            json={"active": True, "authority_confirmed": True, "expires_days": 30},
        )
        self.assertEqual(admin_enabled.status_code, 200)
        self.assertTrue(admin_enabled.json()["active"])

        revoked = self.teacher_client.post(
            f"/api/teacher/students/{self.student_id}/external-ai-authorization",
            json={"active": False, "expires_days": 30},
        )
        self.assertEqual(revoked.status_code, 200)
        self.assertFalse(revoked.json()["active"])
        self.assertEqual(revoked.json()["status"], "revoked")
        db = self.Session()
        try:
            row = db.query(StudentExternalAiAuthorization).filter_by(student_user_id=self.student_id).one()
            self.assertEqual(row.authorized_by_user_id, self.teacher_id)
            self.assertEqual(db.query(SensitiveAccessLog).filter_by(action="enable_student_external_ai").count(), 2)
            self.assertEqual(db.query(SensitiveAccessLog).filter_by(action="revoke_student_external_ai").count(), 1)
        finally:
            db.close()

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
        profile_before = self.teacher_client.get(f"/api/teacher/students/{self.student_id}/profile", params={"request_id": request_id}).json()

        db = self.Session()
        try:
            db.add(ChatMessage(user_id=self.student_id, role="user", content="审批之后新增的内容", emotion="平静", created_at=datetime.now() + timedelta(seconds=1)))
            db.add(MoodRecord(user_id=self.student_id, mood_score=1, mood_label="难过", content="审批之后新增的情绪记录", created_at=datetime.now() + timedelta(seconds=1)))
            db.commit()
        finally:
            db.close()
        fixed_snapshot = self.teacher_client.get(f"/api/teacher/students/{self.student_id}/case-context", params={"request_id": request_id})
        self.assertNotIn("审批之后新增的内容", [item["content"] for item in fixed_snapshot.json()["records"]])
        profile_after = self.teacher_client.get(f"/api/teacher/students/{self.student_id}/profile", params={"request_id": request_id}).json()
        self.assertEqual(profile_after, profile_before)

        db = self.Session()
        try:
            self.assertEqual(db.query(StudentCaseAccessRequest).filter_by(id=request_id, status="approved").count(), 1)
            self.assertGreaterEqual(db.query(SensitiveAccessLog).filter_by(action="view_student_original_content", actor_user_id=self.teacher_id).count(), 1)
            self.assertGreaterEqual(db.query(SensitiveAccessLog).filter_by(action="view_student_support_profile", actor_user_id=self.teacher_id).count(), 2)
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
        direct_profile = self.admin_client.get(f"/api/teacher/students/{self.student_id}/profile")
        self.assertEqual(direct_profile.status_code, 200)
        self.assertNotIn("avg_score", direct_profile.json())
        descriptive_detail = self.admin_client.get(f"/api/admin/user-detail/{self.student_id}", params={"days": 30})
        self.assertEqual(descriptive_detail.status_code, 200)
        self.assertTrue(all("avg" not in item for item in descriptive_detail.json()["trend"]))
        self.assertTrue(all({"date", "count", "dominant_label"}.issubset(item) for item in descriptive_detail.json()["trend"]))
        self.assertEqual(self.admin_client.get(f"/api/admin/user-detail/{self.student_id}", params={"days": 31}).status_code, 422)
        record_summary = self.admin_client.get(f"/api/admin/user-analysis/{self.student_id}")
        self.assertEqual(record_summary.status_code, 200)
        self.assertTrue(record_summary.json()["degraded"])
        self.assertEqual(record_summary.json()["source"], "deterministic_record_registry")
        self.assertTrue(record_summary.json()["version"])
        self.assertTrue(record_summary.json()["generated_at"])

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
        self.assertEqual(self.admin_client.get("/api/admin/chats").status_code, 410)

        db = self.Session()
        try:
            self.assertGreaterEqual(db.query(SensitiveAccessLog).filter_by(action="view_student_support_profile", actor_user_id=self.admin_id).count(), 1)
        finally:
            db.close()

    def test_urgent_student_assessment_enters_minimum_safety_path(self):
        db = self.Session()
        try:
            db.add(StudentWellbeingAssessment(
                assessment_code="ASSESS-URGENT-TEST",
                user_id=self.student_id,
                answers_json="{}",
                result_json='{"risk_label":"需要立即协助","emotion_summary":"学生主动安全回答需要立即支持","domains":[],"support_needs":[]}',
                risk_level="urgent",
                review_status="needs_professional_review",
                expires_at=datetime.now() + timedelta(days=30),
            ))
            db.commit()
        finally:
            db.close()

        warning = self.teacher_client.get("/api/teacher/warning-list")
        item = next(row for row in warning.json()["warnings"] if row["student_id"] == self.student_id)
        self.assertTrue(item["urgent"])
        self.assertIn("危机", item["reason"])
        detail = self.teacher_client.get(f"/api/teacher/warning/{self.student_id}/detail")
        self.assertTrue(detail.json()["urgent"])
        direct = self.admin_client.get(f"/api/teacher/students/{self.student_id}/work-product")
        self.assertEqual(direct.status_code, 200)
        self.assertEqual(direct.json()["risk"], "urgent")
        self.assertTrue(any(item.startswith("assessment-") for item in direct.json()["observation"]["trigger_evidence_ids"]))

    def test_warning_followup_persists_until_a_new_student_record(self):
        initial = self.teacher_client.get("/api/teacher/warning-list")
        self.assertEqual(initial.status_code, 200)
        item = next(row for row in initial.json()["warnings"] if row["student_id"] == self.student_id)
        self.assertEqual(item["status"], "pending")

        handled = self.teacher_client.post(
            f"/api/teacher/warning/{self.student_id}/handle",
            json={"note": "已完成一次低压力线下关怀并记录学生意愿"},
        )
        self.assertEqual(handled.status_code, 200)
        refreshed = self.teacher_client.get("/api/teacher/warning-list").json()["warnings"]
        self.assertEqual(next(row for row in refreshed if row["student_id"] == self.student_id)["status"], "handled")

        new_record = self.student_client.post("/api/mood/record", json={
            "user_id": self.student_id,
            "label": "焦虑",
            "score": 3,
            "content": "新增的主动记录",
        })
        self.assertEqual(new_record.status_code, 200)
        after_new_signal = self.teacher_client.get("/api/teacher/warning-list").json()["warnings"]
        self.assertEqual(next(row for row in after_new_signal if row["student_id"] == self.student_id)["status"], "pending")
        handled_again = self.teacher_client.post(
            f"/api/teacher/warning/{self.student_id}/handle",
            json={"note": "已核对刚产生的主动记录并安排后续关注"},
        )
        self.assertEqual(handled_again.status_code, 200)
        immediate_refresh = self.teacher_client.get("/api/teacher/warning-list").json()["warnings"]
        self.assertEqual(next(row for row in immediate_refresh if row["student_id"] == self.student_id)["status"], "handled")

    def test_teacher_student_list_does_not_expose_emotion_average(self):
        response = self.teacher_client.get("/api/teacher/student-list")
        self.assertEqual(response.status_code, 200)
        item = next(row for row in response.json()["students"] if row["id"] == self.student_id)
        self.assertNotIn("avg_mood_score", item)

    def test_work_product_is_audited_traceable_and_requires_same_access(self):
        self.assertEqual(self.teacher_client.get(f"/api/teacher/students/{self.student_id}/work-product").status_code, 403)
        db = self.Session()
        try:
            for index in range(9):
                db.add(MoodRecord(user_id=self.student_id, mood_score=6, mood_label="平静", content=f"普通记录{index}", created_at=datetime.now() - timedelta(minutes=20 - index)))
            db.add(ChatMessage(user_id=self.student_id, role="user", content="继父每天打我，我害怕回去", emotion="害怕", created_at=datetime.now() - timedelta(minutes=55)))
            for index in range(51):
                db.add(ChatMessage(user_id=self.student_id, role="user", content=f"今天完成了普通课堂活动{index}", emotion="平静", created_at=datetime.now() - timedelta(minutes=54 - index)))
            db.commit()
        finally:
            db.close()

        product = self.admin_client.get(f"/api/teacher/students/{self.student_id}/work-product")
        self.assertEqual(product.status_code, 200)
        payload = product.json()
        self.assertEqual(payload["access_basis"], "admin_direct")
        self.assertEqual(payload["risk"], "urgent")
        self.assertIn("12356", payload["decision"])
        self.assertIn("110", payload["decision"])
        self.assertIn("120", payload["decision"])
        self.assertEqual([step["status"] for step in payload["pipeline"]], ["completed"] * 4)
        self.assertGreaterEqual(len(payload["observation"]["evidence_ids"]), 1)
        self.assertTrue(payload["observation"]["trigger_evidence_ids"])
        self.assertTrue(any(item["content"] == "继父每天打我，我害怕回去" for item in payload["records"]))
        self.assertTrue(set(payload["observation"]["trigger_evidence_ids"]).issubset(payload["decision_evidence_ids"]))
        self.assertEqual(len(payload["tasks"]), 3)
        self.assertIn("不作诊断", payload["guardrails"])
        confirmed = self.admin_client.post(
            f"/api/teacher/students/{self.student_id}/work-product/task-decisions",
            json={"product_id": payload["case_id"], "task_index": 0, "decision": "confirmed"},
        )
        self.assertEqual(confirmed.status_code, 200)
        sleep(1.1)
        regenerated = self.admin_client.get(f"/api/teacher/students/{self.student_id}/work-product").json()
        self.assertEqual(regenerated["case_id"], payload["case_id"])
        self.assertIn(0, regenerated["confirmed_task_indices"])
        forged = self.admin_client.post(
            f"/api/teacher/students/{self.student_id}/work-product/task-decisions",
            json={"product_id": f"WP-{self.student_id}-direct-{self.admin_id}-20990101000000", "task_index": 0, "decision": "confirmed"},
        )
        self.assertEqual(forged.status_code, 403)
        db = self.Session()
        try:
            self.assertGreaterEqual(db.query(SensitiveAccessLog).filter_by(action="generate_teacher_work_product", actor_user_id=self.admin_id).count(), 1)
            self.assertGreaterEqual(db.query(SensitiveAccessLog).filter_by(action="confirmed_work_product_task", actor_user_id=self.admin_id).count(), 1)
        finally:
            db.close()

    def test_direct_work_product_uses_business_cutoff_across_utc_date_boundary(self):
        first = self.admin_client.get(f"/api/teacher/students/{self.student_id}/work-product")
        self.assertEqual(first.status_code, 200)
        payload = first.json()
        db = self.Session()
        try:
            snapshot = db.query(TeacherWorkProductSnapshot).filter_by(product_id=payload["case_id"]).one()
            snapshot.created_at = datetime.now() - timedelta(days=1)
            db.commit()
        finally:
            db.close()

        confirmed = self.admin_client.post(
            f"/api/teacher/students/{self.student_id}/work-product/task-decisions",
            json={"product_id": payload["case_id"], "task_index": 0, "decision": "confirmed"},
        )
        self.assertEqual(confirmed.status_code, 200)
        regenerated = self.admin_client.get(f"/api/teacher/students/{self.student_id}/work-product")
        self.assertEqual(regenerated.status_code, 200)
        self.assertEqual(regenerated.json()["case_id"], payload["case_id"])
        self.assertIn(0, regenerated.json()["confirmed_task_indices"])

    def test_direct_snapshot_is_superseded_when_a_new_urgent_signal_arrives(self):
        first = self.admin_client.get(f"/api/teacher/students/{self.student_id}/work-product")
        self.assertEqual(first.status_code, 200)
        first_payload = first.json()
        self.assertNotEqual(first_payload["risk"], "urgent")
        confirmed = self.admin_client.post(
            f"/api/teacher/students/{self.student_id}/work-product/task-decisions",
            json={"product_id": first_payload["case_id"], "task_index": 0, "decision": "confirmed"},
        )
        self.assertEqual(confirmed.status_code, 200)
        sleep(0.05)
        db = self.Session()
        try:
            db.add(ChatMessage(
                user_id=self.student_id,
                role="user",
                content="哥哥拿刀威胁我，我现在害怕回去",
                emotion="害怕",
                created_at=datetime.now(),
            ))
            db.commit()
        finally:
            db.close()
        revised = self.admin_client.get(f"/api/teacher/students/{self.student_id}/work-product")
        self.assertEqual(revised.status_code, 200)
        revised_payload = revised.json()
        self.assertEqual(revised_payload["risk"], "urgent")
        self.assertNotEqual(revised_payload["case_id"], first_payload["case_id"])
        self.assertEqual(revised_payload["confirmed_task_indices"], [])
        self.assertTrue(revised_payload["observation"]["trigger_evidence_ids"])
        self.assertTrue(any(item["content"] == "哥哥拿刀威胁我，我现在害怕回去" for item in revised_payload["records"]))

    def test_direct_snapshot_is_superseded_when_any_new_student_record_arrives(self):
        first = self.admin_client.get(f"/api/teacher/students/{self.student_id}/work-product").json()
        sleep(0.05)
        db = self.Session()
        try:
            db.add(MoodRecord(
                user_id=self.student_id,
                mood_score=4,
                mood_label="焦虑",
                content="今天课间有些紧张",
                created_at=datetime.now(),
            ))
            db.commit()
        finally:
            db.close()
        revised = self.admin_client.get(f"/api/teacher/students/{self.student_id}/work-product").json()
        self.assertNotEqual(revised["case_id"], first["case_id"])
        self.assertTrue(any(item["content"] == "今天课间有些紧张" for item in revised["records"]))

    def test_approved_teacher_gets_redacted_urgent_override_without_new_original(self):
        submitted = self.teacher_client.post(
            f"/api/teacher/students/{self.student_id}/access-requests",
            json={"reason": "需要结合授权记录制定关怀计划并确认安全边界", "scope": "recent_30_days"},
        )
        request_id = submitted.json()["request_id"]
        self.admin_client.post(
            f"/api/teacher/access-requests/{request_id}/decision",
            json={"decision": "approved", "note": "同意最小必要范围"},
        )
        first_payload = self.teacher_client.get(
            f"/api/teacher/students/{self.student_id}/work-product",
            params={"request_id": request_id},
        ).json()
        self.assertNotEqual(first_payload["risk"], "urgent")
        confirmed = self.teacher_client.post(
            f"/api/teacher/students/{self.student_id}/work-product/task-decisions",
            params={"request_id": request_id},
            json={"product_id": first_payload["case_id"], "task_index": 0, "decision": "confirmed"},
        )
        self.assertEqual(confirmed.status_code, 200)
        sleep(0.05)
        db = self.Session()
        try:
            db.add(ChatMessage(
                user_id=self.student_id,
                role="user",
                content="哥哥拿刀威胁我，我现在害怕回去",
                emotion="害怕",
                created_at=datetime.now(),
            ))
            db.commit()
        finally:
            db.close()
        revised_payload = self.teacher_client.get(
            f"/api/teacher/students/{self.student_id}/work-product",
            params={"request_id": request_id},
        ).json()
        self.assertEqual(revised_payload["risk"], "urgent")
        self.assertNotEqual(revised_payload["case_id"], first_payload["case_id"])
        self.assertEqual(revised_payload["confirmed_task_indices"], [])
        self.assertNotIn("哥哥拿刀威胁我", " ".join(item["content"] for item in revised_payload["records"]))
        safety_rows = [item for item in revised_payload["records"] if item["source"] == "最少必要安全事件"]
        self.assertEqual(len(safety_rows), 1)
        self.assertTrue(safety_rows[0]["redacted"])
        self.assertIn(safety_rows[0]["id"], revised_payload["observation"]["trigger_evidence_ids"])
        context = self.teacher_client.get(
            f"/api/teacher/students/{self.student_id}/case-context",
            params={"request_id": request_id},
        ).json()
        self.assertNotIn("哥哥拿刀威胁我", " ".join(item["content"] for item in context["records"]))

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
        self.assertEqual(self.teacher_client.get(f"/api/teacher/warning/{self.student_id}/detail").status_code, 403)
        self.assertEqual(self.teacher_client.post(f"/api/teacher/warning/{self.student_id}/handle", json={"note": "越权处理"}).status_code, 403)

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
            for message in ("我想死", "我想结束生命", "我准备烧炭", "不是我想这样，但我不想活了", "爸爸打我，我不敢回家", "继父每天打我，我害怕回去", "哥哥拿刀威胁我", "爸爸用皮带抽我，我很害怕", "叔叔逼我和他发生关系", "哥哥把我关在屋里不让我出去", "家里有人用烟头烫我", "家里有人把我锁在厕所不让我出去", "家里有人性侵我"):
                response = student_client.post(
                    "/api/chat/send",
                    json={"user_id": self.student_id, "message": message},
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn("12356", response.json()["reply"])
                self.assertIn("110", response.json()["reply"])
                self.assertEqual(response.json()["emotion"], "需要立即协助")
                self.assertEqual(response.json()["conversation_signal"], "urgent")

            routine = student_client.post(
                "/api/chat/send",
                json={"user_id": self.student_id, "message": "小组活动让我担心说错话"},
            )
            self.assertEqual(routine.status_code, 200)
            self.assertEqual(routine.json()["conversation_signal"], "urgent")
            self.assertNotIn("support", routine.json())
        finally:
            student_client.close()

    def test_admin_generates_reviews_signs_and_downloads_final_report(self):
        generated = self.admin_client.post(f"/api/teacher/students/{self.student_id}/review-reports")
        self.assertEqual(generated.status_code, 200, generated.text)
        report = generated.json()
        self.assertEqual(report["status"], "draft")
        self.assertEqual(report["report_version"], "teacher-review-report-v2")
        self.assertEqual(len(report["agent_review"]["workflow"]), 7)
        self.assertFalse(report["data_scope"]["original_text_external_transfer"])
        self.assertIn("不是医学诊断", report["boundary"])
        self.assertTrue(report["review_checklist"])
        self.assertIn(report["evidence_audit"]["status"], {"partial", "review_ready"})
        self.assertGreater(report["evidence_audit"]["claim_count"], 0)
        self.assertEqual(report["evidence_audit"]["record_count"], len(report["evidence_audit"]["ledger"]))
        self.assertTrue(all("excerpt" not in item and "content" not in item for item in report["evidence_audit"]["ledger"]))
        self.assertIn("不是心理风险概率", report["evidence_audit"]["boundary"])
        self.assertTrue(all(item["status"] in {"record_linked", "guidance_linked", "declared_gap", "unlinked"} for item in report["evidence_audit"]["claims"]))

        blocked = self.admin_client.post(
            f"/api/teacher/students/{self.student_id}/review-reports/{report['report_id']}/decision",
            json={"decision": "reviewed", "checklist_confirmed": False, "note": "已线下核对"},
        )
        self.assertEqual(blocked.status_code, 400)
        gap_not_acknowledged = self.admin_client.post(
            f"/api/teacher/students/{self.student_id}/review-reports/{report['report_id']}/decision",
            json={"decision": "reviewed", "checklist_confirmed": True, "note": "已线下核对并明确责任人"},
        )
        self.assertEqual(gap_not_acknowledged.status_code, 400)
        signed = self.admin_client.post(
            f"/api/teacher/students/{self.student_id}/review-reports/{report['report_id']}/decision",
            json={"decision": "reviewed", "checklist_confirmed": True, "evidence_gap_acknowledged": True, "note": "已线下核对并明确责任人，后续补充支持意愿"},
        )
        self.assertEqual(signed.status_code, 200, signed.text)
        self.assertEqual(signed.json()["status"], "reviewed")
        terminal = self.admin_client.post(
            f"/api/teacher/students/{self.student_id}/review-reports/{report['report_id']}/decision",
            json={"decision": "revision_requested", "checklist_confirmed": False, "note": "尝试修改已签署报告"},
        )
        self.assertEqual(terminal.status_code, 409)
        reused = self.admin_client.post(f"/api/teacher/students/{self.student_id}/review-reports")
        self.assertEqual(reused.json()["report_id"], report["report_id"])

        pdf = self.admin_client.get(f"/api/teacher/students/{self.student_id}/review-reports/{report['report_id']}.pdf")
        self.assertEqual(pdf.status_code, 200, pdf.text)
        self.assertEqual(pdf.headers["content-type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        db = self.Session()
        try:
            self.assertEqual(db.query(TeacherReviewReport).filter_by(report_id=report["report_id"]).count(), 1)
            self.assertGreaterEqual(db.query(SensitiveAccessLog).filter_by(action="review_teacher_report", actor_user_id=self.admin_id, result="denied_checklist").count(), 1)
            self.assertGreaterEqual(db.query(SensitiveAccessLog).filter_by(action="review_teacher_report", actor_user_id=self.admin_id, result="denied_gap_ack").count(), 1)
            self.assertGreaterEqual(db.query(SensitiveAccessLog).filter_by(action="generate_teacher_review_report", actor_user_id=self.admin_id).count(), 1)
            self.assertGreaterEqual(db.query(SensitiveAccessLog).filter_by(action="download_teacher_review_report", actor_user_id=self.admin_id).count(), 1)
        finally:
            db.close()

    def test_regular_teacher_report_requires_approved_request_scope(self):
        denied = self.teacher_client.post(f"/api/teacher/students/{self.student_id}/review-reports")
        self.assertEqual(denied.status_code, 403)
        submitted = self.teacher_client.post(
            f"/api/teacher/students/{self.student_id}/access-requests",
            json={"reason": "需要结合授权记录形成可审签的支持报告", "scope": "recent_30_days"},
        )
        request_id = submitted.json()["request_id"]
        approved = self.admin_client.post(
            f"/api/teacher/access-requests/{request_id}/decision",
            json={"decision": "approved", "note": "同意最小必要范围"},
        )
        self.assertEqual(approved.status_code, 200)
        generated = self.teacher_client.post(
            f"/api/teacher/students/{self.student_id}/review-reports",
            params={"request_id": request_id},
        )
        self.assertEqual(generated.status_code, 200, generated.text)
        report_id = generated.json()["report_id"]
        self.assertEqual(self.teacher_client.get(f"/api/teacher/students/{self.student_id}/review-reports/latest").json()["report_id"], report_id)
        self.assertEqual(self.teacher_client.get(
            f"/api/teacher/students/{self.student_id}/review-reports/latest",
            params={"request_id": request_id + 9999},
        ).status_code, 403)
        self.assertEqual(self.teacher_client.get(
            f"/api/teacher/students/{self.student_id}/review-reports/latest",
            params={"request_id": request_id},
        ).json()["report_id"], report_id)
        revision_without_note = self.teacher_client.post(
            f"/api/teacher/students/{self.student_id}/review-reports/{report_id}/decision",
            params={"request_id": request_id},
            json={"decision": "revision_requested", "checklist_confirmed": False, "note": ""},
        )
        self.assertEqual(revision_without_note.status_code, 400)
        revision = self.teacher_client.post(
            f"/api/teacher/students/{self.student_id}/review-reports/{report_id}/decision",
            params={"request_id": request_id},
            json={"decision": "revision_requested", "checklist_confirmed": False, "note": "需要补充学生愿意接受的支持方式"},
        )
        self.assertEqual(revision.status_code, 200)
        blocked_sign = self.teacher_client.post(
            f"/api/teacher/students/{self.student_id}/review-reports/{report_id}/decision",
            params={"request_id": request_id},
            json={"decision": "reviewed", "checklist_confirmed": True, "note": "直接签署"},
        )
        self.assertEqual(blocked_sign.status_code, 409)
        revised = self.teacher_client.post(
            f"/api/teacher/students/{self.student_id}/review-reports",
            params={"request_id": request_id},
        )
        self.assertEqual(revised.status_code, 200)
        self.assertEqual(revised.json()["revision_number"], 2)
        self.assertEqual(revised.json()["parent_report_id"], report_id)

    def test_report_model_only_receives_deidentified_structured_fields(self):
        model_payload = '{"summary_focus":"functioning","opening_style":"open_choice"}'
        mocked = AsyncMock(return_value=model_payload)
        with patch("api.teacher.student_external_ai_allowed", return_value=True), patch("teacher_review_engine.is_spark_available", return_value=True), patch("teacher_review_engine.ask_spark", mocked):
            generated = self.admin_client.post(f"/api/teacher/students/{self.student_id}/review-reports")
        self.assertEqual(generated.status_code, 200, generated.text)
        report = generated.json()
        self.assertEqual(report["generation"]["source"], "xunfei_constrained")
        self.assertTrue(report["generation"]["external_transfer"])
        self.assertIn("建议教师先核对", report["executive_summary"])
        self.assertIn("可以选择暂时不回答", report["support_plan"]["conversation_opening"])
        prompt = str(mocked.await_args.args[0])
        self.assertNotIn("最近早上不太想去学校", prompt)
        self.assertNotIn("我和同学相处得有点累", prompt)
        self.assertIn("source_counts", prompt)

    def test_failed_external_report_attempt_is_audited_and_dangerous_words_degrade(self):
        unsafe_payload = '{"summary_focus":"达到重度抑郁","opening_style":"保证绝对保密"}'
        mocked = AsyncMock(return_value=unsafe_payload)
        with patch("api.teacher.student_external_ai_allowed", return_value=True), patch("teacher_review_engine.is_spark_available", return_value=True), patch("teacher_review_engine.ask_spark", mocked):
            generated = self.admin_client.post(f"/api/teacher/students/{self.student_id}/review-reports")
        self.assertEqual(generated.status_code, 200, generated.text)
        generation = generated.json()["generation"]
        self.assertTrue(generation["external_transfer_attempted"])
        self.assertFalse(generation["external_transfer_succeeded"])
        self.assertEqual(generation["external_transfer_failure"], "invalid_or_unsafe_output")
        self.assertTrue(generation["transferred_fields"])
        self.assertNotIn("绝对保密", generated.json()["support_plan"]["conversation_opening"])
        db = self.Session()
        try:
            self.assertGreaterEqual(db.query(SensitiveAccessLog).filter_by(action="external_ai_transfer_attempt", actor_user_id=self.admin_id, result="failed_safe_degrade").count(), 1)
        finally:
            db.close()

    def test_urgent_report_stops_ordinary_plan_and_uses_safety_specific_evidence(self):
        db = self.Session()
        try:
            db.add(ChatMessage(user_id=self.student_id, role="user", content="我想死，不想再继续了", emotion="需要立即协助", created_at=datetime.now()))
            db.commit()
        finally:
            db.close()
        generated = self.admin_client.post(f"/api/teacher/students/{self.student_id}/review-reports")
        self.assertEqual(generated.status_code, 200, generated.text)
        report = generated.json()
        self.assertEqual(report["overall_decision"]["risk_level"], "urgent")
        self.assertTrue(report["safety_review"]["ordinary_plan_stopped"])
        self.assertGreaterEqual(len(report["safety_review"]["immediate_actions"]), 3)
        self.assertEqual(report["support_plan"]["tasks"], [])
        self.assertEqual(report["support_plan"]["questions"], [])
        self.assertEqual(report["support_plan"]["conversation_opening"], "")
        self.assertEqual({item["code"] for item in report["evidence_sources"]}, {"NICE-NG225", "WHO-SHS-2021"})

    def test_insufficient_evidence_report_cannot_be_signed(self):
        db = self.Session()
        try:
            db.query(MoodRecord).filter(MoodRecord.user_id == self.student_id).delete()
            db.query(ChatMessage).filter(ChatMessage.user_id == self.student_id).delete()
            db.commit()
        finally:
            db.close()
        generated = self.admin_client.post(f"/api/teacher/students/{self.student_id}/review-reports")
        self.assertEqual(generated.status_code, 200, generated.text)
        report = generated.json()
        self.assertEqual(report["evidence_audit"]["status"], "insufficient")
        signed = self.admin_client.post(
            f"/api/teacher/students/{self.student_id}/review-reports/{report['report_id']}/decision",
            json={"decision": "reviewed", "checklist_confirmed": True, "evidence_gap_acknowledged": True, "note": "已确认当前没有足够证据"},
        )
        self.assertEqual(signed.status_code, 409)
        db = self.Session()
        try:
            self.assertEqual(db.query(TeacherReviewReport).filter_by(report_id=report["report_id"], status="draft").count(), 1)
            self.assertGreaterEqual(db.query(SensitiveAccessLog).filter_by(action="review_teacher_report", actor_user_id=self.admin_id, result="denied_evidence_gate").count(), 1)
        finally:
            db.close()

    def test_report_decision_uses_compare_and_swap_for_terminal_state(self):
        generated = self.admin_client.post(f"/api/teacher/students/{self.student_id}/review-reports")
        self.assertEqual(generated.status_code, 200, generated.text)
        report_id = generated.json()["report_id"]
        with patch("sqlalchemy.orm.Query.update", return_value=0):
            raced = self.admin_client.post(
                f"/api/teacher/students/{self.student_id}/review-reports/{report_id}/decision",
                json={"decision": "revision_requested", "checklist_confirmed": False, "note": "并发审核操作测试"},
            )
        self.assertEqual(raced.status_code, 409, raced.text)
        db = self.Session()
        try:
            self.assertEqual(db.query(TeacherReviewReport).filter_by(report_id=report_id, status="draft").count(), 1)
            self.assertEqual(db.query(TeacherReviewReportDecision).filter_by(report_id=report_id).count(), 0)
            self.assertGreaterEqual(db.query(SensitiveAccessLog).filter_by(action="review_teacher_report", actor_user_id=self.admin_id, result="denied_concurrent_terminal").count(), 1)
        finally:
            db.close()

    def test_model_narrative_rejects_diagnosis_names_and_qualitative_probability(self):
        unsafe_summaries = [
            "这些结构化信息符合抑郁障碍表现，建议教师据此作出判断并安排后续。",
            "这些结构化信息高度提示自闭症，建议教师据此作出判断并安排后续。",
            "这些结构化信息显示学生有六成会持续恶化，应当由教师立刻据此判断。",
            "这些结构化信息显示学生十有八九会持续恶化，应当由教师立刻据此判断。",
            "这些结构化信息达到重度抑郁，老师应据此安排支持。",
            "这些结构化信息高度符合孤独谱系障碍，老师应据此安排支持。",
            "这些结构化信息超过一半的可能会持续恶化，老师应据此安排支持。",
        ]
        for summary in unsafe_summaries:
            with self.subTest(summary=summary):
                candidate = NarrativeOutput(
                    executive_summary=summary,
                    conversation_opening="我想先听听你愿意分享的部分，也可以暂时不回答。",
                )
                self.assertFalse(_safe_model_narrative(candidate))


if __name__ == "__main__":
    unittest.main()
