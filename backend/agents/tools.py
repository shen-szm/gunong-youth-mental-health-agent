"""
心岛守护者 - 工具集

这些工具是 Agent "调用工具与环境交互" 能力的核心体现。
分为四类：
1. 感知工具：从数据库获取用户状态
2. 环境工具：控制心岛游戏场景（通过指令下发给前端）
3. 活动工具：启动/推荐疗愈活动
4. 安全工具：危机检测与干预
5. 交付工具：生成可验收报告
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

import screening_engine
from guardian_engine import _context_has_urgent_meaning
from models import (
    MoodRecord, StudentConversationSummary, StudentWellbeingAssessment,
    StudentChatSession,
)


# ── 感知工具 ──────────────────────────────────────────────

def get_mood_history(db: Session, user_id: int, days: int = 7) -> list[dict]:
    """获取用户近期心情记录。"""
    cutoff = datetime.now() - timedelta(days=days)
    records = (
        db.query(MoodRecord)
        .filter(MoodRecord.user_id == user_id, MoodRecord.created_at >= cutoff)
        .order_by(MoodRecord.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "label": r.mood_label,
            "content": r.content or "",
            "date": r.created_at.strftime("%Y-%m-%d"),
        }
        for r in records
    ]


def get_latest_mood(db: Session, user_id: int) -> dict | None:
    """获取最近一条心情记录。"""
    record = (
        db.query(MoodRecord)
        .filter(MoodRecord.user_id == user_id)
        .order_by(MoodRecord.created_at.desc())
        .first()
    )
    if not record:
        return None
    return {
        "label": record.mood_label,
        "content": record.content or "",
        "date": record.created_at.strftime("%Y-%m-%d %H:%M"),
    }


def get_chat_summary(db: Session, user_id: int, days: int = 7) -> str:
    """获取用户近期倾诉小结。"""
    cutoff = datetime.now() - timedelta(days=days)
    summaries = (
        db.query(StudentConversationSummary)
        .join(StudentChatSession, StudentConversationSummary.session_id == StudentChatSession.id)
        .filter(
            StudentConversationSummary.user_id == user_id,
            StudentConversationSummary.generated_at >= cutoff,
            StudentChatSession.summary_deleted_at.is_(None),
            StudentConversationSummary.expires_at > datetime.now(),
        )
        .order_by(StudentConversationSummary.generated_at.desc())
        .limit(3)
        .all()
    )
    if not summaries:
        return ""
    parts = []
    for s in summaries:
        try:
            data = json.loads(s.summary_json)
            parts.append(data.get("summary", "")[:200])
        except (json.JSONDecodeError, TypeError):
            parts.append(s.summary_json[:200])
    return " | ".join(parts)


def analyze_activity_pattern(behaviors: list[dict]) -> dict:
    """从游戏行为日志中分析活动偏好和节律。"""
    if not behaviors:
        return {"preference": "未知", "login_pattern": "数据不足", "breathing_rate": 0.0}

    # 活动偏好
    place_counts: dict[str, int] = {}
    for b in behaviors:
        place = b.get("place") or b.get("activity")
        if place:
            place_counts[place] = place_counts.get(place, 0) + 1
    preference = max(place_counts, key=place_counts.get) if place_counts else "探索"

    # 登录节律（简单分析）
    hours = [b.get("hour", 12) for b in behaviors if "hour" in b]
    if hours:
        avg_hour = sum(hours) / len(hours)
        if avg_hour < 6:
            login_pattern = "深夜活跃"
        elif avg_hour < 12:
            login_pattern = "上午活跃"
        elif avg_hour < 18:
            login_pattern = "下午活跃"
        else:
            login_pattern = "晚间活跃"
    else:
        login_pattern = "数据不足"

    # 呼吸完成率
    breathing = [b for b in behaviors if b.get("activity") == "breathing"]
    if breathing:
        completed = sum(1 for b in breathing if b.get("completed"))
        breathing_rate = completed / len(breathing)
    else:
        breathing_rate = 0.0

    return {
        "preference": preference,
        "login_pattern": login_pattern,
        "breathing_rate": round(breathing_rate, 2),
        "total_activities": len(behaviors),
    }


# ── 环境控制工具 ──────────────────────────────────────────
# 这些工具生成指令，通过 IslandCommand 表下发给前端轮询/WebSocket 接收

ISLAND_WEATHERS = ["clear", "cloudy", "rain", "starry"]


def create_island_command(db: Session, user_id: int, command_type: str,
                          payload: dict, reason: str = "") -> dict:
    """
    创建一条心岛指令，前端通过轮询或 WebSocket 接收并执行。
    这是 Agent "调用工具改变环境" 的核心机制。
    """
    from models import IslandCommand  # 延迟导入避免循环
    cmd = IslandCommand(
        user_id=user_id,
        command_type=command_type,
        payload_json=json.dumps(payload, ensure_ascii=False),
        reason=reason,
        status="pending",
    )
    db.add(cmd)
    db.flush()
    return {
        "command_id": cmd.id,
        "type": command_type,
        "payload": payload,
    }


def set_island_weather(db: Session, user_id: int, weather: str, reason: str = "") -> dict:
    """设置心岛天气效果。"""
    if weather not in ISLAND_WEATHERS:
        weather = "clear"
    return create_island_command(
        db, user_id, "set_weather",
        {"weather": weather},
        reason or f"天气切换为{weather}",
    )


def trigger_pet_action(db: Session, user_id: int, action: str,
                       message: str = "", reason: str = "") -> dict:
    """触发咕团行为（移动到玩家身边、说话、播放动画）。"""
    valid_actions = ["approach", "speak", "sit", "follow", "celebrate"]
    if action not in valid_actions:
        action = "approach"
    return create_island_command(
        db, user_id, "pet_action",
        {"action": action, "message": message},
        reason or f"咕团执行{action}",
    )


def show_toast(db: Session, user_id: int, message: str,
               toast_type: str = "info", reason: str = "") -> dict:
    """在心岛显示一条温和提示。"""
    return create_island_command(
        db, user_id, "toast",
        {"message": message, "type": toast_type},
        reason or "显示提示",
    )


# ── 活动推荐工具 ──────────────────────────────────────────

BREATHING_MODES = {
    "box": {"label": "星灯呼吸", "pattern": "4-4-4-4", "cycles": 4, "适合": "日常放松"},
    "478": {"label": "深海呼吸", "pattern": "4-7-8", "cycles": 4, "适合": "焦虑/睡前"},
    "coherent": {"label": "海浪呼吸", "pattern": "5-5", "cycles": 6, "适合": "快速平静"},
}


def recommend_activity(db: Session, user_id: int, mood_state: str) -> dict:
    """根据情绪状态推荐合适的活动。"""
    recommendations = {
        "anxious": {
            "activity": "breathing",
            "mode": "478",
            "message": "咕团注意到你有点紧绷，要不要一起做4-7-8深海呼吸？",
            "place": "rest",
        },
        "sad": {
            "activity": "pet",
            "mode": "",
            "message": "今天好像安静了一些，咕团想在你身边坐一会儿。",
            "place": "home",
        },
        "tired": {
            "activity": "beach",
            "mode": "",
            "message": "累了的话，去潮汐沙滩走走吧，不用做什么，看看海就好。",
            "place": "beach",
        },
        "happy": {
            "activity": "garden",
            "mode": "",
            "message": "心情不错！去花园看看你的植物长得怎么样了？",
            "place": "garden",
        },
        "calm": {
            "activity": "any",
            "mode": "",
            "message": "现在很平静，想做什么都可以，咕团陪着你。",
            "place": "",
        },
    }
    rec = recommendations.get(mood_state, recommendations["calm"])
    return create_island_command(
        db, user_id, "recommend",
        rec,
        reason=f"根据{mood_state}状态推荐活动",
    )


# ── 安全工具 ──────────────────────────────────────────────

def detect_crisis(text: str) -> tuple[bool, str]:
    """复用全站的保守语义安全策略，不维护第二套弱关键词表。"""
    if not text:
        return False, ""
    return (_context_has_urgent_meaning(text), "deterministic_safety_policy")


def get_user_safety_state(db: Session, user_id: int) -> dict:
    """聚合聊天与支持需求自评的最小风险状态，不返回或复制敏感原文。"""
    now = datetime.now()
    assessment = (
        db.query(StudentWellbeingAssessment)
        .filter(
            StudentWellbeingAssessment.user_id == user_id,
            StudentWellbeingAssessment.deleted_at.is_(None),
            StudentWellbeingAssessment.expires_at > now,
        )
        .order_by(
            StudentWellbeingAssessment.created_at.desc(),
            StudentWellbeingAssessment.id.desc(),
        )
        .first()
    )
    urgent_session = (
        db.query(StudentChatSession.id)
        .filter(
            StudentChatSession.user_id == user_id,
            StudentChatSession.status == "urgent",
        )
        .first()
    )
    screening_risk = screening_engine.active_screening_risk(db, user_id)
    if screening_risk == "urgent":
        return {"risk_level": "urgent", "evidence": "current_standard_screening"}
    if urgent_session or (assessment and assessment.risk_level == "urgent"):
        return {"risk_level": "urgent", "evidence": "shared_safety_state"}
    assessment_risk = assessment.risk_level if assessment and assessment.risk_level in {
        "professional", "watch"} else "routine"
    risk = screening_engine.merge_risk(assessment_risk, screening_risk)
    if risk in {"professional", "watch"}:
        evidence = (
            "current_standard_screening"
            if screening_engine.RISK_ORDER[screening_risk] >= screening_engine.RISK_ORDER[assessment_risk]
            else "current_support_assessment"
        )
        return {"risk_level": risk, "evidence": evidence}
    return {"risk_level": "routine", "evidence": "no_active_escalation"}


def get_crisis_resources() -> dict:
    """获取危机干预资源。"""
    return {
        "hotline": "12356",
        "hotline_name": "全国心理援助热线",
        "emergency": "110 / 120",
        "message": (
            "你现在的感受很重要，请先联系一位可信的成年人，"
            "或拨打12356心理援助热线；如果有即时危险，请拨打110或120。"
        ),
    }


# ── 交付工具：报告生成 ────────────────────────────────────

def build_report_data(db: Session, user_id: int, days: int = 7) -> dict:
    """聚合生成报告所需的全部数据。"""
    moods = get_mood_history(db, user_id, days)
    chat = get_chat_summary(db, user_id, days)

    # 只做描述性统计，不把自定义心情值计算成心理量表分数。
    if moods:
        label_counts: dict[str, int] = {}
        for m in moods:
            label_counts[m["label"]] = label_counts.get(m["label"], 0) + 1
        dominant_label = max(label_counts, key=label_counts.get) if label_counts else "未知"
    else:
        dominant_label = "数据不足"
        label_counts = {}

    return {
        "period_days": days,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "mood_dominant": dominant_label,
        "mood_distribution": label_counts,
        "mood_records_count": len(moods),
        "recent_labels": [item["label"] for item in moods[-5:]],
        # 报告只保存派生标签和可核验计数，不二次复制心情或倾诉原文。
        "chat_summary_available": bool(chat),
    }


# ── 工具注册表 ────────────────────────────────────────────

def get_perception_tools(db: Session) -> dict[str, Any]:
    """感知 Agent 可用的工具。"""
    return {
        "get_mood_history": lambda **kw: get_mood_history(db, **kw),
        "get_latest_mood": lambda **kw: get_latest_mood(db, **kw),
        "get_chat_summary": lambda **kw: get_chat_summary(db, **kw),
        "analyze_activity_pattern": lambda **kw: analyze_activity_pattern(**kw),
        "detect_crisis": lambda **kw: detect_crisis(**kw),
    }


def get_companion_tools(db: Session) -> dict[str, Any]:
    """陪伴 Agent 可用的工具（环境控制 + 活动推荐）。"""
    return {
        "set_island_weather": lambda **kw: set_island_weather(db, **kw),
        "trigger_pet_action": lambda **kw: trigger_pet_action(db, **kw),
        "show_toast": lambda **kw: show_toast(db, **kw),
        "recommend_activity": lambda **kw: recommend_activity(db, **kw),
    }


def get_reporter_tools(db: Session) -> dict[str, Any]:
    """报告 Agent 可用的工具。"""
    return {
        "build_report_data": lambda **kw: build_report_data(db, **kw),
        "get_mood_history": lambda **kw: get_mood_history(db, **kw),
    }
