"""
心岛守护者多智能体系统

5个Agent协同：感知 → 安全 → 规划 → 陪伴 → 报告
游戏环境是Agent的交互界面和执行工具。
"""
from .base import IslandContext, AgentResult, BaseAgent, Tool, ToolCall
from .orchestrator import IslandOrchestrator
from .perception import PerceptionAgent
from .safety import SafetyAgent
from .planner import PlanningAgent
from .companion_agent import CompanionAgent
from .reporter import ReportAgent

__all__ = [
    "IslandContext",
    "AgentResult",
    "BaseAgent",
    "Tool",
    "ToolCall",
    "IslandOrchestrator",
    "PerceptionAgent",
    "SafetyAgent",
    "PlanningAgent",
    "CompanionAgent",
    "ReportAgent",
]
