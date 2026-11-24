import sys
import json
import unittest
from unittest.mock import AsyncMock
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from teacher_intent_benchmark import CASES, evaluate, score_case
from teacher_task_intent import IntentInput


class BenchmarkTests(unittest.IsolatedAsyncioTestCase):
    async def test_retry_statistics_keep_failed_first_attempt(self):
        model = AsyncMock(side_effect=['invalid JSON', json.dumps({'contract': CASES[0]['expected_contract'], 'clarification': 'none'})])
        report = await evaluate(model, 'unit-test-double', cases=[CASES[0]], allow_format_retry=True)
        self.assertEqual(report['first_passed'], 0)
        self.assertEqual(report['passed'], 1)
        self.assertEqual(report['model_calls'], 2)
        self.assertEqual(report['retried_cases'], 1)

    def test_dataset_is_unique_valid_and_has_all_categories(self):
        self.assertEqual(len(CASES), 24)
        self.assertEqual(len({item['id'] for item in CASES}), len(CASES))
        self.assertEqual(len({item['category'] for item in CASES}), 8)
        for item in CASES:
            IntentInput(goal=item['goal'])
            self.assertTrue(item['expected_contract'] or item['accepted_clarifications'])

    async def test_offline_has_no_model_score(self):
        report = await evaluate()
        self.assertEqual(report['mode'], 'offline_readiness_only')
        self.assertIsNone(report['passed'])
        self.assertIsNone(report['pass_rate'])
        self.assertTrue(all(row['passed'] is None for row in report['results']))
        self.assertTrue(all(row['actual']['status'] == 'model_unavailable' or row['actual']['source'] == 'local_policy' for row in report['results']))
        self.assertEqual(report['local_guard']['blocked'], 11)
        self.assertEqual(report['local_guard']['supported_cases_blocked'], 1)
        self.assertFalse(report['local_guard']['counts_as_model_success'])

    async def test_failed_provider_counts_all_cases_as_failed_not_refused(self):
        model = AsyncMock(side_effect=TimeoutError())
        report = await evaluate(model, 'unit-test-double-not-a-real-model')
        self.assertEqual(model.await_count, 24 - report['local_guard']['blocked'])
        self.assertEqual(report['passed'], 0)
        self.assertEqual(report['pass_rate'], 0)
        self.assertEqual(sum(group['total'] for group in report['categories'].values()), 24)
        self.assertTrue(all(row['reason'] == 'no_valid_model_result' for row in report['results']))

    def test_exact_contract_and_safe_refusal_are_scored_separately(self):
        item = CASES[0]
        valid = {'source': 'model_extracted', 'status': 'ready_for_review', 'contract': item['expected_contract'], 'can_prepare': True, 'execution_started': False, 'student_data_accessed': False}
        self.assertTrue(score_case(item, valid)[0])
        self.assertFalse(score_case(item, {**valid, 'contract': {**item['expected_contract'], 'period_days': 7}})[0])
        self.assertFalse(score_case(item, {**valid, 'execution_started': True})[0])
        attack = next(row for row in CASES if row['category'] == 'prompt_injection')
        refusal = {**valid, 'status': 'needs_clarification', 'contract': None, 'can_prepare': False, 'clarification': 'unsupported_action'}
        self.assertTrue(score_case(attack, refusal)[0])
        self.assertFalse(score_case(attack, {**refusal, 'source': 'none', 'status': 'model_timeout'})[0])
        self.assertFalse(score_case(attack, valid)[0])
