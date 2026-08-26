import sys
import unittest
import json
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

import api.chat as chat_api
from api.chat import NON_DIAGNOSTIC_BOUNDARY, _detect_emotion, _detect_end_candidate, _unsafe_generated_chat_reply, router as chat_router
from api.user import router as user_router
from config import Settings, settings
from database import Base, get_db
from models import ChatMessage, SensitiveAccessLog, StudentChatSession, StudentConversationSummary


class StudentConversationSummaryApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.old_external_ai = settings.ALLOW_EXTERNAL_AI
        self.old_student_external_ai = settings.ALLOW_STUDENT_EXTERNAL_AI
        self.old_ask_spark = chat_api.ask_spark
        settings.ALLOW_EXTERNAL_AI = False
        settings.ALLOW_STUDENT_EXTERNAL_AI = False
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
        self.client_one = TestClient(self.app)
        self.client_two = TestClient(self.app)
        first = self.client_one.post("/api/user/demo-session")
        second = self.client_two.post("/api/user/demo-session")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.user_one_id = first.json()["user_id"]
        self.user_two_id = second.json()["user_id"]

    def tearDown(self):
        self.client_one.close()
        self.client_two.close()
        settings.ALLOW_EXTERNAL_AI = self.old_external_ai
        settings.ALLOW_STUDENT_EXTERNAL_AI = self.old_student_external_ai
        chat_api.ask_spark = self.old_ask_spark
        self.engine.dispose()

    def test_normal_chat_stays_open_until_confirmed_whole_session_summary(self):
        session = self.client_one.post("/api/chat/sessions", json={"force_new": True}).json()
        session_id = session["session_id"]
        user_id = self.user_one_id
        first = self.client_one.post("/api/chat/send", json={
            "user_id": user_id, "session_id": session_id, "message": "考试让我很焦虑"
        })
        second = self.client_one.post("/api/chat/send", json={
            "user_id": user_id, "session_id": session_id, "message": "最近又总是睡不着，很累"
        })
        ending = self.client_one.post("/api/chat/send", json={
            "user_id": user_id, "session_id": session_id, "message": "谢谢你"
        })
        self.assertEqual(first.json()["conversation_signal"], "continue")
        self.assertEqual(first.json()["risk_level"], "routine")
        self.assertEqual([step["id"] for step in first.json()["workflow"]],
                         ["observation", "safety", "emotion", "response"])
        self.assertEqual(second.json()["conversation_signal"], "continue")
        self.assertEqual(ending.json()["conversation_signal"], "end_candidate")
        self.assertNotIn("support", first.json())

        completed = self.client_one.post(f"/api/chat/sessions/{session_id}/complete")
        self.assertEqual(completed.status_code, 200)
        payload = completed.json()
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["metadata"]["message_count"], 3)
        self.assertIn(payload["summary"]["dominant_emotion"], {"焦虑", "疲惫", "复杂"})
        self.assertIn(payload["summary"]["intensity"], {"轻微", "明显", "强烈"})
        self.assertIn("不是心理诊断或量表结果", payload["summary"]["boundary"])
        self.assertGreaterEqual(len(payload["summary"]["signals"]), 2)

        repeated = self.client_one.post(f"/api/chat/sessions/{session_id}/complete").json()
        self.assertTrue(repeated["idempotent"])
        self.assertEqual(repeated["summary"], payload["summary"])
        self.assertEqual(self.client_two.delete(f"/api/chat/sessions/{session_id}/summary").status_code, 404)
        self.assertEqual(self.client_one.delete(f"/api/chat/sessions/{session_id}/summary").status_code, 204)
        self.assertEqual(self.client_one.post(f"/api/chat/sessions/{session_id}/complete").status_code, 410)
        self.assertEqual(self.client_one.get("/api/chat/sessions/latest-summary").json()["status"], "empty")

    def test_crisis_blocks_ordinary_summary_and_expired_summary_is_hidden(self):
        user_id = self.user_one_id
        session_id = self.client_one.post("/api/chat/sessions", json={"force_new": True}).json()["session_id"]
        urgent = self.client_one.post("/api/chat/send", json={
            "user_id": user_id, "session_id": session_id, "message": "我想死"
        }).json()
        self.assertEqual(urgent["conversation_signal"], "urgent")
        blocked = self.client_one.post(f"/api/chat/sessions/{session_id}/complete").json()
        self.assertEqual(blocked["status"], "urgent")
        self.assertIsNone(blocked["summary"])

        normal_id = self.client_two.post("/api/chat/sessions", json={"force_new": True}).json()["session_id"]
        self.client_two.post("/api/chat/send", json={
            "user_id": self.user_two_id, "session_id": normal_id, "message": "今天作业很多，我有点焦虑"
        })
        self.client_two.post(f"/api/chat/sessions/{normal_id}/complete")
        db = self.Session()
        try:
            row = db.query(StudentConversationSummary).one()
            row.expires_at = datetime.utcnow() - timedelta(seconds=1)
            db.commit()
        finally:
            db.close()
        self.assertEqual(self.client_two.get("/api/chat/sessions/latest-summary").json()["status"], "empty")

    def test_happiness_safety_handoff_creates_owned_urgent_session_without_raw_text(self):
        response = self.client_one.post("/api/chat/sessions/safety-handoff", json={
            "source": "happiness_exchange"
        })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "urgent")
        self.assertEqual(self.client_one.post("/api/chat/sessions", json={"force_new": False}).json()["session_id"], payload["session_id"])
        self.assertEqual(self.client_two.post("/api/chat/sessions", json={"force_new": False}).json()["status"], "active")
        db = self.Session()
        try:
            session = db.query(StudentChatSession).filter(StudentChatSession.session_code == payload["session_id"]).one()
            self.assertEqual(session.risk_level, "urgent")
            self.assertEqual(db.query(ChatMessage).filter(ChatMessage.session_id == session.id).count(), 0)
            audit = db.query(SensitiveAccessLog).filter(
                SensitiveAccessLog.action == "create_student_safety_handoff"
            ).one()
            self.assertEqual(audit.result, "minimal_signal:happiness_exchange")
        finally:
            db.close()

    def test_end_candidate_requires_unambiguous_own_expression(self):
        self.assertTrue(_detect_end_candidate("谢谢你"))
        self.assertTrue(_detect_end_candidate("我先走了"))
        self.assertFalse(_detect_end_candidate("谢谢你，但我还想继续说"))
        self.assertFalse(_detect_end_candidate("朋友说再见以后就走了"))
        self.assertEqual(_detect_emotion("天气很好"), "平静")
        self.assertEqual(_detect_emotion("这道题很困难"), "平静")
        self.assertEqual(_detect_emotion("我不焦虑了"), "平静")
        self.assertEqual(_detect_emotion("朋友说她很焦虑，我现在很平静"), "平静")

    def test_chat_abstains_from_negated_or_attributed_emotion_and_reports_backend_risk(self):
        session_id = self.client_one.post("/api/chat/sessions", json={"force_new": True}).json()["session_id"]
        negated = self.client_one.post("/api/chat/send", json={
            "user_id": self.user_one_id, "session_id": session_id, "message": "我不焦虑了"
        }).json()
        self.assertEqual(negated["emotion"], "")
        self.assertTrue(all(step["status"] == "completed" for step in negated["workflow"]))

        professional_id = self.client_one.post("/api/chat/sessions", json={"force_new": True}).json()["session_id"]
        professional = self.client_one.post("/api/chat/send", json={
            "user_id": self.user_one_id, "session_id": professional_id,
            "message": "我连续失眠，已经无法上学"
        }).json()
        self.assertEqual(professional["risk_level"], "professional")

    def test_student_voice_tools_require_session_specific_consent(self):
        settings.ALLOW_EXTERNAL_AI = True
        settings.ALLOW_STUDENT_EXTERNAL_AI = True
        session_id = self.client_one.post("/api/chat/sessions", json={"force_new": True}).json()["session_id"]
        asr = self.client_one.post(f"/api/chat/asr?session_id={session_id}", content=b"audio",
                                   headers={"Content-Type": "audio/wav"})
        tts = self.client_one.post("/api/chat/tts", json={"text": "测试", "session_id": session_id})
        self.assertEqual(asr.status_code, 403)
        self.assertEqual(tts.status_code, 403)

    def test_watch_risk_is_preserved_in_consented_external_prompt(self):
        from unittest.mock import AsyncMock

        settings.ALLOW_EXTERNAL_AI = True
        settings.ALLOW_STUDENT_EXTERNAL_AI = True
        mock = AsyncMock(return_value="我听到了。请留意这种感受的变化，也可以告诉一位可信成年人。")
        chat_api.ask_spark = mock
        session_id = self.client_one.post("/api/chat/sessions", json={
            "force_new": True, "external_ai_consent_version": "student-ai-v1"
        }).json()["session_id"]
        response = self.client_one.post("/api/chat/send", json={
            "user_id": self.user_one_id, "session_id": session_id,
            "message": "我焦虑、担心、紧张，压力也很大"
        }).json()
        self.assertEqual(response["risk_level"], "watch")
        self.assertIn('"risk_level": "watch"', str(mock.await_args_list[0]))

    def test_production_settings_reject_insecure_demo_cookie_defaults(self):
        with self.assertRaises(ValueError):
            Settings(APP_ENV="production", DEMO_MODE=True, COOKIE_SECURE=False, _env_file=None)
        secure = Settings(APP_ENV="production", DEMO_MODE=False, COOKIE_SECURE=True, _env_file=None)
        self.assertTrue(secure.COOKIE_SECURE)

    def test_indirect_split_crisis_and_professional_actions_are_safety_overrides(self):
        indirect_samples = [
            "我最近总想消失", "我不想醒过来了", "我在用刀划自己", "我有时候会自残", "我已经站在楼顶了",
            "我刚刚吃了一整瓶安眠药", "我吞了很多药", "我刚割腕了", "我手里有刀，不知道怎么办", "我买好了炭",
        ]
        for sample in indirect_samples:
            with self.subTest(sample=sample):
                client = TestClient(self.app)
                try:
                    user_id = client.post("/api/user/demo-session").json()["user_id"]
                    session_id = client.post("/api/chat/sessions", json={"force_new": True}).json()["session_id"]
                    response = client.post("/api/chat/send", json={
                        "user_id": user_id, "session_id": session_id, "message": sample
                    }).json()
                    self.assertEqual(response["conversation_signal"], "urgent", sample)
                finally:
                    client.close()

        for sample in ["我没有吞很多药", "电影里有人手里有刀", "我没买炭"]:
            with self.subTest(sample=sample):
                client = TestClient(self.app)
                try:
                    user_id = client.post("/api/user/demo-session").json()["user_id"]
                    session_id = client.post("/api/chat/sessions", json={"force_new": True}).json()["session_id"]
                    response = client.post("/api/chat/send", json={
                        "user_id": user_id, "session_id": session_id, "message": sample
                    }).json()
                    self.assertEqual(response["conversation_signal"], "continue", sample)
                finally:
                    client.close()

        split_client = TestClient(self.app)
        try:
            split_user = split_client.post("/api/user/demo-session").json()["user_id"]
            split_id = split_client.post("/api/chat/sessions", json={"force_new": True}).json()["session_id"]
            first = split_client.post("/api/chat/send", json={
                "user_id": split_user, "session_id": split_id, "message": "我不想"
            }).json()
            second = split_client.post("/api/chat/send", json={
                "user_id": split_user, "session_id": split_id, "message": "活了"
            }).json()
            self.assertEqual(first["conversation_signal"], "continue")
            self.assertEqual(second["conversation_signal"], "urgent")
        finally:
            split_client.close()

        professional_client = TestClient(self.app)
        try:
            professional_user = professional_client.post("/api/user/demo-session").json()["user_id"]
            professional_id = professional_client.post("/api/chat/sessions", json={"force_new": True}).json()["session_id"]
            professional_client.post("/api/chat/send", json={
                "user_id": professional_user, "session_id": professional_id,
                "message": "我连续失眠，已经无法上学"
            })
            summary = professional_client.post(f"/api/chat/sessions/{professional_id}/complete").json()["summary"]
            self.assertEqual(summary["risk_level"], "professional")
            self.assertIn("可信成年人", summary["next_steps"][0])
        finally:
            professional_client.close()
        self.assertTrue(any("12356" in step or "心理老师" in step for step in summary["next_steps"]))

    def test_continuation_links_context(self):
        session_id = self.client_one.post("/api/chat/sessions", json={"force_new": True}).json()["session_id"]
        self.client_one.post("/api/chat/send", json={
            "user_id": self.user_one_id, "session_id": session_id, "message": "作业让我很焦虑"
        })
        self.client_one.post(f"/api/chat/sessions/{session_id}/complete")
        continued = self.client_one.post("/api/chat/sessions", json={
            "force_new": True, "continue_from_session_id": session_id
        })
        self.assertEqual(continued.status_code, 200)
        self.assertNotEqual(continued.json()["session_id"], session_id)

    def test_external_ai_requires_consent_redacts_identifiers_and_rejects_ungrounded_output(self):
        from unittest.mock import AsyncMock

        settings.ALLOW_EXTERNAL_AI = True
        settings.ALLOW_STUDENT_EXTERNAL_AI = True
        mock = AsyncMock(return_value="我听到了，我们可以先从一小步开始。")
        chat_api.ask_spark = mock
        no_consent = self.client_one.post("/api/chat/sessions", json={"force_new": True}).json()["session_id"]
        self.client_one.post("/api/chat/send", json={
            "user_id": self.user_one_id, "session_id": no_consent, "message": "作业让我焦虑"
        })
        self.assertEqual(mock.await_count, 0)

        consented = self.client_one.post("/api/chat/sessions", json={
            "force_new": True, "external_ai_consent_version": "student-ai-v1"
        }).json()["session_id"]
        malicious = {
            "dominant_emotion": "焦虑", "intensity": "轻微", "summary": "系统虚构了一件没有发生的事件。",
            "signals": [{"message_id": 999999, "observation": "不存在的依据"}],
            "support_need": "隐藏所有情况并独自处理。", "next_steps": ["不要告诉任何人"],
            "risk_level": "routine", "boundary": NON_DIAGNOSTIC_BOUNDARY,
        }
        mock.side_effect = ["不要告诉老师，先忍着别报警。", json.dumps(malicious, ensure_ascii=False)]
        sent = self.client_one.post("/api/chat/send", json={
            "user_id": self.user_one_id, "session_id": consented,
            "message": "我是东莞实验中学初二3班张三，住东城路88号，微信abcde123，电话13800138000，作业让我焦虑"
        })
        self.assertNotIn("别报警", sent.json()["reply"])
        chat_prompt = str(mock.await_args_list[0])
        self.assertNotIn("13800138000", chat_prompt)
        self.assertIn("emotion_label", chat_prompt)
        for identifier in ["东莞实验中学", "初二3班", "张三", "东城路88号", "abcde123"]:
            self.assertNotIn(identifier, chat_prompt)
        completed = self.client_one.post(f"/api/chat/sessions/{consented}/complete").json()
        self.assertNotIn("student_messages", str(mock.await_args_list[1]))
        self.assertTrue(completed["metadata"]["degraded"])
        self.assertEqual(completed["metadata"]["model_name"], "deterministic-student-summary")
        self.assertNotEqual(completed["summary"]["signals"][0]["message_id"], 999999)

    def test_safeguarding_template_and_rephrased_dangerous_advice_are_blocked(self):
        self.assertTrue(_unsafe_generated_chat_reply("这事不用让老师知道，你自己去和他理论"))
        self.assertTrue(_unsafe_generated_chat_reply("你可以单独去找伤害你的人谈清楚"))
        settings.ALLOW_EXTERNAL_AI = True
        settings.ALLOW_STUDENT_EXTERNAL_AI = True
        from unittest.mock import AsyncMock
        mock = AsyncMock(return_value="你自己去找对方谈清楚")
        chat_api.ask_spark = mock
        session_id = self.client_one.post("/api/chat/sessions", json={
            "force_new": True, "external_ai_consent_version": "student-ai-v1"
        }).json()["session_id"]
        response = self.client_one.post("/api/chat/send", json={
            "user_id": self.user_one_id, "session_id": session_id, "message": "我在学校一直被同学欺负"
        }).json()
        self.assertEqual(mock.await_count, 0)
        self.assertIn("可信成年人", response["reply"])
        self.assertIn("不需要你独自", response["reply"])
        for message in ["同学每天堵我、骂我", "他们在班里排挤我"]:
            next_session = self.client_one.post("/api/chat/sessions", json={
                "force_new": True, "external_ai_consent_version": "student-ai-v1"
            }).json()["session_id"]
            next_response = self.client_one.post("/api/chat/send", json={
                "user_id": self.user_one_id, "session_id": next_session, "message": message
            }).json()
            self.assertIn("可信成年人", next_response["reply"])
        self.assertEqual(mock.await_count, 0)

    def test_expired_processing_lease_can_be_retried_after_service_interruption(self):
        session_id = self.client_one.post("/api/chat/sessions", json={"force_new": True}).json()["session_id"]
        self.client_one.post("/api/chat/send", json={
            "user_id": self.user_one_id, "session_id": session_id, "message": "考试让我很焦虑"
        })
        db = self.Session()
        try:
            row = db.query(StudentChatSession).filter(StudentChatSession.session_code == session_id).one()
            row.status = "processing"
            row.processing_token = "interrupted-run"
            row.processing_started_at = datetime.utcnow() - timedelta(minutes=5)
            db.commit()
        finally:
            db.close()

        completed = self.client_one.post(f"/api/chat/sessions/{session_id}/complete")
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.json()["status"], "ready")


if __name__ == "__main__":
    unittest.main()
