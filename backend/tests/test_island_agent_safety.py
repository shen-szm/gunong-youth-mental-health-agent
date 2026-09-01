import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agents.base import BaseAgent, IslandContext
from agents.companion_agent import CompanionAgent
from agents.planner import PlanningAgent
from agents.reporter import ReportAgent


class IslandAgentSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_transfer_callback_runs_before_provider_response(self):
        callback = MagicMock()
        agent = BaseAgent(allow_external_ai=True, transfer_start_callback=callback)
        with patch("agents.base.is_spark_available", return_value=True), patch(
            "agents.base.ask_spark", new=AsyncMock(return_value="untrusted provider output")
        ):
            reply, used = await agent.call_llm([{"role": "user", "content": "redacted"}])
        self.assertTrue(used)
        self.assertEqual(reply, "untrusted provider output")
        callback.assert_called_once_with("base")

    async def test_companion_reports_actual_external_model_use(self):
        agent = CompanionAgent(MagicMock(), allow_external_ai=True)
        agent.call_llm = AsyncMock(return_value=("咕，我在这里。", True))
        context = IslandContext(user_id=1, intervention_plan={"steps": []})

        with patch.object(agent, "_update_pet_state"):
            result = await agent.run(context)

        self.assertTrue(result.data["llm_used"])
        self.assertEqual(result.data["model_name"], "xunfei-constrained")

    async def test_watch_companion_uses_only_reviewed_template(self):
        agent = CompanionAgent(MagicMock(), allow_external_ai=True)
        agent.call_llm = AsyncMock(return_value=("模型文案", True))
        context = IslandContext(user_id=1, risk_level="watch", mood_labels=["难过"], intervention_plan={"steps": []})
        with patch.object(agent, "_update_pet_state"):
            result = await agent.run(context)
        agent.call_llm.assert_not_awaited()
        self.assertFalse(result.data["llm_used"])

    def test_generated_report_cannot_supply_its_own_advice(self):
        data = {"mood_distribution": {"难过": 2}}
        self.assertFalse(ReportAgent._safe_report_text("你可以自己处理，不要告诉老师。", data))
        self.assertTrue(ReportAgent._safe_report_text("近期主动记录中，难过出现得较多；这不代表完整心理状态。", data))

    def test_planner_cannot_infer_mood_from_behavior_fields(self):
        context = IslandContext(
            user_id=1,
            mood_labels=[],
            recent_moods=[],
            activity_preference="breathing",
            login_pattern="late_night",
            breathing_completion=0.2,
        )
        step = {"action": "recommend", "params": {"mood_state": "anxious"}}
        self.assertIsNone(PlanningAgent._validated_step(step, context))

        context.mood_labels = ["焦虑"]
        self.assertEqual(
            PlanningAgent._validated_step(step, context),
            {"action": "recommend", "params": {"mood_state": "anxious"}},
        )

    def test_rule_plans_do_not_translate_one_emotion_into_another(self):
        planner = PlanningAgent()
        angry = planner._rule_based_plan(IslandContext(user_id=1, mood_labels=["愤怒"]))
        tired = planner._rule_based_plan(IslandContext(user_id=1, mood_labels=["疲惫"]))
        neutral = planner._rule_based_plan(IslandContext(user_id=1, mood_labels=[]))
        self.assertNotIn("recommend", [step["action"] for step in angry["steps"]])
        self.assertEqual(tired["steps"][-1]["params"]["mood_state"], "tired")
        self.assertNotIn("recommend", [step["action"] for step in neutral["steps"]])


if __name__ == "__main__":
    unittest.main()
