"""教师最终评审报告：授权范围内的可审计、多 Agent 工作成果。"""

from __future__ import annotations

from datetime import datetime, timedelta
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from guardian_engine import generated_content_violations
from xunfei.spark_api import ask_spark, is_spark_available


RiskLevel = Literal["routine", "watch", "professional", "urgent"]


class NarrativeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    executive_summary: str = Field(min_length=20, max_length=260)
    conversation_opening: str = Field(min_length=8, max_length=120)


EVIDENCE_REGISTRY = [
    {
        "code": "WHO-AMH-2025",
        "title": "Mental health of adolescents",
        "issuer": "World Health Organization",
        "url": "https://www.who.int/news-room/fact-sheets/detail/adolescent-mental-health",
        "use": "保护因素、家庭学校支持环境与避免过度医疗化",
    },
    {
        "code": "WHO-SHS-2021",
        "title": "WHO guideline on school health services",
        "issuer": "World Health Organization",
        "url": "https://www.who.int/publications/i/item/9789240029392",
        "use": "学校支持、服务衔接与转介边界",
    },
    {
        "code": "WHO-HAT-2020",
        "title": "Helping Adolescents Thrive",
        "issuer": "World Health Organization",
        "url": "https://www.who.int/publications/b/55043",
        "use": "青少年心理健康促进与预防性支持",
    },
    {
        "code": "NICE-NG225",
        "title": "Self-harm: assessment, management and preventing recurrence",
        "issuer": "National Institute for Health and Care Excellence",
        "url": "https://www.nice.org.uk/guidance/ng225",
        "use": "安全计划、保密边界、家庭参与与后续支持",
    },
]


