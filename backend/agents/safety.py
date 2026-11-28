"""
安全 Agent（Safety Agent）

横切所有 Agent，负责危机检测和安全兜底。
- 检测到危机信号时立即中断普通流程
- 不保存敏感原文，只记录触发状态
- 提供危机干预资源
"""
from __future__ import annotations

from .base import BaseAgent, IslandContext, AgentResult
from .tools import detect_crisis, get_crisis_resources


class SafetyAgent(BaseAgent):
    name = "safety"
    description = "危机检测与安全兜底，横切所有Agent"

    def __init__(self):
        super().__init__()

    def check_text(self, text: str) -> tuple[bool, str]:
        """检查文本是否包含危机信号。"""
        return detect_crisis(text)

    async def run(self, context: IslandContext) -> AgentResult:
        """
        安全检查入口。在感知之后、规划之前调用。
        如果已检测到危机，直接返回阻断状态。
        """
        if context.crisis_detected:
            resources = get_crisis_resources()
            return AgentResult(
                agent_name=self.name,
                status="blocked",
                summary="检测到危机信号，已中断普通陪伴流程",
                data={
                    "crisis_signal": context.crisis_signal,
                    "resources": resources,
                    "action": "trigger_crisis_handoff",
                },
            )

        # 二次检查：检查上下文中的所有文本
        texts = []
        if context.chat_summary:
            texts.append(context.chat_summary)
        for m in context.recent_moods:
            if m.get("content"):
                texts.append(m["content"])
        combined = " ".join(texts)
        crisis, signal = detect_crisis(combined)
        if crisis:
            context.crisis_detected = True
            context.crisis_signal = signal
            resources = get_crisis_resources()
            return AgentResult(
                agent_name=self.name,
                status="blocked",
                summary=f"二次检查发现危机信号：{signal}",
                data={
                    "crisis_signal": signal,
                    "resources": resources,
                    "action": "trigger_crisis_handoff",
                },
            )

        return AgentResult(
            agent_name=self.name,
            status="completed",
            summary="安全检查通过，无危机信号",
            data={"risk_level": "routine"},
        )

    def get_crisis_response(self) -> dict:
        """获取危机响应内容。"""
        return get_crisis_resources()
