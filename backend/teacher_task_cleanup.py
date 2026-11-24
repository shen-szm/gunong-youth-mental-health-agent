"""Operator-only checkpoint retention, preview by default. Never opens the business DB."""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from uuid import UUID

from langgraph.checkpoint.sqlite import SqliteSaver


class ExistingSaver(SqliteSaver):
    def setup(self):
        # Do not create tables or migrate the file during a retention preview.
        tables = {row[0] for row in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"checkpoints", "writes"} <= tables:
            raise ValueError("unsupported checkpoint schema")
        self.is_setup = True


def cleanup_expired(directory, *, apply=False, now=None):
    root = Path(directory).resolve(strict=True)
    checkpoint = root / "checkpoints.sqlite"
    coordination = root / "coordination.sqlite"
    for path in (checkpoint, coordination):
        if not path.is_file() or path.is_symlink() or path.resolve().parent != root:
            raise ValueError("expected local checkpoint and coordination files")
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        raise ValueError("timezone-aware cutoff required")
    # Same cross-process lock as execution. No folder or database is created.
    with closing(sqlite3.connect(coordination.as_uri() + "?mode=rw", uri=True, timeout=2)) as lock:
        lock.execute("BEGIN IMMEDIATE")
        try:
            mode = "rw" if apply else "ro"
            with closing(sqlite3.connect(checkpoint.as_uri() + f"?mode={mode}", uri=True, check_same_thread=False)) as conn:
                saver = ExistingSaver(conn)
                saver.setup()
                identifiers = [row[0] for row in conn.execute("SELECT DISTINCT thread_id FROM checkpoints WHERE checkpoint_ns='' ORDER BY thread_id")]
                states, expired, invalid = {}, set(), []
                for task_id in identifiers:
                    try:
                        if str(UUID(task_id)) != task_id:
                            continue
                    except ValueError:
                        continue  # Child threads and unrelated namespaces are not roots.
                    item = saver.get_tuple({"configurable": {"thread_id": task_id}})
                    state = item.checkpoint.get("channel_values", {}) if item else {}
                    states[task_id] = state
                    try:
                        if type(state.get("owner")) is not int or state["owner"] <= 0:
                            raise ValueError("missing owner")
                        relation = state.get("revision")
                        if relation is not None:
                            if not isinstance(relation, dict) or not isinstance(relation.get("parent_task_id"), str) or str(UUID(relation["parent_task_id"])) != relation["parent_task_id"]:
                                raise ValueError("invalid revision relationship")
                        expiry = datetime.fromisoformat(state["expires"])
                        if expiry.tzinfo is None:
                            raise ValueError("missing timezone")
                        if expiry <= instant:
                            expired.add(task_id)
                    except (ValueError, KeyError, TypeError):
                        invalid.append(task_id)
                # Preserve expired ancestors of retained tasks, transitively.
                retained = set(states) - expired
                pending = list(retained)
                while pending:
                    state = states[pending.pop()]
                    relation = state.get("revision") or {}
                    parent = relation.get("parent_task_id") if isinstance(relation, dict) else None
                    if isinstance(parent, str) and parent in states and parent not in retained:
                        retained.add(parent)
                        pending.append(parent)
                candidates = sorted(expired - retained)
                # Invalid roots may have unreadable relationships: fail closed on writes.
                if apply and invalid:
                    raise ValueError("invalid task metadata; inspect before applying cleanup")
                result = {"mode": "apply" if apply else "preview", "cutoff": instant.isoformat(),
                          "expired_task_ids": candidates, "retained_dependency_ids": sorted(expired & retained),
                          "invalid_task_ids": invalid, "deleted_task_count": 0, "reports_deleted": 0}
                if apply and candidates:
                    has_attempts = bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='case_attempts'").fetchone())
                    # Parent, child, pending writes and retry ledger commit atomically.
                    with conn:
                        conn.execute("BEGIN IMMEDIATE")
                        for task_id in candidates:
                            threads = (task_id, task_id + ":case")
                            conn.execute("DELETE FROM checkpoints WHERE thread_id IN (?, ?)", threads)
                            conn.execute("DELETE FROM writes WHERE thread_id IN (?, ?)", threads)
                            if has_attempts:
                                conn.execute("DELETE FROM case_attempts WHERE task_id=?", (task_id,))
                    result["deleted_task_count"] = len(candidates)
                return result
        finally:
            lock.rollback()
