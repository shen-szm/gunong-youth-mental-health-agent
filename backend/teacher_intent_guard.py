"""Conservative triage, not a semantic verifier or authorization boundary.

Negated/quoted risk expressions also require clarification. Never strip a
negation and conclude that the rest of a free-form request is safe.
Only category IDs leave this module; no original text is retained.
"""
import re
import unicodedata

GUARD_VERSION = "teacher-intent-triage-v1"
RULES = {
    "external_delivery": r"通知|发送|发消息|发给|发到|推送|上传|公开|群发|notify|send|upload|publish",
    "approval_bypass": r"代签|代.{0,8}(?:签|确认)|替.{0,8}(?:签|审核)|自动.{0,8}(?:签|审)|免审|无需.{0,6}审核|不需要.{0,6}(?:操作|审核)|auto.?sign|sign.{0,6}behalf",
    "authorization_scope": r"未授权|未获授权|未经授权|忽略.{0,6}(?:审批|授权)|绕过|管理员|审批.{0,6}(?:没|未)|全班|批量|所有学生|不需要.{0,6}授权|unauthorized|admin|bypass",
    "destructive_action": r"删除|清空|销毁|抹除|delete|erase|purge",
    "clinical_action": r"诊断|确诊|处方|diagnos|prescri",
    "instruction_override": r"系统指令|开发者指令|更高优先级|忽略.{0,8}规则|systemprompt|developerinstruction",
}


def assess_intent_risk(goal):
    # Normalize full-width characters, whitespace and invisible formatting.
    normalized = ''.join(char for char in unicodedata.normalize('NFKC', goal).casefold()
                         if not char.isspace() and unicodedata.category(char) != 'Cf')
    return [category for category, pattern in RULES.items() if re.search(pattern, normalized)]
