"""Explicit revision readiness check. No new plan, report, model call or notification."""
import json
import hashlib
from uuid import uuid5, NAMESPACE_URL

from teacher_case_workflow import TeacherCaseTools, case_graph
from teacher_task_runtime import TaskConflict


def source_fingerprint(product):
    # Only a digest is persisted; serialized evidence stays in request memory.
    source = {"records": product.get("records", []), "assessment": product.get("assessment_summary"), "risk": product.get("risk")}
    return hashlib.sha256(json.dumps(source, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def check_revision(store, owner, task_id, db):
    from api.teacher import student_work_product
    from models import TeacherReviewReport

    with store._session(owner) as (plans, saver):
        parent = store._owned(plans, saver, store._config(task_id), owner).values
        if parent.get("status") != "plan_approved" or not parent.get("target"):
            raise TaskConflict("approved case task required")
        tools = TeacherCaseTools(db, owner, parent["target"])
        teacher = tools.authorize()
        snapshot = case_graph(saver, tools).get_state({"configurable": {"thread_id": task_id + ":case"}})
        state = snapshot.values or {}
        if snapshot.next or not state.get("artifact_valid"):
            raise TaskConflict("completed report required")
        tools.verify(state["product_id"], state["report_id"])
        row = db.query(TeacherReviewReport).filter_by(report_id=state["report_id"]).one()
        if row.status != "revision_requested":
            raise TaskConflict("report has not been returned")
        original = json.loads(row.report_json)
        original_ids = {item["evidence_id"] for item in (original.get("evidence_audit") or {}).get("ledger", [])}
        current = student_work_product(parent["target"]["student_id"], parent["target"]["access_request_id"], db, teacher)
        current_ids = {item["id"] for item in current.get("records", [])}
        added = current_ids - original_ids
        removed = original_ids - current_ids
        tools.authorize()
        tools.verify(state["product_id"], state["report_id"])
        urgent = current.get("risk") == "urgent"
        return {
            "parent_task_id": task_id, "parent_report_id": state["report_id"],
            "source_product_id": current["case_id"], "source_fingerprint": source_fingerprint(current),
            "source": "authorized_record_comparison",
            "status": "requires_human_support" if urgent else "ready_for_plan_review" if added else "waiting_for_material",
            "added_record_count": len(added), "removed_record_count": len(removed),
            "authorization_changed": False,
            "new_plan_created": False, "new_report_created": False,
            "teacher_confirmation_required": True,
            "boundary": "新增记录不代表证据充分或退回问题已解决；须先核对相关性，再确认新计划。",
        }


def create_revision(store, owner, task_id, db):
    checked = check_revision(store, owner, task_id, db)
    if checked["status"] != "ready_for_plan_review":
        raise TaskConflict("new authorized material is required; safety takes precedence")
    parent = store.get(owner, task_id)
    revision = {key: checked[key] for key in (
        "parent_task_id", "parent_report_id", "source_product_id", "source_fingerprint",
        "added_record_count", "removed_record_count",
    )}
    # One child per parent and verified source, including retries after a lost response.
    request_id = str(uuid5(NAMESPACE_URL, f"teacher-revision:{owner}:{task_id}:{checked['source_product_id']}:{checked['source_fingerprint']}"))
    return store.create(owner, request_id, parent["contract"], parent["target"], revision=revision)
