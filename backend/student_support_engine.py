from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError

from sqlalchemy.orm import Session

from models import StudentChatSession, StudentSupportEvent, StudentSupportRun
from student_support_resources import route_support_resources


PROMPT_VERSION = "student-support-orchestrator-v1"


def _plan(risk_level: str, external_ai_enabled: bool) -> tuple[list[dict], list[str]]:
    plan = [
        {"id": "observation", "agent": "ConversationObserver", "tool": "derived_feature_extractor"},
        {"id": "safety", "agent": "StudentSafetyGate", "tool": "deterministic_safety_rules"},
    ]
    tools = ["derived_feature_extractor", "deterministic_safety_rules"]
    if risk_level == "urgent":
        plan.append({"id": "handoff", "agent": "SafetyCoordinator", "tool": "urgent_support_router"})
        tools.append("urgent_support_router")
        return plan, tools
    plan.append({"id": "emotion", "agent": "EmotionSynthesizer", "tool": "emotion_feature_synthesizer"})
    tools.append("emotion_feature_synthesizer")
    if risk_level in {"watch", "professional"}:
        plan.append({"id": "resource", "agent": "ResourceNavigator", "tool": "local_support_resource_registry"})
        tools.append("local_support_resource_registry")
    generator = "xunfei_response_strategy_selector" if external_ai_enabled else "deterministic_response_template"
    plan.extend([
        {"id": "response", "agent": "ResponseAgent", "tool": generator},
        {"id": "review", "agent": "StudentResponseReviewer", "tool": "generated_content_validator"},
        {"id": "coordinate", "agent": "StudentCoordinator", "tool": "student_delivery_formatter"},
    ])
    tools.extend([generator, "generated_content_validator", "student_delivery_formatter"])
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
    idempotency_key: str | None = None,
    context_message_count: int = 0,
    request_fingerprint: str = "",
) -> StudentSupportRun:
    key = idempotency_key or f"chat-message:{message_id}"
    existing = db.query(StudentSupportRun).filter_by(idempotency_key=key).first()
    if existing:
        return existing
    plan, tools = _plan(risk_level, external_ai_enabled)
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
        db.add_all([
            StudentSupportEvent(
                run_id=run.id, sequence=1, agent_type="ConversationObserver",
                tool_name="derived_feature_extractor", status="completed",
                summary="已提取低识别风险的支持主题、情绪和功能影响特征",
                source="deterministic", evidence_json=json.dumps(["derived_features"], ensure_ascii=False),
            ),
            StudentSupportEvent(
                run_id=run.id, sequence=2, agent_type="StudentSafetyGate",
                tool_name="deterministic_safety_rules",
                status="attention" if risk_level in {"professional", "urgent"} else "completed",
                summary=f"已完成安全分流：{risk_level}", source="safety_rule",
                evidence_json=json.dumps(["session_recent_turns"], ensure_ascii=False),
            ),
        ])
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
    existing = {event.sequence for event in db.query(StudentSupportEvent).filter_by(run_id=run.id).all()}
    sequence = 3
    resources = route_support_resources(risk_level)
    if risk_level == "urgent":
        if sequence not in existing:
            db.add(StudentSupportEvent(
                run_id=run.id, sequence=sequence, agent_type="SafetyCoordinator",
                tool_name="urgent_support_router", status="attention",
                summary="普通生成已停止，已交付真人安全支持路径", source="safety_rule",
                evidence_json=json.dumps([item["id"] for item in resources], ensure_ascii=False),
            ))
        run.status = "attention"
        run.model_name = "safety-override"
    else:
        summaries = {
            "emotion": ("EmotionSynthesizer", "emotion_feature_synthesizer", f"已整理情绪线索：{emotion or '不确定'} · {intensity}"),
            "resource": ("ResourceNavigator", "local_support_resource_registry", f"已从本地审计注册表匹配 {len(resources)} 个支持入口"),
            "response": ("ResponseAgent", "xunfei_response_strategy_selector" if source == "xunfei_constrained" else "deterministic_response_template", "模型已选择回应策略，后端完成安全话术实现"),
            "review": ("StudentResponseReviewer", "generated_content_validator", "枚举策略与后端话术已完成结构、安全及重复内容复核" if source == "xunfei_constrained" else "规则回应已完成诊断措辞与危险建议校验"),
            "coordinate": ("StudentCoordinator", "student_delivery_formatter", "已交付回应、情绪线索与下一步状态"),
        }
        for step in plan[2:]:
            agent, tool, summary = summaries[step["id"]]
            evidence = [f"risk:{risk_level}", f"source:{source}"]
            if step["id"] == "resource":
                evidence = [item["id"] for item in resources]
            elif step["id"] == "review":
                evidence = ["strict_schema", "diagnostic_language_filter", "dangerous_advice_filter"]
            db.add(StudentSupportEvent(
                run_id=run.id, sequence=sequence, agent_type=agent, tool_name=tool,
                status="completed", summary=summary,
                source="model" if step["id"] == "response" and source == "xunfei_constrained" else "deterministic",
                evidence_json=json.dumps(evidence, ensure_ascii=False),
            ))
            sequence += 1
        run.status = "completed"
        run.model_name = "xunfei-response-strategy-selector" if source == "xunfei_constrained" else "deterministic-student-support"
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
