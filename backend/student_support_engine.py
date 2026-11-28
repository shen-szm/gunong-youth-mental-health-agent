from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError

from sqlalchemy.orm import Session

from models import StudentChatSession, StudentSupportEvent, StudentSupportRun
from student_support_resources import route_support_resources


PROMPT_VERSION = "student-support-orchestrator-v2"


def _bounded_support_contract(
    risk_level: str,
    external_ai_enabled: bool,
    derived_features: dict | None,
    companion_engine: bool = False,
) -> tuple[dict, dict]:
    """Build a small, auditable plan from derived voluntary-expression cues only."""
    features = derived_features or {}
    allowed_themes = {"同伴相处", "学习任务", "休息和精力", "家庭相处", "最近发生的事情"}
    allowed_impacts = {"学习", "睡眠精力", "饮食", "同伴相处", "家庭相处"}
    theme = features.get("support_theme")
    if theme not in allowed_themes:
        theme = "最近发生的事情"
    impacts = [
        item for item in features.get("functional_impact", [])
        if item in allowed_impacts
    ][:3]
    impact_phrase = f"，优先照顾{'、'.join(impacts)}方面的影响" if impacts else ""
    objective_by_risk = {
        "routine": f"围绕{theme}交付一轮低负担、非诊断性支持{impact_phrase}",
        "watch": f"围绕{theme}交付可选择的小步骤，并准备可信成年人支持入口{impact_phrase}",
        "professional": f"围绕{theme}交付非诊断性支持，并明确连接真人专业支持{impact_phrase}",
    }
    constraints = [
        "仅依据学生主动表达的结构化线索",
        "不从行为、活跃度或沉默推断情绪",
        "危机规则始终优先于普通计划",
        "不作医学诊断或量表结论",
        (
            "外部模型接收本轮对话原文用于生成朋友式回应；姓名、学校、联系方式和精确地址不发送"
            if companion_engine
            else "外部模型仅可在受限枚举中选择回应策略"
            if external_ai_enabled
            else "本轮使用本地确定性策略，不向外部模型传输数据"
        ),
    ]
    if risk_level == "professional":
        constraints.append("不得把需要真人支持的任务交给学生独自完成")
    contract = {
        "objective": objective_by_risk.get(risk_level, objective_by_risk["routine"]),
        "constraints": constraints,
        "acceptance_criteria": [
            "安全分流先于普通回应",
            "交付一个清晰且低负担的下一步",
            "明确后续责任人和支持边界",
            "结果可由结构化验收项逐项核对",
        ],
    }
    scope = {
        "support_theme": theme,
        "functional_impact": impacts,
        "risk_level": risk_level,
        "execution_mode": (
            "companion_model" if companion_engine
            else "constrained_model" if external_ai_enabled
            else "local_deterministic"
        ),
        "cue_policy": (
            "student_voluntary_transcript_and_structured" if companion_engine
            else "student_voluntary_structured_only"
        ),
    }
    return contract, scope


def _urgent_safety_contract() -> dict:
    return {
        "objective": "停止普通生成并交付可立即执行的真人安全支持路径",
        "constraints": [
            "危机规则优先",
            "普通内容生成停用",
            "不要求学生独自处置",
            "不向可能的伤害来源交接",
        ],
        "acceptance_criteria": [
            "明确可信成年人或教师接力",
            "提供12356心理支持入口",
            "迫切危险时提供110和120紧急路径",
        ],
    }


def _delivery_artifact(plan: list[dict], risk_level: str) -> dict:
    planner = next((step for step in plan if step.get("id") == "task_plan"), None)
    scope = planner.get("scope", {}) if planner else {}
    theme = scope.get("support_theme", "当前安全")
    impacts = scope.get("functional_impact") or []
    if risk_level == "urgent":
        return {
            "title": "真人安全支持接力",
            "outcome": "普通生成已停止，系统已交付可信成年人、12356及紧急求助路径",
            "next_action": "立即由可信成年人或教师确认当下安全，迫切危险时联系110或120",
            "next_owner": "trusted_adult_or_emergency_support",
        }
    owner_by_risk = {
        "routine": "student_choice",
        "watch": "student_with_trusted_adult",
        "professional": "trusted_adult_or_school_support",
    }
    action_by_risk = {
        "routine": "由学生决定继续表达、尝试一个低负担步骤或暂时停止",
        "watch": "由学生选择一位可信成年人共同确认下一步",
        "professional": "当天联系可信成年人或校内专业支持",
    }
    impact_summary = f"；主动提及的功能影响为{'、'.join(impacts)}" if impacts else ""
    return {
        "title": f"{theme}支持交付",
        "outcome": f"已交付一轮非诊断性支持与可选择的下一步{impact_summary}",
        "next_action": action_by_risk.get(risk_level, action_by_risk["routine"]),
        "next_owner": owner_by_risk.get(risk_level, "student_choice"),
    }


