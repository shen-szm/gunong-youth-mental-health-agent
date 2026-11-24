"""Teacher-only planning and opt-in, permission-bound case execution."""
from pathlib import Path
import sqlite3
from uuid import UUID
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from auth import require_teacher
from config import settings
from models import User
from database import get_db
from teacher_task_planner import PlanningRequest, TaskContract, preview_task
from teacher_task_intent import IntentInput, interpret_intent
from xunfei.spark_api import ask_spark, is_spark_available

router = APIRouter(prefix="/api/teacher/tasks", tags=["teacher-tasks"])


@router.get("/capabilities")
def capabilities(teacher: User = Depends(require_teacher)):
    # No optional runtime import: baseline deployments keep the pilot hidden.
    return {"durable_case_execution": settings.ENABLE_TEACHER_DURABLE_PLANS}


@router.post("/preview")
async def preview(request: PlanningRequest, teacher: User = Depends(require_teacher)):
    enabled = settings.ALLOW_TEACHER_TASK_PLANNER_AI and settings.ALLOW_EXTERNAL_AI and is_spark_available()
    return await preview_task(request, generate=ask_spark if enabled else None)


@router.post("/intent-preview")
async def intent_preview(request: IntentInput, teacher: User = Depends(require_teacher)):
    enabled = settings.ALLOW_TEACHER_TASK_PLANNER_AI and settings.ALLOW_EXTERNAL_AI and is_spark_available()
    return await interpret_intent(request, generate=ask_spark if enabled else None)


class CreatePlanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    contract: TaskContract


class CreateCasePlanInput(CreatePlanInput):
    student_id: int = Field(gt=0, strict=True)
    access_request_id: int | None = Field(default=None, gt=0, strict=True)


class DecidePlanInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    approved: bool


class TerminatePlanInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    confirmed: bool
    reason: Literal["manual", "source_changed", "retry_exhausted"] = "manual"


def durable_store(db: Session = Depends(get_db)):
    if not settings.ENABLE_TEACHER_DURABLE_PLANS:
        raise HTTPException(404, "持久化计划试点尚未启用")
    # Lazy import: baseline installation does not require optional graph packages.
    from teacher_task_runtime import DurableTeacherPlans

    def authorize(owner):
        row = db.query(User).populate_existing().filter(User.id == owner).first()
        return bool(row and int(row.is_admin or 0) >= 1)

    return DurableTeacherPlans(Path(__file__).resolve().parents[1] / ".teacher-plan-runtime", authorize)


def call_store(operation):
    from teacher_task_runtime import TaskConflict
    try:
        return operation()
    except PermissionError:
        raise HTTPException(403, "教师权限已失效") from None
    except LookupError:
        raise HTTPException(404, "任务不存在或已过期") from None
    except TaskConflict:
        raise HTTPException(409, "任务条件或确认状态已变化，请重新查看") from None
    except sqlite3.OperationalError:
        raise HTTPException(503, "任务存储暂不可用，请稍后重试") from None


class ClarificationInput(IntentInput):
    request_id: UUID = Field(strict=False)
    student_id: int = Field(gt=0, strict=True)
    access_request_id: int | None = Field(default=None, gt=0, strict=True)


class ClarificationDecisionInput(IntentInput):
    decisions: dict[str, Literal['prohibited', 'requested', 'quoted', 'uncertain']] = Field(max_length=6)


def clarification_store(store=Depends(durable_store), db: Session = Depends(get_db)):
    from teacher_clarification import ClarificationStore
    from teacher_case_workflow import TeacherCaseTools
    return ClarificationStore(store.directory, lambda owner, target: TeacherCaseTools(db, owner, target).authorize())


def call_clarification(operation):
    from teacher_clarification import ClarificationConflict
    try:
        return call_store(operation)
    except ClarificationConflict:
        raise HTTPException(409, '原始需求、核对结果或规则已变化，请重新核对；未解除执行限制') from None


@router.post('/clarifications')
def create_clarification(payload: ClarificationInput, teacher: User = Depends(require_teacher), store=Depends(clarification_store)):
    if not payload.confirmed:
        raise HTTPException(422, '请明确确认保存需求指纹与分类记录，不保存需求原文')
    target = {'student_id': payload.student_id, 'access_request_id': payload.access_request_id}
    return call_clarification(lambda: store.create(teacher.id, str(payload.request_id), payload.goal, target))


@router.get('/clarifications/{receipt_id}')
def read_clarification(receipt_id: UUID, teacher: User = Depends(require_teacher), store=Depends(clarification_store)):
    return call_clarification(lambda: store.get(teacher.id, str(receipt_id)))


