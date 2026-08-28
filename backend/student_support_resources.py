"""Small, auditable support-resource registry used by the student orchestrator."""

from __future__ import annotations


NHC_12356_SOURCE = "https://www.nhc.gov.cn/yzygj/c100068/202412/49a1a65386cd4be582d4702fd0926ee8.shtml"


def route_support_resources(risk_level: str) -> list[dict[str, str]]:
    """Return only nationally stable routes; never invent a local institution."""
    resources: list[dict[str, str]] = []
    if risk_level in {"watch", "professional", "urgent"}:
        resources.append({
            "id": "trusted-adult",
            "title": "可信成年人支持",
            "action": "联系一位不涉事的家长、教师或其他可信成年人并说明现在需要陪伴",
            "source": "safety-policy",
        })
    if risk_level in {"professional", "urgent"}:
        resources.append({
            "id": "12356",
            "title": "12356 心理援助热线",
            "action": "拨打 12356 获得心理支持与求助导航",
            "source": NHC_12356_SOURCE,
        })
    if risk_level == "urgent":
        resources.extend([
            {"id": "110", "title": "公安报警 110", "action": "危险正在发生时立即拨打 110", "source": "national-emergency-number"},
            {"id": "120", "title": "医疗急救 120", "action": "需要紧急医疗帮助时立即拨打 120", "source": "national-emergency-number"},
        ])
    return resources
