"""教师最终评审报告 PDF 渲染。"""

from html import escape
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _font_name() -> str:
    for path in (Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/simhei.ttf")):
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont("TeacherReviewCN", str(path), subfontIndex=0))
                return "TeacherReviewCN"
            except Exception:
                continue
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    return "STSong-Light"


def _p(text, style):
    return Paragraph(escape(str(text or "")).replace("\n", "<br/>"), style)


def _bullets(items, style):
    story = []
    for item in items:
        text = item if isinstance(item, str) else item.get("title") or item.get("item") or item.get("factor") or str(item)
        story.extend([Paragraph(f'<font color="#3D6B5E">●</font>&nbsp;&nbsp;{escape(str(text))}', style), Spacer(1, 1.4 * mm)])
    return story


def generate_teacher_review_pdf(report: dict) -> bytes:
    buffer = BytesIO()
    font = _font_name()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=15 * mm,
        bottomMargin=16 * mm,
        title=f"咕哝教师最终评审报告-{report.get('report_id', '')}",
        author="咕哝 AI 辅助系统",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("TRTitle", parent=styles["Title"], fontName=font, fontSize=20, leading=28, textColor=colors.HexColor("#263D36"), alignment=TA_CENTER, spaceAfter=4 * mm)
    subtitle = ParagraphStyle("TRSub", parent=styles["Normal"], fontName=font, fontSize=8.7, leading=13, textColor=colors.HexColor("#66746F"), alignment=TA_CENTER, spaceAfter=6 * mm)
    heading = ParagraphStyle("TRHeading", parent=styles["Heading2"], fontName=font, fontSize=13, leading=19, textColor=colors.HexColor("#315F53"), spaceBefore=4 * mm, spaceAfter=2 * mm)
    body = ParagraphStyle("TRBody", parent=styles["BodyText"], fontName=font, fontSize=9.5, leading=15.5, textColor=colors.HexColor("#34443F"), spaceAfter=2 * mm)
    small = ParagraphStyle("TRSmall", parent=body, fontSize=8, leading=12, textColor=colors.HexColor("#687771"))

    overall = report.get("overall_decision") or {}
    risk = overall.get("risk_level", "routine")
    risk_style = {
        "routine": ("#E8F3EE", "#315E51"),
        "watch": ("#FFF3CE", "#7A5A12"),
        "professional": ("#FBE7D9", "#8C4528"),
        "urgent": ("#F9DFDC", "#8E302A"),
    }[risk]
    status_label = {"draft": "待教师审核", "reviewed": "教师已签署", "revision_requested": "待修订"}.get(report.get("status"), report.get("status"))
    story = [
        _p(report.get("title"), title),
        _p(f"报告 {report.get('report_id')}　|　版本 {report.get('report_version')}　|　状态 {status_label}　|　AI辅助、教师审核", subtitle),
        Table([[_p(f"{overall.get('risk_label')} · {overall.get('priority')}　{overall.get('decision')}", body)]], colWidths=[176 * mm], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(risk_style[0])),
            ("BOX", (0, 0), (-1, -1), .8, colors.HexColor(risk_style[1])),
            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ])),
        _p("一、执行摘要", heading),
        _p(report.get("executive_summary"), body),
        _p(report.get("boundary"), small),
        _p("二、数据范围与质量", heading),
    ]
    scope = report.get("data_scope") or {}
    scope_rows = [
        ["观察时间窗", f"{scope.get('period_start')} 至 {scope.get('content_cutoff')}"],
        ["访问依据", scope.get("access_basis")],
        ["记录来源", "、".join(f"{k}{v}条" for k, v in (scope.get("source_counts") or {}).items()) or "暂无"],
        ["信息质量", scope.get("quality")],
        ["原文外传", "未发送给外部模型"],
    ]
    story.append(Table([[_p(a, small), _p(b, body)] for a, b in scope_rows], colWidths=[34 * mm, 142 * mm], style=TableStyle([
        ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#CCD8D3")), ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EFF4F1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ])))
    story.extend([_p("信息缺口", heading), *_bullets(scope.get("information_gaps") or ["当前未记录额外信息缺口"], body)])

    context = report.get("context_review") or {}
    story.extend([_p("三、功能影响、风险与保护因素", heading)])
    for item in context.get("functioning") or []:
        story.append(_p(f"{item.get('domain')} · {item.get('level')}：{item.get('observation')}", body))
    story.extend([_p("风险因素", heading), *_bullets(context.get("risk_factors") or [], body), _p("保护因素", heading), *_bullets(context.get("protective_factors") or [], body)])

    plan = report.get("support_plan") or {}
    if risk == "urgent":
        safety = report.get("safety_review") or {}
        story.extend([PageBreak(), _p("四、立即安全处置（普通支持计划已停止）", heading), *_bullets(safety.get("immediate_actions") or [], body), _p("升级阈值", heading), *_bullets(safety.get("escalation_thresholds") or [], body)])
    else:
        story.extend([PageBreak(), _p("四、教师支持计划", heading), _p(f"建议开场：{plan.get('conversation_opening')}", body), _p("行动任务", heading), *_bullets(plan.get("tasks") or [], body), _p("建议询问", heading), *_bullets(plan.get("questions") or [], body), _p("需要避免", heading), *_bullets(plan.get("avoid") or [], body)])
        if plan.get("follow_up"):
            story.extend([_p("回访安排", heading), *_bullets([f"第{item.get('day')}天：{item.get('focus')}" for item in plan.get("follow_up")], body)])

    agent = report.get("agent_review") or {}
    story.extend([_p("五、Agent 执行与交叉审查", heading)])
    agent_rows = [[_p("Agent", small), _p("工具", small), _p("结果", small)]]
    for step in agent.get("workflow") or []:
        agent_rows.append([_p(step.get("agent"), body), _p(step.get("tool"), small), _p(step.get("result"), small)])
    story.append(Table(agent_rows, colWidths=[36 * mm, 49 * mm, 91 * mm], repeatRows=1, style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8F1ED")), ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#C7D6D0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ])))

    audit = report.get("evidence_audit") or {}
    story.extend([
        _p("六、结论—证据可追溯审计", heading),
        _p(f"{audit.get('label')}：{audit.get('summary')}", body),
    ])
    audit_rows = [
        ["授权记录", audit.get("record_count", 0)],
        ["已被引用", audit.get("cited_record_count", 0)],
        ["报告主张", audit.get("claim_count", 0)],
        ["未关联主张", audit.get("unlinked_claim_count", 0)],
    ]
    story.append(Table([[_p(a, small), _p(b, body)] for a, b in audit_rows], colWidths=[45 * mm, 131 * mm], style=TableStyle([
        ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#CCD8D3")), ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EFF4F1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])))
    claim_rows = [[_p("主张", small), _p("关联依据", small)]]
    claim_status = {"record_linked": "学生记录", "guidance_linked": "权威指南", "declared_gap": "信息缺口", "unlinked": "未关联"}
    for claim in audit.get("claims") or []:
        basis = "、".join(claim.get("evidence_ids") or claim.get("guidance_codes") or []) or claim_status.get(claim.get("status"), "未关联")
        claim_rows.append([_p(f"{claim.get('claim_id')} · {claim.get('section')} · {claim.get('label')}", small), _p(f"{claim_status.get(claim.get('status'), claim.get('status'))}：{basis}", small)])
    if len(claim_rows) > 1:
        story.append(Table(claim_rows, colWidths=[116 * mm, 60 * mm], repeatRows=1, style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8F1ED")), ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#C7D6D0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])))
    story.append(_p(audit.get("boundary"), small))

    story.extend([_p("七、证据来源与适用边界", heading)])
    for source in report.get("evidence_sources") or []:
        story.append(_p(f"{source.get('code')} · {source.get('title')}（{source.get('issuer')}）\n{source.get('use')}\n{source.get('url')}", small))
    story.extend([_p("八、教师审核", heading), *_bullets([item.get("item") for item in report.get("review_checklist") or []], body), _p(f"审核意见：{report.get('review_note') or '尚未填写'}", body), _p(f"签署教师：{report.get('teacher_label')}　|　签署时间：{report.get('reviewed_at') or '尚未签署'}　|　修订号：{report.get('revision_number', 1)}", small), _p(f"内容摘要：{report.get('content_hash') or '生成后记录'}", small), _p("本报告必须由具备权限的教师核对后使用；子 Agent 工程复核不能替代持证心理专业人员正式签署。", small)])

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(font, 8)
        canvas.setFillColor(colors.HexColor("#71817B"))
        digest = (report.get("content_hash") or "")[:12]
        canvas.drawString(17 * mm, 9 * mm, f"咕哝 {report.get('report_version')} · R{report.get('revision_number', 1)} · {status_label} · {digest}")
        canvas.drawRightString(193 * mm, 9 * mm, f"第 {doc.page} 页")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
