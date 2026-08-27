"""学生心理状态评估多 Agent 编排。

该模块只生成支持性观察，不进行疾病诊断，也不把自建题目包装成标准化量表。
风险等级、危机覆盖和证据约束全部由确定性规则控制；大模型只能润色已验证的摘要。
"""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from config import settings
from guardian_engine import generated_content_violations
from xunfei.spark_api import ask_spark


Frequency = Literal["never", "several_days", "more_than_half", "nearly_every_day", "unsure"]
RiskLevel = Literal["routine", "watch", "professional", "urgent"]
DomainLevel = Literal["未见明显影响", "需要留意", "影响明显", "信息不足"]

FREQUENCY_LEVEL = {
    "never": 0,
    "several_days": 1,
    "more_than_half": 2,
    "nearly_every_day": 3,
    "unsure": -1,
}

ITEM_LABELS = {
    "low_mood": "低落或提不起精神",
    "low_interest": "难以从平时喜欢的事中获得兴趣",
    "worry": "紧张、担心或难以放松",
    "sleep": "睡眠节律受到影响",
    "energy": "精力不足或容易疲惫",
    "concentration": "集中注意比较困难",
    "loneliness": "孤单或难以获得支持",
    "school_impact": "学习或到校受到影响",
    "home_impact": "家庭生活或日常照料受到影响",
}

DOMAIN_ITEMS = {
    "emotion": ("情绪体验", ["low_mood", "low_interest", "worry"]),
    "rhythm": ("睡眠与精力", ["sleep", "energy"]),
    "functioning": ("学习与日常功能", ["concentration", "school_impact", "home_impact"]),
    "connection": ("支持与联结", ["loneliness"]),
}

ALLOWED_EMOTIONS = {"开心", "平静", "焦虑", "难过", "愤怒", "疲惫", "孤独", "委屈", "害怕", "复杂", "不确定"}


class DomainObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Literal["emotion", "rhythm", "functioning", "connection"]
    label: str
    level: DomainLevel
    observation: str
    evidence_ids: list[str] = Field(default_factory=list, max_length=4)


class AssessmentPipelineStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Literal["safety", "emotion", "function", "planning", "review", "coordination"]
    agent: str
    status: Literal["completed", "attention", "blocked"]
    summary: str = Field(min_length=2, max_length=120)
    evidence_ids: list[str] = Field(default_factory=list, max_length=6)


class AssessmentConflict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str = Field(min_length=2, max_length=40)
    views: list[str] = Field(min_length=2, max_length=3)
    resolution: str = Field(min_length=4, max_length=140)


class AssessmentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    risk_level: RiskLevel
    risk_label: str
    boundary: str
    period_label: str
    emotion_summary: str
    emotion_intensity: Literal["未单独推断"]
    domains: list[DomainObservation] = Field(min_length=4, max_length=4)
    support_needs: list[str] = Field(min_length=1, max_length=4)
    priority_action: str
    alternative_actions: list[str] = Field(default_factory=list, max_length=2)
    questions_for_followup: list[str] = Field(default_factory=list, max_length=3)
    information_gaps: list[str] = Field(default_factory=list, max_length=4)
    safety_actions: list[str] = Field(default_factory=list, max_length=6)
    evidence_ids: list[str] = Field(default_factory=list, max_length=12)
    pipeline: list[AssessmentPipelineStep] = Field(min_length=6, max_length=6)
    review_findings: list[str] = Field(min_length=2, max_length=4)
    conflicts: list[AssessmentConflict] = Field(default_factory=list, max_length=3)
    model_name: str
    prompt_version: Literal["wellbeing-assessment-v1"] = "wellbeing-assessment-v1"
    degraded: bool = False
    review_status: Literal["needs_professional_review"]


class AssessmentNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=10, max_length=180)


def _level_for(values: list[str]) -> DomainLevel:
    known = [FREQUENCY_LEVEL[value] for value in values if value in FREQUENCY_LEVEL and FREQUENCY_LEVEL[value] >= 0]
    if not known:
        return "信息不足"
    highest = max(known)
    return "影响明显" if highest >= 2 else "需要留意" if highest == 1 else "未见明显影响"


