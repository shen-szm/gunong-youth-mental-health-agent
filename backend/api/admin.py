"""
管理员路由 - 用户管理、数据统计
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import User, MoodRecord, ChatMessage, SensitiveAccessLog, StudentCaseAccessRequest, TeacherStudentAssignment, UserSession
from config import settings
from auth import require_admin, require_admin_teacher

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/stats")
def get_stats(user_id: int | None = None, db: Session = Depends(get_db), current_admin: User = Depends(require_admin)):
    from datetime import datetime, timedelta
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_mood = db.query(MoodRecord).filter(MoodRecord.created_at >= today_start).count()
    today_users = db.query(User).filter(User.created_at >= today_start).count()
    return {
        "user_count": db.query(User).count(),
        "mood_count": db.query(MoodRecord).count(),
        "chat_count": db.query(ChatMessage).count(),
        "today_mood_count": today_mood,
        "today_users": today_users,
    }

@router.get("/users")
def get_users(user_id: int | None = None, page: int = 1, size: int = 20, db: Session = Depends(get_db), current_admin: User = Depends(require_admin_teacher)):
    total = db.query(User).count()
    users = db.query(User).order_by(User.id.desc()).offset((page - 1) * size).limit(size).all()
    enriched_users = []
    for u in users:
        mood_records = db.query(MoodRecord).filter(MoodRecord.user_id == u.id).all()
        latest_mood = db.query(MoodRecord).filter(MoodRecord.user_id == u.id).order_by(MoodRecord.created_at.desc()).first()
        mood_count = len(mood_records)
        avg_mood_score = round(sum(m.mood_score for m in mood_records) / mood_count, 1) if mood_count else 0
        enriched_users.append({
            "id": u.id,
            "username": u.username,
            "nickname": u.nickname,
            "is_admin": bool(u.is_admin),
            "created_at": str(u.created_at),
            "mood_count": mood_count,
            "avg_mood_score": avg_mood_score,
            "latest_mood_label": latest_mood.mood_label if latest_mood else "",
            "latest_mood_score": latest_mood.mood_score if latest_mood else 0,
            "latest_mood_at": latest_mood.created_at.isoformat() if latest_mood and latest_mood.created_at else "",
        })
    return {
        "users": enriched_users,
        "total": total,
    }

@router.post("/set-admin/{target_user_id}")
def set_admin(target_user_id: int, user_id: int | None = None, db: Session = Depends(get_db), current_admin: User = Depends(require_admin_teacher)):
    from api.companion import clear_companion_context_for_user
    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if int(target.is_admin or 0) >= 2:
        raise HTTPException(status_code=400, detail="不能通过兼容接口修改管理员教师")
    before = int(target.is_admin or 0)
    target.is_admin = 1 if not target.is_admin else 0
    # 角色变化后必须重新认证，避免旧学生会话在提权后立即继承教师权限。
    clear_companion_context_for_user(target.id, db)
    db.query(UserSession).filter(UserSession.user_id == target.id).delete(synchronize_session=False)
    if not target.is_admin:
        db.query(TeacherStudentAssignment).filter(TeacherStudentAssignment.teacher_user_id == target.id).update({"active": 0})
        db.query(StudentCaseAccessRequest).filter(
            StudentCaseAccessRequest.teacher_user_id == target.id,
            StudentCaseAccessRequest.status.in_(["pending", "approved"]),
        ).update({"status": "revoked", "expires_at": None, "review_note": "教师角色已撤销"}, synchronize_session=False)
    db.commit()
    db.add(SensitiveAccessLog(actor_user_id=current_admin.id, action="update_account_role", resource_type="user", resource_id=str(target.id), result=f"allowed_{before}_to_{target.is_admin}"))
    db.commit()
    action = "设为教师" if target.is_admin else "取消教师"
    return {"msg": f"已将 {target.username} {action}"}

@router.delete("/users/{target_user_id}")
def delete_user(target_user_id: int, user_id: int | None = None, db: Session = Depends(get_db), current_admin: User = Depends(require_admin_teacher)):
    raise HTTPException(
        status_code=410,
        detail="账号硬删除已禁用，请使用受审计的停用流程",
    )

@router.get("/chats")
def get_chats(user_id: int | None = None, limit: int = 500, db: Session = Depends(get_db), current_admin: User = Depends(require_admin_teacher)):
    db.add(SensitiveAccessLog(actor_user_id=current_admin.id, action="list_chat_content", resource_type="chat", resource_id="recent", result="denied_bulk_export"))
    db.commit()
    raise HTTPException(status_code=410, detail="批量聊天原文接口已停用，请从单个支持工单按审计范围查看")


@router.get("/user-detail/{target_user_id}")
def get_user_detail(target_user_id: int, user_id: int | None = None, days: int = Query(30, ge=1, le=30), db: Session = Depends(get_db), current_admin: User = Depends(require_admin_teacher)):
    """获取用户详情：基本信息 + 心情趋势 + 情绪分布 + 高频词"""
    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if int(target.is_admin or 0) >= 2:
        raise HTTPException(status_code=400, detail="不能删除管理员教师")
    db.add(SensitiveAccessLog(actor_user_id=current_admin.id, action="view_user_detail", resource_type="user", resource_id=str(target_user_id), result="allowed"))
    db.commit()

    from datetime import datetime, timedelta

    # ── 基本信息 ──
    total_moods = db.query(MoodRecord).filter(MoodRecord.user_id == target_user_id).count()
    total_chats = db.query(ChatMessage).filter(ChatMessage.user_id == target_user_id).count()
    first_chat = db.query(ChatMessage).filter(ChatMessage.user_id == target_user_id).order_by(ChatMessage.created_at.asc()).first()
    use_days = 0
    if first_chat:
        use_days = (datetime.now() - first_chat.created_at).days + 1

    # ── 主动记录变化（按日次数与常见标签，不输出分数） ──
    since = datetime.now() - timedelta(days=days)
    moods = db.query(MoodRecord).filter(
        MoodRecord.user_id == target_user_id,
        MoodRecord.created_at >= since
    ).order_by(MoodRecord.created_at.asc()).all()

    daily = {}
    for m in moods:
        day = m.created_at.strftime("%m-%d")
        bucket = daily.setdefault(day, {"count": 0, "labels": {}})
        bucket["count"] += 1
        bucket["labels"][m.mood_label] = bucket["labels"].get(m.mood_label, 0) + 1
    trend = [
        {
            "date": day,
            "count": bucket["count"],
            "dominant_label": max(bucket["labels"], key=bucket["labels"].get),
        }
        for day, bucket in sorted(daily.items())
    ]

    # ── 情绪分布 ──
    dist = {}
    for m in moods:
        dist[m.mood_label] = dist.get(m.mood_label, 0) + 1

    # ── 高频词（词云数据） ──
    import re
    from collections import Counter

    # 中文停用词
    stop_words = set("的 了 是 在 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着 没有 看 好 自己 这 他 她 它 们 那 些 么 什么 被 让 把 给 从 对 与 而 但 又 还 吧 啊 呢 吗 哦 嗯 嗯呀 哈 嘿 哇 么 地 得 过 能 做 想 知道 觉得 可以 这个 那个 然后 所以 因为 如果 虽然 但是 或者 就是 已经 可能 应该 需要 没有 只是 这样 那些 现在 怎么 什么 为什".split())

    all_texts = []
    # 从情绪记录中取内容
    mood_texts = [m.content for m in moods if m.content]
    all_texts.extend(mood_texts)
    # 从聊天记录中取用户消息
    if days >= 30:
        chat_limit = 200
    else:
        chat_limit = 100
    user_msgs = db.query(ChatMessage).filter(
        ChatMessage.user_id == target_user_id,
        ChatMessage.role == "user",
        ChatMessage.created_at >= since
    ).order_by(ChatMessage.created_at.desc()).limit(chat_limit).all()
    all_texts.extend([c.content for c in user_msgs])

    # 分词并统计
    word_counter = Counter()
    for text in all_texts:
        # 提取中文词（2字以上）
        words = re.findall(r'[\u4e00-\u9fa5]{2,}', text)
        for w in words:
            if w not in stop_words:
                word_counter[w] += 1

    word_cloud = [{"word": w, "count": c} for w, c in word_counter.most_common(50)]

    return {
        "user": {
            "id": target.id,
            "username": target.username,
            "nickname": target.nickname,
            "is_admin": bool(target.is_admin),
            "created_at": str(target.created_at),
        },
        "stats": {
            "total_moods": total_moods,
            "total_chats": total_chats,
            "use_days": use_days,
            "record_window_days": days,
        },
        "trend": trend,
        "distribution": dist,
        "word_cloud": word_cloud,
    }


@router.get("/user-analysis/{target_user_id}")
async def get_user_analysis(target_user_id: int, user_id: int | None = None, db: Session = Depends(get_db), current_admin: User = Depends(require_admin_teacher)):
    """整理已有主动记录，供管理员教师结合线下观察复核。"""
    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    db.add(SensitiveAccessLog(actor_user_id=current_admin.id, action="generate_user_analysis", resource_type="user", resource_id=str(target_user_id), result="allowed"))
    db.commit()

    from datetime import datetime, timedelta

    # 获取最近30天数据
    since = datetime.now() - timedelta(days=30)
    moods = db.query(MoodRecord).filter(
        MoodRecord.user_id == target_user_id,
        MoodRecord.created_at >= since
    ).order_by(MoodRecord.created_at.asc()).all()

    if not moods:
        return {
            "analysis": "近30天暂无足够主动记录。当前不能形成可靠摘要，建议以学生意愿和线下观察为准。",
            "degraded": True,
            "source": "deterministic_record_registry",
            "version": "teacher-record-summary-v1",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }

    from collections import Counter
    dist = Counter(m.mood_label for m in moods)
    dist_str = "、".join([f"{label}({count}次)" for label, count in dist.most_common()])
    return {
        "analysis": (
            f"记录摘要：近30天共存在{len(moods)}次学生主动记录，已记录标签分布为{dist_str}。"
            "需要核对：这些内容只覆盖学生主动留下的片段，不能代表其完整心理状态，需要与学生意愿和线下观察相互印证。"
            "行动草案：先进行一次低压力关怀并询问学生希望获得的支持；如出现明确安全风险，立即按校园危机流程升级。"
            "不得据此作医学、纪律或人格判断。聊天正文和昵称不会通过该接口发送给第三方。"
        ),
        "degraded": True,
        "source": "deterministic_record_registry",
        "version": "teacher-record-summary-v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
