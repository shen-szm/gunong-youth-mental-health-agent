"""
情绪记录API路由 - 情绪数据查询与统计
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from database import get_db
from models import MoodRecord, User
from auth import ensure_user_scope, get_current_user

router = APIRouter(prefix="/api/mood", tags=["mood"])


class MoodRecordInput(BaseModel):
    user_id: int
    label: str
    score: int
    content: str = ""


@router.post("/record")
async def record_mood(data: MoodRecordInput, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_user_scope(data.user_id, current_user)
    """记录一条情绪"""
    record = MoodRecord(
        user_id=data.user_id,
        mood_label=data.label,
        mood_score=data.score,
        content=data.content,
        created_at=datetime.now(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"msg": "记录成功", "id": record.id}


@router.get("/today")
async def get_today_mood(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_user_scope(user_id, current_user)
    """获取今日情绪记录"""
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
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
    since = datetime.now() - timedelta(days=days)
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
    since = datetime.now() - timedelta(days=days)
    records = db.query(MoodRecord).filter(
        MoodRecord.user_id == user_id,
        MoodRecord.created_at >= since
    ).all()

    if not records:
        return {"avg_score": 0, "count": 0, "distribution": {}, "trend": []}

    # 情绪分布
    dist = {}
    for r in records:
        dist[r.mood_label] = dist.get(r.mood_label, 0) + 1

    # 按日平均分
    daily = {}
    for r in records:
        day = r.created_at.strftime("%m-%d")
        daily.setdefault(day, []).append(r.mood_score)
    trend = [{"date": d, "avg": round(sum(s)/len(s), 1)} for d, s in sorted(daily.items())]

    return {
        "avg_score": round(sum(r.mood_score for r in records) / len(records), 1),
        "count": len(records),
        "distribution": dist,
        "trend": trend,
    }

@router.get("/insight")
async def get_ai_insight(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_user_scope(user_id, current_user)
    """返回本地描述性情绪回顾，不向外部模型传输学生记录。"""

    # 获取最近7天情绪记录
    since = datetime.now() - timedelta(days=7)
    records = db.query(MoodRecord).filter(
        MoodRecord.user_id == user_id,
        MoodRecord.created_at >= since
    ).order_by(MoodRecord.created_at.asc()).all()

    if not records:
        return {"insight": "开始记录你的情绪吧，咕哝会在这里给你温暖的洞察~"}

    labels = [record.mood_label for record in records]
    common = max(set(labels), key=labels.count)
    return {
        "insight": f"过去7天共记录{len(records)}次，较常出现的是“{common}”。请结合近期生活事件自行回顾，这不是心理诊断。",
        "generated_by": "local_descriptive_summary",
    }