def _verify_delivery(
    *,
    plan: list[dict],
    risk_level: str,
    source: str,
    output_message_id: int | None,
    task_contract: dict,
    artifact: dict,
    resources: list[dict],
    safety_gate_first: bool,
) -> dict:
    def check(check_id: str, label: str, passed: bool, evidence: str) -> dict:
        return {
            "id": check_id,
            "label": label,
            "status": "passed" if passed else "failed",
            "evidence": evidence,
        }

    plan_ids = {step.get("id") for step in plan}
    resource_ids = {item.get("id") for item in resources}
    if risk_level == "urgent":
        checks = [
            check(
                "ordinary_generation_stopped",
                "普通生成已停止",
                source == "safety_override" and safety_gate_first and not plan_ids.intersection({"task_plan", "emotion", "response", "review", "coordinate"}),
                "首个持久化事件为确定性安全门，且普通规划与生成步骤未进入计划",
            ),
            check(
                "safety_output_linked",
                "安全回应交付已落库",
                output_message_id is not None,
                "仅记录安全回应消息引用，不在交付物复制聊天原文",
            ),
            check(
                "human_handoff_present",
                "真人接力路径完整",
                "trusted-adult" in resource_ids,
                "可信成年人或教师是首要接力人",
            ),
            check(
                "support_line_present",
                "心理支持入口可用",
                "12356" in resource_ids,
                "已匹配全国统一12356心理援助热线",
            ),
            check(
                "emergency_route_present",
                "紧急求助路径完整",
                {"110", "120"}.issubset(resource_ids),
                "危险迫近时提供110与120路径",
            ),
            check(
                "responsibility_assigned",
                "下一责任人明确",
                artifact.get("next_owner") == "trusted_adult_or_emergency_support",
                "交付物将下一步交给真人安全支持方",
            ),
        ]
    else:
        checks = [
            check(
                "task_contract_complete",
                "任务契约完整",
                all(task_contract.get(key) for key in ("objective", "constraints", "acceptance_criteria")),
                "目标、约束与验收标准均已结构化",
            ),
            check(
                "safety_gate_completed",
                "安全分流已先行",
                safety_gate_first and bool(plan) and plan[0].get("id") == "safety",
                f"首个持久化事件和首个计划步骤均为确定性安全门，分流为{risk_level}",
            ),
            check(
                "output_linked",
                "回应交付已落库",
                output_message_id is not None,
                "仅记录输出消息引用，不在交付物复制聊天原文",
            ),
            check(
                "structured_cues_only",
                "最小必要数据边界",
                any(
                    step.get("scope", {}).get("cue_policy") in {
                        "student_voluntary_structured_only",
                        "student_voluntary_transcript_and_structured",
                    }
                    for step in plan
                ),
                "验收器只使用学生主动表达的派生主题、功能影响和风险分流；对话原文仅用于生成回应",
            ),
            check(
                "responsibility_assigned",
                "下一责任人明确",
                bool(artifact.get("next_owner")),
                "交付物已声明下一步责任归属",
            ),
        ]
    return {
        "status": "verified" if all(item["status"] == "passed" for item in checks) else "needs_attention",
        "checks": checks,
    }


