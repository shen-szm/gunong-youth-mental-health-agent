import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import api.chat as chat_api
from api.chat import router as chat_router
from api.user import router as user_router
from config import settings
from database import Base, get_db
from models import ChatMessage, SensitiveAccessLog, StudentChatSession


class StudentChatCompanionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.old_settings = {
            "ALLOW_EXTERNAL_AI": settings.ALLOW_EXTERNAL_AI,
            "ALLOW_STUDENT_EXTERNAL_AI": settings.ALLOW_STUDENT_EXTERNAL_AI,
            "STUDENT_AI_ACCESS_MODE": settings.STUDENT_AI_ACCESS_MODE,
            "PLATFORM_STUDENT_AI_GOVERNANCE_ACK": settings.PLATFORM_STUDENT_AI_GOVERNANCE_ACK,
            "STUDENT_COMPANION_ENGINE": settings.STUDENT_COMPANION_ENGINE,
            "DEEPSEEK_API_KEY": settings.DEEPSEEK_API_KEY,
        }
        self.old_ask_deepseek = chat_api.ask_deepseek
        settings.ALLOW_EXTERNAL_AI = True
        settings.ALLOW_STUDENT_EXTERNAL_AI = True
        settings.STUDENT_AI_ACCESS_MODE = "platform_direct"
        settings.PLATFORM_STUDENT_AI_GOVERNANCE_ACK = True
        settings.STUDENT_COMPANION_ENGINE = "deepseek"
        settings.DEEPSEEK_API_KEY = "test-deepseek-key"

        self.app = FastAPI()
        self.app.include_router(user_router)
        self.app.include_router(chat_router)

        def override_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        self.app.dependency_overrides[get_db] = override_db
        self.client = TestClient(self.app)
        self.user_id = self.client.post("/api/user/demo-session").json()["user_id"]
        self.session_id = self.client.post(
            "/api/chat/sessions", json={"force_new": True}
        ).json()["session_id"]

    def tearDown(self):
        self.client.close()
        for key, value in self.old_settings.items():
            setattr(settings, key, value)
        chat_api.ask_deepseek = self.old_ask_deepseek
        self.engine.dispose()

    def _send(self, message, session_id=None, idempotency_key=None):
        payload = {
            "user_id": self.user_id,
            "session_id": session_id if session_id is not None else self.session_id,
            "message": message,
        }
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key
        return self.client.post("/api/chat/send", json=payload)

    def _state(self, session_code=None):
        db = self.Session()
        try:
            row = db.query(StudentChatSession).filter_by(
                session_code=session_code or self.session_id
            ).one()
            return json.loads(row.companion_state_json or "{}"), row
        finally:
            db.close()

    def test_companion_turn_returns_visible_reply_and_hides_state(self):
        mock = AsyncMock(return_value=(
            '连球都不想打了啊，那是真的提不起劲。\n'
            '[[XM_STATE]]{"scores": {"1": 2}, "crisis": false}'
        ))
        chat_api.ask_deepseek = mock

        response = self._send("以前挺爱打球的，现在朋友叫我也不想去。")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["analysis_source"], "deepseek_companion")
        self.assertNotIn("[[XM_STATE]]", body["reply"])
        self.assertIn("提不起劲", body["reply"])
        self.assertEqual(body["agent_run"]["model_name"], "deepseek-companion")
        self.assertFalse(body["agent_run"]["degraded"])

        state, session = self._state()
        self.assertEqual(state["scored"], {"1": 2})
        self.assertEqual(session.external_ai_consent_version, "platform-direct-transcript-v3")

        prompt = str(mock.await_args_list[0])
        self.assertIn("以前挺爱打球的", prompt)
        self.assertIn("[[XM_STATE]]", prompt)

        db = self.Session()
        try:
            audit = db.query(SensitiveAccessLog).filter_by(
                action="external_model_transfer_chat"
            ).one()
            self.assertEqual(
                audit.result, "platform_direct_transcript_chat_transcript_to_deepseek"
            )
        finally:
            db.close()

    def test_empty_model_reply_falls_back_and_conversation_continues(self):
        mock = AsyncMock(side_effect=[
            "",
            '嗯，我在听。\n[[XM_STATE]]{"scores": {}, "crisis": false}',
        ])
        chat_api.ask_deepseek = mock

        first = self._send("今天有点累。")
        self.assertEqual(first.status_code, 200)
        first_body = first.json()
        self.assertEqual(first_body["analysis_source"], "deterministic")
        self.assertTrue(first_body["reply"].strip())
        self.assertTrue(first_body["agent_run"]["degraded"])

        db = self.Session()
        try:
            session_row = db.query(StudentChatSession).filter_by(
                session_code=self.session_id
            ).one()
            user_messages = db.query(ChatMessage).filter_by(
                session_id=session_row.id, role="user"
            ).all()
            self.assertEqual(len(user_messages), 1)
        finally:
            db.close()

        second = self._send("就是提不太起劲。")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["analysis_source"], "deepseek_companion")
        self.assertTrue(second.json()["reply"].strip())
        self.assertEqual(mock.await_count, 2)

    def test_clinical_language_is_replaced_by_fallback(self):
        mock = AsyncMock(return_value="你的量表得分是 12 分，属于明显症状。")
        chat_api.ask_deepseek = mock

        response = self._send("我最近不太对劲。")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["analysis_source"], "deterministic")
        self.assertNotIn("量表", body["reply"])
        self.assertNotIn("症状", body["reply"])
        self.assertTrue(body["agent_run"]["degraded"])
        state, _ = self._state()
        self.assertEqual(state, {})

    def test_urgent_signal_still_bypasses_the_model(self):
        mock = AsyncMock()
        chat_api.ask_deepseek = mock

        response = self._send("我最近总想消失。")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["analysis_source"], "safety_override")
        self.assertEqual(body["conversation_signal"], "urgent")
        self.assertEqual(body["risk_level"], "urgent")
        mock.assert_not_awaited()

    def test_idempotent_replay_does_not_apply_state_twice(self):
        mock = AsyncMock(return_value=(
            '嗯，我在。\n[[XM_STATE]]{"scores": {}, "crisis": false}'
        ))
        chat_api.ask_deepseek = mock

        first = self._send("最近有点闷。", idempotency_key="companion-idem-0001")
        second = self._send("最近有点闷。", idempotency_key="companion-idem-0001")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["reply"], second.json()["reply"])
        self.assertEqual(mock.await_count, 1)

        state, _ = self._state()
        self.assertEqual(state["focusCounts"], {"1": 1})
        db = self.Session()
        try:
            session_row = db.query(StudentChatSession).filter_by(
                session_code=self.session_id
            ).one()
            self.assertEqual(
                db.query(ChatMessage).filter_by(session_id=session_row.id, role="user").count(),
                1,
            )
        finally:
            db.close()

    def test_stale_consent_session_is_not_sent_to_model(self):
        db = self.Session()
        try:
            db.query(StudentChatSession).filter_by(
                session_code=self.session_id
            ).update({"status": "completed"})
            stale = StudentChatSession(
                session_code="SC-STALE-CONSENT-01",
                user_id=self.user_id,
                status="active",
                risk_level="routine",
                external_ai_consent_version="platform-direct-deidentified-v1",
            )
            db.add(stale)
            db.commit()
            stale_code = stale.session_code
        finally:
            db.close()

        mock = AsyncMock(return_value=(
            '嗯，我在。\n[[XM_STATE]]{"scores": {}, "crisis": false}'
        ))
        chat_api.ask_deepseek = mock

        response = self.client.post("/api/chat/send", json={
            "user_id": self.user_id,
            "message": "最近有点睡不着。",
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.json()["session_id"], stale_code)
        mock.assert_awaited_once()

        db = self.Session()
        try:
            stale = db.query(StudentChatSession).filter_by(session_code=stale_code).one()
            self.assertEqual(stale.status, "abandoned")
            new_session = db.query(StudentChatSession).filter_by(
                session_code=response.json()["session_id"]
            ).one()
            self.assertEqual(
                new_session.external_ai_consent_version, "platform-direct-transcript-v3"
            )
        finally:
            db.close()

    def test_session_start_replaces_stale_consent_session(self):
        db = self.Session()
        try:
            db.query(StudentChatSession).filter_by(
                session_code=self.session_id
            ).update({"status": "completed"})
            stale = StudentChatSession(
                session_code="SC-STALE-CONSENT-03",
                user_id=self.user_id,
                status="active",
                risk_level="routine",
                external_ai_consent_version="platform-direct-deidentified-v1",
            )
            db.add(stale)
            db.commit()
            stale_code = stale.session_code
        finally:
            db.close()

        started = self.client.post("/api/chat/sessions", json={"force_new": False})
        self.assertEqual(started.status_code, 200)
        self.assertNotEqual(started.json()["session_id"], stale_code)
        self.assertEqual(started.json()["companion_engine"], "deepseek")

        db = self.Session()
        try:
            self.assertEqual(
                db.query(StudentChatSession).filter_by(session_code=stale_code).one().status,
                "abandoned",
            )
        finally:
            db.close()

    def test_explicit_stale_session_requires_a_new_conversation(self):
        db = self.Session()
        try:
            stale = StudentChatSession(
                session_code="SC-STALE-CONSENT-02",
                user_id=self.user_id,
                status="active",
                risk_level="routine",
                external_ai_consent_version="platform-direct-deidentified-v1",
            )
            db.add(stale)
            db.commit()
            stale_code = stale.session_code
        finally:
            db.close()

        mock = AsyncMock()
        chat_api.ask_deepseek = mock
        response = self._send("最近有点烦。", session_id=stale_code)
        self.assertEqual(response.status_code, 409)
        self.assertIn("隐私说明已更新", response.json()["detail"])
        mock.assert_not_awaited()

if __name__ == "__main__":
    unittest.main()
