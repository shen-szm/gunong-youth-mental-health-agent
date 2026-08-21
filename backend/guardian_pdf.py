"""守护者支持方案书 PDF 生成器。"""

from io import BytesIO
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from guardian_schemas import SupportPlanOutput
from models import EvidenceSource, GuardianCase


def _font_name() -> str:
    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
    ]
    for path in candidates:
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont("GuardianCN", str(path), subfontIndex=0))
                return "GuardianCN"
            except Exception:
                continue
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    return "STSong-Light"


def _paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def _bullet_list(items: list[str], style: ParagraphStyle, accent: str = "#3D6B5E") -> list:
    result = []
    for item in items:
        result.append(Paragraph(f'<font color="{accent}">●</font>&nbsp;&nbsp;{escape(item)}', style))
        result.append(Spacer(1, 1.8 * mm))
    return result


def generate_guardian_pdf(case: GuardianCase, plan: SupportPlanOutput, evidence: list[EvidenceSource]) -> bytes:
    buffer = BytesIO()
    font = _font_name()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"咕哝守护者支持方案-{case.case_code}",
        author="咕哝 AI 辅助系统",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "GuardianTitle",
        parent=styles["Title"],
        fontName=font,
        fontSize=22,
        leading=30,
        textColor=colors.HexColor("#243B35"),
        alignment=TA_CENTER,
        spaceAfter=5 * mm,
    )
    subtitle = ParagraphStyle(
        "GuardianSubtitle",
        parent=styles["Normal"],
        fontName=font,
        fontSize=9.5,
        leading=15,
        textColor=colors.HexColor("#5E706A"),
        alignment=TA_CENTER,
        spaceAfter=7 * mm,
    )
    heading = ParagraphStyle(
        "GuardianHeading",
        parent=styles["Heading2"],
        fontName=font,
        fontSize=14,
        leading=20,
        textColor=colors.HexColor("#2E6255"),
        spaceBefore=4 * mm,
        spaceAfter=2 * mm,
    )
    body = ParagraphStyle(
        "GuardianBody",
        parent=styles["BodyText"],
        fontName=font,
        fontSize=10,
        leading=16,
        textColor=colors.HexColor("#34443F"),
        spaceAfter=2 * mm,
    )
    small = ParagraphStyle(
        "GuardianSmall",
        parent=body,
        fontSize=8.2,
        leading=12,
        textColor=colors.HexColor("#65756F"),
    )
    label, bg, ink = {
        "routine": ("日常支持", "#E8F3EE", "#315E51"),
        "watch": ("需要关注", "#FFF3CE", "#7A5A12"),
        "professional": ("尽快获得专业支持", "#FBE7D9", "#8C4528"),
        "urgent": ("立即协助", "#F9DFDC", "#8E302A"),
    }[plan.risk_level]

    story = [
        _paragraph("咕哝 · 守护者支持方案", title),
        _paragraph(
            f"工单 {case.case_code}　|　版本 {plan.release_version}　|　待专业人员审核　|　AI辅助生成",
            subtitle,
        ),
        Table(
            [[_paragraph(f"{label}　{plan.action_priority}", body)]],
            colWidths=[174 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor(ink)),
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor(ink)),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            ),
        ),
        _paragraph("一、守护者观察摘要", heading),
        _paragraph(plan.observation_summary, body),
        _paragraph("本摘要来自成人守护者的单次观察，未直接访谈青少年，也未使用标准化量表。", small),
        _paragraph("二、现在先做什么", heading),
        *_bullet_list(plan.immediate_actions, body, ink),
    ]

    if plan.seven_day_actions:
        story.extend([_paragraph("三、未来7天行动", heading), *_bullet_list(plan.seven_day_actions, body)])

    story.extend(
        [
            _paragraph("四、沟通话术参考", heading),
            *_bullet_list(plan.conversation_prompts, body, "#4C6A86"),
            _paragraph("五、需要避免", heading),
            *_bullet_list(plan.avoid_actions, body, "#A04B42"),
            _paragraph("六、可核验的求助资源", heading),
        ]
    )

    resource_rows = [[_paragraph("资源", small), _paragraph("联系与说明", small)]]
    for resource in plan.resources:
        resource_rows.append(
            [
                _paragraph(resource.name, body),
                _paragraph(
                    f"{resource.phone or '请查看来源'} · {resource.availability}\n{resource.note}\n核验：{resource.verified_at}",
                    small,
                ),
            ]
        )
    story.append(
        Table(
            resource_rows,
            colWidths=[54 * mm, 120 * mm],
            repeatRows=1,
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8F1ED")),
                    ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#C7D6D0")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            ),
        )
    )

    story.extend([_paragraph("七、证据与审查轨迹", heading)])
    evidence_by_code = {item.source_code: item for item in evidence}
    for code in plan.evidence_codes:
        source = evidence_by_code.get(code)
        if not source:
            continue
        story.append(
            KeepTogether(
                [
                    _paragraph(f"{source.title}（{source.issuer}）", body),
                    _paragraph(f"{source.summary}\n来源：{source.source_url}\n核验日期：{source.reviewed_at}", small),
                    Spacer(1, 1 * mm),
                ]
            )
        )

    if plan.disagreements:
        story.extend([_paragraph("结构化分歧", heading), *_bullet_list(plan.disagreements, body)])
    story.extend(
        [
            _paragraph("最终裁决", heading),
            _paragraph(plan.review_resolution, body),
            _paragraph("八、适用边界", heading),
            _paragraph(plan.ai_disclosure, body),
            _paragraph(plan.boundary_notice, body),
            _paragraph(
                "隐私提示：本比赛预览只允许合成数据，不收集姓名、学校、电话或精确地址；本方案未经过持证心理专家签署。",
                small,
            ),
        ]
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(font, 8)
        canvas.setFillColor(colors.HexColor("#71817B"))
        canvas.drawString(18 * mm, 10 * mm, f"咕哝 {plan.release_version} · AI辅助生成 · 待专业人员审核")
        canvas.drawRightString(192 * mm, 10 * mm, f"第 {doc.page} 页")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
