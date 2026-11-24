"""Durable PLAN approval, not student-data execution. Local-disk pilot only."""
from contextlib import contextmanager, closing
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import TypedDict
from uuid import UUID, uuid5, NAMESPACE_URL

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt
from langsmith import tracing_context

from teacher_task_planner import TaskContract, fallback_plan


class TaskState(TypedDict, total=False):
    owner: int
    contract: dict
    digest: str
    expires: str
    status: str
    plan: list[str]
    target: dict
    revision: dict
    termination: dict
    last_failure: dict | None


def build_graph(saver):
    def plan(state):
        contract = TaskContract.model_validate(state["contract"])
        return {"plan": fallback_plan(contract).tools, "status": "waiting_approval"}

    def approve(state):
        decision = interrupt({"kind": "confirm_plan", "digest": state["digest"], "tools": state["plan"], "target": state.get("target")})
        if decision.get("digest") != state["digest"] or type(decision.get("approved")) is not bool:
            raise ValueError("invalid approval")
        return {"status": "plan_approved" if decision["approved"] else "cancelled"}

    builder = StateGraph(TaskState)
    builder.add_node("plan", plan)
    builder.add_node("approval", approve)
    builder.add_edge(START, "plan")
    builder.add_edge("plan", "approval")
    builder.add_edge("approval", END)
    return builder.compile(checkpointer=saver)


class TaskConflict(ValueError):
    pass


