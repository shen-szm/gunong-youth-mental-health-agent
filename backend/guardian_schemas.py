"""守护者工作台的严格输入输出契约。"""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


ReporterRole = Literal["parent", "teacher"]
RiskLevel = Literal["routine", "watch", "professional", "urgent"]


class GuardianCaseCreate(StrictModel):
    reporter_role: ReporterRole
    age_band: Literal["12-14", "15-18"]
    signals: list[
        Literal[
            "mood_low",
            "irritability",
            "school_refusal",
            "social_withdrawal",
            "sleep_change",
            "performance_drop",
            "family_conflict",
            "self_harm_sign",
            "death_talk",
        ]
    ] = Field(min_length=1, max_length=9)
    duration: Literal["under_1_week", "1_2_weeks", "2_4_weeks", "1_3_months", "over_3_months"]
    functional_impact: Literal["none", "partial", "significant"]
    district: Literal[
        "莞城街道",
        "东城街道",
        "南城街道",
        "万江街道",
        "中堂镇",
        "其他镇街",
    ]
    context: str = Field(default="", max_length=500)
    guardian_may_be_source: bool = False
    consent_version: Literal["guardian-demo-v1"]
    synthetic_data_confirmed: Literal[True]

    @field_validator("context")
    @classmethod
    def reject_direct_identifiers(cls, value: str) -> str:
        value = value.strip()
        blocked_labels = ("姓名：", "身份证", "手机号", "电话：", "学校全称")
        identifier_patterns = (
            r"(?<!\d)1[3-9]\d{9}(?!\d)",
            r"(?<!\d)\d{17}[\dXx](?!\d)",
            r"(?<!\d)0\d{2,3}[- ]?\d{7,8}(?!\d)",
            r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
            r"[\u4e00-\u9fff]{2,24}(?:中学|学校|学院)",
            r"(?:路|街|巷|小区|社区|村).{0,12}\d+(?:号|栋|单元|室)",
        )
        if any(label in value for label in blocked_labels) or any(
            re.search(pattern, value) for pattern in identifier_patterns
        ):
            raise ValueError("补充描述不得包含姓名、证件号、电话或学校全称")
        return value


class AssessmentOutput(StrictModel):
    risk_level: RiskLevel
    method: Literal["guardian_observation_v1"] = "guardian_observation_v1"
    standardized_scale_used: Literal[False] = False
    observed_pattern: str
    functional_summary: str
    uncertainty: str
    next_step: str


class KnowledgeOutput(StrictModel):
    evidence_codes: list[str]
    evidence_summary: list[str]
    evidence_limit: str


class ResourceItem(StrictModel):
    resource_code: str
    name: str
    type: str
    phone: str
    availability: str
    district: str
    address: str
    source_url: str
    verified_at: str
    note: str


class ResourceOutput(StrictModel):
    resources: list[ResourceItem]
    selection_note: str


class InterventionOutput(StrictModel):
    immediate_actions: list[str]
    seven_day_actions: list[str]
    conversation_prompts: list[str]
    avoid_actions: list[str]
    tailored_note: str
    generated_by: Literal["xunfei_structured", "reviewed_template"]


class ReviewOutput(StrictModel):
    evidence_coverage: Literal["complete", "partial", "unavailable"]
    role_fit: Literal["parent", "teacher"]
    safety_override_applied: bool
    disagreements: list[str]
    resolution: str
    forbidden_terms_found: list[str]


class SupportPlanOutput(StrictModel):
    case_code: str
    release_version: str
    risk_level: RiskLevel
    risk_label: str
    action_priority: str
    observation_summary: str
    immediate_actions: list[str]
    seven_day_actions: list[str]
    conversation_prompts: list[str]
    avoid_actions: list[str]
    resources: list[ResourceItem]
    evidence_codes: list[str]
    disagreements: list[str]
    review_resolution: str
    follow_up_days: list[int]
    review_status: Literal["needs_professional_review"] = "needs_professional_review"
    ai_disclosure: str
    boundary_notice: str


class FollowUpResponse(StrictModel):
    mood_change: Literal["improved", "slightly_improved", "unchanged", "worse"]
    action_completion: Literal["most", "some", "none"]
    difficulty: str = Field(default="", max_length=300)
    needs_adjustment: bool
    current_safety: Literal["safe", "unsure", "immediate_danger"]
    new_self_harm_or_suicide_signal: bool = False
    action_taken_or_means_available: bool = False
    family_harm_or_unsafe_home: bool = False
