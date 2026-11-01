import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const read = path => fs.readFileSync(new URL(path, import.meta.url), 'utf8')

test('heart island exposes direct constrained model use and the actual generation source on desktop', () => {
  const workspace = read('../src/components/island/StudentIslandWorkspace.vue')
  const api = read('../src/api/island.js')
  assert.doesNotMatch(workspace + api, /student-island-ai-v1|external_ai_consent_version/)
  assert.match(workspace, /无需单独申请/)
  assert.match(workspace, /讯飞受约束生成/)
  assert.match(workspace, /安全规则强制覆盖/)
  assert.match(workspace, /@media \(min-width: 1024px\)/)
  assert.match(workspace, /不会依据游戏成绩或使用行为判断情绪/)
  assert.match(workspace, /plan\?\.data\?\.plan\?\.support_action/)
  assert.match(workspace, /data\?\.safety_status === 'professional'/)
  assert.match(workspace, /data\?\.safety_status === 'watch'/)
  assert.match(workspace, /agent-safety-action/)
})

test('student chat directly enables companion dialogue and states raw-text transfer truthfully', () => {
  const room = read('../src/views/RoomHomeView.vue')
  const chatView = read('../src/views/StudentChatView.vue')
  const api = read('../src/api/chat.js')
  assert.match(room + chatView, /DeepSeek 小满对话已启用/)
  assert.match(room + chatView, /讯飞策略协作已启用/)
  assert.match(room + chatView, /对话原文会发送给平台接入的 DeepSeek 模型，用于生成本轮回应和本次小结/)
  assert.match(room + chatView, /姓名、学校、联系方式、精确地址和原始录音不会发送/)
  assert.match(room + chatView, /危机判断与风险等级始终由本地安全规则优先处理/)
  assert.doesNotMatch(room + chatView, /小结仍只使用去标识化线索/)
  assert.match(room + chatView, /const fresh = await startChatSession\(true\)/)
  assert.doesNotMatch(room + chatView + api, /student-ai-v1|update_external_ai_consent|updateChatAiConsent/)
  assert.match(room, /voiceInputEnabled\.value = !!session\.data\.voice_input_enabled/)
  assert.doesNotMatch(room, /v-if="chatMessages\.length === 0" class="chat-ai-consent"/)
  assert.match(room, /const session = await startChatSession\(false\)[\s\S]*externalAiConsent\.value = !!session\.data\.external_ai_enabled/)
  assert.match(room, /companionEngine\.value = session\.data\.companion_engine/)
})

test('teacher work product stays local while student model access is globally governed', () => {
  const view = read('../src/views/AdminView.vue')
  const api = read('../src/api/teacher.js')
  assert.match(view, /本地确定性规则/)
  assert.match(view, /teacherGenerationLabel/)
  assert.doesNotMatch(view + api, /teacher-derived-ai-v1|teacher_data_basis|derived_narrative/)
  assert.match(view, /学生无需逐次申请或等待教师开通/)
  assert.match(api, /external-ai-authorization/)
})

test('student agent rail distinguishes companion, model, deterministic, safety and fallback sources on desktop', () => {
  const room = read('../src/views/RoomHomeView.vue')
  const rail = read('../src/components/StudentAgentRail.vue')
  assert.match(room, /studentAgentState\.source = res\.data\.analysis_source/)
  for (const label of ['DeepSeek 小满对话', '讯飞策略协作', '本地确定性规则', '安全规则强制覆盖', '规则安全降级']) assert.match(rail, new RegExp(label))
  assert.match(rail, /<details class="agent-technical-details">/)
  assert.match(rail, /本轮回应由 DeepSeek 小满对话生成/)
  assert.doesNotMatch(rail, /聊天原文不外发/)
})