def _plan(
    risk_level: str,
    external_ai_enabled: bool,
    derived_features: dict | None = None,
    companion_engine: bool = False,
) -> tuple[list[dict], list[str]]:
    plan = [
        {"id": "safety", "agent": "StudentSafetyGate", "tool": "deterministic_safety_rules"},
    ]
    tools = ["deterministic_safety_rules"]
    if risk_level == "urgent":
        plan.extend([
            {"id": "handoff", "agent": "SafetyCoordinator", "tool": "urgent_support_router"},
            {"id": "verify", "agent": "OutcomeVerifier", "tool": "student_delivery_verifier"},
        ])
        tools.extend(["urgent_support_router", "student_delivery_verifier"])
        return plan, tools
    plan.append({"id": "observation", "agent": "ConversationObserver", "tool": "derived_feature_extractor"})
    tools.append("derived_feature_extractor")
    task_contract, scope = _bounded_support_contract(
        risk_level, external_ai_enabled, derived_features, companion_engine,
    )
    plan.append({
        "id": "task_plan",
        "agent": "StudentTaskPlanner",
        "tool": "bounded_support_planner",
        "scope": scope,
        "task_contract": task_contract,
    })
    tools.append("bounded_support_planner")
    plan.append({"id": "emotion", "agent": "EmotionSynthesizer", "tool": "emotion_feature_synthesizer"})
    tools.append("emotion_feature_synthesizer")
    if risk_level in {"watch", "professional"}:
        plan.append({"id": "resource", "agent": "ResourceNavigator", "tool": "local_support_resource_registry"})
        tools.append("local_support_resource_registry")
    generator = (
        "deepseek_companion_generator" if companion_engine
        else "xunfei_response_strategy_selector" if external_ai_enabled
        else "deterministic_response_template"
    )
    plan.extend([
        {"id": "response", "agent": "ResponseAgent", "tool": generator},
        {"id": "review", "agent": "StudentResponseReviewer", "tool": "generated_content_validator"},
        {"id": "verify", "agent": "OutcomeVerifier", "tool": "student_delivery_verifier"},
        {"id": "coordinate", "agent": "StudentCoordinator", "tool": "student_delivery_formatter"},
    ])
    tools.extend([generator, "generated_content_validator", "student_delivery_verifier", "student_delivery_formatter"])
    return plan, tools


