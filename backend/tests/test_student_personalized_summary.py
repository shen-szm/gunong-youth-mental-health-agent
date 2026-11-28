import json
import re
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
from deepseek_client import DeepSeekError
from models import SensitiveAccessLog, StudentChatSession

COMPANION_REPLY = '嗯，我在听。\n[[XM_STATE]]{"scores": {}, "crisis": false}'


def _prompt_turns(prompt: str) -> list[tuple[int, str]]:
    return [(int(mid), text) for mid, text in re.findall(r"\[消息#(\d+)\] (.+)", prompt)]


def _personalized_summary(prompt: str, *, summary=None, quote=None, message_id=None,
                          support_need="先被认真听见，再慢慢决定下一步。",
                          next_steps=None) -> str:
    turns = _prompt_turns(prompt)
    first_id, first_text = turns[0]
    signals = [{
        "message_id": message_id if message_id is not None else first_id,
        "quote": quote if quote is not None else first_text[:8],
        "observation": "这句话里有很具体的疲惫和为难",
    }]
    if quote is not None:
        signals[0]["message_id"] = first_id
    if len(turns) > 1 and quote is None:
        signals.append({
            "message_id": turns[1][0], "quote": turns[1][1][:6],
            "observation": "你也在担心这件事接下来会怎样",
        })
    return json.dumps({
        "summary": summary or (
            f"你从「{first_text[:10]}」说起，把最近压着你的那件事讲得很具体，"
            "也说到它怎样占住了你的晚上。你在试着把最难受的部分说清楚。"
        ),
        "signals": signals,
        "support_need": support_need,
        "next_steps": next_steps or ["把最难受的部分写成一句话", "找一个信得过的人说说"],
    }, ensure_ascii=False)


