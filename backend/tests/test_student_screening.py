import json
import sys
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import api.chat as chat_api
import screening_engine
from agents.tools import get_user_safety_state
from api.chat import router as chat_router
from api.companion import router as companion_router
from api.screening import router as screening_router
from api.teacher import router as teacher_router
from api.user import router as user_router
from app_time import china_now_naive
from config import settings
from database import Base, get_db
from models import (
    SensitiveAccessLog,
    StudentChatSession,
    StudentScreeningRun,
    TeacherStudentAssignment,
    User,
)
from security import get_password_hash


def answers_total(total):
    """把总分从左到右按 0~3 填满；第9题只会在总分 25 以上被填到。"""
    remaining = total
    answers = {}
    for item in range(1, 10):
        value = min(3, remaining)
        answers[str(item)] = value
        remaining -= value
    if remaining:
        raise ValueError("total out of range")
    return answers


def answers_item9(value=2):
    answers = {str(item): 0 for item in range(1, 10)}
    answers["9"] = value
    return answers


def answers_with_item9(total, item9=1):
    """第9题为正、总分指定的答卷；其余分数优先填前 8 题。"""
    if not 1 <= item9 <= 3 or not item9 <= total <= item9 + 24:
        raise ValueError("total out of range")
    answers = {str(item): 0 for item in range(1, 10)}
    answers["9"] = item9
    remaining = total - item9
    for item in range(1, 9):
        value = min(3, remaining)
        answers[str(item)] = value
        remaining -= value
    if remaining:
        raise ValueError("total out of range")
    return answers


class StudentScreeningTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.old_settings = {
            "STUDENT_SCREENING_ENABLED": settings.STUDENT_SCREENING_ENABLED,
            "ALLOW_EXTERNAL_AI": settings.ALLOW_EXTERNAL_AI,
            "ALLOW_STUDENT_EXTERNAL_AI": settings.ALLOW_STUDENT_EXTERNAL_AI,
            "STUDENT_AI_ACCESS_MODE": settings.STUDENT_AI_ACCESS_MODE,
            "PLATFORM_STUDENT_AI_GOVERNANCE_ACK": settings.PLATFORM_STUDENT_AI_GOVERNANCE_ACK,
            "STUDENT_COMPANION_ENGINE": settings.STUDENT_COMPANION_ENGINE,
            "DEEPSEEK_API_KEY": settings.DEEPSEEK_API_KEY,
        }
        self.old_ask_deepseek = chat_api.ask_deepseek
        settings.STUDENT_SCREENING_ENABLED = True
        settings.ALLOW_EXTERNAL_AI = False
        settings.ALLOW_STUDENT_EXTERNAL_AI = False
        settings.STUDENT_AI_ACCESS_MODE = "platform_direct"
        settings.PLATFORM_STUDENT_AI_GOVERNANCE_ACK = True
        settings.STUDENT_COMPANION_ENGINE = "deepseek"
        settings.DEEPSEEK_API_KEY = ""

        app = FastAPI()
        app.include_router(user_router)
        app.include_router(screening_router)
        app.include_router(chat_router)
        app.include_router(companion_router)
        app.include_router(teacher_router)

        def override_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        self.app = app
        self.student = TestClient(app)
        self.other_student = TestClient(app)
        self.teacher = TestClient(app)
        self.unassigned_teacher = TestClient(app)
        self.admin = TestClient(app)
        self.student_id = self.student.post("/api/user/demo-session").json()["user_id"]
        self.other_student_id = self.other_student.post("/api/user/demo-session").json()["user_id"]
        db = self.Session()
        try:
            teacher = User(username="screen_teacher", password_hash=get_password_hash("TeacherPassword12"),
                           nickname="筛查教师", is_admin=1)
            unassigned = User(username="screen_other_teacher",
                              password_hash=get_password_hash("TeacherPassword12"),
                              nickname="未分配教师", is_admin=1)
            admin = User(username="screen_admin", password_hash=get_password_hash("AdminPassword12"),
                         nickname="管理员教师", is_admin=2)
            db.add_all([teacher, unassigned, admin])
            db.commit()
            self.teacher_id = teacher.id
            self.admin_id = admin.id
            db.add(TeacherStudentAssignment(
                teacher_user_id=teacher.id,
                student_user_id=self.student_id,
                assigned_by_user_id=admin.id,
                active=1,
            ))
            db.commit()
        finally:
            db.close()
        self.teacher.post("/api/user/login", json={"username": "screen_teacher", "password": "TeacherPassword12"})
        self.unassigned_teacher.post(
            "/api/user/login", json={"username": "screen_other_teacher", "password": "TeacherPassword12"})
        self.admin.post("/api/user/login", json={"username": "screen_admin", "password": "AdminPassword12"})

    def tearDown(self):
        for client in (self.student, self.other_student, self.teacher, self.unassigned_teacher, self.admin):
            client.close()
        for key, value in self.old_settings.items():
            setattr(settings, key, value)
        chat_api.ask_deepseek = self.old_ask_deepseek
        self.engine.dispose()

    def _submit(self, client=None, answers=None, ack=True):
        return (client or self.student).post("/api/screening/submit", json={
            "answers": answers or answers_total(9),
            "disclosure_ack": ack,
        })

    def _new_session(self, client=None):
        return (client or self.student).post(
            "/api/chat/sessions", json={"force_new": True}
        ).json()["session_id"]

    # ── 功能开关与 schema ────────────────────────────────

    def test_schema_is_hidden_until_enabled_and_describes_consent(self):
        settings.STUDENT_SCREENING_ENABLED = False
        self.assertEqual(self.student.get("/api/screening/schema").status_code, 404)
        self.assertEqual(self._submit().status_code, 404)
        settings.STUDENT_SCREENING_ENABLED = True

        schema = self.student.get("/api/screening/schema")
        self.assertEqual(schema.status_code, 200)
        payload = schema.json()
        self.assertEqual(payload["instrument"], "phq9")
        self.assertEqual(len(payload["items"]), 9)
        self.assertEqual([option["value"] for option in payload["options"]], [0, 1, 2, 3])
        self.assertIn("不是诊断", payload["boundary"])
        self.assertIn("不发送给外部模型", payload["disclosure"])
        self.assertIn("90", payload["disclosure"])
        self.assertIn("看不到每道题", payload["disclosure"])
        self.assertNotIn("抑郁", json.dumps(payload, ensure_ascii=False))

    # ── 计分与分级边界 ───────────────────────────────────

    def test_scoring_bands_and_risk_never_downgrade(self):
        expected = {
            0: ("minimal", "无明显", "routine"),
            4: ("minimal", "无明显", "routine"),
            5: ("mild", "轻度", "routine"),
            9: ("mild", "轻度", "routine"),
            10: ("moderate", "中度", "watch"),
            14: ("moderate", "中度", "watch"),
            15: ("moderately_severe", "中重度", "professional"),
            19: ("moderately_severe", "中重度", "professional"),
            20: ("severe", "重度", "professional"),
            27: ("severe", "重度", "professional"),
        }
        for total, (band, label, risk) in expected.items():
            with self.subTest(total=total):
                self.assertEqual(screening_engine.band_for(total), (band, label))
                self.assertEqual(screening_engine.risk_for(total, False), risk)
                self.assertEqual(screening_engine.risk_for(total, True), "urgent")
        self.assertEqual(screening_engine.merge_risk("routine", "watch"), "watch")
        self.assertEqual(screening_engine.merge_risk("watch", "professional"), "professional")
        self.assertEqual(screening_engine.merge_risk("professional", "urgent"), "urgent")
        self.assertEqual(screening_engine.merge_risk(None, "routine"), "routine")

    def test_score_rejects_incomplete_or_out_of_range_answers(self):
        incomplete = answers_total(9)
        incomplete.pop("5")
        with self.assertRaises(ValueError):
            screening_engine.score(incomplete)
        extra = answers_total(9)
        extra["10"] = 1
        with self.assertRaises(ValueError):
            screening_engine.score(extra)
        for bad in (4, -1, True, "2", 1.5):
            answers = answers_total(9)
            answers["3"] = bad
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    screening_engine.score(answers)

    # ── 提交、持久化、删除 ───────────────────────────────

    def test_submit_persists_server_side_answers_and_returns_band_without_items(self):
        response = self._submit(answers=answers_total(12))
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["band"], "moderate")
        self.assertEqual(payload["band_label"], "中度")
        self.assertEqual(payload["total_score"], 12)
        self.assertFalse(payload["item9_positive"])
        self.assertFalse(payload["urgent"])
        self.assertIn("不是诊断", payload["boundary"])
        rendered = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("做事时提不起劲", rendered)
        self.assertNotIn("answers", rendered)

        db = self.Session()
        try:
            row = db.query(StudentScreeningRun).one()
            self.assertEqual(row.user_id, self.student_id)
            self.assertEqual(row.total_score, 12)
            self.assertEqual(json.loads(row.answers_json)["1"], 3)
            self.assertEqual(
                db.query(SensitiveAccessLog).filter_by(action="create_student_screening").count(), 1)
        finally:
            db.close()

        latest = self.student.get("/api/screening/latest").json()["screening"]
        self.assertEqual(latest["run_code"], payload["run_code"])
        self.assertIsNone(self.other_student.get("/api/screening/latest").json()["screening"])

        self.assertEqual(self.other_student.delete(f"/api/screening/{payload['run_code']}").status_code, 404)
        self.assertEqual(self.student.delete(f"/api/screening/{payload['run_code']}").status_code, 204)
        self.assertIsNone(self.student.get("/api/screening/latest").json()["screening"])
        db = self.Session()
        try:
            row = db.query(StudentScreeningRun).one()
            self.assertIsNotNone(row.deleted_at)
            self.assertEqual(row.answers_json, "{}")
            self.assertEqual(db.query(SensitiveAccessLog).filter_by(action="delete_student_screening").count(), 1)
        finally:
            db.close()

    def test_invalid_submissions_are_rejected(self):
        self.assertEqual(self._submit(answers=answers_total(9), ack=False).status_code, 400)
        missing = answers_total(9)
        missing.pop("9")
        self.assertEqual(self._submit(answers=missing).status_code, 422)
        extra = answers_total(9)
        extra["10"] = 0
        self.assertEqual(self._submit(answers=extra).status_code, 422)
        for bad in (4, -1, True, "2"):
            answers = answers_total(9)
            answers["2"] = bad
            with self.subTest(bad=bad):
                self.assertEqual(self._submit(answers=answers).status_code, 422)
        self.assertEqual(self.student.post("/api/screening/submit", json={
            "answers": answers_total(9), "disclosure_ack": True, "extra": 1,
        }).status_code, 422)

    def test_expired_screening_is_cleaned_and_hidden(self):
        created = self._submit(answers=answers_total(12)).json()
        db = self.Session()
        try:
            row = db.query(StudentScreeningRun).one()
            row.expires_at = china_now_naive() - timedelta(days=1)
            db.commit()
        finally:
            db.close()
        self.assertIsNone(self.student.get("/api/screening/latest").json()["screening"])
        db = self.Session()
        try:
            row = db.query(StudentScreeningRun).filter_by(run_code=created["run_code"]).one()
            self.assertIsNotNone(row.deleted_at)
            self.assertEqual(row.answers_json, "{}")
        finally:
            db.close()

    # ── 第9题与安全交接 ─────────────────────────────────

    def test_item9_creates_urgent_session_and_resolve_clears_safety_flag(self):
        session_id = self._new_session()
        response = self._submit(answers=answers_item9(2))
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["band"], "minimal")
        self.assertEqual(payload["total_score"], 2)
        self.assertTrue(payload["item9_positive"])
        self.assertTrue(payload["urgent"])
        self.assertEqual(payload["urgent_session_id"], session_id)

        db = self.Session()
        try:
            row = db.query(StudentScreeningRun).one()
            self.assertEqual(row.safety_flag_active, 1)
            session = db.query(StudentChatSession).filter_by(session_code=session_id).one()
            self.assertEqual(session.status, "urgent")
            self.assertEqual(screening_engine.active_screening_risk(db, self.student_id), "urgent")
        finally:
            db.close()

        latest = self.student.get("/api/screening/latest").json()["screening"]
        self.assertTrue(latest["urgent"])
        self.assertEqual(latest["urgent_session_id"], session_id)
        self.assertEqual(
            self.student.delete(f"/api/screening/{payload['run_code']}").status_code, 409)

        resolved = self.student.post(f"/api/chat/sessions/{session_id}/resolve-safety", json={
            "current_safe": True, "contacted_trusted_adult": True,
        })
        self.assertEqual(resolved.status_code, 200)
        db = self.Session()
        try:
            row = db.query(StudentScreeningRun).one()
            self.assertEqual(row.safety_flag_active, 0)
            self.assertEqual(screening_engine.active_screening_risk(db, self.student_id), "routine")
            self.assertEqual(
                db.query(SensitiveAccessLog).filter_by(
                    action="resolve_student_screening_safety").count(), 1)
        finally:
            db.close()
        self.assertFalse(self.student.get("/api/screening/latest").json()["screening"]["urgent"])
        self.assertEqual(self.student.delete(f"/api/screening/{payload['run_code']}").status_code, 204)

    # ── 聊天、小结、宠物与 Agent 风险合并 ───────────────

    def test_professional_screening_skips_model_and_returns_support_template(self):
        settings.ALLOW_EXTERNAL_AI = True
        settings.ALLOW_STUDENT_EXTERNAL_AI = True
        settings.DEEPSEEK_API_KEY = "test-key"
        session_id = self._new_session()
        self._submit(answers=answers_total(15))
        mocked = AsyncMock()
        chat_api.ask_deepseek = mocked

        response = self.student.post("/api/chat/send", json={
            "user_id": self.student_id, "session_id": session_id, "message": "今天有点累，想随便聊聊。",
        })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        mocked.assert_not_awaited()
        self.assertEqual(payload["risk_level"], "professional")
        self.assertEqual(payload["analysis_source"], "deterministic")
        self.assertIn("可信成年人", payload["reply"])

    def test_professional_screening_acknowledgement_restores_chat_and_keeps_result(self):
        session_id = self._new_session()
        created = self._submit(answers=answers_total(15)).json()
        denied = self.student.post("/api/screening/acknowledge", json={
            "contacted_trusted_adult": False,
        })
        self.assertEqual(denied.status_code, 400)

        response = self.student.post("/api/screening/acknowledge", json={
            "contacted_trusted_adult": True,
        })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["acknowledged"])
        self.assertIsNotNone(payload["acknowledged_at"])
        self.assertEqual(payload["risk_level"], "watch")
        self.assertEqual(payload["total_score"], 15)
        self.assertEqual(payload["band"], "moderately_severe")
        self.assertFalse(payload["urgent"])

        latest = self.student.get("/api/screening/latest").json()["screening"]
        self.assertTrue(latest["acknowledged"])
        self.assertEqual(latest["run_code"], created["run_code"])
        self.assertEqual(latest["total_score"], 15)

        chat = self.student.post("/api/chat/send", json={
            "user_id": self.student_id, "session_id": session_id, "message": "今天有点累，想随便聊聊。",
        })
        self.assertEqual(chat.status_code, 200)
        self.assertEqual(chat.json()["risk_level"], "watch")
        self.assertNotIn("这些影响已经不适合只靠你自己扛着", chat.json()["reply"])

        # 重复确认保持幂等，不重复写审计。
        self.assertEqual(self.student.post("/api/screening/acknowledge", json={
            "contacted_trusted_adult": True,
        }).status_code, 200)
        db = self.Session()
        try:
            row = db.query(StudentScreeningRun).filter_by(run_code=created["run_code"]).one()
            self.assertIsNotNone(row.acknowledged_at)
            self.assertEqual(row.total_score, 15)
            self.assertEqual(
                db.query(SensitiveAccessLog).filter_by(
                    action="acknowledge_student_screening").count(), 1)
        finally:
            db.close()

    def test_watch_screening_raises_chat_risk_without_crisis_lock(self):
        settings.ALLOW_EXTERNAL_AI = False
        session_id = self._new_session()
        self._submit(answers=answers_total(12))
        response = self.student.post("/api/chat/send", json={
            "user_id": self.student_id, "session_id": session_id, "message": "今天有点累，想随便聊聊。",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["risk_level"], "watch")
        self.assertEqual(response.json()["conversation_signal"], "continue")

    def test_urgent_screening_forces_safety_override_in_chat(self):
        session_id = self._new_session()
        self._submit(answers=answers_item9(1))
        response = self.student.post("/api/chat/send", json={
            "user_id": self.student_id, "session_id": session_id, "message": "今天有点累，想随便聊聊。",
        })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["risk_level"], "urgent")
        self.assertEqual(payload["analysis_source"], "safety_override")
        self.assertIn("12356", payload["reply"])

    def test_urgent_handoff_then_acknowledgement_does_not_relock_chat(self):
        session_id = self._new_session()
        created = self._submit(answers=answers_with_item9(16, 1)).json()
        self.assertTrue(created["urgent"])
        blocked = self.student.post("/api/screening/acknowledge", json={
            "contacted_trusted_adult": True,
        })
        self.assertEqual(blocked.status_code, 409)

        resolved = self.student.post(f"/api/chat/sessions/{session_id}/resolve-safety", json={
            "current_safe": True, "contacted_trusted_adult": True,
        })
        self.assertEqual(resolved.status_code, 200)
        db = self.Session()
        try:
            row = db.query(StudentScreeningRun).filter_by(run_code=created["run_code"]).one()
            self.assertEqual(row.safety_flag_active, 0)
            self.assertIsNotNone(row.acknowledged_at)
            self.assertEqual(screening_engine.active_screening_risk(db, self.student_id), "watch")
        finally:
            db.close()

        latest = self.student.get("/api/screening/latest").json()["screening"]
        self.assertTrue(latest["acknowledged"])
        self.assertFalse(latest["urgent"])
        self.assertEqual(latest["risk_level"], "watch")

        chat = self.student.post("/api/chat/send", json={
            "user_id": self.student_id, "message": "现在想聊聊学校的事。",
        })
        self.assertEqual(chat.status_code, 200)
        self.assertEqual(chat.json()["risk_level"], "watch")
        self.assertNotEqual(chat.json()["analysis_source"], "safety_override")

    def test_professional_screening_raises_summary_risk_and_template(self):
        settings.ALLOW_EXTERNAL_AI = False
        session_id = self._new_session()
        self._submit(answers=answers_total(15))
        self.student.post("/api/chat/send", json={
            "user_id": self.student_id, "session_id": session_id, "message": "今天有点累，想随便聊聊。",
        })
        summary = self.student.post(f"/api/chat/sessions/{session_id}/complete")
        self.assertEqual(summary.status_code, 200)
        body = summary.json()
        self.assertEqual(body["status"], "ready")
        self.assertEqual(body["summary"]["risk_level"], "professional")
        self.assertIn("可信成年人", body["summary"]["support_need"])
        self.assertNotIn("总分", json.dumps(body, ensure_ascii=False))

    def test_agent_tools_and_companion_merge_screening_risk(self):
        self._submit(answers=answers_total(15))
        db = self.Session()
        try:
            state = get_user_safety_state(db, self.student_id)
        finally:
            db.close()
        self.assertEqual(state, {"risk_level": "professional", "evidence": "current_standard_screening"})

        companion = self.student.post("/api/companion/chat", json={"content": "今天有点累"})
        self.assertEqual(companion.status_code, 200)
        self.assertEqual(companion.json()["risk_level"], "professional")
        self.assertTrue(companion.json()["handoff_required"])

        self._submit(answers=answers_item9(3))
        urgent = self.student.post("/api/companion/chat", json={"content": "今天有点累"})
        self.assertEqual(urgent.status_code, 200)
        self.assertEqual(urgent.json()["risk_level"], "urgent")
        self.assertEqual(urgent.json()["mode"], "urgent")
        self.assertTrue(urgent.json()["handoff_required"])

    # ── 教师端 ───────────────────────────────────────────

    def test_teacher_roster_and_warning_show_band_total_without_answers(self):
        self._submit(answers=answers_total(12))
        listed = self.teacher.get("/api/teacher/student-list").json()["students"]
        student = next(item for item in listed if item["id"] == self.student_id)
        self.assertEqual(student["screening"]["band_label"], "中度")
        self.assertEqual(student["screening"]["total_score"], 12)
        self.assertNotIn("answers", json.dumps(student, ensure_ascii=False))
        self.assertNotIn(self.student_id, [item["id"] for item in
                                           self.unassigned_teacher.get("/api/teacher/student-list").json()["students"]])

        warnings = self.teacher.get("/api/teacher/warning-list").json()["warnings"]
        warning = next(item for item in warnings if item["student_id"] == self.student_id)
        self.assertIn("标准筛查", warning["reason"])
        self.assertFalse(warning["urgent"])

        self._submit(answers=answers_item9(2))
        warnings = self.teacher.get("/api/teacher/warning-list").json()["warnings"]
        warning = next(item for item in warnings if item["student_id"] == self.student_id)
        self.assertTrue(warning["urgent"])
        self.assertIn("第9题", warning["reason"])

    def test_teacher_profile_and_work_product_include_screening_summary_only(self):
        self._submit(answers=answers_total(15))
        profile = self.admin.get(f"/api/teacher/students/{self.student_id}/profile")
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json()["screening_summary"]["band_label"], "中重度")
        self.assertEqual(profile.json()["screening_summary"]["total_score"], 15)
        self.assertEqual(profile.json()["risk_level"], "high")

        product = self.admin.get(f"/api/teacher/students/{self.student_id}/work-product")
        self.assertEqual(product.status_code, 200)
        payload = product.json()
        self.assertEqual(payload["screening_summary"]["band_label"], "中重度")
        self.assertEqual(payload["screening_summary"]["total_score"], 15)
        self.assertFalse(payload["screening_summary"]["safety_active"])
        self.assertEqual(payload["risk"], "professional")
        sources = {record["source"] for record in payload["records"]}
        self.assertIn("标准筛查", sources)
        self.assertIn("15/27", json.dumps(payload["records"], ensure_ascii=False))
        self.assertTrue(any("1次标准筛查" in step["result"] for step in payload["pipeline"]))
        rendered = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("做事时提不起劲", rendered)
        self.assertNotIn('"answers"', rendered)


if __name__ == "__main__":
    unittest.main()
