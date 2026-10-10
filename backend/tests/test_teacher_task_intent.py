import sys
import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from teacher_task_intent import IntentInput, ExplicitIntentContract, interpret_intent
from teacher_task_planner import TaskContract


class IntentTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_json_syntax_gets_one_retry_and_retains_first_failure(self):
        contract = TaskContract(objective="conversation_preparation", period_days=30).model_dump()
        valid = json.dumps({'contract': contract, 'clarification': 'none'})
        request = IntentInput(goal='近30天授权资料个案沟通报告及清单，不检索', confirmed=True)
        model = AsyncMock(side_effect=['```json\n{}\n```', valid])
        result = await interpret_intent(request, model, allow_format_retry=True)
        self.assertTrue(result['can_prepare'])
        self.assertEqual(result['model_attempts'], 2)
        self.assertEqual(result['first_attempt']['status'], 'invalid_result')
        self.assertEqual(model.await_count, 2)
        self.assertNotIn('```', str(model.await_args_list[1]))
        for raw in ['bad json', '{"contract":{},"clarification":"none"}', '{"contract":null,"clarification":"unsupported_action"}']:
            model = AsyncMock(return_value=raw)
            result = await interpret_intent(request, model, allow_format_retry=True)
            self.assertFalse(result['can_prepare'])
            self.assertEqual(model.await_count, 2 if raw == 'bad json' else 1)

    async def test_product_default_does_not_enable_experimental_retry(self):
        model = AsyncMock(return_value='invalid JSON')
        result = await interpret_intent(IntentInput(goal='准备沟通报告', confirmed=True), model)
        self.assertEqual(model.await_count, 1)
        self.assertFalse(result['format_retry_used'])
    async def test_consent_and_disabled_never_call_model(self):
        model = AsyncMock()
        result = await interpret_intent(IntentInput(goal="沟通准备任务"), model)
        self.assertEqual(result["status"], "confirmation_required")
        model.assert_not_awaited()
        result = await interpret_intent(IntentInput(goal="沟通准备任务", confirmed=True))
        self.assertEqual(result["status"], "model_unavailable")
        self.assertFalse(result["can_prepare"])

    async def test_valid_extraction_is_review_only(self):
        payload = {"contract": TaskContract(objective="conversation_preparation", period_days=30).model_dump(), "clarification": "none"}
        model = AsyncMock(return_value=json.dumps(payload))
        result = await interpret_intent(IntentInput(goal="准备近30天的个案沟通报告和核对清单", confirmed=True), model)
        self.assertTrue(result["can_prepare"])
        self.assertFalse(result["execution_started"])
        self.assertFalse(result["student_data_accessed"])
        self.assertNotIn("goal", result)
        payload["contract"]["period_days"] = 7
        result = await interpret_intent(IntentInput(goal="准备近7天报告", confirmed=True), AsyncMock(return_value=json.dumps(payload)))
        self.assertEqual(result["status"], "unsupported_contract")
        self.assertEqual(result["contract"]["period_days"], 7)
        self.assertFalse(result["can_prepare"])

    async def test_uncertain_and_invalid_outputs_fail_closed(self):
        request = IntentInput(goal="帮我处理一下", confirmed=True)
        for raw in ['{"contract":null,"clarification":"ambiguous"}', '{"contract":{"objective":"conversation_preparation","scope":"all_students"},"clarification":"none"}', 'not json', '{"contract":null,"clarification":"none","tool":"send"}']:
            result = await interpret_intent(request, AsyncMock(return_value=raw))
            self.assertFalse(result["can_prepare"])
            self.assertIsNone(result["contract"])
        for error in [RuntimeError('provider-secret'), TimeoutError()]:
            result = await interpret_intent(request, AsyncMock(side_effect=error))
            self.assertFalse(result["can_prepare"])
            self.assertNotIn('provider-secret', str(result))

    async def test_extraction_requires_every_field_without_changing_execution_defaults(self):
        complete = TaskContract(objective="conversation_preparation", period_days=30).model_dump()
        schema = ExplicitIntentContract.model_json_schema()
        self.assertEqual(set(schema['required']), set(complete))
        self.assertTrue(all('default' not in field for field in schema['properties'].values()))
        self.assertEqual(TaskContract(objective="conversation_preparation").period_days, 7)
        for key in complete:
            missing = {name: value for name, value in complete.items() if name != key}
            result = await interpret_intent(IntentInput(goal="准备沟通报告", confirmed=True), AsyncMock(return_value=json.dumps({'contract': missing, 'clarification': 'none'})))
            self.assertFalse(result['can_prepare'])
            self.assertEqual(result['status'], 'invalid_result')

    async def test_validation_diagnostics_exclude_raw_values_and_unknown_names(self):
        raw = json.dumps({'contract': None, 'clarification': 'secret-value', 'secret-field-name': 'secret-body'})
        result = await interpret_intent(IntentInput(goal='准备沟通报告', confirmed=True), AsyncMock(return_value=raw))
        self.assertEqual(result['status'], 'invalid_result')
        self.assertTrue(result['validation_issues'])
        self.assertNotIn('secret', str(result))
        bad_json = await interpret_intent(IntentInput(goal='准备沟通报告', confirmed=True), AsyncMock(return_value='```json\n{}\n```'))
        self.assertEqual(bad_json['validation_issues'][0]['kind'], 'json_invalid')
