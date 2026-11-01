"""PHQ-9 标准筛查的确定性计分、分级与风险分流。"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app_time import china_now_naive
from models import StudentScreeningRun

INSTRUMENT = "phq9"
INSTRUMENT_VERSION = "phq-9-cn-v1"
RETENTION_DAYS = 90
ACTIVE_DAYS = 30

ITEMS = [
    {"id": 1, "text": "做事时提不起劲或没有兴趣"},
    {"id": 2, "text": "感到心情低落、沮丧或绝望"},
    {"id": 3, "text": "入睡困难、睡不安或睡眠过多"},
    {"id": 4, "text": "感觉疲倦或没有活力"},
    {"id": 5, "text": "食欲不振或吃太多"},
    {"id": 6, "text": "觉得自己很糟，或觉得自己很失败，或让自己、家人失望"},
    {"id": 7, "text": "对事物专注有困难，例如阅读报纸或看电视时"},
    {"id": 8, "text": "动作或说话速度缓慢到别人已经觉察；或正好相反——烦躁或坐立不安、动来动去的情况更胜于平常"},
    {"id": 9, "text": "有不如死掉或用某种方式伤害自己的念头"},
]

OPTIONS = [
    {"value": 0, "label": "完全不会"},
    {"value": 1, "label": "好几天"},
    {"value": 2, "label": "一半以上的天数"},
    {"value": 3, "label": "几乎每天"},
]

BANDS = [
    {"band": "minimal", "label": "无明显", "min": 0, "max": 4},
    {"band": "mild", "label": "轻度", "min": 5, "max": 9},
    {"band": "moderate", "label": "中度", "min": 10, "max": 14},
    {"band": "moderately_severe", "label": "中重度", "min": 15, "max": 19},
    {"band": "severe", "label": "重度", "min": 20, "max": 27},
]

BAND_LABELS = {item["band"]: item["label"] for item in BANDS}
RISK_ORDER = {"routine": 0, "watch": 1, "professional": 2, "urgent": 3}

DISCLOSURE = (
    "计分在咕哝服务器完成，不发送给外部模型。老师可以看到本次分级、总分和填写时间，"
    "看不到每道题的具体选项；如果第9题有应答，老师会看到需要立即核实安全的标记。"
    "结果保留90天，你可以随时删除。"
)
BOUNDARY = "PHQ-9 是常用筛查工具，不是诊断；结果只用于支持分流，不能替代专业人员面谈。"


def _question_keys(answers: dict) -> set[str]:
    return {str(key) for key in answers}


def score(answers: dict) -> int:
    """严格按 9 题、0~3 分计分；非法输入直接拒绝，不做静默补零。"""
    if _question_keys(answers) != {str(item["id"]) for item in ITEMS}:
        raise ValueError("筛查题目不完整")
    total = 0
    for item in ITEMS:
        value = answers[str(item["id"])]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 3:
            raise ValueError("筛查选项不合法")
        total += value
    return total


def band_for(total: int) -> tuple[str, str]:
    if not 0 <= total <= 27:
        raise ValueError("筛查总分超出范围")
    for item in BANDS:
        if item["min"] <= total <= item["max"]:
            return item["band"], item["label"]
    raise ValueError("筛查总分超出范围")


def risk_for(total: int, item9_positive: bool) -> str:
    if item9_positive:
        return "urgent"
    if total >= 15:
        return "professional"
    if total >= 10:
        return "watch"
    return "routine"


def merge_risk(*levels: str | None) -> str:
    valid = [level for level in levels if level in RISK_ORDER]
    if not valid:
        return "routine"
    return max(valid, key=lambda level: RISK_ORDER[level])


def item9_answered(answers: dict) -> bool:
    value = answers.get("9", answers.get(9))
    return bool(isinstance(value, int) and not isinstance(value, bool) and value > 0)


def student_message(band: str, item9_positive: bool) -> str:
    if item9_positive:
        return (
            "你在第9题上有了应答，这需要被认真对待。请先和一位可信成年人待在一起，"
            "并告诉学校心理老师；如果出现伤害自己的念头或迫切危险，立即拨打12356、110或120。"
            "这不是你的错，也不需要你一个人扛。"
        )
    messages = {
        "minimal": "最近两周的负担看起来不算重。继续留意睡眠、精力和身边的人，有不舒服随时可以说。",
        "mild": "最近两周有些时候不太轻松。可以先看看这些日子和什么有关，再决定要不要和信任的人聊聊。",
        "moderate": "最近两周的负担已经值得被认真对待。建议和一位可信成年人或学校心理老师聊一次，不需要一个人扛。",
        "moderately_severe": "最近两周的大部分时间可能都不太轻松。建议尽快联系学校心理老师或正规医疗机构，越早得到支持越好。",
        "severe": "最近两周的负担很重。请尽快告诉一位可信成年人，并联系学校心理老师或正规医疗机构。",
    }
    return messages.get(band, messages["moderate"])


def _base_query(db: Session, user_ids: list[int] | int):
    query = db.query(StudentScreeningRun).filter(
        StudentScreeningRun.deleted_at.is_(None),
        StudentScreeningRun.expires_at > china_now_naive(),
    )
    if isinstance(user_ids, int):
        return query.filter(StudentScreeningRun.user_id == user_ids)
    return query.filter(StudentScreeningRun.user_id.in_(user_ids))


def latest_screening(db: Session, user_id: int, *, cutoff: datetime | None = None) -> StudentScreeningRun | None:
    query = _base_query(db, user_id)
    if cutoff is not None:
        query = query.filter(StudentScreeningRun.created_at <= cutoff)
    return query.order_by(
        StudentScreeningRun.created_at.desc(), StudentScreeningRun.id.desc()
    ).first()


def latest_screenings_for_students(db: Session, student_ids: list[int]) -> dict[int, StudentScreeningRun]:
    """一次查询取每个学生在保留期内的最近一次筛查，避免教师端 N+1。"""
    if not student_ids:
        return {}
    rows = _base_query(db, student_ids).order_by(
        StudentScreeningRun.user_id,
        StudentScreeningRun.created_at.desc(),
        StudentScreeningRun.id.desc(),
    ).all()
    latest: dict[int, StudentScreeningRun] = {}
    for row in rows:
        latest.setdefault(row.user_id, row)
    return latest


def run_risk(row: StudentScreeningRun, *, now: datetime | None = None) -> str:
    """当前有效风险：第9题安全标记只在其激活时把风险提到 urgent；已确认联系可信成年人的专业级风险降为 watch。"""
    now = now or china_now_naive()
    if row.created_at < now - timedelta(days=ACTIVE_DAYS):
        return "routine"
    if row.item9_positive and row.safety_flag_active:
        return "urgent"
    risk = risk_for(row.total_score, False)
    if risk == "professional" and row.acknowledged_at is not None:
        return "watch"
    return risk


def active_screening_risk(db: Session, user_id: int, *, now: datetime | None = None) -> str:
    row = latest_screening(db, user_id)
    if not row:
        return "routine"
    return run_risk(row, now=now)


def safety_active(row: StudentScreeningRun | None) -> bool:
    return bool(row and row.item9_positive and row.safety_flag_active)


def cleanup_expired(db: Session, user_id: int) -> None:
    now = china_now_naive()
    rows = db.query(StudentScreeningRun).filter(
        StudentScreeningRun.user_id == user_id,
        StudentScreeningRun.expires_at <= now,
        StudentScreeningRun.deleted_at.is_(None),
    ).all()
    for row in rows:
        row.deleted_at = now
        row.answers_json = "{}"


def to_student_payload(row: StudentScreeningRun, *, urgent_session_id: str | None = None) -> dict:
    urgent = safety_active(row)
    return {
        "run_code": row.run_code,
        "instrument": row.instrument,
        "instrument_version": row.instrument_version,
        "band": row.band,
        "band_label": BAND_LABELS.get(row.band, "中度"),
        "total_score": row.total_score,
        "message": student_message(row.band, bool(row.item9_positive)),
        "item9_positive": bool(row.item9_positive),
        "safety_active": urgent,
        "urgent": urgent,
        "urgent_session_id": urgent_session_id,
        "risk_level": run_risk(row),
        "acknowledged": bool(row.acknowledged_at),
        "acknowledged_at": row.acknowledged_at.isoformat() if row.acknowledged_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "disclosure": DISCLOSURE,
        "boundary": BOUNDARY,
    }


def to_teacher_summary(row: StudentScreeningRun | None) -> dict | None:
    if not row:
        return None
    return {
        "band": row.band,
        "band_label": BAND_LABELS.get(row.band, "中度"),
        "total_score": row.total_score,
        "item9_positive": bool(row.item9_positive),
        "safety_active": safety_active(row),
        "risk_level": run_risk(row),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def answers_from_row(row: StudentScreeningRun) -> dict:
    try:
        payload = json.loads(row.answers_json or "{}")
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}
