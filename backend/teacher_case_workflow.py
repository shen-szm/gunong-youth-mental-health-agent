"""Real case tools with reference-only LangGraph checkpoints; no autonomous messaging."""
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from typing import TypedDict

from fastapi import HTTPException
from langgraph.graph import StateGraph, START, END

from teacher_task_runtime import TaskConflict


class CaseState(TypedDict, total=False):
    product_id: str
    report_id: str
    report_hash: str
    evidence_status: str
    artifact_valid: bool
    steps: list[str]
    evidence_available: bool
    information_incomplete: bool


def case_graph(saver, tools):
    def invoke(operation):
        try:
            return operation()
        except HTTPException as exc:
            if exc.status_code in {401, 403, 404}:
                raise PermissionError("case authorization unavailable") from None
            raise TaskConflict("case source unavailable") from None
        except (PermissionError, TaskConflict):
            raise
        except Exception:
            raise RuntimeError("teacher tool failed") from None

    def query(state):
        return {"product_id": invoke(tools.query), "steps": ["query_authorized_items"]}

    def render(state):
        report_id = invoke(lambda: tools.render(state["product_id"]))
        return {"report_id": report_id, "steps": [*state["steps"], "render_work_product"]}

    def gaps(state):
        summary = invoke(lambda: tools.check_evidence(state["product_id"]))
        return {**summary, "steps": [*state["steps"], "check_evidence_gaps"]}

    def verify(state):
        result = invoke(lambda: tools.verify(state["product_id"], state["report_id"]))
        return {**result, "steps": [*state["steps"], "verify_work_product"]}

    builder = StateGraph(CaseState)
    builder.add_node("query", query)
    builder.add_node("render", render)
    builder.add_node("gaps", gaps)
    builder.add_node("verify", verify)
    builder.add_edge(START, "query")
    builder.add_edge("query", "gaps")
    builder.add_edge("gaps", "render")
    builder.add_edge("render", "verify")
    builder.add_edge("verify", END)
    return builder.compile(checkpointer=saver)


class TeacherCaseTools:
    def __init__(self, db, owner, target):
        self.db, self.owner, self.target = db, owner, target

    def authorize(self):
        from api.teacher import _require_student_access
        from models import User
        self.db.expire_all()
        teacher = self.db.query(User).populate_existing().filter(User.id == self.owner).first()
        if not teacher or int(teacher.is_admin or 0) < 1:
            raise PermissionError("teacher role revoked")
        approved = _require_student_access(self.db, teacher, self.target["student_id"], self.target["access_request_id"])
        if (approved.id if approved else None) != self.target["access_request_id"]:
            raise PermissionError("authorization scope changed")
        return teacher

    def query(self):
        from api.teacher import student_work_product
        teacher = self.authorize()
        result = student_work_product(self.target["student_id"], self.target["access_request_id"], self.db, teacher)
        self.authorize()
        if getattr(self, "revision", None):
            from teacher_revision_check import source_fingerprint
            if result["case_id"] != self.revision["source_product_id"] or source_fingerprint(result) != self.revision["source_fingerprint"]:
                raise TaskConflict("confirmed revision source changed")

        return result["case_id"]

    def render(self, product_id):
        from api.teacher import generate_teacher_review_report
        from models import TeacherReviewReport
        teacher = self.authorize()
        # Existing endpoint reuses immutable draft/reviewed reports. Pin the source
        # before invoking it so retries cannot silently consume a newer case.
        if self.query() != product_id:
            raise TaskConflict("source changed; create a new task")
        report = asyncio.run(generate_teacher_review_report(self.target["student_id"], self.target["access_request_id"], self.db, teacher))
        self.authorize()
        row = self.db.query(TeacherReviewReport).filter_by(report_id=report["report_id"]).one()
        if getattr(self, "revision", None):
            self.query()
        if row.source_product_id != product_id:
            raise TaskConflict("source changed during generation")
        return row.report_id

    def check_evidence(self, product_id):
        from api.teacher import student_work_product
        teacher = self.authorize()
        product = student_work_product(self.target["student_id"], self.target["access_request_id"], self.db, teacher)
        if product["case_id"] != product_id:
            raise TaskConflict("source changed")
        # Validate the input shape used by the existing report evidence checker.
        if not isinstance(product.get("records", []), list) or not isinstance(product.get("assessment_summary") or {}, dict):
            raise TaskConflict("invalid evidence structure")
        self.authorize()
        return {"evidence_available": bool(product.get("records")),
                "information_incomplete": not product.get("records") or not product.get("assessment_summary") or bool((product.get("assessment_summary") or {}).get("information_gaps"))}

    def verify(self, product_id, report_id):
        from models import TeacherReviewReport
        self.authorize()
        row = self.db.query(TeacherReviewReport).filter_by(
            report_id=report_id, source_product_id=product_id,
            student_user_id=self.target["student_id"], generated_by_user_id=self.owner,
            request_id=self.target["access_request_id"],
        ).first()
        if not row:
            raise TaskConflict("report missing or scope changed")
        digest = hashlib.sha256(row.report_json.encode("utf-8")).hexdigest()
        if digest != row.content_hash:
            raise TaskConflict("report integrity mismatch")
        report = json.loads(row.report_json)
        audit = report.get("evidence_audit") or {}
        return {"report_hash": digest, "artifact_valid": True, "report_status": row.status,
                "evidence_status": "review_ready" if audit.get("status") == "review_ready" else "needs_review"}