class DurableTeacherPlans:
    def __init__(self, directory, authorize):
        self.directory = Path(directory).resolve()
        self.authorize = authorize

    @contextmanager
    def _session(self, owner):
        if type(owner) is not int or owner <= 0 or not self.authorize(owner):
            raise PermissionError("teacher access denied")
        self.directory.mkdir(parents=True, exist_ok=True)
        # A separate SQLite write transaction serializes callers across processes.
        # The OS releases the lock on crash; checkpoint writes use a different DB.
        with closing(sqlite3.connect(self.directory / "coordination.sqlite", timeout=2)) as lock:
            lock.execute("BEGIN IMMEDIATE")
            try:
                if not self.authorize(owner):
                    raise PermissionError("teacher access revoked")
                with closing(sqlite3.connect(self.directory / "checkpoints.sqlite", check_same_thread=False)) as connection:
                    saver = SqliteSaver(connection)
                    with tracing_context(enabled=False):
                        yield build_graph(saver), saver
            finally:
                lock.rollback()

    @staticmethod
    def _config(task_id):
        return {"configurable": {"thread_id": str(UUID(task_id))}, "recursion_limit": 8}

    def _owned(self, graph, saver, config, owner):
        snapshot = graph.get_state(config)
        state = snapshot.values
        if not state or state.get("owner") != owner:
            raise LookupError("task not found")
        if datetime.fromisoformat(state["expires"]) <= datetime.now(timezone.utc):
            saver.delete_thread(config["configurable"]["thread_id"])
            self._delete_case(saver, config["configurable"]["thread_id"])
            raise LookupError("task expired")
        return snapshot

    @staticmethod
    def _public(task_id, snapshot):
        state = snapshot.values
        return {"task_id": task_id, "contract": state["contract"], "digest": state["digest"],
                "status": state.get("status", "running"), "tools": state.get("plan", []),
                "source": "local_rules", "execution_started": False, "student_data_accessed": False,
                "capability": "durable_plan_approval", "expires_at": state["expires"],
                "target": state.get("target"), "revision": state.get("revision"), "termination": state.get("termination"),
                "last_failure": state.get("last_failure")}

    def history(self, owner, target, limit=30):
        """Latest plan snapshots only; no student prose, no execution or TTL deletion."""
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ValueError("invalid history limit")
        with self._session(owner) as (_, saver):
            saver.setup()
            roots = saver.conn.execute("SELECT thread_id, MAX(checkpoint_id) FROM checkpoints WHERE checkpoint_ns='' AND length(thread_id)=36 GROUP BY thread_id ORDER BY MAX(checkpoint_id) DESC").fetchall()
            items = []
            for task_id, _ in roots:
                try:
                    config = self._config(task_id)
                except ValueError:
                    continue
                entry = saver.get_tuple(config)
                state = entry.checkpoint.get("channel_values", {}) if entry else {}
                if state.get("owner") != owner or state.get("target") != target:
                    continue
                try:
                    if datetime.fromisoformat(state["expires"]) <= datetime.now(timezone.utc):
                        continue
                except (KeyError, ValueError, TypeError):
                    continue
                items.append({"task_id": task_id, "status": state.get("status", "running"),
                              "updated_at": entry.checkpoint["ts"], "expires_at": state["expires"],
                              "is_revision": bool(state.get("revision"))})
                if len(items) > limit:
                    break
            return {"items": items[:limit], "has_more": len(items) > limit}

    def create(self, owner, request_id, contract, target=None, revision=None):
        # Stable per-user idempotency key. A changed contract needs a new request ID.
        task_id = str(uuid5(NAMESPACE_URL, f"teacher-plan:{owner}:{UUID(request_id)}"))
        contract = TaskContract.model_validate(contract).model_dump()
        if target is not None:
            if set(target) != {"student_id", "access_request_id"} or type(target["student_id"]) is not int or target["student_id"] <= 0:
                raise ValueError("invalid target")
            access_id = target["access_request_id"]
            if access_id is not None and (type(access_id) is not int or access_id <= 0):
                raise ValueError("invalid access request")
        fingerprint = {"contract": contract, "target": target} if target is not None else contract
        if revision is not None:
            fingerprint = {"contract": contract, "target": target, "revision": revision}
        digest = hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()
        config = self._config(task_id)
        with self._session(owner) as (graph, saver):
            snapshot = graph.get_state(config)
            if snapshot.values:
                snapshot = self._owned(graph, saver, config, owner)
                if snapshot.values["digest"] != digest:
                    raise TaskConflict("idempotency key reused with changed contract")
                if snapshot.values.get("status") is None:
                    graph.invoke(None, config)
            else:
                graph.invoke({"owner": owner, "contract": contract, "digest": digest, "target": target, "revision": revision,
                              "expires": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()}, config)
            return self._public(task_id, graph.get_state(config))

    def get(self, owner, task_id):
        config = self._config(task_id)
        with self._session(owner) as (graph, saver):
            return self._public(task_id, self._owned(graph, saver, config, owner))

    def decide(self, owner, task_id, digest, approved):
        if type(approved) is not bool:
            raise ValueError("approval must be boolean")
        config = self._config(task_id)
        with self._session(owner) as (graph, saver):
            snapshot = self._owned(graph, saver, config, owner)
            if digest != snapshot.values["digest"]:
                raise TaskConflict("stale approval")
            terminal = "plan_approved" if approved else "cancelled"
            status = snapshot.values.get("status")
            if status in {"plan_approved", "cancelled"}:
                if status != terminal:
                    raise TaskConflict("task already decided")
                return self._public(task_id, snapshot)
            if status != "waiting_approval":
                raise TaskConflict("task not ready for approval")
            graph.invoke(Command(resume={"digest": digest, "approved": approved}), config)
            return self._public(task_id, graph.get_state(config))

    def terminate(self, owner, task_id, digest, reason="manual"):
        if reason not in {"manual", "source_changed", "retry_exhausted"}:
            raise ValueError("invalid termination reason")
        config = self._config(task_id)
        with self._session(owner) as (graph, saver):
            snapshot = self._owned(graph, saver, config, owner)
            if snapshot.values["digest"] != digest:
                raise TaskConflict("stale termination confirmation")
            if snapshot.values.get("status") == "terminated":
                return self._public(task_id, snapshot)
            if snapshot.values.get("status") not in {"waiting_approval", "plan_approved"}:
                raise TaskConflict("task cannot be terminated")
            child = saver.get_tuple({"configurable": {"thread_id": task_id + ":case"}})
            if child and child.checkpoint.get("channel_values", {}).get("artifact_valid"):
                raise TaskConflict("delivered report must use report review instead")
            graph.update_state(config, {"status": "terminated", "termination": {
                "actor_id": owner, "at": datetime.now(timezone.utc).isoformat(), "reason": reason,
            }}, as_node="approval")
            return self._public(task_id, graph.get_state(config))

    def delete(self, owner, task_id):
        config = self._config(task_id)
        with self._session(owner) as (graph, saver):
            self._owned(graph, saver, config, owner)
            saver.delete_thread(config["configurable"]["thread_id"])
            self._delete_case(saver, config["configurable"]["thread_id"])

    @staticmethod
    def _delete_case(saver, task_id):
        saver.delete_thread(task_id + ":case")
        if saver.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='case_attempts'").fetchone():
            saver.conn.execute("DELETE FROM case_attempts WHERE task_id=?", (task_id,))
            saver.conn.commit()