@router.post('/clarifications/{receipt_id}/decision')
def decide_clarification(receipt_id: UUID, payload: ClarificationDecisionInput, teacher: User = Depends(require_teacher), store=Depends(clarification_store)):
    if not payload.confirmed:
        raise HTTPException(422, '请明确确认分类结果；这不会授权任务执行')
    return call_clarification(lambda: store.decide(teacher.id, str(receipt_id), payload.goal, payload.decisions))


@router.post("/durable-plans")
def create_plan(payload: CreatePlanInput, teacher: User = Depends(require_teacher), store=Depends(durable_store)):
    return call_store(lambda: store.create(teacher.id, str(payload.request_id), payload.contract.model_dump()))


@router.get("/durable-plans/{task_id}")
def get_plan(task_id: UUID, teacher: User = Depends(require_teacher), store=Depends(durable_store)):
    return call_store(lambda: store.get(teacher.id, str(task_id)))


@router.post("/durable-plans/{task_id}/decision")
def decide_plan(task_id: UUID, payload: DecidePlanInput, teacher: User = Depends(require_teacher), store=Depends(durable_store)):
    return call_store(lambda: store.decide(teacher.id, str(task_id), payload.digest, payload.approved))


@router.delete("/durable-plans/{task_id}", status_code=204)
def delete_plan(task_id: UUID, teacher: User = Depends(require_teacher), store=Depends(durable_store)):
    call_store(lambda: store.delete(teacher.id, str(task_id)))
    return Response(status_code=204)


@router.post("/durable-plans/{task_id}/terminate")
def terminate_plan(task_id: UUID, payload: TerminatePlanInput, teacher: User = Depends(require_teacher), store=Depends(durable_store)):
    if not payload.confirmed:
        raise HTTPException(422, "请明确确认终止任务")
    return call_store(lambda: store.terminate(teacher.id, str(task_id), payload.digest, payload.reason))


@router.post("/case-plans")
def create_case_plan(payload: CreateCasePlanInput, teacher: User = Depends(require_teacher), store=Depends(durable_store), db: Session = Depends(get_db)):
    from teacher_case_workflow import TeacherCaseTools
    target = {"student_id": payload.student_id, "access_request_id": payload.access_request_id}
    call_store(lambda: TeacherCaseTools(db, teacher.id, target).authorize())
    contract = payload.contract
    if (contract.objective, contract.period_days, contract.output_format, contract.resource_policy) != ("conversation_preparation", 30, "checklist", "not_needed"):
        raise HTTPException(422, "当前执行仅支持30天授权范围的个案沟通准备标准报告，不支持一页简报或额外检索")
    return call_store(lambda: store.create(teacher.id, str(payload.request_id), contract.model_dump(), target=target))


@router.get("/case-history")
def case_history(student_id: int = Query(gt=0), access_request_id: int | None = Query(default=None, gt=0),
                 teacher: User = Depends(require_teacher), store=Depends(durable_store), db: Session = Depends(get_db)):
    from teacher_case_workflow import TeacherCaseTools
    target = {"student_id": student_id, "access_request_id": access_request_id}
    def read():
        TeacherCaseTools(db, teacher.id, target).authorize()
        result = store.history(teacher.id, target)
        TeacherCaseTools(db, teacher.id, target).authorize()
        return result
    return call_store(read)


@router.post("/durable-plans/{task_id}/execute")
def execute_case_plan(task_id: UUID, teacher: User = Depends(require_teacher), store=Depends(durable_store), db: Session = Depends(get_db)):
    from teacher_case_workflow import TeacherCaseTools, execute_case
    return call_store(lambda: execute_case(store, teacher.id, str(task_id), lambda target: TeacherCaseTools(db, teacher.id, target)))


@router.get("/durable-plans/{task_id}/execution")
def case_execution(task_id: UUID, teacher: User = Depends(require_teacher), store=Depends(durable_store), db: Session = Depends(get_db)):
    from teacher_case_workflow import TeacherCaseTools, execute_case
    return call_store(lambda: execute_case(store, teacher.id, str(task_id), lambda target: TeacherCaseTools(db, teacher.id, target), run=False))


@router.post("/durable-plans/{task_id}/revision-check")
def revision_check(task_id: UUID, teacher: User = Depends(require_teacher), store=Depends(durable_store), db: Session = Depends(get_db)):
    from teacher_revision_check import check_revision
    return call_store(lambda: check_revision(store, teacher.id, str(task_id), db))


@router.post("/durable-plans/{task_id}/revision-plans")
def revision_plan(task_id: UUID, teacher: User = Depends(require_teacher), store=Depends(durable_store), db: Session = Depends(get_db)):
    from teacher_revision_check import create_revision
    return call_store(lambda: create_revision(store, teacher.id, str(task_id), db))