def execute_case(store, owner, task_id, tools_factory, run=True):
    """Explicit retry resumes checkpoints. Reads never execute nodes."""
    with store._session(owner) as (plan_graph, saver):
        config = store._config(task_id)
        parent = store._owned(plan_graph, saver, config, owner).values
        if parent.get("status") != "plan_approved" or not parent.get("target"):
            raise TaskConflict("case target must be bound and approved")
        contract = parent["contract"]
        if (contract["objective"], contract["period_days"], contract["output_format"], contract["resource_policy"]) != ("conversation_preparation", 30, "checklist", "not_needed"):
            raise TaskConflict("unsupported execution contract")
        tools = tools_factory(parent["target"])
        tools.authorize()
        config = {"configurable": {"thread_id": task_id + ":case"}, "recursion_limit": 8}
        graph = case_graph(saver, tools)
        snapshot = graph.get_state(config)
        error = None
        saver.conn.execute("CREATE TABLE IF NOT EXISTS case_attempts (task_id TEXT PRIMARY KEY, attempts INTEGER NOT NULL)")
        saver.conn.commit()
        ledger = saver.conn.execute("SELECT attempts FROM case_attempts WHERE task_id=?", (task_id,)).fetchone()
        attempts = ledger[0] if ledger else 0
        if run and (not snapshot.values or snapshot.next):
            if parent.get("revision"):
                from models import TeacherReviewReport
                revision = parent["revision"]
                origin = store._owned(plan_graph, saver, store._config(revision["parent_task_id"]), owner).values
                if origin.get("target") != parent["target"]:
                    raise TaskConflict("revision target changed")
                old = tools.db.query(TeacherReviewReport).filter_by(report_id=revision["parent_report_id"], generated_by_user_id=owner).first()
                if not old or old.status != "revision_requested":
                    raise TaskConflict("returned report required")
                tools.verify(old.source_product_id, old.report_id)
                tools.revision = revision
                tools.query()  # Recheck pinned evidence before any report side effect.
            if attempts >= 3:
                raise TaskConflict("retry budget exhausted")
            attempts += 1
            saver.conn.execute("INSERT INTO case_attempts VALUES (?, ?) ON CONFLICT(task_id) DO UPDATE SET attempts=excluded.attempts", (task_id, attempts))
            saver.conn.commit()
            try:
                graph.invoke(None if snapshot.values else {"steps": []}, config)
            except (PermissionError, HTTPException):
                raise
            except TaskConflict:
                error = "source_or_artifact_changed"
            except Exception:
                # Never return or persist provider errors / student payloads.
                error = "tool_failed"
            failure = {"code": error, "at": datetime.now(timezone.utc).isoformat(), "attempt": attempts} if error else None
            plan_graph.update_state(store._config(task_id), {"last_failure": failure}, as_node="approval")
            parent = {**parent, "last_failure": failure}
        snapshot = graph.get_state(config)
        tools.authorize()
        values = snapshot.values or {}
        complete = bool(values.get("artifact_valid") and not snapshot.next)
        current_report = {}
        if complete:
            # Recheck stored artifact on every read, not only at generation time.
            current_report = tools.verify(values["product_id"], values["report_id"])
        failure = parent.get("last_failure") if not complete else None
        error = error or (failure or {}).get("code")
        return {"task_id": task_id, "status": "awaiting_report_review" if complete else "failed" if error or any(t.error for t in snapshot.tasks) else "pending",
                "completed_tools": values.get("steps", []), "report_id": values.get("report_id") if complete else None,
                "report_hash": values.get("report_hash") if complete else None,
                "evidence_status": values.get("evidence_status") if complete else None,
                "error": error, "last_failure": failure, "execution_source": "langgraph_existing_teacher_tools",
                "attempts": attempts,
                "report_status": current_report.get("report_status") if complete else None,
                "human_followup_completed": False}
