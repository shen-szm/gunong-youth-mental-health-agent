import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from api.chat import router as chat_router
from api.student_agent import router as student_agent_router
from api.student_agent import cleanup_expired_support_runs
from api.user import router as user_router
from config import settings
from database import Base, get_db
from database import _migrate_student_support_runs
from models import StudentSupportEvent, StudentSupportRun
from student_support_engine import recover_stale_support_run


class StudentSupportAgentTests(unittest.TestCase):
    def setUp(self):
        self.old_external = settings.ALLOW_EXTERNAL_AI
        self.old_student = settings.ALLOW_STUDENT_EXTERNAL_AI
        settings.ALLOW_EXTERNAL_AI = False
        settings.ALLOW_STUDENT_EXTERNAL_AI = False
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        app = FastAPI()
        app.include_router(user_router)
        app.include_router(chat_router)
        app.include_router(student_agent_router)

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

    def tearDown(self):
        self.one.close()
        self.two.close()
        settings.ALLOW_EXTERNAL_AI = self.old_external
        settings.ALLOW_STUDENT_EXTERNAL_AI = self.old_student
        self.engine.dispose()

    def _send(self, message):
        session = self.one.post("/api/chat/sessions", json={"force_new": True}).json()
        return self.one.post("/api/chat/send", json={
            "user_id": self.user_one,
            "session_id": session["session_id"],
            "message": message,
        })

    def test_chat_delivers_persisted_dynamic_agent_plan_without_raw_text(self):
        response = self._send("最近考试让我很焦虑，连续失眠并且已经影响上课")
        self.assertEqual(response.status_code, 200)
        run = response.json()["agent_run"]
        self.assertEqual(run["status"], "completed")
        self.assertIn("deterministic_safety_rules", run["tools"])
        self.assertIn("local_support_resource_registry", run["tools"])
        self.assertNotIn("xunfei_structured_synthesizer", run["tools"])
        self.assertGreaterEqual(len(run["events"]), 6)
        self.assertNotIn("考试让我很焦虑", str(run))
        self.assertIn("非诊断性", run["deliverable"]["boundary"])

        latest = self.one.get("/api/student-agent/runs/latest")
        self.assertEqual(latest.status_code, 200)
        self.assertEqual(latest.json()["run_code"], run["run_code"])
        forbidden = self.two.get(f"/api/student-agent/runs/{run['run_code']}")
        self.assertEqual(forbidden.status_code, 404)

        db = self.Session()
        try:
            stored = db.query(StudentSupportRun).filter_by(run_code=run["run_code"]).one()
            self.assertEqual(stored.user_id, self.user_one)
            self.assertEqual(db.query(StudentSupportEvent).filter_by(run_id=stored.id).count(), len(run["events"]))
        finally:
            db.close()

    def test_urgent_plan_stops_normal_generation_and_records_handoff(self):
        response = self._send("我现在想伤害自己")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["conversation_signal"], "urgent")
        run = payload["agent_run"]
        self.assertEqual(run["status"], "attention")
        self.assertEqual(run["model_name"], "safety-override")
        self.assertIn("urgent_support_router", run["tools"])
        self.assertNotIn("xunfei_structured_synthesizer", run["tools"])
        self.assertEqual(run["events"][-1]["agent"], "SafetyCoordinator")

    def test_timeline_combines_agent_runs_without_exposing_conversation_text(self):
        self._send("今天有一点累")
        timeline = self.one.get("/api/student-agent/timeline?days=30&limit=20")
        self.assertEqual(timeline.status_code, 200)
        self.assertTrue(any(item["type"] == "agent_run" for item in timeline.json()))
        self.assertNotIn("今天有一点累", timeline.text)

    def test_neutral_turn_count_does_not_create_watch_risk(self):
        session = self.one.post("/api/chat/sessions", json={"force_new": True}).json()
        for index in range(6):
            response = self.one.post("/api/chat/send", json={
                "user_id": self.user_one, "session_id": session["session_id"],
                "message": f"今天完成了第{index + 1}项作业",
                "idempotency_key": f"neutral_turn_{index:02d}",
            })
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["risk_level"], "routine")

    def test_client_idempotency_key_replays_one_result(self):
        session = self.one.post("/api/chat/sessions", json={"force_new": True}).json()
        payload = {
            "user_id": self.user_one, "session_id": session["session_id"],
            "message": "今天有一点累", "idempotency_key": "same_request_12345",
        }
        first = self.one.post("/api/chat/send", json=payload)
        second = self.one.post("/api/chat/send", json=payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["agent_run"]["run_code"], second.json()["agent_run"]["run_code"])
        self.assertEqual(first.json()["emotion_basis"], second.json()["emotion_basis"])
        db = self.Session()
        try:
            self.assertEqual(db.query(StudentSupportRun).filter_by(user_id=self.user_one).count(), 1)
        finally:
            db.close()

        conflict = dict(payload, message="这是另一条内容")
        self.assertEqual(self.one.post("/api/chat/send", json=conflict).status_code, 409)

    def test_running_lease_uses_utc_and_only_recovers_stale_tasks(self):
        run_code = self._send("今天有一点累").json()["agent_run"]["run_code"]
        db = self.Session()
        try:
            row = db.query(StudentSupportRun).filter_by(run_code=run_code).one()
            row.status = "running"
            row.started_at = datetime.utcnow()
            row.completed_at = None
            db.commit()
        finally:
            db.close()
        self.assertEqual(self.one.get("/api/student-agent/runs/latest").json()["status"], "running")
        db = self.Session()
        try:
            row = db.query(StudentSupportRun).filter_by(run_code=run_code).one()
            row.started_at = datetime.utcnow() - timedelta(minutes=6)
            db.commit()
        finally:
            db.close()
        self.assertEqual(self.one.get("/api/student-agent/runs/latest").json()["status"], "failed")

    def test_direct_idempotent_retry_recovers_stale_run(self):
        session = self.one.post("/api/chat/sessions", json={"force_new": True}).json()
        payload = {
            "user_id": self.user_one, "session_id": session["session_id"],
            "message": "今天有一点累", "idempotency_key": "stale_retry_12345",
        }
        first = self.one.post("/api/chat/send", json=payload).json()
        db = self.Session()
        try:
            row = db.query(StudentSupportRun).filter_by(run_code=first["agent_run"]["run_code"]).one()
            row.status = "running"
            row.started_at = datetime.utcnow() - timedelta(minutes=6)
            db.commit()
        finally:
            db.close()
        retry = self.one.post("/api/chat/send", json=payload)
        self.assertEqual(retry.status_code, 503)
        db = self.Session()
        try:
            self.assertEqual(db.query(StudentSupportRun).filter_by(run_code=first["agent_run"]["run_code"]).one().status, "failed")
        finally:
            db.close()

    def test_stale_recovery_cas_never_overwrites_completed_run(self):
        run_code = self._send("今天有一点累").json()["agent_run"]["run_code"]
        db = self.Session()
        try:
            row = db.query(StudentSupportRun).filter_by(run_code=run_code).one()
            row.started_at = datetime.utcnow() - timedelta(minutes=6)
            row.status = "completed"
            db.commit()
            self.assertFalse(recover_stale_support_run(db, row.id, datetime.utcnow() - timedelta(minutes=5)))
            db.refresh(row)
            self.assertEqual(row.status, "completed")
        finally:
            db.close()

    def test_alpha23_review_table_is_forward_migrated(self):
        legacy_engine = create_engine("sqlite://", poolclass=StaticPool)
        with legacy_engine.begin() as connection:
            connection.execute(text("""
                CREATE TABLE student_support_runs (
                    id INTEGER PRIMARY KEY, run_code VARCHAR(48), user_id INTEGER,
                    idempotency_key VARCHAR(80), status VARCHAR(24), started_at DATETIME
                )
            """))
            connection.execute(text(
                "INSERT INTO student_support_runs (id, run_code, user_id, idempotency_key, status, started_at) "
                "VALUES (1, 'SSR-OLD', 1, 'old-key', 'completed', CURRENT_TIMESTAMP)"
            ))
        _migrate_student_support_runs(legacy_engine)
        columns = {item["name"] for item in inspect(legacy_engine).get_columns("student_support_runs")}
        self.assertTrue({"request_fingerprint", "input_message_id", "output_message_id", "context_message_count", "emotion_basis_json", "expires_at"}.issubset(columns))
        with legacy_engine.connect() as connection:
            self.assertIsNotNone(connection.execute(text("SELECT expires_at FROM student_support_runs WHERE id=1")).scalar_one())
        legacy_engine.dispose()

    def test_expiry_cleanup_and_owned_delete(self):
        run_code = self._send("今天有一点累").json()["agent_run"]["run_code"]
        forbidden = self.two.delete(f"/api/student-agent/runs/{run_code}")
        self.assertEqual(forbidden.status_code, 404)
        deleted = self.one.delete(f"/api/student-agent/runs/{run_code}")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.one.get(f"/api/student-agent/runs/{run_code}").status_code, 404)

        expiring = self._send("今天还算平静").json()["agent_run"]["run_code"]
        db = self.Session()
        try:
            row = db.query(StudentSupportRun).filter_by(run_code=expiring).one()
            row.expires_at = datetime.utcnow() - timedelta(seconds=1)
            db.commit()
        finally:
            db.close()
        db = self.Session()
        try:
            self.assertEqual(cleanup_expired_support_runs(db), 1)
            self.assertIsNone(db.query(StudentSupportRun).filter_by(run_code=expiring).first())
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