def _intensity_for_domain(level: DomainLevel) -> str:
    return {"影响明显": "强烈", "需要留意": "明显", "未见明显影响": "轻微"}.get(level, "不确定")


def _risk_policy(answers: dict[str, str]) -> tuple[RiskLevel, list[str]]:
    if answers.get("self_harm") == "yes" or answers.get("unsafe_home") == "yes":
        return "urgent", [key for key in ("self_harm", "unsafe_home") if answers.get(key) == "yes"]
    if answers.get("self_harm") == "unsure" or answers.get("unsafe_home") == "unsure":
        return "professional", [key for key in ("self_harm", "unsafe_home") if answers.get(key) == "unsure"]
    strong = [key for key in ITEM_LABELS if FREQUENCY_LEVEL.get(answers.get(key, "unsure"), -1) >= 2]
    if answers.get("school_impact") == "nearly_every_day" or answers.get("home_impact") == "nearly_every_day" or len(strong) >= 2:
        return "professional", strong
    noticeable = [key for key in ITEM_LABELS if FREQUENCY_LEVEL.get(answers.get(key, "unsure"), -1) == 1]
    if strong or len(noticeable) >= 2:
        return "watch", strong + noticeable
    return "routine", noticeable


def _support_plan(risk: RiskLevel, domains: list[DomainObservation]) -> tuple[list[str], str, list[str]]:
    affected = {domain.id for domain in domains if domain.level in {"需要留意", "影响明显"}}
    needs: list[str] = []
    if "emotion" in affected:
        needs.append("获得不评判的倾听，并把当前压力拆成较小部分")
    if "rhythm" in affected:
        needs.append("优先恢复基本睡眠、休息和日常节律")
    if "functioning" in affected:
        needs.append("由可信成年人协助降低当前学习或生活负担")
    if "connection" in affected:
        needs.append("连接一位学生信任且不涉事的安全成年人")
    if not needs:
        needs.append("保持当前可行的自我照顾，并继续观察变化")
    if risk == "urgent":
        return needs[:4], "现在就去找一位不涉事的可信成年人陪在身边，并进入安全求助路径。", []
    if risk == "professional":
        return needs[:4], "今天把这份结果告诉一位可信成年人，请对方协助联系学校心理老师、12356或正规医疗机构进一步评估。", ["暂时减少一项最影响日常的负担", "记录今天最需要支持的一件事"]
    if risk == "watch":
        return needs[:4], "24小时内选择一位可信成年人，完成一次低压力的近况沟通。", ["先完成一项五分钟以内的照顾行动", "三天后再次回顾变化"]
    return needs[:4], "从一项五分钟以内、不会增加负担的自我照顾行动开始。", ["需要时继续倾诉", "一周内再回顾一次状态"]


def _safe_narrative(candidate: AssessmentNarrative, selected_emotions: list[str]) -> bool:
    rendered = json.dumps(candidate.model_dump(), ensure_ascii=False)
    if generated_content_violations(rendered):
        return False
    if re.search(
        r"(?:PHQ|GAD|确诊|患有|概率|百分之|%|总分|量表分|治疗|用药|"
        r"建议|应该|必须|需要|联系|求助|拨打|咨询)",
        rendered,
        re.I,
    ):
        return False
    # 模型只能改写学生主动选择的情绪，不得补充新的情绪标签。
    mentioned = {emotion for emotion in ALLOWED_EMOTIONS if emotion in candidate.summary}
    return mentioned.issubset(set(selected_emotions) | {"不确定"})


