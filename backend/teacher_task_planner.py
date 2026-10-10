"""Bounded planning preview. No student records are read and no tools execute here."""
from __future__ import annotations

import asyncio
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Tool = Literal["query_authorized_items", "check_evidence_gaps", "search_approved_resources", "render_work_product", "verify_work_product"]
TOOLS = {
    "query_authorized_items": "查询授权事项",
    "check_evidence_gaps": "检查资料缺口",
    "search_approved_resources": "检索审核资源",
    "render_work_product": "生成工作成果",
    "verify_work_product": "核验工作成果",
}
PLANNER_VERSION = "teacher-task-preview-v1"


class TaskContract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    objective: Literal["weekly_followup", "conversation_preparation"]
    period_days: Literal[7, 14, 30] = 7
    scope: Literal["authorized_only"] = "authorized_only"
    output_format: Literal["checklist", "one_page_brief"] = "checklist"
    resource_policy: Literal["not_needed", "approved_only"] = "not_needed"
    delivery: Literal["draft_for_review"] = "draft_for_review"


class PlanningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    contract: TaskContract
    confirmed: bool = False


class ToolPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    tools: list[Tool] = Field(min_length=4, max_length=5)

    @model_validator(mode="after")
    def ordered_safe_tools(self):
        if len(set(self.tools)) != len(self.tools):
            raise ValueError("duplicate tool")
        required = ["query_authorized_items", "check_evidence_gaps", "render_work_product", "verify_work_product"]
        if [tool for tool in self.tools if tool != "search_approved_resources"] != required:
            raise ValueError("required dependencies violated")
        if "search_approved_resources" in self.tools and self.tools.index("search_approved_resources") != 2:
            raise ValueError("retrieval must follow evidence checking")
        return self


def fallback_plan(contract: TaskContract) -> ToolPlan:
    tools = ["query_authorized_items", "check_evidence_gaps"]
    if contract.resource_policy == "approved_only":
        tools.append("search_approved_resources")
    return ToolPlan(tools=tools + ["render_work_product", "verify_work_product"])


def parse_plan(raw: str, contract: TaskContract) -> ToolPlan:
    # Accept a single JSON document, not a salvaged object inside arbitrary prose.
    plan = ToolPlan.model_validate_json(raw)
    if ("search_approved_resources" in plan.tools) != (contract.resource_policy == "approved_only"):
        raise ValueError("resource policy violated")
    return plan


def planner_messages(contract: TaskContract, repair: bool = False) -> list[dict]:
    return [
        {"role": "system", "content": (
            "你是教师任务规划器，只返回一个JSON对象，唯一字段tools为工具名称数组。"
            "必需顺序：query_authorized_items、check_evidence_gaps、render_work_product、verify_work_product。"
            "resource_policy为approved_only时，在check_evidence_gaps之后插入search_approved_resources；"
            "否则不检索。不得重复、增加工具或其他字段。这里只规划，不读取学生资料、不执行工具、不发送通知。"
            + ("上次输出未通过契约校验，请严格遵守JSON结构和工具顺序。" if repair else "")
        )},
        {"role": "user", "content": json.dumps(contract.model_dump(), ensure_ascii=False)},
    ]


async def preview_task(request: PlanningRequest, generate=None) -> dict:
    contract = request.contract
    base = {
        "planner_version": PLANNER_VERSION,
        "contract": contract.model_dump(),
        "execution_started": False,
        "student_data_accessed": False,
        "approval_granted": False,
        "capability": "bounded_planning_preview",
        "limitations": ["只验证受限工具规划，不代表自由任务理解或自主执行已经实现", "任务确认不授予学生资料访问权限", "执行阶段仍须重新检查授权"],
    }
    if not request.confirmed:
        return {**base, "status": "waiting_confirmation", "source": "none", "model_attempts": 0, "fallback_reason": None, "steps": []}
    plan = fallback_plan(contract)
    source, attempts, failure = "local_rules", 0, "model_disabled"
    if generate is not None:
        for attempt in range(2):
            attempts += 1
            try:
                raw = await asyncio.wait_for(generate(planner_messages(contract, repair=bool(attempt)), max_tokens=300, temperature=0), timeout=12)
                plan = parse_plan(raw, contract)
                source, failure = "model_selected", None
                break
            except (ValueError, TypeError):
                failure = "invalid_plan"
            except TimeoutError:
                failure = "model_timeout"
                break
            except Exception:
                # Do not persist or return provider errors (which may contain credentials).
                failure = "model_unavailable"
                break
    steps = []
    for index, tool in enumerate(plan.tools):
        steps.append({"id": f"step-{index + 1}", "tool": tool, "label": TOOLS[tool], "status": "planned", "depends_on": [f"step-{index}"] if index else []})
    return {**base, "status": "preview_ready", "source": source, "model_attempts": attempts, "fallback_reason": failure, "steps": steps}
