"""守护者多 Agent 编排器。

风险等级由确定性规则决定。大模型只允许润色一条支持性说明，且输出必须经过
禁用词校验；任何失败都会显式降级为已审核模板。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
import secrets
from typing import Any

from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from guardian_schemas import (
    AssessmentOutput,
    InterventionOutput,
    KnowledgeOutput,
    ResourceItem,
    ResourceOutput,
    ReviewOutput,
    SupportPlanOutput,
)
from models import (
    AgentRun,
    EvidenceSource,
    FollowUpTask,
    GuardianCase,
    SafetyEvent,
    SupportPlan,
)
from xunfei.spark_api import ask_spark, is_spark_available

DATA_DIR = Path(__file__).resolve().parent / "data"
AGENT_TYPES = [
    "SafetyGate",
    "Assessor",
    "KnowledgeAgent",
    "ResourceAgent",
    "InterventionAgent",
    "CrossReviewer",
    "Coordinator",
]

SIGNAL_LABELS = {
    "mood_low": "持续情绪低落",
    "irritability": "易怒或情绪波动",
    "school_refusal": "抗拒或回避上学",
    "social_withdrawal": "社交退缩",
    "sleep_change": "睡眠明显变化",
    "performance_drop": "学习表现明显下降",
    "family_conflict": "家庭冲突增加",
    "self_harm_sign": "出现自伤痕迹",
    "death_talk": "谈到死亡或不想活",
}

DURATION_LABELS = {
    "under_1_week": "不足1周",
    "1_2_weeks": "1至2周",
    "2_4_weeks": "2至4周",
    "1_3_months": "1至3个月",
    "over_3_months": "3个月以上",
}

IMPACT_LABELS = {
    "none": "尚未明显影响日常功能",
    "partial": "已部分影响上学、社交或家庭生活",
    "significant": "已明显影响上学、社交或家庭生活",
}

RISK_LABELS = {
    "routine": ("日常支持", "保持观察并提供稳定支持"),
    "watch": ("需要关注", "从今天开始执行支持计划，并在3天后复盘"),
    "professional": ("尽快获得专业支持", "建议尽快联系学校心理老师或正规医疗机构评估"),
    "urgent": ("立即协助", "先确保当下安全，并立即联系专业或紧急服务"),
}

FORBIDDEN_CLINICAL_PATTERNS = {
    "diagnostic_label": r"(?:患有|得了|属于|诊断为|确诊为|可能(?:是|患有)|疑似).{0,5}(?:抑郁|焦虑|双相|强迫|精神分裂|人格障碍)",
    "treatment_instruction": r"(?:需要|建议|应该|必须).{0,8}(?:服药|用药|药物治疗|心理治疗|住院治疗)",
    "medication_or_prescription": r"(?:处方|抗抑郁药|抗焦虑药|自行加药|自行停药)",
    "efficacy_promise": r"(?:保证|一定|肯定).{0,6}(?:治好|治愈|康复|有效)",
    "fabricated_scale_score": r"(?:PHQ[-‑]?9|GAD[-‑]?7).{0,8}(?:得分|评分|分数|\d+分)",
}
EXPLICIT_URGENT = {"self_harm_sign", "death_talk"}
URGENT_PATTERNS = [
    r"不想活(?:了)?",
    r"想死(?:了)?",
    r"想结束(?:自己|这条)?生命",
    r"(?:想|准备|打算).{0,8}轻生",
    r"活着(?:没|没有)意思",
    r"想(?:要)?自杀",
    r"(?:准备|打算|想).{0,12}(?:跳楼|跳下去|割腕|吞药|烧炭|上吊)",
    r"(?:藏|囤|攒).{0,8}药.{0,12}(?:一起|一次|全部).{0,4}(?:吃|吞)",
    r"药.{0,6}(?:藏|囤|攒).{0,12}(?:一起|一次|全部).{0,4}(?:吃|吞)",
    r"(?:提到|说过|表示|谈到).{0,4}轻生",
    r"已经.{0,8}(?:割腕|自伤|吞药|服药|烧炭)",
    r"写(?:好|了).{0,4}遗书",
    r"永远睡过去",
    r"没有我.{0,6}更好",
    r"撑不下去",
]
NEGATION_PREFIX = re.compile(r"(?:没有|否认|从未|并未|不是|没想过).{0,4}$")
QUOTE_PREFIX = re.compile(r"(?:新闻|电影|课文|别人|同学说|讨论).{0,6}$")


def load_json(name: str) -> list[dict[str, Any]]:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def seed_evidence_sources(db: Session) -> None:
    for item in load_json("guardian_evidence.json"):
        row = db.query(EvidenceSource).filter(EvidenceSource.source_code == item["source_code"]).first()
        values = {
            "title": item["title"],
            "issuer": item["issuer"],
            "source_url": item["source_url"],
            "evidence_level": item["evidence_level"],
            "tags_json": json.dumps(item["tags"], ensure_ascii=False),
            "summary": item["summary"],
            "reviewed_at": item["reviewed_at"],
            "review_status": "source_verified",
        }
        if row:
            for key, value in values.items():
                setattr(row, key, value)
        else:
            db.add(EvidenceSource(source_code=item["source_code"], **values))
    db.commit()


def create_case_code() -> str:
    return f"GM-{datetime.now():%Y%m%d}-{secrets.token_hex(2).upper()}"


def create_run_code(case_code: str) -> str:
    return f"RUN-{case_code}-{secrets.token_hex(2).upper()}"


def _json(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    return json.dumps(value, ensure_ascii=False)


def _signals(case: GuardianCase) -> list[str]:
    return json.loads(case.signals_json or "[]")


def _context_has_urgent_meaning(context: str) -> bool:
    text = re.sub(r"\s+", "", context)
    for pattern in URGENT_PATTERNS:
        match = re.search(pattern, text)
        if not match:
            continue
        prefix = text[max(0, match.start() - 12) : match.start()]
        if NEGATION_PREFIX.search(prefix) or QUOTE_PREFIX.search(prefix):
            continue
        return True
    return False


def generated_content_violations(text: str) -> list[str]:
    """Return policy categories found in generated text before it is persisted."""
    compact = re.sub(r"\s+", "", text)
    return [name for name, pattern in FORBIDDEN_CLINICAL_PATTERNS.items() if re.search(pattern, compact, re.I)]


def classify_risk(case: GuardianCase) -> tuple[str, str]:
    signals = set(_signals(case))
    if case.guardian_may_be_source:
        return "urgent", "family_harm_or_unsafe_guardian"
    if signals & EXPLICIT_URGENT:
        return "urgent", "explicit_urgent_signal"
    if _context_has_urgent_meaning(case.context):
        return "urgent", "semantic_urgent_signal"

    long_duration = case.duration in {"2_4_weeks", "1_3_months", "over_3_months"}
    severe_function = case.functional_impact == "significant"
    if (long_duration and case.functional_impact in {"partial", "significant"}) or severe_function:
        return "professional", "duration_and_function"
    if len(signals) >= 3 or "school_refusal" in signals:
        return "professional", "multiple_observed_changes"
    if signals:
        return "watch", "observed_change"
    return "routine", "no_material_change"


def ensure_agent_runs(db: Session, case: GuardianCase) -> list[AgentRun]:
    existing = {row.agent_type: row for row in db.query(AgentRun).filter(AgentRun.case_id == case.id).all()}
    for index, agent_type in enumerate(AGENT_TYPES):
        if agent_type not in existing:
            row = AgentRun(
                run_code=f"{create_run_code(case.case_code)}-{index + 1}",
                case_id=case.id,
                agent_type=agent_type,
                status="queued",
            )
            db.add(row)
            existing[agent_type] = row
    db.commit()
    return [existing[name] for name in AGENT_TYPES]


async def _pause() -> None:
    if settings.AGENT_STEP_DELAY_MS > 0:
        await asyncio.sleep(settings.AGENT_STEP_DELAY_MS / 1000)


def _start_run(db: Session, case_id: int, agent_type: str) -> AgentRun:
    run = db.query(AgentRun).filter(AgentRun.case_id == case_id, AgentRun.agent_type == agent_type).first()
    run.status = "running"
    run.started_at = datetime.now()
    db.commit()
    return run


def _complete_run(
    db: Session,
    run: AgentRun,
    output: Any,
    summary: str,
    evidence_codes: list[str] | None = None,
    model_name: str = "deterministic-policy-v1",
    degraded: bool = False,
) -> None:
    run.status = "completed"
    run.summary = summary
    run.output_json = _json(output)
    run.evidence_json = _json(evidence_codes or [])
    run.model_name = model_name
    run.degraded = int(degraded)
    run.completed_at = datetime.now()
    db.commit()


def _skip_for_safety(db: Session, case_id: int, agent_types: list[str]) -> None:
    db.query(AgentRun).filter(
        AgentRun.case_id == case_id,
        AgentRun.agent_type.in_(agent_types),
    ).update(
        {
            AgentRun.status: "skipped_for_safety",
            AgentRun.summary: "安全规则已终止常规方案生成",
            AgentRun.completed_at: datetime.now(),
        },
        synchronize_session=False,
    )
    db.commit()


def build_assessment(case: GuardianCase) -> AssessmentOutput:
    labels = [SIGNAL_LABELS[item] for item in _signals(case)]
    risk_label, priority = RISK_LABELS[case.risk_level]
    return AssessmentOutput(
        risk_level=case.risk_level,
        observed_pattern=f"守护者观察到：{'、'.join(labels)}；持续{DURATION_LABELS[case.duration]}。",
        functional_summary=IMPACT_LABELS[case.functional_impact],
        uncertainty="信息来自成人守护者的单次结构化观察，未直接访谈青少年，也未使用标准化量表。",
        next_step=f"{risk_label}：{priority}。",
    )


def build_knowledge(db: Session, case: GuardianCase) -> KnowledgeOutput:
    seed_evidence_sources(db)
    preferred = ["CN-MHL-001", "CN-NHC-004", "WHO-AMH-005", "WHO-AI-006"]
    rows = db.query(EvidenceSource).filter(EvidenceSource.source_code.in_(preferred)).all()
    by_code = {row.source_code: row for row in rows}
    ordered = [by_code[code] for code in preferred if code in by_code]
    return KnowledgeOutput(
        evidence_codes=[row.source_code for row in ordered],
        evidence_summary=[row.summary for row in ordered],
        evidence_limit="这些资料支持产品边界、早期求助与服务导航，不足以对单一个案作临床诊断或疗效预测。",
    )


def build_resources(case: GuardianCase) -> ResourceOutput:
    items = [ResourceItem.model_validate(item) for item in load_json("guardian_resources.json")]
    if case.risk_level == "urgent":
        order = ["HOTLINE-12356", "EMERGENCY-110", "EMERGENCY-120", "DG-HOTLINE-88881111", "DG-HOSPITAL-7"]
    elif case.risk_level == "professional":
        order = ["HOTLINE-12356", "DG-HOTLINE-88881111", "DG-HOSPITAL-7"]
    else:
        order = ["DG-HOTLINE-88881111", "HOTLINE-12356", "DG-HOSPITAL-7"]
    by_code = {item.resource_code: item for item in items}
    selected = [by_code[code] for code in order if code in by_code]
    return ResourceOutput(
        resources=selected,
        selection_note=f"基于东莞示范白名单与{case.district}区级位置筛选；未使用地图POI推断机构资质。",
    )


def _base_intervention(case: GuardianCase) -> InterventionOutput:
    is_parent = case.reporter_role == "parent"
    if is_parent:
        immediate = [
            "选择不赶时间、没有旁人的场景，用观察事实而不是评价开启沟通。",
            "先确认孩子此刻更需要被倾听、一起解决问题，还是暂时安静陪伴。",
        ]
        seven = [
            "连续7天只记录睡眠、到校、社交和情绪变化，不给孩子贴标签。",
            "每天安排一次与成绩无关、可由孩子拒绝的短暂共同活动。",
            "第3天复盘变化；若功能继续下降，提前联系学校心理老师或正规医疗机构。",
        ]
        prompts = [
            "我注意到你最近好像比平时更累。我不是来追问原因的，想先知道现在怎样陪你会舒服一点。",
            "你可以现在说、晚点说，或者先不说；如果需要找其他可信的大人，我也可以陪你一起。",
        ]
        avoid = ["不要说“你就是想太多了”或拿孩子与他人比较。", "不要承诺对任何危险信息都绝对保密。"]
    else:
        immediate = [
            "在私下、低压力场景中核对近期到校、课堂参与和同伴互动变化。",
            "使用“我注意到……”描述事实，并说明学生可以选择何时、向谁表达。",
        ]
        seven = [
            "记录一周内可观察的到校、课堂、课间和作业变化，避免公开点名。",
            "与学校心理老师核对支持路径，仅共享完成支持所必需的信息。",
            "与家长沟通时先描述事实和保护目标，不使用“不正常”等标签。",
        ]
        prompts = [
            "我注意到你最近几次课间都一个人待着，想确认你是否需要一点支持。你可以选择现在说或换个时间。",
            "我不会根据一次谈话给你下结论；如果你愿意，我们可以一起找学校里更合适的支持。",
        ]
        avoid = ["不要在全班面前询问或暗示心理状态。", "不要把AI生成内容当作纪律处分或医学判断依据。"]

    if case.risk_level == "professional":
        immediate.append("在继续日常支持的同时，尽快联系具备资质的专业人员进行面对面评估。")
    return InterventionOutput(
        immediate_actions=immediate,
        seven_day_actions=seven,
        conversation_prompts=prompts,
        avoid_actions=avoid,
        tailored_note="方案基于守护者观察和已审核模板生成，应结合青少年本人意愿与专业意见调整。",
        generated_by="reviewed_template",
    )


async def build_intervention(case: GuardianCase) -> tuple[InterventionOutput, bool, str]:
    base = _base_intervention(case)
    if not settings.ALLOW_GUARDIAN_SYNTHETIC_AI or not is_spark_available():
        return base, True, "reviewed-template-v1"

    prompt = (
        "你是青少年心理健康教育支持工具的文案助手。根据以下去标识化观察，"
        "只写一句不超过70字的支持说明。禁止诊断、治疗、药物和疗效承诺，不新增事实。\n"
        f"角色：{case.reporter_role}；年龄：{case.age_band}；风险动作级别：{case.risk_level}；"
        f"表现：{','.join(_signals(case))}；功能影响：{case.functional_impact}。"
    )
    try:
        note = (await ask_spark([{"role": "user", "content": prompt}], max_tokens=120, temperature=0.2)).strip()
        if not note or len(note) > 100 or generated_content_violations(note):
            return base, True, "reviewed-template-v1"
        output = base.model_copy(update={"tailored_note": note, "generated_by": "xunfei_structured"})
        return output, False, settings.SPARK_MODEL
    except Exception:
        return base, True, "reviewed-template-v1"


def build_review(
    case: GuardianCase,
    intervention: InterventionOutput,
    knowledge: KnowledgeOutput,
    resources: ResourceOutput,
) -> ReviewOutput:
    disagreements: list[str] = []
    if case.duration in {"under_1_week", "1_2_weeks"} and case.functional_impact == "significant":
        disagreements.append("观察时间较短，但功能影响明显；安全规则要求按“尽快获得专业支持”处理。")
    if case.reporter_role == "teacher" and "family_conflict" in _signals(case):
        disagreements.append("教师可提供校内支持，但不应据此推断家庭责任；家庭沟通需保持最小必要披露。")
    forbidden = generated_content_violations(_json(intervention))
    required_evidence = {"CN-MHL-001", "CN-NHC-004"}
    available_evidence = set(knowledge.evidence_codes)
    if not available_evidence or not resources.resources:
        evidence_coverage = "unavailable"
        disagreements.append("权威证据或核验资源当前不可用；已降级为待人工补充的审核模板。")
    elif not required_evidence.issubset(available_evidence):
        evidence_coverage = "partial"
        disagreements.append("必需的一手证据未完整返回；结论只能作为待人工补充的部分审查。")
    else:
        evidence_coverage = "complete"
    return ReviewOutput(
        evidence_coverage=evidence_coverage,
        role_fit=case.reporter_role,
        safety_override_applied=case.risk_level in {"professional", "urgent"},
        disagreements=disagreements,
        resolution="以确定性风险分流和最小伤害原则为最高优先级；生成式内容不得下调风险动作级别。",
        forbidden_terms_found=forbidden,
    )


def build_urgent_plan(case: GuardianCase, resources: ResourceOutput) -> SupportPlanOutput:
    trusted_adult = (
        "如果监护人可能是伤害来源，请优先联系可信教师、其他安全成年人或直接拨打110。"
        if case.guardian_may_be_source
        else "请让一位可信成年人持续陪在孩子身边。"
    )
    return SupportPlanOutput(
        case_code=case.case_code,
        release_version=settings.RELEASE_VERSION,
        risk_level="urgent",
        risk_label=RISK_LABELS["urgent"][0],
        action_priority=RISK_LABELS["urgent"][1],
        observation_summary="输入中出现需要立即核实安全的明确危险信号，系统已停止常规方案生成。",
        immediate_actions=[
            trusted_adult,
            "温和询问孩子此刻是否安全、是否已经采取行动；不要争辩、责备或让其独处。",
            "将药物、刀具、绳索等潜在危险物移出可及范围，并立即拨打12356；存在迫切危险时拨打110或120。",
        ],
        seven_day_actions=[],
        conversation_prompts=["我很在意你现在的安全。我会陪着你，我们现在一起联系能够立即提供帮助的人。"],
        avoid_actions=["不要只让孩子保证“不会出事”后离开。", "不要用普通家庭建议替代紧急援助。"],
        resources=resources.resources,
        evidence_codes=["CN-MHL-001", "CN-AI-003", "CN-NHC-004"],
        disagreements=[],
        review_resolution="危机安全规则直接裁决，未进入常规Agent协商。",
        follow_up_days=[],
        ai_disclosure="本内容由AI辅助系统按固定安全规则生成，你正在与AI而非真人互动。",
        boundary_notice="本系统不提供诊断或治疗。出现即时危险时，请立即联系12356、110或120并寻求线下帮助。",
    )


def build_plan(
    case: GuardianCase,
    assessment: AssessmentOutput,
    knowledge: KnowledgeOutput,
    resources: ResourceOutput,
    intervention: InterventionOutput,
    review: ReviewOutput,
) -> SupportPlanOutput:
    label, priority = RISK_LABELS[case.risk_level]
    return SupportPlanOutput(
        case_code=case.case_code,
        release_version=settings.RELEASE_VERSION,
        risk_level=case.risk_level,
        risk_label=label,
        action_priority=priority,
        observation_summary=assessment.observed_pattern + assessment.functional_summary,
        immediate_actions=intervention.immediate_actions,
        seven_day_actions=intervention.seven_day_actions,
        conversation_prompts=intervention.conversation_prompts,
        avoid_actions=intervention.avoid_actions,
        resources=resources.resources,
        evidence_codes=knowledge.evidence_codes,
        disagreements=review.disagreements,
        review_resolution=review.resolution,
        follow_up_days=[3, 7, 15],
        ai_disclosure="本方案由咕哝AI辅助生成，你正在使用AI工具而非接受真人心理服务。",
        boundary_notice="仅用于心理健康教育、支持建议和求助导航，不能替代专业人员的评估、诊断或治疗。",
    )


def _save_plan(db: Session, case: GuardianCase, plan: SupportPlanOutput) -> None:
    existing = db.query(SupportPlan).filter(SupportPlan.case_id == case.id).first()
    if existing:
        existing.version = settings.RELEASE_VERSION
        existing.plan_json = _json(plan)
        existing.review_status = "needs_professional_review"
    else:
        db.add(
            SupportPlan(
                case_id=case.id,
                version=settings.RELEASE_VERSION,
                plan_json=_json(plan),
                review_status="needs_professional_review",
            )
        )
    db.commit()


def rebuild_plan_from_reviewed_templates(db: Session, case: GuardianCase) -> SupportPlanOutput:
    """Keep case risk and plan consistent without sending follow-up text to a model."""
    assessment = build_assessment(case)
    knowledge = build_knowledge(db, case)
    resources = build_resources(case)
    intervention = _base_intervention(case)
    review = build_review(case, intervention, knowledge, resources)
    plan = build_plan(case, assessment, knowledge, resources, intervention, review)
    _save_plan(db, case, plan)
    return plan


def apply_followup_safety_override(db: Session, case: GuardianCase, trigger_code: str) -> SupportPlanOutput:
    """Apply the deterministic urgent route atomically during a follow-up."""
    case.risk_level = "urgent"
    case.status = "completed"
    db.add(
        SafetyEvent(
            case_id=case.id,
            trigger_code=trigger_code,
            action_code="urgent_support_route",
            redacted_summary="回访出现新的安全信号，已切换紧急支持路径。",
        )
    )
    resources = build_resources(case)
    plan = build_urgent_plan(case, resources)
    _save_plan(db, case, plan)
    return plan


def _schedule_followups(db: Session, case: GuardianCase, days: list[int]) -> None:
    for day in days:
        existing = db.query(FollowUpTask).filter(
            FollowUpTask.case_id == case.id,
            FollowUpTask.day_offset == day,
        ).first()
        if not existing:
            db.add(FollowUpTask(case_id=case.id, day_offset=day, due_at=datetime.now() + timedelta(days=day)))
    db.commit()


async def process_case(case_id: int) -> None:
    db = SessionLocal()
    active_run: AgentRun | None = None
    try:
        case = db.query(GuardianCase).filter(GuardianCase.id == case_id).first()
        if not case or case.status == "completed":
            return
        case.status = "processing"
        db.commit()
        ensure_agent_runs(db, case)

        active_run = _start_run(db, case.id, "SafetyGate")
        risk_level, trigger = classify_risk(case)
        case.risk_level = risk_level
        _complete_run(
            db,
            active_run,
            {"risk_level": risk_level, "trigger_code": trigger, "rule_priority": "absolute"},
            f"完成确定性安全分流：{RISK_LABELS[risk_level][0]}",
        )
        await _pause()

        if risk_level == "urgent":
            db.add(
                SafetyEvent(
                    case_id=case.id,
                    trigger_code=trigger,
                    action_code="urgent_support_route",
                    redacted_summary="检测到明确危险信号；已停止常规方案流程。",
                )
            )
            db.commit()
            _skip_for_safety(db, case.id, ["Assessor", "KnowledgeAgent", "InterventionAgent", "CrossReviewer"])
            resource_run = _start_run(db, case.id, "ResourceAgent")
            resources = build_resources(case)
            _complete_run(db, resource_run, resources, "已加载紧急求助资源", ["CN-NHC-004"])
            coordinator = _start_run(db, case.id, "Coordinator")
            plan = build_urgent_plan(case, resources)
            _save_plan(db, case, plan)
            _complete_run(db, coordinator, plan, "安全规则已生成紧急协助卡", plan.evidence_codes)
            case.status = "completed"
            db.commit()
            return

        active_run = _start_run(db, case.id, "Assessor")
        assessment = build_assessment(case)
        _complete_run(db, active_run, assessment, "完成非标准化守护者观察摘要")
        await _pause()

        active_run = _start_run(db, case.id, "KnowledgeAgent")
        knowledge = build_knowledge(db, case)
        _complete_run(db, active_run, knowledge, f"检索到{len(knowledge.evidence_codes)}条权威证据", knowledge.evidence_codes)

        resource_run = _start_run(db, case.id, "ResourceAgent")
        resources = build_resources(case)
        _complete_run(db, resource_run, resources, f"匹配到{len(resources.resources)}项核验资源", ["CN-NHC-004"])
        await _pause()

        active_run = _start_run(db, case.id, "InterventionAgent")
        intervention, degraded, model_name = await build_intervention(case)
        _complete_run(
            db,
            active_run,
            intervention,
            "已生成家长版行动建议" if case.reporter_role == "parent" else "已生成教师版行动建议",
            knowledge.evidence_codes,
            model_name=model_name,
            degraded=degraded,
        )
        await _pause()

        active_run = _start_run(db, case.id, "CrossReviewer")
        review = build_review(case, intervention, knowledge, resources)
        if review.forbidden_terms_found:
            raise ValueError("clinical_term_guard_failed")
        _complete_run(db, active_run, review, "完成证据、角色与安全交叉审查", knowledge.evidence_codes)
        await _pause()

        active_run = _start_run(db, case.id, "Coordinator")
        plan = build_plan(case, assessment, knowledge, resources, intervention, review)
        _save_plan(db, case, plan)
        _schedule_followups(db, case, plan.follow_up_days)
        _complete_run(db, active_run, plan, "方案书与3/7/15天站内回访已生成", plan.evidence_codes)
        case.status = "completed"
        db.commit()
    except Exception as exc:
        if active_run:
            active_run.status = "failed"
            active_run.error_code = type(exc).__name__
            active_run.summary = "当前步骤未完成，可安全重试"
            active_run.completed_at = datetime.now()
        case = db.query(GuardianCase).filter(GuardianCase.id == case_id).first()
        if case:
            case.status = "failed"
        db.commit()
    finally:
        db.close()
