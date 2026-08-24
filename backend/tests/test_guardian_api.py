import sys
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import guardian_engine
import api.guardian as guardian_api
from api.guardian import router as guardian_router
from api.user import router as user_router
from config import settings
from database import Base, get_db
from models import GuardianCase, SafetyEvent, SensitiveAccessLog, SupportPlan, User
from validation import sanitized_validation_exception_handler


class GuardianApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.old_session_local = guardian_engine.SessionLocal
        self.old_api_session_local = guardian_api.SessionLocal
        self.old_delay = settings.AGENT_STEP_DELAY_MS
        self.old_external_ai = settings.ALLOW_EXTERNAL_AI
        self.old_guardian_ai = settings.ALLOW_GUARDIAN_EXTERNAL_AI
        guardian_engine.SessionLocal = self.Session
        guardian_api.SessionLocal = self.Session
        settings.AGENT_STEP_DELAY_MS = 0
        settings.ALLOW_EXTERNAL_AI = False
        settings.ALLOW_GUARDIAN_EXTERNAL_AI = False

        self.app = FastAPI()
        self.app.add_exception_handler(RequestValidationError, sanitized_validation_exception_handler)
        self.app.include_router(user_router)
        self.app.include_router(guardian_router)

        def override_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        self.app.dependency_overrides[get_db] = override_db
        self.client_one = TestClient(self.app)
        self.client_two = TestClient(self.app)

    def tearDown(self):
        self.client_one.close()
        self.client_two.close()
        guardian_engine.SessionLocal = self.old_session_local
        guardian_api.SessionLocal = self.old_api_session_local
        settings.AGENT_STEP_DELAY_MS = self.old_delay
        settings.ALLOW_EXTERNAL_AI = self.old_external_ai
        settings.ALLOW_GUARDIAN_EXTERNAL_AI = self.old_guardian_ai
        self.engine.dispose()

    @staticmethod
    def payload():
        return {
            "reporter_role": "parent",
            "age_band": "15-18",
            "signals": ["mood_low", "social_withdrawal", "performance_drop"],
            "duration": "2_4_weeks",
            "functional_impact": "partial",
            "district": "南城街道",
            "context": "近三周更常独处，仍愿意一起吃饭。",
            "guardian_may_be_source": False,
            "consent_version": "guardian-support-v1",
            "deidentified_confirmed": True,
        }

    def _login_both(self):
        first = self.client_one.post("/api/user/demo-session")
        second = self.client_two.post("/api/user/demo-session")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(first.json()["user_id"], second.json()["user_id"])

    def test_requires_session_and_isolates_demo_browsers(self):
        unauthenticated = TestClient(self.app)
        try:
            self.assertEqual(unauthenticated.get("/api/guardian/follow-ups").status_code, 401)
        finally:
            unauthenticated.close()
        self._login_both()
        created = self.client_one.post("/api/guardian/cases", json=self.payload())
        self.assertEqual(created.status_code, 202)
        case_code = created.json()["case_id"]
        self.assertEqual(self.client_two.get(f"/api/guardian/cases/{case_code}").status_code, 403)
        self.assertEqual(self.client_one.get(f"/api/guardian/cases/{case_code}").status_code, 200)
        self.assertEqual(self.client_two.get("/api/guardian/follow-ups").json()["items"], [])

    def test_completed_retry_is_idempotent_and_sse_finishes(self):
        self._login_both()
        case_code = self.client_one.post("/api/guardian/cases", json=self.payload()).json()["case_id"]
        retry = self.client_one.post(f"/api/guardian/cases/{case_code}/retry")
        self.assertEqual(retry.status_code, 202)
        self.assertTrue(retry.json()["idempotent"])
        with self.client_one.stream("GET", f"/api/guardian/cases/{case_code}/events") as stream:
            body = "".join(stream.iter_text())
        self.assertIn("event: snapshot", body)
        self.assertIn("event: complete", body)

    def test_followup_new_danger_atomically_replaces_plan(self):
        self._login_both()
        case_code = self.client_one.post("/api/guardian/cases", json=self.payload()).json()["case_id"]
        task = self.client_one.get("/api/guardian/follow-ups").json()["items"][0]
        response = self.client_one.post(
            f"/api/guardian/follow-ups/{task['id']}/responses",
            json={
                "mood_change": "worse",
                "action_completion": "none",
                "difficulty": "",
                "needs_adjustment": True,
                "current_safety": "unsure",
                "new_self_harm_or_suicide_signal": True,
                "action_taken_or_means_available": False,
                "family_harm_or_unsafe_home": False,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["urgent_override"])
        case_payload = self.client_one.get(f"/api/guardian/cases/{case_code}").json()
        self.assertEqual(case_payload["case"]["risk_level"], "urgent")
        self.assertEqual(case_payload["plan"]["risk_level"], "urgent")
        db = self.Session()
        try:
            case = db.query(GuardianCase).filter(GuardianCase.case_code == case_code).one()
            self.assertEqual(db.query(SafetyEvent).filter(SafetyEvent.case_id == case.id).count(), 1)
            self.assertGreaterEqual(db.query(SensitiveAccessLog).count(), 3)
            self.assertIsNotNone(db.query(SupportPlan).filter(SupportPlan.case_id == case.id).first())
        finally:
            db.close()

    def test_context_rejects_direct_identifiers_without_echoing_them(self):
        self._login_both()
        payload = self.payload()
        payload["context"] = "请联系13800138000了解情况"
        response = self.client_one.post("/api/guardian/cases", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("13800138000", response.text)


if __name__ == "__main__":
    unittest.main()
