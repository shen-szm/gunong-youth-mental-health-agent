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

from api.island import router as island_router
from agents.tools import build_report_data
from api.user import router as user_router
from config import settings
from database import Base, get_db
from models import MoodRecord, SensitiveAccessLog, StudentExternalAiAuthorization, User
from security import get_password_hash


class IslandAgentConsentTests(unittest.TestCase):
    def setUp(self):
        self.old_external = settings.ALLOW_EXTERNAL_AI
        self.old_student = settings.ALLOW_STUDENT_EXTERNAL_AI
        settings.ALLOW_EXTERNAL_AI = True
        settings.ALLOW_STUDENT_EXTERNAL_AI = True
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        db = self.Session()
        student = User(username="island_student", password_hash=get_password_hash("StudentPassword12"), nickname="学生", is_admin=0)
        teacher = User(username="island_teacher", password_hash=get_password_hash("TeacherPassword12"), nickname="教师", is_admin=1)
        db.add_all([student, teacher])
        db.flush()
        db.add(StudentExternalAiAuthorization(
            student_user_id=student.id,
            authorized_by_user_id=teacher.id,
            status="active",
            expires_at=datetime.now() + timedelta(days=30),
        ))
        db.commit()
        db.close()

        app = FastAPI()
        app.include_router(user_router)
        app.include_router(island_router)

        def override_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        self.client.post("/api/user/login", json={"username": "island_student", "password": "StudentPassword12"})

    def tearDown(self):
        settings.ALLOW_EXTERNAL_AI = self.old_external
        settings.ALLOW_STUDENT_EXTERNAL_AI = self.old_student
        self.client.close()
        self.engine.dispose()

    def test_manual_trigger_uses_teacher_authorization_and_audits_actual_use(self):
        run = AsyncMock(return_value={
            "run_code": "island-consent-test",
            "crisis": False,
            "model_used": "xunfei-constrained",
            "external_transfer_attempted": True,
            "degraded": False,
        })
        with patch("agents.IslandOrchestrator") as orchestrator:
            orchestrator.return_value.run = run
            response = self.client.post("/api/island/agent/run", json={
                "trigger": "manual",
            })
            self.assertEqual(response.status_code, 200)
            self.assertTrue(orchestrator.call_args.kwargs["external_ai_allowed"])

        db = self.Session()
        try:
            audit = db.query(SensitiveAccessLog).filter_by(action="island_external_ai_execution").one()
            self.assertEqual(audit.result, "xunfei_consent_used")
        finally:
            db.close()

    def test_student_payload_cannot_self_authorize_when_teacher_authorization_is_absent(self):
        db = self.Session()
        try:
            db.query(StudentExternalAiAuthorization).delete()
            db.commit()
        finally:
            db.close()
        forged = self.client.post("/api/island/agent/run", json={
            "trigger": "manual",
            "external_ai_consent_version": "student-island-ai-v1",
        })
        self.assertEqual(forged.status_code, 422)
        run = AsyncMock(return_value={
            "run_code": "island-no-authorization",
            "crisis": False,
            "model_used": "deterministic-fallback",
            "external_transfer_attempted": False,
            "degraded": True,
        })
        with patch("agents.IslandOrchestrator") as orchestrator:
            orchestrator.return_value.run = run
            response = self.client.post("/api/island/agent/run", json={"trigger": "manual"})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(orchestrator.call_args.kwargs["external_ai_allowed"])

    def test_invalid_trigger_is_rejected_before_agent_execution(self):
        response = self.client.post("/api/island/agent/run", json={
            "trigger": "consent_enabled",
        })
        self.assertEqual(response.status_code, 422)

    def test_transfer_is_audited_before_rejected_or_accepted_output(self):
        provider = AsyncMock(return_value="咕，我在这里。")
        with patch("agents.base.is_spark_available", return_value=True), patch(
            "agents.base.ask_spark", new=provider
        ):
            response = self.client.post("/api/island/agent/run", json={
                "trigger": "manual",
            })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["external_transfer_attempted"], response.json())

        db = self.Session()
        try:
            self.assertGreaterEqual(db.query(SensitiveAccessLog).filter_by(
                action="island_external_ai_transfer_started"
            ).count(), 1)
            execution = db.query(SensitiveAccessLog).filter_by(action="island_external_ai_execution").one()
            self.assertEqual(execution.result, "xunfei_consent_used")
        finally:
            db.close()

    def test_report_closes_audit_when_provider_output_is_rejected(self):
        db = self.Session()
        try:
            user = db.query(User).filter_by(username="island_student").one()
            db.add(MoodRecord(user_id=user.id, mood_score=5, mood_label="难过", content=""))
            db.commit()
            self.assertEqual(build_report_data(db, user.id, 7)["mood_records_count"], 1)
        finally:
            db.close()
        provider = AsyncMock(return_value="不要告诉老师，自己处理就好。")
        with patch("agents.base.is_spark_available", return_value=True), patch(
            "agents.base.ask_spark", new=provider
        ):
            response = self.client.post("/api/island/report/generate", json={
                "days": 7,
            })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["external_transfer_attempted"], response.json())
        self.assertFalse(response.json()["llm_used"])
        db = self.Session()
        try:
            audit = db.query(SensitiveAccessLog).filter_by(action="generate_island_emotion_report").one()
            self.assertEqual(audit.result, "transfer_attempted_output_rejected_or_failed")
            self.assertTrue(audit.resource_id.startswith("island-report-"))
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
