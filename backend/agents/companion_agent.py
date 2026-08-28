"""
陪伴 Agent（Companion Agent）

职责：以咕团身份执行规划Agent制定的干预计划。
- 调用环境控制工具（切换昼夜/天气、触发咕团行为、显示提示）
- 生成咕团对话（大模型生成，失败降级为模板）
- 记录执行结果，更新咕团状态
"""
from __future__ import annotations

import json
import re
from datetime import datetime

from sqlalchemy.orm import Session

from .base import BaseAgent, IslandContext, AgentResult, Tool
from .tools import get_companion_tools, BREATHING_MODES
from guardian_engine import generated_content_violations


# 咕团模板回复（降级方案）
PET_TEMPLATES = {
    "greeting": [
        "咕，你来啦。今天想做点什么？",
        "咕团一直在等你呢。",
        "咕，今天的心岛很安静。",
    ],
    "comfort": [
        "咕团在这里，不用急。",
        "先深呼吸一下，咕团陪着你。",
        "今天好像有点累，咕团给你靠一会儿。",
    ],
    "happy": [
        "咕！今天心情不错呢！",
        "咕团也开心！要不要去花园看看？",
    ],
    "breathing": [
        "来，跟着咕团一起呼吸——吸……呼……",
        "慢慢吸气，4秒；屏住，7秒；慢慢呼气，8秒。",
    ],
    "beach": [
        "去沙滩走走吧，听听海浪的声音。",
        "退潮的时候沙滩上会有小贝壳哦。",
    ],
}


