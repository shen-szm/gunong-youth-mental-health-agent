"""
情绪记录API路由 - 情绪数据查询与统计
"""
import json
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from database import get_db
from models import ChatMessage, MoodRecord, StudentConversationSummary, User
from auth import ensure_user_scope, get_current_user, require_real_user
from app_time import china_day_start_naive, china_now_naive
from config import settings

router = APIRouter(prefix="/api/mood", tags=["mood"])


class MoodRecordInput(BaseModel):
    user_id: int
    label: str
    score: int
    content: str = ""


class ActivityReflectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    activity: str = Field(pattern=r"^(garden|fishing|happiness|pet)$")
    feeling: str = Field(pattern=r"^(lighter|same|energized|more_tense)$")
    note: str = Field(default="", max_length=120)


@router.post("/activity-reflection")
async def record_activity_reflection(data: ActivityReflectionInput,
                                     db: Session = Depends(get_db),
                                     current_user: User = Depends(require_real_user)):
    labels = {
        "lighter": ("轻松一些", 6),
        "same": ("差不多", 5),
        "energized": ("更有精神", 7),
        "more_tense": ("更紧绷", 3),
    }
    activity_names = {"garden": "岛屿种植", "fishing": "岛屿钓鱼", "happiness": "幸福交换", "pet": "宠物陪伴"}
    label, score = labels[data.feeling]
    content = f"{activity_names[data.activity]}结束后的主动自评"
    if data.note.strip():
        content += f"：{data.note.strip()}"
    row = MoodRecord(user_id=current_user.id, mood_label=label, mood_score=score,
                     content=content, input_type="activity", created_at=china_now_naive())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "label": label, "source": "student_activity_reflection"}