def _cross_review(*, risk: RiskLevel, domains: list[DomainObservation],
                  emotions: list[str], priority_action: str,
                  safety_actions: list[str], evidence_ids: list[str]) -> tuple[list[str], list[AssessmentConflict]]:
    """独立复核证据边界与安全冲突，失败即阻断协调结果。"""
    allowed_evidence = set(ITEM_LABELS) | {"self_harm", "unsafe_home"}
    if not set(evidence_ids).issubset(allowed_evidence):
        raise ValueError("assessment contains unknown evidence")
    if risk == "urgent" and (len(safety_actions) < 3 or "12356" not in " ".join(safety_actions)):
        raise ValueError("urgent assessment lost required safety actions")
    if risk == "professional" and not all(token in priority_action for token in ("今天", "可信成年人")):
        raise ValueError("professional action was weakened")
    if risk == "watch" and "24小时内" not in priority_action:
        raise ValueError("watch action was weakened")

    findings = [
        "风险等级与优先行动已通过确定性安全策略复核",
        "所有领域结论均绑定本次主动回答的证据编号",
        "未生成诊断、量表计分、概率或疾病判断",
    ]
    conflicts: list[AssessmentConflict] = []
    emotion_domain = next(item for item in domains if item.id == "emotion")
    if emotions and emotion_domain.level in {"需要留意", "影响明显"}:
        conflicts.append(AssessmentConflict(
            topic="时间窗口差异",
            views=[f"此刻主动选择：{'、'.join(emotions)}", f"近两周情绪领域：{emotion_domain.level}"],
            resolution="两者描述不同时间窗口，协调器分别保留，不把近两周影响解释为此刻情绪强度。",
        ))
    return findings, conflicts


