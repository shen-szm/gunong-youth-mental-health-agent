"""
心岛守护者多智能体系统 - 基础定义

每个 Agent 遵循统一协议：
- 接收上下文（IslandContext）
- 可调用注册的工具（Tool）
- 返回结构化结果（AgentResult）

设计原则：
1. 不做心理诊断，只描述状态和提供支持
2. 安全 Agent 横切所有 Agent，危机时立即中断
3. 大模型调用失败时降级为确定性模板
4. 所有工具调用可审计、可追溯
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Literal

from xunfei.spark_api import ask_spark, is_spark_available


# ── 工具定义 ──────────────────────────────────────────────

@dataclass
class Tool:
    """Agent 可调用的工具。"""
    name: str
    description: str
    handler: Callable[..., Any]
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    """一次工具调用记录。"""
    tool_name: str
    arguments: dict[str, Any]
    result: Any = None
    success: bool = True
    error: str = ""


# ── 上下文与结果 ──────────────────────────────────────────

@dataclass
class IslandContext:
    """在心岛 Agent 之间传递的共享上下文。"""
    user_id: int
    nickname: str = ""
    # 感知结果
    mood_labels: list[str] = field(default_factory=list)
    recent_moods: list[dict] = field(default_factory=list)
    game_behaviors: list[dict] = field(default_factory=list)
    chat_summary: str = ""
    # 行为模式
    activity_preference: str = ""            # 最常去的地点
    login_pattern: str = ""                  # 登录节律描述
    breathing_completion: float = 0.0        # 呼吸完成率
    # 安全
    crisis_detected: bool = False
    crisis_signal: str = ""
    risk_level: Literal["routine", "watch", "professional", "urgent"] = "routine"
    # 规划结果
    intervention_plan: dict | None = None
    # 陪伴执行结果
    companion_actions: list[dict] = field(default_factory=list)
    # 元信息
    triggered_at: datetime = field(default_factory=datetime.now)
    notes: list[str] = field(default_factory=list)


@dataclass
class AgentResult:
    """Agent 执行结果。"""
    agent_name: str
    status: Literal["completed", "degraded", "blocked", "skipped"]
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[ToolCall] = field(default_factory=list)
    error: str = ""


# ── Agent 基类 ────────────────────────────────────────────

class BaseAgent:
    """所有心岛 Agent 的基类。"""

    name: str = "base"
    description: str = ""

    def __init__(self, allow_external_ai: bool = False):
        self.tools: dict[str, Tool] = {}
        self.allow_external_ai = allow_external_ai

    def register_tool(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def call_tool(self, name: str, **kwargs) -> ToolCall:
        """调用注册的工具，记录调用过程。"""
        call = ToolCall(tool_name=name, arguments=kwargs)
        tool = self.tools.get(name)
        if not tool:
            call.success = False
            call.error = f"工具 {name} 未注册"
            return call
        try:
            call.result = tool.handler(**kwargs)
            call.success = True
        except Exception as e:
            call.success = False
            call.error = str(e)
        return call

    async def call_llm(self, messages: list[dict], max_tokens: int = 512,
                       temperature: float = 0.7, fallback: str = "") -> tuple[str, bool]:
        """
        调用大模型，失败时返回 fallback。
        返回 (回复内容, 是否使用了大模型)。
        """
        if not self.allow_external_ai or not is_spark_available():
            return fallback, False
        try:
            reply = await ask_spark(messages, max_tokens=max_tokens, temperature=temperature)
            if reply and reply.strip():
                return reply.strip(), True
            return fallback, False
        except Exception:
            return fallback, False

    async def run(self, context: IslandContext) -> AgentResult:
        """子类实现具体逻辑。"""
        raise NotImplementedError