@router.get("/report")
async def get_emotion_report(days: int = 30, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    """汇总学生主动记录、受约束对话识别和倾诉小结，不输出诊断或虚假精度。"""
    days = min(max(days, 7), 30)
    since = china_now_naive() - timedelta(days=days)
    moods = db.query(MoodRecord).filter(
        MoodRecord.user_id == current_user.id, MoodRecord.created_at >= since
    ).order_by(MoodRecord.created_at.asc()).all()
    chats = db.query(ChatMessage).filter(
        ChatMessage.user_id == current_user.id,
        ChatMessage.role == "user",
        ChatMessage.created_at >= since,
    ).order_by(ChatMessage.created_at.asc()).all()
    summary_row = db.query(StudentConversationSummary).filter(
        StudentConversationSummary.user_id == current_user.id,
        StudentConversationSummary.expires_at > datetime.utcnow(),
    ).order_by(StudentConversationSummary.generated_at.desc()).first()

    distribution = {}
    timeline = []
    for item in moods:
        distribution[item.mood_label] = distribution.get(item.mood_label, 0) + 1
        timeline.append({
            "time": item.created_at.isoformat() if item.created_at else None,
            "emotion": item.mood_label,
            "source": "活动后主动反馈" if item.input_type == "activity" else "主动心情记录",
        })
    for item in chats:
        if not item.emotion or item.emotion == "需要立即协助":
            continue
        distribution[item.emotion] = distribution.get(item.emotion, 0) + 1
        timeline.append({
            "time": item.created_at.isoformat() if item.created_at else None,
            "emotion": item.emotion,
            "source": "倾诉对话线索",
        })
    timeline = sorted(timeline, key=lambda row: row["time"] or "")[-12:]
    latest_summary = None
    if summary_row:
        try:
            latest_summary = json.loads(summary_row.summary_json)
        except (TypeError, ValueError):
            latest_summary = None
    ordered = sorted(distribution.items(), key=lambda item: (-item[1], item[0]))
    if latest_summary:
        overview = latest_summary.get("summary", "近期倾诉已经完成一次非诊断性整理。")
        support_focus = latest_summary.get("support_need", "先被认真听见，再决定一个负担较小的下一步。")
        next_steps = latest_summary.get("next_steps", [])[:3]
    elif ordered:
        overview = f"近{days}天记录中较常出现的是“{ordered[0][0]}”。这只反映已记录内容，不代表完整心理状态。"
        support_focus = "结合当时发生的事情回看变化，并保留自己主动修正标签的权利。"
        next_steps = ["选择一条最想补充的记录，写下当时发生了什么", "如果不适持续影响生活，告诉一位可信成年人"]
    else:
        overview = "目前还没有足够的主动记录或对话线索生成回顾。"
        support_focus = "从一次主动心情记录、一次倾诉或一次活动后自评开始。"
        next_steps = ["记录此刻最接近的感受，也可以选择暂不确定"]
    return {
        "period_days": days,
        "generated_at": china_now_naive().isoformat(),
        "sources": {
            "self_records": len(moods),
            "conversation_signals": len([row for row in chats if row.emotion]),
            "conversation_summary": bool(latest_summary),
        },
        "distribution": dict(ordered),
        "timeline": timeline,
        "overview": overview,
        "support_focus": support_focus,
        "next_steps": next_steps,
        "latest_conversation": latest_summary,
        "boundary": "这是基于主动记录与对话线索的非诊断性回顾，不是心理测评或医学结论。",
    }


@router.post("/record")
async def record_mood(data: MoodRecordInput, db: Session = Depends(get_db), current_user: User = Depends(require_real_user)):
    ensure_user_scope(data.user_id, current_user)
    """记录一条情绪"""
    record = MoodRecord(
        user_id=data.user_id,
        mood_label=data.label,
        mood_score=data.score,
        content=data.content,
        created_at=china_now_naive(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"msg": "记录成功", "id": record.id}


@router.get("/today")
async def get_today_mood(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_user_scope(user_id, current_user)
    """获取今日情绪记录"""
    today_start = china_day_start_naive()
    record = db.query(MoodRecord).filter(
        MoodRecord.user_id == user_id,
        MoodRecord.created_at >= today_start
    ).order_by(MoodRecord.created_at.desc()).first()

    if not record:
        return {"label": None, "score": None}

    return {"label": record.mood_label, "score": record.mood_score}

@router.get("/list")
async def get_mood_list(user_id: int, days: int = 30, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_user_scope(user_id, current_user)
    """获取情绪记录列表"""
    since = china_now_naive() - timedelta(days=days)
    records = db.query(MoodRecord).filter(
        MoodRecord.user_id == user_id,
        MoodRecord.created_at >= since
    ).order_by(MoodRecord.created_at.asc()).all()

    return [{
        "id": r.id,
        "score": r.mood_score,
        "label": r.mood_label,
        "content": r.content,
        "date": r.created_at.strftime("%Y-%m-%d"),
        "time": r.created_at.strftime("%H:%M"),
    } for r in records]

@router.get("/stats")
async def get_mood_stats(user_id: int, days: int = 7, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_user_scope(user_id, current_user)
    """获取情绪统计数据"""
    since = china_now_naive() - timedelta(days=days)
    records = db.query(MoodRecord).filter(
        MoodRecord.user_id == user_id,
        MoodRecord.created_at >= since
    ).all()

    if not records:
        return {"count": 0, "recorded_days": 0, "distribution": {}, "trend": []}

    # 情绪分布
    dist = {}
    for r in records:
        dist[r.mood_label] = dist.get(r.mood_label, 0) + 1

    # 按日呈现学生主动选择的标签，不计算未经验证的平均心理分。
    daily = {}
    for r in records:
        day = r.created_at.strftime("%m-%d")
        daily.setdefault(day, []).append(r.mood_label)
    trend = [{"date": day, "labels": list(dict.fromkeys(labels)), "count": len(labels)} for day, labels in sorted(daily.items())]

    return {
        "count": len(records),
        "recorded_days": len(daily),
        "distribution": dist,
        "trend": trend,
    }

@router.get("/insight")
async def get_ai_insight(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_user_scope(user_id, current_user)
    """生成基于主动标签的描述性洞察，不把自由文本未经同意发送给外部模型。"""

    # 获取最近7天情绪记录
    since = china_now_naive() - timedelta(days=7)
    records = db.query(MoodRecord).filter(
        MoodRecord.user_id == user_id,
        MoodRecord.created_at >= since
    ).order_by(MoodRecord.created_at.asc()).all()

    if not records:
        return {"insight": "开始记录你的情绪吧，咕哝会在这里给你温暖的洞察~"}

    labels = [record.mood_label for record in records]
    common = max(set(labels), key=labels.count)
    return {
        "insight": f"过去7天共主动记录{len(records)}次，较常出现的是“{common}”。可以结合当时发生的事情回看变化；这只描述已记录内容，不代表完整心理状态。",
        "analysis_source": "descriptive_records",
    }
