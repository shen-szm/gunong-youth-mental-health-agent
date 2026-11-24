import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import tempfile
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from auth import get_current_user
from api.teacher_tasks import router
from api.teacher_tasks import durable_store
from teacher_task_planner import TaskContract, PlanningRequest, fallback_plan, parse_plan, preview_task


class PlannerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.contract = TaskContract(objective="weekly_followup")
        self.request = PlanningRequest(contract=self.contract, confirmed=True)
        self.valid = fallback_plan(self.contract).model_dump_json()

    async def test_confirmation_precedes_model(self):
        model = AsyncMock()
        result = await preview_task(PlanningRequest(contract=self.contract), model)
        model.assert_not_awaited()
        self.assertEqual(result["steps"], [])
        self.assertEqual(result["status"], "waiting_confirmation")

    async def test_success_is_only_planned_not_executed(self):
        result = await preview_task(self.request, AsyncMock(return_value=self.valid))
        self.assertEqual(result["source"], "model_selected")
        self.assertFalse(result["execution_started"])
        self.assertFalse(result["student_data_accessed"])
        self.assertFalse(result["approval_granted"])
        self.assertTrue(all(step["status"] == "planned" for step in result["steps"]))

    async def test_invalid_plan_repaired_once(self):
        model = AsyncMock(side_effect=['{"tools":["send_notification"]}', self.valid])
        result = await preview_task(self.request, model)
        self.assertEqual(result["source"], "model_selected")
        self.assertEqual(result["model_attempts"], 2)
        self.assertNotIn("send_notification", json.dumps(model.await_args_list[-1].args))

    async def test_invalid_model_falls_back_truthfully(self):
        model = AsyncMock(return_value="not json")
        result = await preview_task(self.request, model)
        self.assertEqual(result["source"], "local_rules")
        self.assertEqual(result["fallback_reason"], "invalid_plan")
        self.assertEqual(model.await_count, 2)

    async def test_disabled_and_provider_failure(self):
        self.assertEqual((await preview_task(self.request))["fallback_reason"], "model_disabled")
        result = await preview_task(self.request, AsyncMock(side_effect=RuntimeError("secret-provider-value")))
        self.assertNotIn("secret-provider-value", json.dumps(result))
        self.assertEqual(result["model_attempts"], 1)
        self.assertEqual(result["fallback_reason"], "model_unavailable")

    async def test_timeout_not_retried(self):
        result = await preview_task(self.request, AsyncMock(side_effect=TimeoutError()))
        self.assertEqual(result["fallback_reason"], "model_timeout")
        self.assertEqual(result["model_attempts"], 1)

    def test_extra_prose_and_scope_expansion_rejected(self):
        for extra in ({"student_id": 1}, {"prompt": "private prose"}, {"scope": "all_students"}, {"delivery": "send"}, {"period_days": "7"}):
            with self.subTest(extra=extra), self.assertRaises(ValidationError):
                TaskContract.model_validate({"objective": "weekly_followup", **extra})

    def test_tool_graph_invariants(self):
        valid = json.loads(self.valid)["tools"]
        for tools in (valid[::-1], valid + [valid[0]], valid[:-1], ["send_notification"] + valid):
            with self.subTest(tools=tools), self.assertRaises(ValueError):
                parse_plan(json.dumps({"tools": tools}), self.contract)
        with self.assertRaises(ValueError):
            parse_plan(self.valid[:-1] + ',"private":"data"}', self.contract)

    async def test_resource_policy_changes_plan_and_model_input_is_enum_only(self):
        contract = self.contract.model_copy(update={"resource_policy": "approved_only"})
        model = AsyncMock(return_value=fallback_plan(contract).model_dump_json())
        result = await preview_task(PlanningRequest(contract=contract, confirmed=True), model)
        self.assertEqual(len(result["steps"]), 5)
        sent = json.loads(model.await_args.args[0][1]["content"])
        self.assertEqual(sent, contract.model_dump())
        with self.assertRaises(ValueError):
            parse_plan(self.valid, contract)


class PlannerApiTests(unittest.TestCase):
    def test_intent_endpoint_requires_teacher_and_respects_model_gate(self):
        payload = {"goal": "准备近30天个案沟通报告", "confirmed": True}
        url = "/api/teacher/tasks/intent-preview"
        self.assertEqual(self.client.post(url, json=payload).status_code, 401)
        self.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, is_admin=0)
        self.assertEqual(self.client.post(url, json=payload).status_code, 403)
        self.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, is_admin=1)
        with patch("api.teacher_tasks.settings.ALLOW_TEACHER_TASK_PLANNER_AI", False), patch("api.teacher_tasks.ask_spark", new_callable=AsyncMock) as model:
            self.assertEqual(self.client.post(url, json=payload).json()["status"], "model_unavailable")
            model.assert_not_awaited()
        self.assertEqual(self.client.post(url, json={**payload, "confirmed": "true"}).status_code, 422)
        self.assertEqual(self.client.post(url, json={**payload, "goal": "x" * 601}).status_code, 422)

    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)
        self.payload = {"contract": {"objective": "weekly_followup"}, "confirmed": True}

    def tearDown(self):
        self.client.close()

    def test_no_session_denied(self):
        self.assertEqual(self.client.post("/api/teacher/tasks/preview", json=self.payload).status_code, 401)

    def test_student_denied(self):
        self.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, is_admin=0)
        self.assertEqual(self.client.post("/api/teacher/tasks/preview", json=self.payload).status_code, 403)

    def test_teacher_allowed_without_external_model(self):
        self.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, is_admin=1)
        with patch("api.teacher_tasks.settings.ALLOW_TEACHER_TASK_PLANNER_AI", False), patch("api.teacher_tasks.ask_spark", new_callable=AsyncMock) as model:
            response = self.client.post("/api/teacher/tasks/preview", json=self.payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source"], "local_rules")
        model.assert_not_awaited()

    def test_durable_plan_api_create_resume_delete(self):
        from teacher_task_runtime import DurableTeacherPlans
        self.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, is_admin=1)
        with tempfile.TemporaryDirectory() as directory:
            self.app.dependency_overrides[durable_store] = lambda: DurableTeacherPlans(directory, lambda owner: owner == 2)
            payload = {"request_id": str(uuid4()), "contract": {"objective": "weekly_followup"}}
            response = self.client.post("/api/teacher/tasks/durable-plans", json=payload)
            self.assertEqual(response.status_code, 200)
            task = response.json()
            url = "/api/teacher/tasks/durable-plans/" + task["task_id"]
            self.assertEqual(self.client.get(url).json()["status"], "waiting_approval")
            self.assertEqual(self.client.post(url + "/decision", json={"digest": "0" * 64, "approved": True}).status_code, 409)
            decision = {"digest": task["digest"], "approved": True}
            self.assertEqual(self.client.post(url + "/decision", json=decision).json()["status"], "plan_approved")
            self.assertEqual(self.client.post(url + "/decision", json={**decision, "approved": "true"}).status_code, 422)
            self.assertEqual(self.client.delete(url).status_code, 204)
            self.assertEqual(self.client.get(url).status_code, 404)