class StudentPersonalizedSummaryTests(unittest.TestCase):
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

    def _seed_conversation(self, messages):
        chat_api.ask_deepseek = AsyncMock(return_value=COMPANION_REPLY)
        for message in messages:
            sent = self.client.post("/api/chat/send", json={
                "user_id": self.user_id, "session_id": self.session_id, "message": message,
            })
            self.assertEqual(sent.status_code, 200)

    def _summary_mock(self, summary_handler):
        calls = {"summary_prompts": []}

        async def fake(messages, max_tokens=1600, temperature=0.85):
            if "倾诉整理助手" in messages[0]["content"]:
                calls["summary_prompts"].append(messages[1]["content"])
                result = summary_handler(messages[1]["content"])
                if isinstance(result, Exception):
                    raise result
                return result
            return COMPANION_REPLY

        chat_api.ask_deepseek = fake
        return calls

    def _complete(self):
        response = self.client.post(f"/api/chat/sessions/{self.session_id}/complete")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_personalized_summary_uses_raw_transcript_and_grounded_quotes(self):
        self._seed_conversation([
            "最近作业多得写不完，晚上一躺下就开始想明天的事。",
            "数学那本练习册还剩很多，越拖越不想打开。",
        ])
        calls = self._summary_mock(lambda prompt: _personalized_summary(prompt))

        payload = self._complete()
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["metadata"]["model_name"], "deepseek-student-summary")
        self.assertFalse(payload["metadata"]["degraded"])
        self.assertEqual(payload["metadata"]["prompt_version"], "student-summary-v4")

        self.assertEqual(len(calls["summary_prompts"]), 1)
        self.assertIn("最近作业多得写不完", calls["summary_prompts"][0])
        self.assertNotIn("[[XM_STATE]]", calls["summary_prompts"][0])

        summary = payload["summary"]
        self.assertIn("最近作业多得写不完", summary["summary"])
        self.assertNotIn("[[XM_STATE]]", json.dumps(summary, ensure_ascii=False))
        self.assertTrue(all("「" in signal["observation"] for signal in summary["signals"]))
        self.assertIn("先被认真听见", summary["support_need"])
        self.assertEqual(summary["risk_level"], "routine")

        db = self.Session()
        try:
            transfer = db.query(SensitiveAccessLog).filter_by(
                action="external_model_transfer_summary").one()
            self.assertEqual(
                transfer.result, "platform_direct_transcript_summary_transcript_to_deepseek")
            result = db.query(SensitiveAccessLog).filter_by(
                action="external_model_result_summary").one()
            self.assertEqual(
                result.result, "validated:student-summary-v4:personalized_from_transcript")
        finally:
            db.close()

    def test_two_grounded_quotes_from_the_same_message_are_allowed(self):
        self._seed_conversation(["最近作业多得写不完，晚上一躺下就开始想明天的事。"])
        self._summary_mock(lambda prompt: json.dumps({
            "summary": "你说到作业多得写不完，一躺下就开始想明天的事，晚上很难真正停下来休息。",
            "signals": [
                {"message_id": _prompt_turns(prompt)[0][0], "quote": "作业多得写不完", "observation": "任务量已经压到你的休息时间里"},
                {"message_id": _prompt_turns(prompt)[0][0], "quote": "一躺下就开始想明天", "observation": "躺下之后脑子仍在处理明天的事"},
            ],
            "support_need": "先让晚上有一个可以停下来的小边界。",
            "next_steps": ["睡前把明天的事写成一张清单", "给自己留十分钟不做任务的时间"],
        }, ensure_ascii=False))

        payload = self._complete()
        self.assertEqual(payload["metadata"]["model_name"], "deepseek-student-summary")
        self.assertFalse(payload["metadata"]["degraded"])
        self.assertEqual(len(payload["summary"]["signals"]), 2)

    def test_ungrounded_quote_falls_back_to_deterministic_summary(self):
        self._seed_conversation(["最近作业多得写不完，晚上一躺下就开始想明天的事。"])
        calls = self._summary_mock(
            lambda prompt: _personalized_summary(prompt, quote="这句话不在原文里出现过"))

        payload = self._complete()
        self.assertEqual(payload["metadata"]["model_name"], "deterministic-student-summary")
        self.assertTrue(payload["metadata"]["degraded"])
        self.assertEqual(len(calls["summary_prompts"]), 1)
        self.assertNotIn("这句话不在原文里出现过", json.dumps(payload, ensure_ascii=False))

    def test_clinical_or_scored_summary_is_rejected(self):
        self._seed_conversation([
            "最近作业多得写不完，晚上一躺下就开始想明天的事，白天也提不起劲。",
        ])
        self._summary_mock(lambda prompt: _personalized_summary(
            prompt, summary="这次聊下来，量表显示你有中度困扰，建议尽快做一次正式评估，先照顾好自己。"))

        payload = self._complete()
        self.assertEqual(payload["metadata"]["model_name"], "deterministic-student-summary")
        self.assertTrue(payload["metadata"]["degraded"])
        self.assertNotIn("量表", payload["summary"]["summary"])

    def test_invented_message_id_is_rejected(self):
        self._seed_conversation(["最近作业多得写不完，晚上一躺下就开始想明天的事。"])
        self._summary_mock(
            lambda prompt: _personalized_summary(prompt, message_id=999999))

        payload = self._complete()
        self.assertEqual(payload["metadata"]["model_name"], "deterministic-student-summary")
        self.assertTrue(payload["metadata"]["degraded"])

    def test_deepseek_failure_keeps_deterministic_summary(self):
        self._seed_conversation(["最近作业多得写不完，晚上一躺下就开始想明天的事。"])
        self._summary_mock(lambda prompt: DeepSeekError("boom"))

        payload = self._complete()
        self.assertEqual(payload["metadata"]["model_name"], "deterministic-student-summary")
        self.assertTrue(payload["metadata"]["degraded"])

        db = self.Session()
        try:
            result = db.query(SensitiveAccessLog).filter_by(
                action="external_model_result_summary").one()
            self.assertEqual(result.result, "failed")
        finally:
            db.close()

    def test_without_consent_transcript_never_reaches_model(self):
        self._seed_conversation(["最近作业多得写不完，晚上一躺下就开始想明天的事。"])
        calls = self._summary_mock(lambda prompt: _personalized_summary(prompt))
        settings.ALLOW_STUDENT_EXTERNAL_AI = False

        payload = self._complete()
        self.assertEqual(payload["metadata"]["model_name"], "deterministic-student-summary")
        self.assertFalse(payload["metadata"]["degraded"])
        self.assertEqual(calls["summary_prompts"], [])

    def test_professional_risk_keeps_deterministic_support_need_and_steps(self):
        self._seed_conversation([
            "我连续失眠快两周了，白天根本没法上学，作业也没力气写，真的不知道该怎么办。",
        ])
        self._summary_mock(lambda prompt: _personalized_summary(
            prompt, support_need="先好好休息一下再说。",
            next_steps=["今晚早点放下手机", "明天再想作业的事"]))

        payload = self._complete()
        self.assertEqual(payload["metadata"]["model_name"], "deepseek-student-summary")
        self.assertEqual(payload["summary"]["risk_level"], "professional")
        self.assertIn("可信成年人", payload["summary"]["support_need"])
        self.assertIn("可信成年人", payload["summary"]["next_steps"][0])
        self.assertNotIn("今晚早点睡", payload["summary"]["next_steps"])


if __name__ == "__main__":
    unittest.main()