def _safe_text(value: Any, limit: int = 240) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _source_counts(records: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in records:
        source = _safe_text(item.get("source") or "其他记录", 30)
        counts[source] = counts.get(source, 0) + 1
    return counts


def _function_observations(work_product: dict) -> list[dict]:
    domains = (work_product.get("assessment_summary") or {}).get("domains") or []
    if not domains:
        return [{"domain": "学习与日常功能", "level": "信息不足", "observation": "当前授权范围内没有足够的结构化自评信息。", "evidence_ids": []}]
    return [
        {
            "domain": _safe_text(item.get("label"), 40),
            "level": _safe_text(item.get("level"), 20),
            "observation": _safe_text(item.get("observation"), 180),
            "evidence_ids": list(item.get("evidence_ids") or [])[:8],
        }
        for item in domains[:6]
    ]


def _protective_factors(work_product: dict) -> list[dict]:
    records = work_product.get("records") or []
    positives = [item for item in records if _safe_text(item.get("emotion"), 20) in {"开心", "平静", "轻松"}]
    factors = []
    if records:
        factors.append({
            "factor": "仍在主动表达或使用支持工具",
            "basis": f"授权范围内存在 {len(records)} 条主动记录。",
            "evidence_ids": [item.get("id") for item in records[:3] if item.get("id")],
        })
    if positives:
        factors.append({
            "factor": "记录中仍出现相对平稳或积极时段",
            "basis": "这些时段可帮助教师了解什么情境可能提供支持，但不能据此排除风险。",
            "evidence_ids": [item.get("id") for item in positives[:3] if item.get("id")],
        })
    return factors


def _risk_factors(work_product: dict) -> list[dict]:
    risk = work_product.get("risk", "routine")
    factors = []
    for domain in _function_observations(work_product):
        if domain["level"] in {"需要留意", "影响明显"}:
            factors.append({
                "factor": f"{domain['domain']}出现值得关注的影响",
                "basis": domain["observation"],
                "evidence_ids": domain["evidence_ids"],
            })
    if risk in {"professional", "urgent"}:
        factors.insert(0, {
            "factor": "当前支持强度已超过常规关怀",
            "basis": "由确定性安全规则和结构化功能影响共同决定，不能由语言模型降低等级。",
            "evidence_ids": list(work_product.get("observation", {}).get("trigger_evidence_ids") or work_product.get("decision_evidence_ids") or [])[:8],
        })
    return factors or [{"factor": "当前未形成稳定风险模式", "basis": "记录数量或信息维度有限，仍需结合线下观察。", "evidence_ids": []}]


def _fallback_summary(work_product: dict) -> str:
    observation = work_product.get("observation") or {}
    counts = _source_counts(work_product.get("records") or [])
    count_text = "、".join(f"{name}{count}条" for name, count in counts.items()) or "暂无可引用记录"
    return (
        f"本报告在已审批的数据范围内整理了{count_text}。"
        f"当前结论为“{_safe_text(observation.get('headline') or '需要继续补充信息', 80)}”。"
        "报告只用于支持教师安排关怀、转介和回访，不构成心理或医学诊断；关键判断仍需教师结合线下观察确认。"
    )


def _safe_model_narrative(candidate: NarrativeOutput) -> bool:
    rendered = json.dumps(candidate.model_dump(), ensure_ascii=False)
    if generated_content_violations(rendered):
        return False
    if re.search(r"(?:确诊|患有|病人|治愈|疗效|量表分|总分|概率|%|百分之|药物|用药)", rendered, re.I):
        return False
    if re.search(r"(?:不要告诉(?:任何人|别人)|必须.{0,8}(?:全部|立刻).{0,8}说|保证.{0,4}(?:绝对)?保密|都是你的错|你太脆弱|别矫情|想开点就好|不许拒绝|瞒着.{0,8}(?:家长|学校|老师))", rendered, re.I):
        return False
    return True


async def build_teacher_review_report(
    *,
    work_product: dict,
    student_label: str,
    teacher_label: str,
    external_ai_allowed: bool,
) -> dict:
    """只向模型发送去标识化结构字段；风险与行动始终由后端规则决定。"""
    risk: RiskLevel = work_product.get("risk", "routine")
    records = list(work_product.get("records") or [])
    source_counts = _source_counts(records)
    assessment = work_product.get("assessment_summary") or {}
    gaps = list(assessment.get("information_gaps") or [])
    if not records:
        gaps.append("授权时间窗内缺少可引用的主动记录")
    if not assessment:
        gaps.append("缺少学生主动完成的结构化支持需求自评")
    gaps.append("尚未结构化记录学生认可的可信支持人及愿意接受、拒绝或暂缓的支持方式")

    summary = _fallback_summary(work_product)
    opening = "我注意到你最近可能承担了不少事情。我想先听听你的感受，哪些部分是我现在可以帮忙的？"
    model_name = "deterministic-teacher-review"
    degraded = False
    external_transfer = False
    external_transfer_attempted = False
    external_transfer_failure = ""
    transferred_fields = []
    if external_ai_allowed and is_spark_available() and risk != "urgent":
        structured_payload = {
            "risk_level": risk,
            "observation_headline": _safe_text((work_product.get("observation") or {}).get("headline"), 100),
            "source_counts": source_counts,
            "function_domains": [{"domain": item["domain"], "level": item["level"]} for item in _function_observations(work_product)],
            "support_needs": list(assessment.get("support_needs") or [])[:5],
            "task_titles": [_safe_text(item.get("title"), 80) for item in work_product.get("tasks") or []],
            "information_gaps": gaps[:6],
        }
        prompt = [
            {"role": "system", "content": (
                "你是学校心理健康支持工单中的受约束报告文字整理器。输入只有去标识化结构字段。"
                "不得诊断、不得输出量表分数或概率、不得补充事实、不得改变风险等级和行动时限。"
                "conversation_opening 必须尊重、非评判、允许学生拒绝回答。只返回严格JSON，且只能包含"
                "executive_summary与conversation_opening两个字符串字段。"
            )},
            {"role": "user", "content": json.dumps(structured_payload, ensure_ascii=False)},
        ]
        external_transfer_attempted = True
        transferred_fields = ["风险等级", "来源计数", "功能领域等级", "支持需要", "任务标题", "信息缺口"]
        try:
            raw = await ask_spark(prompt, max_tokens=520, temperature=0.15)
            candidate = NarrativeOutput.model_validate_json(raw[raw.find("{"):raw.rfind("}") + 1])
            if not _safe_model_narrative(candidate):
                raise ValueError("unsafe teacher review narrative")
            summary = candidate.executive_summary
            opening = candidate.conversation_opening
            model_name = "xunfei-constrained"
            external_transfer = True
        except Exception as exc:
            degraded = True
            external_transfer_failure = "timeout_or_service_error" if isinstance(exc, (TimeoutError, ConnectionError)) else "invalid_or_unsafe_output"

    risk_labels = {"routine": "常规关怀", "watch": "建议持续关注", "professional": "建议尽快连接专业支持", "urgent": "需要立即安全协助"}
    followup_days = [] if risk == "urgent" else ([1, 3, 7] if risk == "professional" else [3, 7, 15])
    guidance_codes = ["WHO-AMH-2025", "WHO-SHS-2021"]
    report_sources = [item for item in EVIDENCE_REGISTRY if item["code"] in {*guidance_codes, "WHO-HAT-2020"}]
    planned_tasks = [{**item, "guidance_codes": guidance_codes} for item in work_product.get("tasks") or []]
    immediate_actions = []
    if risk == "urgent":
        guidance_codes = ["NICE-NG225", "WHO-SHS-2021"]
        report_sources = [item for item in EVIDENCE_REGISTRY if item["code"] in guidance_codes]
        immediate_actions = [
            {"title": "立即确认学生当下安全并由可信成年人持续陪伴，不让学生独处", "owner": "在场教师/校内安全负责人", "due": "立即", "guidance_codes": guidance_codes},
            {"title": "在确保自身安全的前提下远离危险物；正在或即将发生伤害时联系110或120", "owner": "在场教师/安全负责人", "due": "立即", "guidance_codes": guidance_codes},
            {"title": "联系12356及校内危机支持；若监护人可能是伤害来源，改联系其他安全成年人或报警", "owner": "校内危机支持负责人", "due": "立即", "guidance_codes": guidance_codes},
        ]
        planned_tasks = []
    report = {
        "report_id": "",
        "report_version": "teacher-review-report-v1",
        "status": "draft",
        "title": "学生心理健康支持工单 · 最终评审报告",
        "student_label": student_label,
        "teacher_label": teacher_label,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "reviewed_at": None,
        "review_note": "",
        "boundary": "本报告用于学校心理健康教育、支持安排与求助导航，不是医学诊断、心理治疗记录或标准化量表结论。",
        "overall_decision": {
            "risk_level": risk,
            "risk_label": risk_labels[risk],
            "priority": "立即" if risk == "urgent" else "当天" if risk == "professional" else "近期",
            "decision": work_product.get("decision"),
            "evidence_ids": list(work_product.get("decision_evidence_ids") or []),
        },
        "executive_summary": summary,
        "data_scope": {
            "period_start": work_product.get("data_from"),
            "content_cutoff": work_product.get("content_cutoff"),
            "access_basis": work_product.get("access_basis"),
            "source_counts": source_counts,
            "quality": "信息有限" if gaps else "结构完整",
            "information_gaps": list(dict.fromkeys(gaps))[:6],
            "original_text_external_transfer": False,
        },
        "safety_review": {
            "risk_level": risk,
            "ordinary_plan_stopped": risk == "urgent",
            "immediate_actions": immediate_actions,
            "escalation_thresholds": [
                "出现正在实施或即将实施的伤害行为时立即联系110或120",
                "无法确认学生当下安全时，不让学生独处并联系校内安全负责人和12356",
                "监护人可能是伤害来源时，改由可信教师、其他安全成年人或报警路径介入",
            ],
        },
        "context_review": {
            "functioning": _function_observations(work_product),
            "risk_factors": _risk_factors(work_product),
            "protective_factors": _protective_factors(work_product),
            "student_voice": [{
                "evidence_id": item.get("id"),
                "source": item.get("source"),
                "excerpt": _safe_text(item.get("content"), 120),
                "created_at": item.get("created_at"),
            } for item in records[:3]],
        },
        "student_preferences": {
            "status": "待线下确认",
            "accepted_support": [],
            "declined_support": [],
            "deferred_support": [],
            "allowed_share_scope": "待与学生确认；紧急安全事件仅按最少必要原则共享",
        },
        "support_plan": {
            "ordinary_plan_stopped": risk == "urgent",
            "tasks": planned_tasks,
            "conversation_opening": "" if risk == "urgent" else opening,
            "conversation_guidance_codes": [] if risk == "urgent" else ["WHO-AMH-2025", "WHO-SHS-2021"],
            "questions": [] if risk == "urgent" else [
                "最近哪些时候会稍微轻松一点？当时有什么人或事情在帮助你？",
                "这件事对上课、睡眠、吃饭或和人相处有什么变化？",
                "你希望老师提供哪一种帮助？哪些事情暂时不希望被做？",
            ],
            "questions_guidance_codes": [] if risk == "urgent" else ["WHO-AMH-2025", "WHO-SHS-2021"],
            "avoid": [] if risk == "urgent" else ["追问细节或要求一次说完", "承诺绝对保密", "用成绩、纪律或比较来解释学生状态", "把AI整理结果当作诊断结论"],
            "avoid_guidance_codes": [] if risk == "urgent" else ["WHO-AMH-2025", "WHO-SHS-2021"],
            "referral": [] if risk == "urgent" else ["校内心理支持负责人", "12356心理援助热线", "经核验的医疗或社会心理服务资源"],
            "referral_guidance_codes": [] if risk == "urgent" else ["WHO-SHS-2021"],
            "follow_up": [{"day": day, "focus": "安全状态、功能影响、学生接受的支持是否发生变化", "status": "待安排", "guidance_codes": guidance_codes} for day in followup_days],
        },
        "agent_review": {
            "workflow": [
                {"agent": "TaskInterpreter", "tool": "授权范围解析", "status": "completed", "result": "确认工单、教师职责和数据截止时间"},
                {"agent": "SafetyGate", "tool": "确定性安全策略", "status": "attention" if risk == "urgent" else "completed", "result": "风险等级不可被模型降低"},
                {"agent": "EvidenceMapper", "tool": "授权记录查询", "status": "completed", "result": f"映射{len(records)}条记录与证据编号"},
                {"agent": "ContextAnalyst", "tool": "功能与保护因素模板", "status": "blocked" if risk == "urgent" else "completed", "result": "分别整理风险、功能影响、保护因素和信息缺口"},
                {"agent": "SupportPlanner", "tool": "学校支持行动模板", "status": "blocked" if risk == "urgent" else "completed", "result": "生成教师可确认的行动和回访安排"},
                {"agent": "CrossReviewer", "tool": "措辞与证据校验", "status": "attention" if (work_product.get("conflicts") or gaps or degraded) else "completed", "result": "检查诊断措辞、安全冲突、模型话术和证据覆盖"},
                {"agent": "ReportCoordinator", "tool": "报告快照与导出准备", "status": "completed", "result": "形成待教师签署的报告快照；PDF在下载时按需渲染"},
            ],
            "conflicts": list(work_product.get("conflicts") or []),
            "guardrails": list(work_product.get("guardrails") or []),
        },
        "evidence_sources": report_sources,
        "review_checklist": [
            {"item": "已结合线下观察核对学生当下安全", "required": True},
            {"item": "已确认报告未作诊断或虚构量表结论", "required": True},
            {"item": "已与学生确认其愿意接受的支持方式", "required": risk != "urgent"},
            {"item": "已确认转介资源和回访责任人", "required": risk in {"professional", "urgent"}},
        ],
        "generation": {
            "source": "safety_override" if risk == "urgent" else ("xunfei_constrained" if model_name == "xunfei-constrained" else "deterministic"),
            "model_name": model_name,
            "prompt_version": "teacher-review-narrative-v1",
            "degraded": degraded,
            "external_transfer": external_transfer,
            "external_transfer_attempted": external_transfer_attempted,
            "external_transfer_succeeded": external_transfer,
            "external_transfer_failure": external_transfer_failure,
            "transferred_fields": transferred_fields,
        },
    }
    return report