class WellbeingAssessmentOrchestrator:
    """运行可审计的六阶段评估工作流。"""

    async def run(self, *, answers: dict[str, str], emotions: list[str], external_ai_allowed: bool) -> AssessmentResult:
        risk, risk_evidence = _risk_policy(answers)
        all_evidence = [key for key, value in answers.items() if key in ITEM_LABELS and value != "unsure"]
        all_evidence.extend(risk_evidence)

        domains: list[DomainObservation] = []
        for domain_id, (label, item_ids) in DOMAIN_ITEMS.items():
            level = _level_for([answers.get(item, "unsure") for item in item_ids])
            evidence = [item for item in item_ids if answers.get(item, "unsure") != "unsure"]
            affected = [ITEM_LABELS[item] for item in item_ids if FREQUENCY_LEVEL.get(answers.get(item, "unsure"), -1) >= 1]
            observation = "暂时没有足够回答形成观察。" if level == "信息不足" else (
                "本次回答未显示这一领域受到明显影响。" if not affected else "本次主动回答提到：" + "、".join(affected) + "。"
            )
            domains.append(DomainObservation(id=domain_id, label=label, level=level, observation=observation, evidence_ids=evidence))

        emotion_domain = next(item for item in domains if item.id == "emotion")
        valid_emotions = list(dict.fromkeys(item for item in emotions if item in ALLOWED_EMOTIONS))[:3]
        emotion_summary = "、".join(valid_emotions) if valid_emotions else "本次没有选择明确的情绪词"
        support_needs, priority_action, alternatives = _support_plan(risk, domains)
        gaps = [ITEM_LABELS[key] for key in ITEM_LABELS if answers.get(key) == "unsure"][:4]
        followup = [
            "哪些事情最容易让这种状态加重或缓解？",
            "目前有哪位成年人能让你感到相对安全？",
            "这种状态对上课、睡眠或与人相处的影响有没有变化？",
        ][: 2 if risk == "routine" else 3]

        safety_actions = []
        if risk == "urgent":
            safety_actions = [
                "立即与一位不涉事的可信成年人待在一起，不要独处",
                "远离药物、刀具、高处等可能造成伤害的物品或环境",
                "拨打12356；危险正在发生或已经实施伤害时拨打110或120",
                "如果监护人可能是伤害来源，联系可信教师、其他安全成年人或报警",
            ]

        review_findings, conflicts = _cross_review(
            risk=risk, domains=domains, emotions=valid_emotions,
            priority_action=priority_action, safety_actions=safety_actions,
            evidence_ids=list(dict.fromkeys(all_evidence)),
        )

        model_name = "deterministic-assessment"
        degraded = False
        # 只有 routine 可调用模型润色低风险观察摘要。风险等级、支持行动和追问
        # 始终保留确定性结果，避免模型弱化 watch/professional/urgent 的处置强度。
        if external_ai_allowed and risk == "routine":
            prompt = [
                {"role": "system", "content": (
                    "你是未成年人心理支持系统中的受约束文字整理器。只可改写已给出的低风险观察摘要，"
                    "不得给建议、不得诊断、不得输出分数或概率、不得改变风险等级、不得虚构事实。"
                    "只返回严格JSON，字段只能是summary。"
                )},
                {"role": "user", "content": json.dumps({
                    "risk_level": risk,
                    "selected_emotions": valid_emotions,
                    "domains": [{"label": item.label, "level": item.level} for item in domains],
                    "fixed_summary": emotion_summary,
                    "required_schema": {"summary": "10-180字的描述性摘要，不包含行动建议"},
                }, ensure_ascii=False)},
            ]
            try:
                raw = await ask_spark(prompt, max_tokens=400, temperature=0.15)
                candidate = AssessmentNarrative.model_validate_json(raw[raw.find("{"):raw.rfind("}") + 1])
                if not _safe_narrative(candidate, valid_emotions):
                    raise ValueError("unsafe assessment narrative")
                emotion_summary = candidate.summary
                model_name = "xunfei-constrained"
            except Exception:
                degraded = True

        risk_labels = {"routine": "常规关怀", "watch": "建议持续留意", "professional": "建议专业支持", "urgent": "需要立即协助"}
        pipeline = [
            AssessmentPipelineStep(id="safety", agent="SafetyGate", status="attention" if risk == "urgent" else "completed", summary="已切换到立即安全支持" if risk == "urgent" else "已完成明确危险与家庭安全检查", evidence_ids=risk_evidence),
            AssessmentPipelineStep(id="emotion", agent="EmotionObserver", status="blocked" if risk == "urgent" else "completed", summary="紧急状态下停止普通情绪归纳" if risk == "urgent" else "已整理学生主动选择的情绪与近两周变化", evidence_ids=[key for key in ("low_mood", "low_interest", "worry") if key in all_evidence]),
            AssessmentPipelineStep(id="function", agent="FunctionAssessor", status="blocked" if risk == "urgent" else "completed", summary="紧急状态下优先安全处置" if risk == "urgent" else "已检查睡眠、精力、学习和日常影响", evidence_ids=[key for key in ("sleep", "energy", "concentration", "school_impact", "home_impact") if key in all_evidence]),
            AssessmentPipelineStep(id="planning", agent="SupportPlanner", status="blocked" if risk == "urgent" else "completed", summary="普通支持计划已暂停" if risk == "urgent" else "已生成与当前支持强度匹配的下一步", evidence_ids=all_evidence[:6]),
            AssessmentPipelineStep(id="review", agent="CrossReviewer", status="attention" if conflicts or gaps else "completed", summary=f"已完成{len(review_findings)}项强制复核" + (f"，并裁决{len(conflicts)}项信息差异" if conflicts else ""), evidence_ids=all_evidence[:6]),
            AssessmentPipelineStep(id="coordination", agent="Coordinator", status="attention" if risk in {"professional", "urgent"} else "completed", summary="已形成可复核的安全行动" if risk == "urgent" else "已形成学生可执行、教师可审核的结构化结果", evidence_ids=all_evidence[:6]),
        ]
        return AssessmentResult(
            risk_level=risk,
            risk_label=risk_labels[risk],
            boundary="这是基于近两周主动回答形成、尚待专业人员审核的支持需求观察，不是经验证的心理量表或医学诊断，也不能替代专业人员面谈。",
            period_label="过去两周",
            emotion_summary=emotion_summary,
            # “此刻情绪词”与“过去两周领域影响”是不同时间窗口，不能把后者
            # 伪装成前者的强度。当前版本不单独推断此刻情绪强度。
            emotion_intensity="未单独推断",
            domains=domains,
            support_needs=support_needs,
            priority_action=priority_action,
            alternative_actions=alternatives,
            questions_for_followup=followup,
            information_gaps=gaps,
            safety_actions=safety_actions,
            evidence_ids=list(dict.fromkeys(all_evidence))[:12],
            pipeline=pipeline,
            review_findings=review_findings,
            conflicts=conflicts,
            model_name=model_name,
            degraded=degraded,
            review_status="needs_professional_review",
        )
