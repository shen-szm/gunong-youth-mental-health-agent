"""
心岛守护者 - 多智能体调度器

协调5个Agent的执行顺序：
1. 感知Agent → 提取情绪状态
2. 安全Agent → 危机检测（横切）
3. 规划Agent → 制定干预计划
4. 陪伴Agent → 执行干预（咕团+环境控制）
5. 报告Agent → 按需生成报告

调度器保证：
- 安全优先：危机时立即中断，不执行普通陪伴
- 可审计：每次运行记录所有Agent的结果
- 可降级：大模型失败时自动降级为确定性模板
- 无状态：每次运行独立，不依赖内存状态
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from .base import IslandContext, AgentResult
from .perception import PerceptionAgent
from .safety import SafetyAgent
from .planner import PlanningAgent
from .companion_agent import CompanionAgent
from .reporter import ReportAgent
from .tools import get_user_safety_state


class IslandOrchestrator:
    """心岛守护者多智能体调度器。"""

    def __init__(self, db: Session, report_output_dir: str = "data/reports", external_ai_allowed: bool = False):
        self.db = db
        self.current_run_code = "island-pending"
        self.current_user_id = 0
        self.external_transfer_attempted = False
        self.perception = PerceptionAgent(db, allow_external_ai=external_ai_allowed, transfer_start_callback=self._record_transfer_start)
        self.safety = SafetyAgent()
        self.planner = PlanningAgent(allow_external_ai=external_ai_allowed, transfer_start_callback=self._record_transfer_start)
        self.companion = CompanionAgent(db, allow_external_ai=external_ai_allowed, transfer_start_callback=self._record_transfer_start)
        self.reporter = ReportAgent(db, output_dir=report_output_dir, allow_external_ai=external_ai_allowed, transfer_start_callback=self._record_transfer_start)

    async def run(self, user_id: int, nickname: str = "",
                  trigger: str = "login") -> dict:
        """
        执行一次完整的多Agent流程。

        Args:
            user_id: 用户ID
            nickname: 用户昵称
            trigger: 触发原因（login/activity_end/manual/scheduled）

        Returns:
            包含所有Agent结果的字典，可直接返回给前端
        """
        context = IslandContext(user_id=user_id, nickname=nickname)
        run_code = f"island-{uuid.uuid4().hex[:12]}"
        self.current_run_code = run_code
        self.current_user_id = user_id
        started_at = datetime.now()

        results: dict[str, AgentResult] = {}
        commands_issued = 0
        safety_status = "routine"
        model_used = "deterministic"
        degraded = 0

        # Step 0: 确定性安全门必须先于任何模型与普通 Agent。
        safety_state = get_user_safety_state(self.db, user_id)
        context.risk_level = safety_state["risk_level"]
        safety_status = context.risk_level
        if context.risk_level == "urgent":
            context.crisis_detected = True
            context.crisis_signal = safety_state["evidence"]
            safety_result = await self.safety.run(context)
            results["safety"] = safety_result
            self._save_run(run_code, user_id, trigger, results, "urgent", 0,
                           "deterministic", 0, started_at)
            self.db.commit()
            return {
                "run_code": run_code, "crisis": True, "safety_status": "urgent",
                "crisis_resources": safety_result.data.get("resources", {}),
                "perception": {},
                "message": "检测到需要立即关注的信号，已停止普通分析并切换到安全支持路径。",
            }

        # ── Step 1: 感知 ──
        perception_result = await self.perception.run(context)
        results["perception"] = perception_result
        if perception_result.data.get("llm_used"):
            model_used = "xunfei-constrained"

        # ── Step 2: 安全检查（横切）──
        safety_result = await self.safety.run(context)
        results["safety"] = safety_result

        if context.crisis_detected:
            # 危机：中断普通流程，直接返回危机响应
            safety_status = "urgent"
            crisis_data = safety_result.data.get("resources", {})
            self._save_run(run_code, user_id, trigger, results, safety_status,
                           commands_issued, model_used, degraded, started_at)
            self.db.commit()
            return {
                "run_code": run_code,
                "crisis": True,
                "safety_status": "urgent",
                "crisis_resources": crisis_data,
                "perception": self._result_to_dict(perception_result),
                "message": "检测到需要立即关注的信号，已切换到安全支持路径。",
            }

        # ── Step 3: 规划 ──
        plan_result = await self.planner.run(context)
        results["planner"] = plan_result
        if plan_result.data.get("llm_used"):
            model_used = "xunfei-constrained"
        if plan_result.status == "degraded":
            degraded = 1

        # ── Step 4: 陪伴执行 ──
        companion_result = await self.companion.run(context)
        results["companion"] = companion_result
        commands_issued = companion_result.data.get("commands_issued", 0)
        if companion_result.data.get("llm_used"):
            model_used = "xunfei-constrained"
        if companion_result.status == "degraded":
            degraded = 1

        # ── 保存运行记录 ──
        self._save_run(run_code, user_id, trigger, results, safety_status,
                       commands_issued, model_used, degraded, started_at)
        self.db.commit()

        # ── 返回前端可用的结果 ──
        return {
            "run_code": run_code,
            "crisis": False,
            "safety_status": safety_status,
            "trigger": trigger,
            "perception": self._result_to_dict(perception_result),
            "plan": self._result_to_dict(plan_result),
            "companion": self._result_to_dict(companion_result),
            "pet_message": companion_result.data.get("pet_message", ""),
            "commands": self._get_pending_commands(user_id),
            "model_used": model_used,
            "degraded": bool(degraded),
            "external_transfer_attempted": self.external_transfer_attempted,
        }

    async def generate_report(self, user_id: int, nickname: str = "",
                              days: int = 7) -> dict:
        """单独触发生成报告。"""
        context = IslandContext(user_id=user_id, nickname=nickname)
        self.current_run_code = f"island-report-{uuid.uuid4().hex[:12]}"
        self.current_user_id = user_id
        safety_state = get_user_safety_state(self.db, user_id)
        context.risk_level = safety_state["risk_level"]
        if context.risk_level == "urgent":
            context.crisis_detected = True
            context.crisis_signal = safety_state["evidence"]
            safety_result = await self.safety.run(context)
            return {
                "report_code": "", "pdf_path": "", "period_days": days,
                "mood_dominant": "", "llm_used": False, "status": "blocked",
                "crisis": True, "safety_status": "urgent",
                "crisis_resources": safety_result.data.get("resources", {}),
                "message": "当前优先处理安全，已停止生成普通情绪报告。",
                "audit_run_code": self.current_run_code,
                "external_transfer_attempted": self.external_transfer_attempted,
            }
        if context.risk_level in {"watch", "professional"}:
            return {
                "report_code": "", "pdf_path": "", "period_days": days,
                "mood_dominant": "", "llm_used": False, "status": "blocked",
                "crisis": False, "safety_status": context.risk_level,
                "message": (
                    "当前优先落实与可信成年人和专业支持的连接，暂不生成普通情绪报告。"
                    if context.risk_level == "professional"
                    else "当前建议先持续留意并与可信成年人沟通，暂不生成普通情绪报告。"
                ),
                "audit_run_code": self.current_run_code,
                "external_transfer_attempted": self.external_transfer_attempted,
            }
        result = await self.reporter.run(context, days=days)
        self.db.commit()
        return {
            "report_code": result.data.get("report_code", ""),
            "pdf_path": result.data.get("pdf_path", ""),
            "period_days": days,
            "mood_dominant": result.data.get("mood_dominant", ""),
            "llm_used": result.data.get("llm_used", False),
            "status": result.status,
            "audit_run_code": self.current_run_code,
            "external_transfer_attempted": self.external_transfer_attempted,
        }

    def _record_transfer_start(self, agent_name: str) -> None:
        """在发送去标识化字段前落盘最小审计，结果是否采用与是否传输分开记录。"""
        from models import SensitiveAccessLog
        self.external_transfer_attempted = True
        self.db.add(SensitiveAccessLog(
            actor_user_id=self.current_user_id,
            action="island_external_ai_transfer_started",
            resource_type="island_agent_run",
            resource_id=self.current_run_code[:64],
            result=f"agent:{agent_name};model:xunfei-constrained;prompt:v1",
            created_at=datetime.now(),
        ))
        self.db.commit()

    def _save_run(self, run_code: str, user_id: int, trigger: str,
                  results: dict[str, AgentResult], safety_status: str,
                  commands_issued: int, model_used: str, degraded: int,
                  started_at: datetime):
        """保存Agent运行记录到数据库。"""
        from models import IslandAgentRun
        run = IslandAgentRun(
            run_code=run_code,
            user_id=user_id,
            trigger=trigger,
            perception_result=json.dumps(
                self._result_to_dict(results.get("perception")), ensure_ascii=False),
            plan_result=json.dumps(
                self._result_to_dict(results.get("planner")), ensure_ascii=False),
            companion_result=json.dumps(
                self._result_to_dict(results.get("companion")), ensure_ascii=False),
            safety_status=safety_status,
            commands_issued=commands_issued,
            model_used=model_used,
            degraded=degraded,
            started_at=started_at,
            completed_at=datetime.now(),
        )
        self.db.add(run)

    def _get_pending_commands(self, user_id: int) -> list[dict]:
        """获取用户待执行的心岛指令。"""
        from models import IslandCommand
        commands = (
            self.db.query(IslandCommand)
            .filter(IslandCommand.user_id == user_id,
                    IslandCommand.status == "pending")
            .order_by(IslandCommand.created_at.desc())
            .limit(10)
            .all()
        )
        result = []
        for cmd in commands:
            try:
                payload = json.loads(cmd.payload_json or "{}")
            except (json.JSONDecodeError, TypeError):
                payload = {}
            result.append({
                "id": cmd.id,
                "type": cmd.command_type,
                "payload": payload,
                "reason": cmd.reason,
            })
        return result

    def _result_to_dict(self, result: AgentResult | None) -> dict:
        """将AgentResult序列化为可JSON化的字典。"""
        if not result:
            return {}
        return {
            "agent_name": result.agent_name,
            "status": result.status,
            "summary": result.summary,
            "data": result.data,
            "error": result.error,
        }
