import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from teacher_task_runtime import DurableTeacherPlans, TaskConflict


class DurablePlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.allowed = {1, 2}
        self.store = DurableTeacherPlans(self.temp.name, lambda owner: owner in self.allowed)
        self.key = str(uuid4())
        self.contract = {"objective": "weekly_followup"}

    def tearDown(self):
        self.temp.cleanup()

    def create(self):
        return self.store.create(1, self.key, self.contract)

    def test_history_scopes_latest_snapshots_without_deleting_expired(self):
        target = {"student_id": 5, "access_request_id": 12}
        first = self.store.create(1, self.key, self.contract, target)
        self.store.decide(1, first["task_id"], first["digest"], True)
        self.store.create(2, str(uuid4()), self.contract, target)
        self.store.create(1, str(uuid4()), self.contract, {**target, "access_request_id": 13})
        second = self.store.create(1, str(uuid4()), self.contract, target)
        result = self.store.history(1, target, limit=1)
        self.assertEqual([r["task_id"] for r in result["items"]], [second["task_id"]])
        self.assertTrue(result["has_more"])
        self.assertEqual(len(self.store.history(1, target)["items"]), 2)
        with self.store._session(1) as (graph, saver):
            graph.update_state(self.store._config(second["task_id"]), {"expires": "2000-01-01T00:00:00+00:00"})
        self.assertEqual([r["task_id"] for r in self.store.history(1, target)["items"]], [first["task_id"]])
        with self.store._session(1) as (graph, saver):
            self.assertTrue(graph.get_state(self.store._config(second["task_id"])).values)
        self.allowed.remove(1)
        with self.assertRaises(PermissionError):
            self.store.history(1, target)

    def test_create_is_pending_and_idempotent(self):
        first = self.create()
        self.assertEqual(first, self.create())
        self.assertEqual(first["status"], "waiting_approval")
        self.assertFalse(first["execution_started"])
        self.assertFalse(first["student_data_accessed"])
        with self.assertRaises(TaskConflict):
            self.store.create(1, self.key, {**self.contract, "period_days": 14})

    def test_new_process_resumes_official_checkpoint(self):
        first = self.create()
        code = "import json,sys; from teacher_task_runtime import DurableTeacherPlans; s=DurableTeacherPlans(sys.argv[1],lambda owner:owner==1); print(json.dumps(s.decide(1,sys.argv[2],sys.argv[3],True)))"
        result = subprocess.run([sys.executable, "-c", code, self.temp.name, first["task_id"], first["digest"]], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "plan_approved")
        self.assertEqual(self.store.get(1, first["task_id"])["status"], "plan_approved")

    def test_repeated_decision_and_cancel_conflict(self):
        first = self.create()
        result = self.store.decide(1, first["task_id"], first["digest"], False)
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(result, self.store.decide(1, first["task_id"], first["digest"], False))
        with self.assertRaises(TaskConflict):
            self.store.decide(1, first["task_id"], first["digest"], True)

    def test_stale_digest_does_not_resume(self):
        first = self.create()
        with self.assertRaises(TaskConflict):
            self.store.decide(1, first["task_id"], "0" * 64, True)
        self.assertEqual(self.store.get(1, first["task_id"])["status"], "waiting_approval")

    def test_cross_teacher_access_denied_even_if_id_known(self):
        first = self.create()
        for action in (lambda: self.store.get(2, first["task_id"]), lambda: self.store.decide(2, first["task_id"], first["digest"], True), lambda: self.store.delete(2, first["task_id"])):
            with self.assertRaises(LookupError):
                action()

    def test_role_revocation_rechecked(self):
        first = self.create()
        self.allowed.remove(1)
        with self.assertRaises(PermissionError):
            self.store.decide(1, first["task_id"], first["digest"], True)

    def test_duplicate_concurrent_confirmation(self):
        first = self.create()
        def decide(_):
            store = DurableTeacherPlans(self.temp.name, lambda owner: owner == 1)
            return store.decide(1, first["task_id"], first["digest"], True)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(decide, range(4)))
        self.assertTrue(all(result == results[0] for result in results))

    def test_delete_removes_all_checkpoint_rows(self):
        first = self.create()
        self.store.delete(1, first["task_id"])
        with self.assertRaises(LookupError):
            self.store.get(1, first["task_id"])
        with closing(sqlite3.connect(Path(self.temp.name) / "checkpoints.sqlite")) as db:
            for table in ("checkpoints", "writes"):
                self.assertEqual(db.execute(f"SELECT count(*) FROM {table} WHERE thread_id=?", (first["task_id"],)).fetchone()[0], 0)

    def test_expired_task_cannot_resume(self):
        first = self.create()
        with self.store._session(1) as (graph, saver):
            graph.update_state(self.store._config(first["task_id"]), {"expires": "2000-01-01T00:00:00+00:00"})
        with self.assertRaises(LookupError):
            self.store.decide(1, first["task_id"], first["digest"], True)

    def test_invalid_values_do_not_create_tasks(self):
        with self.assertRaises(ValueError):
            self.store.create(1, "not-a-uuid", self.contract)
        with self.assertRaises(ValueError):
            self.store.create(1, self.key, {**self.contract, "student_id": 3})

    def test_termination_is_persisted_idempotent_and_not_resumable(self):
        first = self.create()
        stopped = self.store.terminate(1, first["task_id"], first["digest"], "source_changed")
        self.assertEqual(stopped["status"], "terminated")
        self.assertEqual(stopped["termination"]["actor_id"], 1)
        self.assertEqual(self.store.terminate(1, first["task_id"], first["digest"]), stopped)
        self.assertEqual(DurableTeacherPlans(self.temp.name, lambda owner: owner == 1).get(1, first["task_id"]), stopped)
        self.assertEqual(self.create(), stopped)
        with self.assertRaises(TaskConflict):
            self.store.decide(1, first["task_id"], first["digest"], True)
        with self.store._session(1) as (graph, saver):
            self.assertFalse(graph.get_state(self.store._config(first["task_id"])).next)

    def test_termination_requires_owner_role_and_matching_digest(self):
        first = self.create()
        with self.assertRaises(LookupError):
            self.store.terminate(2, first["task_id"], first["digest"])
        with self.assertRaises(TaskConflict):
            self.store.terminate(1, first["task_id"], "0" * 64)
        self.allowed.remove(1)
        with self.assertRaises(PermissionError):
            self.store.terminate(1, first["task_id"], first["digest"])
