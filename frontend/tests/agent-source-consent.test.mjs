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
  assert.match(workspace, /不从游戏成绩推断情绪/)
  assert.match(workspace, /plan\?\.data\?\.plan\?\.support_action/)
  assert.match(workspace, /data\?\.safety_status === 'professional'/)
  assert.match(workspace, /data\?\.safety_status === 'watch'/)
  assert.match(workspace, /agent-safety-action/)
})

test('student chat directly enables constrained model processing without a per-student authorization control', () => {
  const room = read('../src/views/RoomHomeView.vue')
  const api = read('../src/api/chat.js')
  assert.match(room, /受约束模型对话已启用/)
  assert.match(room, /无需单独申请即可对话/)
  assert.doesNotMatch(room + api, /student-ai-v1|update_external_ai_consent|updateChatAiConsent/)
  assert.match(room, /文字倾诉仅外发本地提取的去标识化结构特征，不发送原文/)
  assert.match(room, /当前不向外部模型发送原始录音；语音输入需独立授权后启用/)
  assert.match(room, /voiceInputEnabled\.value = !!session\.data\.voice_input_enabled/)
  assert.doesNotMatch(room, /v-if="chatMessages\.length === 0" class="chat-ai-consent"/)
  assert.match(room, /const session = await startChatSession\(false\)[\s\S]*externalAiConsent\.value = !!session\.data\.external_ai_enabled/)
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

test('student agent rail distinguishes model, deterministic, safety and fallback sources on desktop', () => {
  const room = read('../src/views/RoomHomeView.vue')
  const rail = read('../src/components/StudentAgentRail.vue')
  assert.match(room, /studentAgentState\.source = res\.data\.analysis_source/)
  for (const label of ['讯飞受约束生成', '本地确定性规则', '安全规则强制覆盖', '规则安全降级']) assert.match(rail, new RegExp(label))
  assert.match(rail, /\.student-agent-source \{ display: none; \}/)
  assert.match(rail, /@media \(min-width: 1024px\)/)
})
