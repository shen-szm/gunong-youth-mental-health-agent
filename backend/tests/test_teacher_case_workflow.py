import sys
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from teacher_task_runtime import DurableTeacherPlans, TaskConflict
from teacher_case_workflow import execute_case


class CaseWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = DurableTeacherPlans(self.temp.name, lambda owner: owner == 1)
        self.contract = {"objective": "conversation_preparation", "period_days": 30}
        self.target = {"student_id": 3, "access_request_id": 7}
        self.task = self.store.create(1, str(uuid4()), self.contract, target=self.target)
        self.store.decide(1, self.task["task_id"], self.task["digest"], True)
        self.calls = []
        self.allowed = True
        self.fail = False
        owner = self

        class Tools:
            def authorize(self):
                if not owner.allowed:
                    raise PermissionError("revoked")

            def query(self):
                self.authorize()
                owner.calls.append("query")
                return "WP-test"

            def check_evidence(self, product_id):
                self.authorize()
                owner.calls.append("gaps")
                return {"evidence_available": True, "information_incomplete": True}

            def render(self, product_id):
                self.authorize()
                owner.calls.append("render")
                if owner.fail:
                    raise RuntimeError("private-provider-error")
                return "TR-test"

            def verify(self, product_id, report_id):
                self.authorize()
                owner.calls.append("verify")
                return {"artifact_valid": True, "report_hash": "a" * 64, "evidence_status": "needs_review"}
        self.tools = Tools()

    def tearDown(self):
        self.temp.cleanup()

    def run_task(self, run=True):
        return execute_case(self.store, 1, self.task["task_id"], lambda target: self.tools, run=run)

    def test_real_graph_records_tools_and_approval_is_not_human_followup(self):
        result = self.run_task()
        self.assertEqual(result["status"], "awaiting_report_review")
        self.assertEqual(len(result["completed_tools"]), 4)
        self.assertFalse(result["human_followup_completed"])
        self.assertEqual(result["report_id"], "TR-test")
        self.run_task()
        self.assertEqual(self.calls.count("render"), 1)

    def test_read_does_not_execute_and_revocation_hides_result(self):
        self.assertEqual(self.run_task(False)["status"], "pending")
        self.assertEqual(self.calls, [])
        self.run_task()
        self.allowed = False
        with self.assertRaises(PermissionError):
            self.run_task(False)

    def test_failure_is_redacted_and_retry_resumes_without_query_replay(self):
        self.fail = True
        first = self.run_task()
        self.assertEqual(first["error"], "tool_failed")
        self.assertNotIn("private-provider-error", str(first))
        self.assertEqual(self.run_task(False)["last_failure"], first["last_failure"])
        self.fail = False
        self.store = DurableTeacherPlans(self.temp.name, lambda owner: owner == 1)
        self.assertEqual(self.run_task()["status"], "awaiting_report_review")
        self.assertIsNone(self.run_task(False)["last_failure"])
        self.assertIsNone(self.store.get(1, self.task["task_id"])["last_failure"])
        self.assertEqual(self.calls.count("query"), 1)

    def test_retry_budget(self):
        self.fail = True
        for _ in range(3):
            self.assertEqual(self.run_task()["status"], "failed")
        with self.assertRaises(TaskConflict):
            self.run_task()

    def test_target_change_invalidates_idempotency(self):
        key = str(uuid4())
        first = self.store.create(1, key, self.contract, target=self.target)
        with self.assertRaises(TaskConflict):
            self.store.create(1, key, self.contract, target={**self.target, "student_id": 4})
        self.assertEqual(first["target"], self.target)

    def test_unapproved_plan_cannot_execute(self):
        task = self.store.create(1, str(uuid4()), self.contract, target=self.target)
        with self.assertRaises(TaskConflict):
            execute_case(self.store, 1, task["task_id"], lambda target: self.tools)
