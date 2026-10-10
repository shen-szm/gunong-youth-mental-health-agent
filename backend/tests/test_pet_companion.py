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

from api.companion import (
    _context_lock, _conversation_contexts, _purge_persisted_safety_states,
    router as companion_router,
)
from api.chat import router as chat_router
from api.island import router as island_router
from api.user import router as user_router
from database import Base, get_db
from models import CompanionSafetyState, SensitiveAccessLog, StudentChatSession


class PetCompanionApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        app = FastAPI()
        app.include_router(user_router)
        app.include_router(companion_router)
        app.include_router(chat_router)
        app.include_router(island_router)

        def override_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        self.anonymous = TestClient(app)
        demo = self.client.post("/api/user/demo-session")
        self.assertEqual(demo.status_code, 200)
        self.user_id = demo.json()["user_id"]

    def tearDown(self):
        self.client.close()
        self.anonymous.close()
        self.engine.dispose()

    def test_requires_http_only_session_and_rejects_extra_identity(self):
        self.assertEqual(
            self.anonymous.post("/api/companion/chat", json={"content": "今天有点累"}).status_code,
            401,
        )
        response = self.client.post(
            "/api/companion/chat", json={"content": "今天有点累", "user_id": 1}
        )
        self.assertEqual(response.status_code, 422)

    def test_crisis_forces_handoff_and_does_not_store_original_content(self):
        for content in ("我想死", "我刚刚吞了很多药", "我现在站在楼顶"):
            payload = self.client.post("/api/companion/chat", json={"content": content}).json()
            self.assertEqual(payload["risk_level"], "urgent", content)
            self.assertEqual(payload["mode"], "urgent")
            self.assertTrue(payload["handoff_required"])
            self.assertIn("110或120", payload["reply"])
            self.assertEqual(payload["workflow"][1]["status"], "blocked")
        with self.Session() as db:
            rows = db.query(SensitiveAccessLog).all()
            self.assertEqual(len(rows), 3)
            rendered = " ".join(f"{row.action} {row.resource_id} {row.result}" for row in rows)
            self.assertNotIn("吞", rendered)
            self.assertNotIn("楼顶", rendered)

    def test_island_pet_talk_propagates_urgent_safety_result(self):
        response = self.client.post(
            "/api/island/pet/interact",
            json={"action": "talk", "message": "我想死"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["risk_level"], "urgent")
        self.assertEqual(payload["mode"], "urgent")
        self.assertTrue(payload["handoff_required"])
        self.assertIn("110", payload["reply"])

    def test_family_harm_uses_safeguarding_route(self):
        payload = self.client.post(
            "/api/companion/chat", json={"content": "继父每天打我，我不敢回家"}
        ).json()
        self.assertEqual(payload["risk_level"], "urgent")
        self.assertTrue(payload["handoff_required"])
        self.assertIn("可信老师", payload["reply"])

    def test_negation_and_attribution_do_not_create_false_emotion_claims(self):
        for content in ("我已经不焦虑了", "同学说他很难过"):
            payload = self.client.post("/api/companion/chat", json={"content": content}).json()
            self.assertEqual(payload["risk_level"], "routine")
            self.assertIn("不会替你猜心情", payload["reply"])

    def test_split_crisis_is_detected_and_latched_for_the_login_session(self):
        first = self.client.post("/api/companion/chat", json={"content": "我不想"})
        self.assertNotEqual(first.json()["risk_level"], "urgent")
        second = self.client.post("/api/companion/chat", json={"content": "活了"})
        self.assertEqual(second.json()["risk_level"], "urgent")
        self.assertTrue(second.json()["handoff_required"])
        after = self.client.post("/api/companion/chat", json={"content": "我不知道怎么办"})
        self.assertEqual(after.json()["risk_level"], "urgent")

    def test_split_overdose_is_detected(self):
        self.assertNotEqual(
            self.client.post("/api/companion/chat", json={"content": "我已经"}).json()["risk_level"],
            "urgent",
        )
        self.assertEqual(
            self.client.post("/api/companion/chat", json={"content": "吞药了"}).json()["risk_level"],
            "urgent",
        )

    def test_derived_safety_state_survives_process_memory_loss_without_raw_text(self):
        self.client.post("/api/companion/chat", json={"content": "我不想"})
        with _context_lock:
            _conversation_contexts.clear()
        second = self.client.post("/api/companion/chat", json={"content": "活了"})
        self.assertEqual(second.json()["risk_level"], "urgent")
        with _context_lock:
            _conversation_contexts.clear()
        after = self.client.post("/api/companion/chat", json={"content": "我不知道怎么办"})
        self.assertEqual(after.json()["risk_level"], "urgent")
        with self.Session() as db:
            row = db.query(CompanionSafetyState).one()
            self.assertNotIn("我不想", row.pending_flags_json)
            self.assertNotIn("活了", row.pending_flags_json)

    def test_logout_removes_shared_safety_state(self):
        self.client.post("/api/companion/chat", json={"content": "我已经"})
        with self.Session() as db:
            self.assertEqual(db.query(CompanionSafetyState).count(), 1)
        self.assertEqual(self.client.post("/api/user/logout").status_code, 200)
        with self.Session() as db:
            self.assertEqual(db.query(CompanionSafetyState).count(), 0)

    def test_expired_derived_state_is_actively_purgeable(self):
        self.client.post("/api/companion/chat", json={"content": "我已经"})
        with self.Session() as db:
            row = db.query(CompanionSafetyState).one()
            row.expires_at = datetime.now() - timedelta(seconds=1)
            db.commit()
            self.assertEqual(_purge_persisted_safety_states(db), 1)
            db.commit()
            self.assertEqual(db.query(CompanionSafetyState).count(), 0)

    def test_urgent_status_restores_and_handoff_latches_main_chat(self):
        self.client.post("/api/companion/chat", json={"content": "我想死"})
        with _context_lock:
            _conversation_contexts.clear()
        status = self.client.get("/api/companion/safety-status")
        self.assertTrue(status.json()["urgent"])
        handoff = self.client.post("/api/companion/handoff")
        self.assertEqual(handoff.json()["status"], "urgent")
        session = self.client.post("/api/chat/sessions", json={"force_new": False})
        self.assertEqual(session.json()["status"], "urgent")
        response = self.client.post("/api/chat/send", json={
            "user_id": self.user_id,
            "session_id": session.json()["session_id"],
            "message": "我不知道怎么办",
        })
        self.assertEqual(response.json()["risk_level"], "urgent")
        still_urgent = self.client.post("/api/chat/sessions", json={"force_new": True})
        self.assertEqual(still_urgent.json()["status"], "urgent")

        incomplete = self.client.post(
            f"/api/chat/sessions/{session.json()['session_id']}/resolve-safety",
            json={"current_safe": True, "contacted_trusted_adult": False},
        )
        self.assertEqual(incomplete.status_code, 400)
        resolved = self.client.post(
            f"/api/chat/sessions/{session.json()['session_id']}/resolve-safety",
            json={"current_safe": True, "contacted_trusted_adult": True},
        )
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.json()["status"], "resolved")
        fresh = self.client.post("/api/chat/sessions", json={"force_new": True})
        self.assertEqual(fresh.json()["status"], "active")
        self.assertNotEqual(fresh.json()["session_id"], session.json()["session_id"])
        with self.Session() as db:
            urgent_session = db.query(StudentChatSession).filter_by(
                session_code=session.json()["session_id"]
            ).one()
            self.assertEqual(urgent_session.status, "abandoned")
            self.assertEqual(urgent_session.risk_level, "urgent")
            self.assertEqual(db.query(CompanionSafetyState).count(), 0)
            audit = db.query(SensitiveAccessLog).filter_by(
                action="resolve_student_urgent_session"
            ).one()
            self.assertEqual(audit.result, "student_confirmed_safe_and_contacted_adult")

    def test_crisis_negation_and_attribution_are_not_misclassified(self):
        for content in ("我不想死", "我不会伤害自己", "朋友说他想死", "老师说他想死"):
            with self.subTest(content=content):
                client = TestClient(self.client.app)
                client.post("/api/user/demo-session")
                result = client.post("/api/companion/chat", json={"content": content})
                self.assertEqual(result.status_code, 200)
                self.assertNotEqual(result.json()["risk_level"], "urgent")
                client.close()

    def test_real_crisis_after_non_quote_context_is_not_suppressed(self):
        samples = (
            "我忍不住想死", "我控制不住想自杀", "我不得不伤害自己",
            "朋友离开后我想死", "老师批评我后我想死", "他离开后我想死",
            "家人不理解我，我想死", "朋友说完后我想死", "朋友说我差，我想死",
            "老师说完我想死", "家人说的话让我想死",
        )
        for content in samples:
            with self.subTest(content=content):
                client = TestClient(self.client.app)
                client.post("/api/user/demo-session")
                result = client.post("/api/companion/chat", json={"content": content})
                self.assertEqual(result.json()["risk_level"], "urgent")
                client.close()


if __name__ == "__main__":
    unittest.main()
