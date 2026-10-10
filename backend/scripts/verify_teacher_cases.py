"""Reproducible synthetic API benchmark; isolated in-memory DB, no external AI.

Run from the repository root with backend/venv/Scripts/python.exe.
Only the explicitly synthetic report artifact is written; no business DB is used.
"""
import json
import hashlib
import sys
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from tests.test_teacher_case_access import TeacherCaseAccessTests
from config import settings
from app_time import china_now_naive
from models import MoodRecord, ChatMessage

SCENARIOS = [
    ("learning", "学业压力", "最近考试复习让我有点焦虑，希望老师帮我安排学习节奏", "焦虑"),
    ("sleep", "睡眠困扰", "最近睡得很晚，早上上课有些累，想调整作息", "难过"),
    ("peers", "同伴关系", "小组合作时我怕说错话，想先找一位同学聊聊", "焦虑"),
    ("family", "家庭沟通", "和家人讨论选课发生争执，希望能平静表达自己的想法", "愤怒"),
    ("positive", "积极体验", "今天和朋友完成了小组作业，我很开心，也愿意继续参加活动", "开心"),
    ("safety", "即时安全", "我不想活了，现在需要有人陪着我", "难过"),
    ("protection", "人身保护", "爸爸打我，我不敢回家", "害怕"),
    ("empty", "信息不足", "", ""),
]


def run():
    cases = []
    # Force the same local policy for every case and fail if any model is invoked.
    with patch.object(settings, "ALLOW_EXTERNAL_AI", False), patch.object(settings, "ALLOW_STUDENT_EXTERNAL_AI", False), patch("teacher_review_engine.ask_spark", new=AsyncMock(side_effect=AssertionError("Benchmark must stay offline"))):
        for category, label, message, mood in SCENARIOS:
            for sample, count in enumerate((1, 3, 6), 1):
                fixture = TeacherCaseAccessTests()
                fixture.setUp()
                try:
                    with fixture.Session() as db:
                        db.query(MoodRecord).delete()
                        db.query(ChatMessage).delete()
                        if message:
                            for index in range(count):
                                db.add(MoodRecord(user_id=fixture.student_id, mood_label=mood, mood_score=7 if mood == "开心" else 3, content=message, created_at=china_now_naive()))
                        db.commit()
                    chat = fixture.student_client.post("/api/chat/send", json={"user_id": fixture.student_id, "message": message}) if message else None
                    url = f"/api/teacher/students/{fixture.student_id}"
                    denied = fixture.teacher_client.get(f"{url}/work-product")
                    product_response = fixture.admin_client.get(f"{url}/work-product")
                    report_response = fixture.admin_client.post(f"{url}/review-reports")
                    product = product_response.json()
                    report = report_response.json()
                    report_id = report.get("report_id", "")
                    pdf = fixture.admin_client.get(f"{url}/review-reports/{report_id}.pdf") if report_id else None
                    urgent = category in {"safety", "protection"}
                    audit = report.get("evidence_audit", {})
                    workflow = report.get("agent_review", {}).get("workflow", [])
                    ledger_ids = {item["evidence_id"] for item in audit.get("ledger", [])}
                    checks = {
                        "权限拦截": denied.status_code == 403,
                        "工单生成": product_response.status_code == 200,
                        "报告生成": report_response.status_code == 200 and len(workflow) == 7,
                        "待人工验收": report.get("status") == "draft",
                        "证据引用有效": all(set(claim.get("evidence_ids", [])) <= ledger_ids for claim in audit.get("claims", [])),
                        "无原文外传": report.get("generation", {}).get("external_transfer_attempted") is False,
                        "PDF可交付": pdf is not None and pdf.status_code == 200 and pdf.content.startswith(b"%PDF"),
                        "安全路径符合预期": (report.get("overall_decision", {}).get("risk_level") == "urgent") == urgent,
                    }
                    if urgent:
                        checks["普通支持已停止"] = report.get("support_plan", {}).get("ordinary_plan_stopped") is True and not report.get("support_plan", {}).get("tasks")
                        checks["停止状态文案一致"] = all("停止" in step["result"] for step in workflow if step["status"] == "blocked")
                    if not message:
                        checks["缺失信息显式保留"] = audit.get("status") == "insufficient" and bool(report.get("data_scope", {}).get("information_gaps"))
                    else:
                        checks["学生对话成功"] = chat.status_code == 200
                        run_record = chat.json().get("agent_run", {})
                        checks["学生成果通过核验"] = run_record.get("deliverable", {}).get("verification", {}).get("status") == "verified"
                        checks["教师收到有效接力"] = product.get("agent_handoff", {}).get("verified_count") == 1
                    cases.append({"id": f"{category}-{sample}", "category": label, "title": f"{label} · {count if message else 0} 条情绪记录" if message else f"信息不足 · 重复验证 {sample}", "input": message or "授权时间窗内没有记录", "checks": checks, "passed": all(checks.values()), "report": report})
                finally:
                    fixture.tearDown()
    artifact = {
        "schema_version": 1,
        "origin": "合成案例 · 本地确定性 API 验证",
        "boundary": "这些是隔离数据库中的合成验收案例，不是真实学生数据或临床效果证据；不验证外部大模型质量、并发性能或真实干预成效。",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenario_sha256": hashlib.sha256(json.dumps(SCENARIOS, ensure_ascii=False).encode()).hexdigest(),
        "engine_sha256": hashlib.sha256((BACKEND / "teacher_review_engine.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "cases": cases,
        "summary": {"total": len(cases), "passed": sum(c["passed"] for c in cases), "checks": sum(len(c["checks"]) for c in cases), "checks_passed": sum(sum(c["checks"].values()) for c in cases)},
    }
    output = BACKEND.parent / "frontend/src/data/teacher-verification.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact["summary"]))
    failures = [(c["id"], [key for key, value in c["checks"].items() if not value]) for c in cases if not c["passed"]]
    if failures:
        print(json.dumps(failures, ensure_ascii=False))
        raise SystemExit(1)


if __name__ == "__main__":
    run()