class CompanionAgent(BaseAgent):
    name = "companion"
    description = "以咕团身份执行干预计划，控制心岛环境"

    def __init__(self, db: Session, allow_external_ai: bool = False, transfer_start_callback=None):
        super().__init__(allow_external_ai=allow_external_ai, transfer_start_callback=transfer_start_callback)
        self.db = db
        for name, handler in get_companion_tools(db).items():
            self.register_tool(Tool(name=name, description=name, handler=handler))

    async def run(self, context: IslandContext) -> AgentResult:
        tool_calls = []
        actions_executed = []

        # 危机状态：不执行普通陪伴
        if context.crisis_detected:
            return AgentResult(
                agent_name=self.name,
                status="skipped",
                summary="危机状态下跳过普通陪伴",
                data={},
            )
        if context.risk_level == "professional":
            return AgentResult(
                agent_name=self.name,
                status="skipped",
                summary="专业支持路径下不执行普通宠物陪伴或外部模型调用",
                data={"commands_issued": 0, "llm_used": False, "model_name": "deterministic-safety"},
            )

        plan = context.intervention_plan or {"steps": []}
        steps = plan.get("steps", [])

        # 执行每一步
        for step in steps:
            action = step.get("action", "")
            params = step.get("params", {})
            result = await self._execute_step(action, params, context)
            tool_calls.extend(result.get("tool_calls", []))
            actions_executed.append(result.get("action", {}))

        # 生成咕团对话
        if context.risk_level == "watch":
            pet_message, llm_used = self._fallback_pet_message(context), False
        else:
            pet_message, llm_used = await self._generate_pet_message(context)
        context.companion_actions = actions_executed

        # 更新咕团状态
        self._update_pet_state(context)

        return AgentResult(
            agent_name=self.name,
            status="completed",
            summary=f"已执行{len(actions_executed)}步干预，咕团说：{pet_message[:30]}",
            data={
                "actions": actions_executed,
                "pet_message": pet_message,
                "commands_issued": len(actions_executed),
                "llm_used": llm_used,
                "model_name": "xunfei-constrained" if llm_used else "deterministic-template",
            },
            tool_calls=tool_calls,
        )

    async def _execute_step(self, action: str, params: dict,
                            context: IslandContext) -> dict:
        """执行单步干预。"""
        tool_calls = []
        action_result = {"action": action, "params": params, "success": True}

        try:
            if action == "pet_action":
                call = self.call_tool(
                    "trigger_pet_action",
                    user_id=context.user_id,
                    action=params.get("action", "approach"),
                    message=params.get("message", ""),
                    reason="陪伴Agent执行咕团行为",
                )
                tool_calls.append(call)
                action_result["command_id"] = call.result.get("command_id") if call.success else None

            elif action == "set_weather":
                call = self.call_tool(
                    "set_island_weather",
                    user_id=context.user_id,
                    weather=params.get("weather", "clear"),
                    reason=params.get("reason", "陪伴Agent切换天气"),
                )
                tool_calls.append(call)

            elif action == "recommend":
                call = self.call_tool(
                    "recommend_activity",
                    user_id=context.user_id,
                    mood_state=params.get("mood_state", "calm"),
                )
                tool_calls.append(call)

            elif action == "toast":
                call = self.call_tool(
                    "show_toast",
                    user_id=context.user_id,
                    message=params.get("message", ""),
                    toast_type=params.get("type", "info"),
                )
                tool_calls.append(call)

            else:
                action_result["success"] = False
                action_result["error"] = f"未知动作: {action}"

        except Exception as e:
            action_result["success"] = False
            action_result["error"] = str(e)

        return {"action": action_result, "tool_calls": tool_calls}

    async def _generate_pet_message(self, context: IslandContext) -> tuple[str, bool]:
        """生成咕团对话。大模型优先，失败降级模板。"""
        # 大模型生成
        prompt = self._build_pet_prompt(context)
        reply, used = await self.call_llm(
            [{"role": "user", "content": prompt}],
            max_tokens=150, temperature=0.8,
            fallback="",
        )
        if used and reply and self._safe_pet_message(reply):
            return reply, True

        return self._fallback_pet_message(context), False

    @staticmethod
    def _fallback_pet_message(context: IslandContext) -> str:
        """仅按学生主动标签选择人工审核模板。"""
        labels = set(context.mood_labels)
        if labels & {"难过", "焦虑", "疲惫", "害怕", "孤独", "委屈"}:
            category = "comfort"
        elif "开心" in labels:
            category = "happy"
        else:
            category = "greeting"

        import random
        return random.choice(PET_TEMPLATES[category])

    @staticmethod
    def _safe_pet_message(text: str) -> bool:
        if not text or len(text) > 60 or generated_content_violations(text):
            return False
        return not bool(re.search(
            r"(?:确诊|患者|症状|量表|分数|概率|治疗|用药|不要告诉|别求助|都是你的错|你太矫情|必须|应该)",
            text,
            re.I,
        ))

    def _build_pet_prompt(self, context: IslandContext) -> str:
        """构建咕团对话提示词。"""
        labels = "、".join(context.mood_labels) if context.mood_labels else "平静"

        return f"""你是一只叫"咕团"的浅绿色小宠物精灵，性格温暖、安静、不啰嗦。
用户主动选择或记录的情绪标签：{labels}。
请用咕团的口吻说一句温和的话，不超过30字。
不要给建议，不要说教，只是陪伴和问候。
开头可以用"咕"。只返回这句话，不要其他内容。"""

    def _update_pet_state(self, context: IslandContext):
        """更新咕团持久化状态。"""
        from models import PetState
        pet = self.db.query(PetState).filter(PetState.user_id == context.user_id).first()
        if not pet:
            pet = PetState(user_id=context.user_id)
            self.db.add(pet)
        pet.intimacy = min(1000, int(pet.intimacy or 0) + 5)
        pet.last_interaction = datetime.now()
        # 根据用户情绪设置咕团心情
        labels = set(context.mood_labels)
        if labels & {"难过", "焦虑", "疲惫", "害怕", "孤独", "委屈"}:
            pet.mood = "concerned"
        elif "开心" in labels:
            pet.mood = "happy"
        else:
            pet.mood = "content"
