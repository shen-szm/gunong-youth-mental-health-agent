from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from teacher_task_runtime import DurableTeacherPlans
from teacher_task_cleanup import cleanup_expired


class TaskCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = DurableTeacherPlans(self.root, lambda owner: owner == 1)

    def tearDown(self):
        self.temp.cleanup()

    def task(self):
        return self.store.create(1, str(uuid4()), {"objective": "weekly_followup"})["task_id"]

    def update(self, task_id, **values):
        with self.store._session(1) as (graph, saver):
            graph.update_state(self.store._config(task_id), values)

    def expire(self, task_id):
        self.update(task_id, expires=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat())

    def test_preview_preserves_expired_and_apply_keeps_active_and_business_report(self):
        expired, active = self.task(), self.task()
        self.expire(expired)
        with closing(sqlite3.connect(self.root / "checkpoints.sqlite")) as conn:
            conn.execute("INSERT INTO checkpoints SELECT ?,checkpoint_ns,checkpoint_id,parent_checkpoint_id,type,checkpoint,metadata FROM checkpoints WHERE thread_id=?", (expired + ":case", expired))
            conn.execute("CREATE TABLE case_attempts(task_id TEXT PRIMARY KEY, attempts INTEGER)")
            conn.executemany("INSERT INTO case_attempts VALUES (?, 1)", [(expired,), (active,)])
            conn.commit()
        report_file = self.root / "business-report.txt"
        report_file.touch()
        preview = cleanup_expired(self.root)
        self.assertEqual(preview["expired_task_ids"], [expired])
        self.assertEqual(preview["deleted_task_count"], 0)
        with closing(sqlite3.connect(self.root / "checkpoints.sqlite")) as conn:
            self.assertGreater(conn.execute("SELECT count(*) FROM checkpoints WHERE thread_id=?", (expired,)).fetchone()[0], 0)
        result = cleanup_expired(self.root, apply=True)
        self.assertEqual(result["deleted_task_count"], 1)
        self.assertTrue(report_file.exists())
        self.assertEqual(self.store.get(1, active)["task_id"], active)
        with closing(sqlite3.connect(self.root / "checkpoints.sqlite")) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM checkpoints WHERE thread_id IN (?,?)", (expired, expired + ":case")).fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT task_id FROM case_attempts").fetchall(), [(active,)])
        self.assertEqual(cleanup_expired(self.root, apply=True)["deleted_task_count"], 0)

    def test_active_revision_retains_expired_ancestors(self):
        parent, middle, child = self.task(), self.task(), self.task()
        self.update(middle, revision={"parent_task_id": parent})
        self.update(child, revision={"parent_task_id": middle})
        self.expire(parent)
        self.expire(middle)
        result = cleanup_expired(self.root, apply=True)
        self.assertEqual(set(result["retained_dependency_ids"]), {parent, middle})
        self.assertEqual(result["deleted_task_count"], 0)
        self.expire(child)
        self.assertEqual(cleanup_expired(self.root, apply=True)["deleted_task_count"], 3)

    def test_invalid_metadata_blocks_apply(self):
        expired, broken = self.task(), self.task()
        self.expire(expired)
        self.update(broken, expires="not-a-date")
        self.assertEqual(cleanup_expired(self.root)["invalid_task_ids"], [broken])
        with self.assertRaises(ValueError):
            cleanup_expired(self.root, apply=True)
        self.assertEqual(cleanup_expired(self.root)["expired_task_ids"], [expired])

    def test_missing_directory_is_not_created(self):
        missing = self.root / "missing"
        with self.assertRaises(FileNotFoundError):
            cleanup_expired(missing)
        self.assertFalse(missing.exists())

    def test_execution_lock_prevents_cleanup(self):
        self.expire(self.task())
        with closing(sqlite3.connect(self.root / "coordination.sqlite")) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaises(sqlite3.OperationalError):
                cleanup_expired(self.root, apply=True)
            conn.rollback()

    def test_delete_failure_rolls_back_parent_and_child_together(self):
        task_id = self.task()
        self.expire(task_id)
        with closing(sqlite3.connect(self.root / "checkpoints.sqlite")) as conn:
            conn.execute("INSERT INTO checkpoints SELECT ?,checkpoint_ns,checkpoint_id,parent_checkpoint_id,type,checkpoint,metadata FROM checkpoints WHERE thread_id=?", (task_id + ":case", task_id))
            conn.execute("CREATE TRIGGER fail_child_delete BEFORE DELETE ON checkpoints WHEN OLD.thread_id LIKE '%:case' BEGIN SELECT RAISE(ABORT, 'test rollback'); END")
            conn.commit()
            count = conn.execute("SELECT count(*) FROM checkpoints").fetchone()[0]
        with self.assertRaises(sqlite3.IntegrityError):
            cleanup_expired(self.root, apply=True)
        with closing(sqlite3.connect(self.root / "checkpoints.sqlite")) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM checkpoints").fetchone()[0], count)
        self.assertEqual(cleanup_expired(self.root)["expired_task_ids"], [task_id])
