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
    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if int(target.is_admin or 0) >= 2:
        raise HTTPException(status_code=400, detail="不能通过兼容接口修改管理员教师")
    before = int(target.is_admin or 0)
    target.is_admin = 1 if not target.is_admin else 0
    # 角色变化后必须重新认证，避免旧学生会话在提权后立即继承教师权限。
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
        detail="本地预览已禁用账号硬删除，请使用受审计的停用流程",
    )

@router.get("/chats")
def get_chats(user_id: int | None = None, limit: int = 500, db: Session = Depends(get_db), current_admin: User = Depends(require_admin_teacher)):
    db.add(SensitiveAccessLog(actor_user_id=current_admin.id, action="list_chat_content", resource_type="chat", resource_id="recent", result="allowed"))
    db.commit()
    chats = db.query(ChatMessage).order_by(ChatMessage.created_at.desc()).limit(limit).all()
    return [
        {
            "id": c.id,
            "user_id": c.user_id,
            "role": c.role,
            "content": c.content,
            "emotion": c.emotion,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in chats
    ]


@router.get("/user-detail/{target_user_id}")
def get_user_detail(target_user_id: int, user_id: int | None = None, days: int = 30, db: Session = Depends(get_db), current_admin: User = Depends(require_admin_teacher)):
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

    # ── 心情趋势（按日平均分） ──
    since = datetime.now() - timedelta(days=days)
    moods = db.query(MoodRecord).filter(
        MoodRecord.user_id == target_user_id,
        MoodRecord.created_at >= since
    ).order_by(MoodRecord.created_at.asc()).all()

    daily = {}
    for m in moods:
        day = m.created_at.strftime("%m-%d")
        daily.setdefault(day, []).append(m.mood_score)
    trend = [{"date": d, "avg": round(sum(s) / len(s), 1)} for d, s in sorted(daily.items())]

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
            "avg_score": round(sum(m.mood_score for m in moods) / len(moods), 1) if moods else 0,
        },
        "trend": trend,
        "distribution": dist,
        "word_cloud": word_cloud,
    }


@router.get("/user-analysis/{target_user_id}")
async def get_user_analysis(target_user_id: int, user_id: int | None = None, db: Session = Depends(get_db), current_admin: User = Depends(require_admin_teacher)):
    """AI 心理分析：总结用户心理状态并给出建议"""
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
        return {"analysis": "该用户暂无足够数据进行分析。"}

    # 获取用户最近的对话内容
    user_msgs = db.query(ChatMessage).filter(
        ChatMessage.user_id == target_user_id,
        ChatMessage.role == "user",
        ChatMessage.created_at >= since
    ).order_by(ChatMessage.created_at.asc()).limit(30).all()

    from collections import Counter
    dist = Counter(m.mood_label for m in moods)
    dist_str = "、".join([f"{label}({count}次)" for label, count in dist.most_common()])
    avg_score = round(sum(m.mood_score for m in moods) / len(moods), 1)

    if not settings.ALLOW_EXTERNAL_AI:
        return {
            "analysis": (
                f"最近30天共记录{len(moods)}次，平均自评为{avg_score}/10；分布为{dist_str}。"
                "这是本地统计摘要，不是诊断。外部AI默认关闭，聊天正文和昵称未发送给第三方；"
                "教师只能据此提供低压力支持和必要转介，不能据此作医学或纪律判断。"
            ),
            "degraded": True,
        }

    # 构造分析提示（仅在显式开启外部AI并完成相应治理后使用）
    mood_summary = "；".join([
        f"{m.created_at.strftime('%m-%d %H:%M')}：{m.mood_label}（分数{m.mood_score}，内容：{m.content[:50] if m.content else '无'}）"
        for m in moods[-15:]
    ])

    chat_summary = " | ".join([f"{c.content[:60]}" for c in user_msgs[-10:]]) if user_msgs else "无对话记录"

    messages = [{
        "role": "user",
        "content": f"""你是心理健康教育支持工具。请基于以下有限记录整理非诊断性观察摘要，并给教师提供谨慎的支持建议。

用户信息：{target.nickname or target.username}，使用{moods[0].created_at.strftime('%Y-%m-%d')}至今
平均情绪分：{avg_score}/10
情绪分布：{dist_str}

最近情绪记录：
{mood_summary}

最近对话内容：
{chat_summary}

请从以下几个方面进行分析（共300字以内）：
1. 观察摘要：记录中出现了哪些情绪与行为变化？不得使用疾病标签。
2. 关键发现：有什么需要特别关注的问题或趋势？
3. 支持建议：给教师可执行的校内支持、最小披露和必要转介建议。必须说明AI不能替代专业评估。"""
    }]

    try:
        from xunfei.spark_api import ask_spark
        analysis = await ask_spark(messages, max_tokens=500, temperature=0.7)
        if not analysis:
            analysis = "AI 分析暂时不可用，请稍后重试。"
    except Exception as e:
        analysis = f"AI 分析出错：{str(e)}"

    return {"analysis": analysis}
