import json
import sys
import unittest
from datetime import datetime, timedelta
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

from api.assessment import router as assessment_router
from api.island import router as island_router
from api.user import router as user_router
from config import settings
from database import Base, get_db
from models import IslandReport, SensitiveAccessLog, StudentAssessmentAgentRun, StudentExternalAiAuthorization, StudentWellbeingAssessment, User
from security import get_password_hash


def complete_answers(value="never"):
    return {
        "low_mood": value,
        "low_interest": value,
        "worry": value,
        "sleep": value,
        "energy": value,
        "concentration": value,
        "loneliness": value,
        "school_impact": value,
        "home_impact": value,
    }


class StudentWellbeingAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.old_external = settings.ALLOW_EXTERNAL_AI
        self.old_student_external = settings.ALLOW_STUDENT_EXTERNAL_AI
        settings.ALLOW_EXTERNAL_AI = False
        settings.ALLOW_STUDENT_EXTERNAL_AI = False
        app = FastAPI()
        app.include_router(user_router)
        app.include_router(assessment_router)
        app.include_router(island_router)

        def override_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        self.one = TestClient(app)
        self.two = TestClient(app)
        self.user_one = self.one.post("/api/user/demo-session").json()["user_id"]
        self.user_two = self.two.post("/api/user/demo-session").json()["user_id"]
        db = self.Session()
        teacher = User(username="assessment_teacher", password_hash=get_password_hash("TeacherPassword12"), nickname="教师", is_admin=1)
        db.add(teacher)
        db.commit()
        self.teacher_id = teacher.id
        db.close()

    def _authorize(self, user_id):
        db = self.Session()
        db.add(StudentExternalAiAuthorization(
            student_user_id=user_id,
            authorized_by_user_id=self.teacher_id,
            status="active",
            expires_at=datetime.now() + timedelta(days=30),
        ))
        db.commit()
        db.close()

    def tearDown(self):
        self.one.close()
        self.two.close()
        settings.ALLOW_EXTERNAL_AI = self.old_external
        settings.ALLOW_STUDENT_EXTERNAL_AI = self.old_student_external
        self.engine.dispose()

    def test_routine_assessment_is_structured_audited_and_has_no_score(self):
        schema = self.one.get("/api/assessment/schema")
        self.assertEqual(schema.status_code, 200)
        response = self.one.post("/api/assessment/submit", json={
            "answers": complete_answers("never"),
            "emotions": ["平静"],
            "self_harm": "no",
            "unsafe_home": "no",
        })
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["risk_level"], "routine")
        self.assertEqual(len(payload["domains"]), 4)
        self.assertEqual(len(payload["pipeline"]), 6)
        self.assertEqual(len(payload["agent_runs"]), 6)
        self.assertEqual(len(payload["review_findings"]), 3)
        rendered = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("总分", rendered)
        self.assertNotIn("确诊", rendered)
        self.assertNotIn("mood_avg", rendered)
        self.assertIn("不是经验证的心理量表", payload["boundary"])
        self.assertEqual(payload["emotion_intensity"], "未单独推断")
        self.assertEqual(payload["review_status"], "needs_professional_review")
        self.assertEqual(self.one.get("/api/assessment/latest").json()["assessment"]["assessment_code"], payload["assessment_code"])

        db = self.Session()
        try:
            row = db.query(StudentWellbeingAssessment).one()
            self.assertEqual(row.user_id, self.user_one)
            self.assertEqual(db.query(StudentAssessmentAgentRun).filter_by(assessment_id=row.id).count(), 6)
            self.assertEqual(db.query(SensitiveAccessLog).filter_by(action="create_self_assessment").count(), 1)
        finally:
            db.close()

    def test_urgent_answers_override_all_ordinary_planning(self):
        answers = complete_answers("several_days")
        response = self.one.post("/api/assessment/submit", json={
            "answers": answers,
            "emotions": ["害怕"],
            "self_harm": "yes",
            "unsafe_home": "no",
        })
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["risk_level"], "urgent")
        self.assertGreaterEqual(len(payload["safety_actions"]), 3)
        statuses = {step["id"]: step["status"] for step in payload["pipeline"]}
        self.assertEqual(statuses["safety"], "attention")
        self.assertEqual(statuses["planning"], "blocked")
        self.assertIn("12356", json.dumps(payload, ensure_ascii=False))
        self.assertEqual(payload["review_status"], "needs_professional_review")
        report = self.one.post("/api/island/report/generate", json={"days": 7})
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.json()["status"], "blocked")
        self.assertTrue(report.json()["crisis"])
        self.assertEqual(report.json()["report_code"], "")
        db = self.Session()
        try:
            self.assertEqual(db.query(IslandReport).count(), 0)
        finally:
            db.close()

    def test_watch_and_professional_actions_are_deterministic_and_skip_model(self):
        settings.ALLOW_EXTERNAL_AI = True
        settings.ALLOW_STUDENT_EXTERNAL_AI = True
        self._authorize(self.user_one)
        watch_answers = complete_answers("never")
        watch_answers["low_mood"] = "several_days"
        watch_answers["sleep"] = "several_days"
        professional_answers = complete_answers("never")
        professional_answers["school_impact"] = "nearly_every_day"

        with patch("agents.wellbeing_assessment.ask_spark", new=AsyncMock()) as mocked:
            watch = self.one.post("/api/assessment/submit", json={
                "answers": watch_answers,
                "emotions": ["难过"],
                "self_harm": "no",
                "unsafe_home": "no",
            }).json()
            professional = self.one.post("/api/assessment/submit", json={
                "answers": professional_answers,
                "emotions": ["疲惫"],
                "self_harm": "no",
                "unsafe_home": "no",
            }).json()

        mocked.assert_not_awaited()
        self.assertEqual(watch["risk_level"], "watch")
        self.assertIn("24小时内", watch["priority_action"])
        self.assertEqual(professional["risk_level"], "professional")
        self.assertIn("今天", professional["priority_action"])
        self.assertIn("可信成年人", professional["priority_action"])
        self.assertEqual(watch["review_status"], "needs_professional_review")
        self.assertEqual(professional["review_status"], "needs_professional_review")

        self.assertEqual(watch["pipeline"][4]["agent"], "CrossReviewer")

        watch_assessment = self.two.post("/api/assessment/submit", json={
            "answers": watch_answers,
            "emotions": ["难过"],
            "self_harm": "no",
            "unsafe_home": "no",
        })
        self.assertEqual(watch_assessment.status_code, 201)
        watch_island = self.two.post("/api/island/agent/run", json={"trigger": "manual"})
        professional_run = self.one.post("/api/island/agent/run", json={"trigger": "manual"})
        self.assertEqual(watch_island.status_code, 200)
        self.assertEqual(watch_island.json()["safety_status"], "watch")
        self.assertEqual(watch_island.json()["plan"]["data"]["plan"]["strategy"], "watch_support")
        self.assertEqual(professional_run.status_code, 200)
        self.assertEqual(professional_run.json()["safety_status"], "professional")
        self.assertEqual(professional_run.json()["plan"]["data"]["plan"]["strategy"], "professional_support")
        self.assertEqual(professional_run.json()["companion"]["status"], "skipped")

    def test_routine_model_can_only_rewrite_safe_summary(self):
        settings.ALLOW_EXTERNAL_AI = True
        settings.ALLOW_STUDENT_EXTERNAL_AI = True
        self._authorize(self.user_one)
        safe_model = AsyncMock(return_value=json.dumps({
            "summary": "本次主动选择的情绪是平静，近两周回答未见明显影响。",
        }, ensure_ascii=False))
        with patch("agents.wellbeing_assessment.ask_spark", new=safe_model):
            result = self.one.post("/api/assessment/submit", json={
                "answers": complete_answers("never"),
                "emotions": ["平静"],
                "self_harm": "no",
                "unsafe_home": "no",
            }).json()

        safe_model.assert_awaited_once()
        self.assertEqual(result["model_name"], "xunfei-constrained")
        self.assertEqual(result["emotion_summary"], "本次主动选择的情绪是平静，近两周回答未见明显影响。")
        self.assertEqual(result["priority_action"], "从一项五分钟以内、不会增加负担的自我照顾行动开始。")

    def test_routine_model_advice_is_rejected_and_degraded(self):
        settings.ALLOW_EXTERNAL_AI = True
        settings.ALLOW_STUDENT_EXTERNAL_AI = True
        self._authorize(self.user_one)
        unsafe_model = AsyncMock(return_value=json.dumps({
            "summary": "你应该立即接受治疗并按我的建议行动。",
        }, ensure_ascii=False))
        with patch("agents.wellbeing_assessment.ask_spark", new=unsafe_model):
            result = self.one.post("/api/assessment/submit", json={
                "answers": complete_answers("never"),
                "emotions": [],
                "self_harm": "no",
                "unsafe_home": "no",
            }).json()

        self.assertTrue(result["degraded"])
        self.assertEqual(result["model_name"], "deterministic-assessment")
        self.assertEqual(result["emotion_summary"], "本次没有选择明确的情绪词")
        self.assertEqual(result["review_status"], "needs_professional_review")

    def test_incomplete_payload_and_cross_user_delete_are_rejected(self):
        incomplete = complete_answers()
        incomplete.pop("sleep")
        self.assertEqual(self.one.post("/api/assessment/submit", json={
            "answers": incomplete, "emotions": [], "self_harm": "no", "unsafe_home": "no",
        }).status_code, 422)
        created = self.one.post("/api/assessment/submit", json={
            "answers": complete_answers(), "emotions": [], "self_harm": "no", "unsafe_home": "no",
        }).json()
        code = created["assessment_code"]
        self.assertEqual(self.two.delete(f"/api/assessment/{code}").status_code, 404)
        self.assertEqual(self.one.delete(f"/api/assessment/{code}").status_code, 204)
        self.assertIsNone(self.one.get("/api/assessment/latest").json()["assessment"])


if __name__ == "__main__":
    unittest.main()