def start_chat_support_run(
    db: Session,
    *,
    user_id: int,
    session: StudentChatSession,
    message_id: int,
    risk_level: str,
    derived_features: dict,
    external_ai_enabled: bool,
    companion_engine: bool = False,
    idempotency_key: str | None = None,
    context_message_count: int = 0,
    request_fingerprint: str = "",
) -> StudentSupportRun:
    key = idempotency_key or f"chat-message:{message_id}"
    existing = db.query(StudentSupportRun).filter_by(idempotency_key=key).first()
    if existing:
        return existing
    plan, tools = _plan(risk_level, external_ai_enabled, derived_features, companion_engine)
    run = StudentSupportRun(
        run_code=f"SSR-{datetime.now():%Y%m%d}-{secrets.token_hex(5).upper()}",
        user_id=user_id,
        session_id=session.id,
        task_type="chat_turn",
        trigger_source="student_chat",
        idempotency_key=key,
        request_fingerprint=request_fingerprint,
        input_message_id=message_id,
        status="running",
        risk_level=risk_level,
        intent_summary=(
            f"支持主题：{derived_features.get('support_theme', '未确定')}；"
            f"情绪线索：{derived_features.get('emotion_label', '不确定')}；"
            f"影响领域：{'、'.join(derived_features.get('functional_impact') or []) or '未说明'}"
        ),
        context_message_count=context_message_count,
        plan_json=json.dumps(plan, ensure_ascii=False),
        tools_json=json.dumps(tools, ensure_ascii=False),
        deliverable_json="{}",
        prompt_version=PROMPT_VERSION,
        started_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    try:
        db.add(run)
        db.flush()
        initial_events = [StudentSupportEvent(
            run_id=run.id, sequence=1, agent_type="StudentSafetyGate",
            tool_name="deterministic_safety_rules",
            status="attention" if risk_level in {"professional", "urgent"} else "completed",
            summary=f"已优先完成确定性安全分流：{risk_level}", source="safety_rule",
            evidence_json=json.dumps(["session_recent_turns"], ensure_ascii=False),
        )]
        if risk_level != "urgent":
            initial_events.append(StudentSupportEvent(
                run_id=run.id, sequence=2, agent_type="ConversationObserver",
                tool_name="derived_feature_extractor", status="completed",
                summary="仅从学生主动表达提取结构化线索；未从行为、活跃度或沉默推断情绪",
                source="deterministic", evidence_json=json.dumps(["derived_features"], ensure_ascii=False),
            ))
        db.add_all(initial_events)
        db.commit()
    except IntegrityError:
        db.rollback()
        winner = db.query(StudentSupportRun).filter_by(idempotency_key=key).first()
        if winner:
            return winner
        raise
    db.refresh(run)
    return run


def complete_chat_support_run(
    db: Session,
    *,
    run: StudentSupportRun,
    risk_level: str,
    source: str,
    emotion: str,
    intensity: str,
    conversation_signal: str,
    degraded: bool = False,
    output_message_id: int | None = None,
    emotion_basis: list[str] | None = None,
) -> StudentSupportRun:
    if run.status in {"completed", "attention"}:
        return run
    claimed = db.query(StudentSupportRun).filter(
        StudentSupportRun.id == run.id, StudentSupportRun.status == "running",
    ).update({StudentSupportRun.status: "finalizing"}, synchronize_session=False)
    if claimed != 1:
        db.rollback()
        db.refresh(run)
        if run.status in {"completed", "attention"}:
            return run
        raise RuntimeError("student support run is no longer available for completion")
    plan = json.loads(run.plan_json)
    existing_events = db.query(StudentSupportEvent).filter_by(run_id=run.id).order_by(StudentSupportEvent.sequence).all()
    existing = {event.sequence for event in existing_events}
    safety_gate_first = bool(
        existing_events
        and existing_events[0].sequence == 1
        and existing_events[0].agent_type == "StudentSafetyGate"
        and existing_events[0].tool_name == "deterministic_safety_rules"
        and existing_events[0].status in {"completed", "attention"}
    )
    sequence = 2 if risk_level == "urgent" else 3
    resources = route_support_resources(risk_level)
    planner = next((step for step in plan if step.get("id") == "task_plan"), None)
    task_contract = _urgent_safety_contract() if risk_level == "urgent" else dict(
        (planner or {}).get("task_contract") or _bounded_support_contract(risk_level, False, {})[0]
    )
    artifact = _delivery_artifact(plan, risk_level)
    verification = _verify_delivery(
        plan=plan,
        risk_level=risk_level,
        source=source,
        output_message_id=output_message_id,
        task_contract=task_contract,
        artifact=artifact,
        resources=resources,
        safety_gate_first=safety_gate_first,
    )
    if risk_level == "urgent":
        if sequence not in existing:
            db.add(StudentSupportEvent(
                run_id=run.id, sequence=sequence, agent_type="SafetyCoordinator",
                tool_name="urgent_support_router", status="attention",
                summary="普通生成已停止，已交付真人安全支持路径", source="safety_rule",
                evidence_json=json.dumps([item["id"] for item in resources], ensure_ascii=False),
            ))
        sequence += 1
        if sequence not in existing:
            db.add(StudentSupportEvent(
                run_id=run.id, sequence=sequence, agent_type="OutcomeVerifier",
                tool_name="student_delivery_verifier",
                status="completed" if verification["status"] == "verified" else "attention",
                summary=(
                    "已验收普通生成停用、真人接力与紧急求助路径，安全交付可接管"
                    if verification["status"] == "verified"
                    else "安全交付存在未通过验收项，需要立即人工补充"
                ),
                source="safety_rule",
                evidence_json=json.dumps(
                    [item["id"] for item in verification["checks"] if item["status"] == "passed"],
                    ensure_ascii=False,
                ),
            ))
        run.status = "attention"
        run.model_name = "safety-override"
    else:
        summaries = {
            "task_plan": (
                "StudentTaskPlanner",
                "bounded_support_planner",
                "已依据学生主动表达的结构化线索形成受限支持计划；未从行为推断情绪",
            ),
            "emotion": ("EmotionSynthesizer", "emotion_feature_synthesizer", f"已整理情绪线索：{emotion or '不确定'} · {intensity}"),
            "resource": ("ResourceNavigator", "local_support_resource_registry", f"已从本地审计注册表匹配 {len(resources)} 个支持入口"),
            "response": (
                "ResponseAgent",
                "deepseek_companion_generator" if source == "deepseek_companion"
                else "xunfei_response_strategy_selector" if source == "xunfei_constrained"
                else "deterministic_response_template",
                "小满对话引擎已生成朋友式回应，安全边界由后端校验"
                if source == "deepseek_companion"
                else "模型已选择受限回应策略，后端完成安全话术实现"
                if source == "xunfei_constrained"
                else "本地规则已生成非诊断性安全回应",
            ),
            "review": (
                "StudentResponseReviewer",
                "generated_content_validator",
                "对话回应已完成诊断措辞、危险建议与重复内容校验"
                if source == "deepseek_companion"
                else "枚举策略与后端话术已完成结构、安全及重复内容复核"
                if source == "xunfei_constrained"
                else "规则回应已完成诊断措辞与危险建议校验",
            ),
            "verify": (
                "OutcomeVerifier",
                "student_delivery_verifier",
                f"已按任务契约完成交付验收：{sum(item['status'] == 'passed' for item in verification['checks'])}/{len(verification['checks'])} 项通过",
            ),
            "coordinate": (
                "StudentCoordinator",
                "student_delivery_formatter",
                "验收通过后已交付回应、结构化结果与下一责任人" if verification["status"] == "verified" else "验收未通过，本轮未宣称完成并转人工关注",
            ),
        }
        for step in plan[2:]:
            agent, tool, summary = summaries[step["id"]]
            evidence = [f"risk:{risk_level}", f"source:{source}"]
            if step["id"] == "task_plan":
                scope = step.get("scope", {})
                evidence = [
                    f"risk:{risk_level}",
                    f"support_theme:{scope.get('support_theme', '最近发生的事情')}",
                    f"functional_impact:{'|'.join(scope.get('functional_impact') or []) or 'not_declared'}",
                    f"execution_mode:{scope.get('execution_mode', 'local_deterministic')}",
                    f"cue_policy:{scope.get('cue_policy', 'student_voluntary_structured_only')}",
                ]
            elif step["id"] == "resource":
                evidence = [item["id"] for item in resources]
            elif step["id"] == "review":
                evidence = ["strict_schema", "diagnostic_language_filter", "dangerous_advice_filter"]
            elif step["id"] == "verify":
                evidence = [item["id"] for item in verification["checks"] if item["status"] == "passed"]
            elif step["id"] == "coordinate":
                evidence = [f"verification:{verification['status']}", f"next_owner:{artifact['next_owner']}"]
            db.add(StudentSupportEvent(
                run_id=run.id, sequence=sequence, agent_type=agent, tool_name=tool,
                status=(
                    "attention"
                    if step["id"] in {"verify", "coordinate"} and verification["status"] != "verified"
                    else "completed"
                ),
                summary=summary,
                source="model" if step["id"] == "response" and source in {"xunfei_constrained", "deepseek_companion"} else "deterministic",
                evidence_json=json.dumps(evidence, ensure_ascii=False),
            ))
            sequence += 1
        run.status = "completed" if verification["status"] == "verified" else "attention"
        run.model_name = (
            "deepseek-companion" if source == "deepseek_companion"
            else "xunfei-response-strategy-selector" if source == "xunfei_constrained"
            else "deterministic-student-support"
        )
    run.risk_level = risk_level
    run.output_message_id = output_message_id
    run.emotion_basis_json = json.dumps(emotion_basis or [], ensure_ascii=False)
    run.degraded = int(degraded)
    run.deliverable_json = json.dumps({
        "emotion": emotion or "不确定",
        "intensity": intensity,
        "conversation_signal": conversation_signal,
        "risk_level": risk_level,
        "generation_source": source,
        "resources": resources,
        "boundary": "非诊断性学生支持，不是医学或量表结论",
        "task_contract": task_contract,
        "verification": verification,
        "artifact": artifact,
    }, ensure_ascii=False)
    run.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(run)
    return run


def fail_chat_support_run(db: Session, run: StudentSupportRun) -> None:
    updated = db.query(StudentSupportRun).filter(
        StudentSupportRun.id == run.id,
        StudentSupportRun.status.in_(["running", "finalizing"]),
    ).update({
        StudentSupportRun.status: "failed",
        StudentSupportRun.degraded: 1,
        StudentSupportRun.model_name: "unavailable",
        StudentSupportRun.completed_at: datetime.utcnow(),
    }, synchronize_session=False)
    if updated != 1:
        db.rollback()
        return
    next_sequence = db.query(StudentSupportEvent).filter_by(run_id=run.id).count() + 1
    db.add(StudentSupportEvent(
        run_id=run.id, sequence=next_sequence, agent_type="StudentCoordinator",
        tool_name="safe_retry_state", status="failed",
        summary="本轮未完成，聊天记录已保留并可安全重试", source="system",
        evidence_json="[]",
    ))
    db.commit()
    db.refresh(run)


def recover_stale_support_run(db: Session, run_id: int, cutoff: datetime) -> bool:
    """CAS recovery: never overwrite a run that completed after it was read."""
    updated = db.query(StudentSupportRun).filter(
        StudentSupportRun.id == run_id,
        StudentSupportRun.status == "running",
        StudentSupportRun.started_at <= cutoff,
    ).update({
        StudentSupportRun.status: "failed",
        StudentSupportRun.degraded: 1,
        StudentSupportRun.model_name: "unavailable",
        StudentSupportRun.completed_at: datetime.utcnow(),
    }, synchronize_session=False)
    if updated != 1:
        db.rollback()
        return False
    next_sequence = db.query(StudentSupportEvent).filter_by(run_id=run_id).count() + 1
    db.add(StudentSupportEvent(
        run_id=run_id, sequence=next_sequence, agent_type="StudentCoordinator",
        tool_name="stale_run_recovery", status="failed",
        summary="任务租约已过期，未宣称完成；聊天记录仍可继续使用", source="system", evidence_json="[]",
    ))
    db.commit()
    return True
