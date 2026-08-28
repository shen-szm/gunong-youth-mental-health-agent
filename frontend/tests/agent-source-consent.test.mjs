import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const read = path => fs.readFileSync(new URL(path, import.meta.url), 'utf8')

test('heart island reads teacher authorization and reports the actual generation source on desktop', () => {
  const workspace = read('../src/components/island/StudentIslandWorkspace.vue')
  const api = read('../src/api/island.js')
  assert.doesNotMatch(workspace + api, /student-island-ai-v1|external_ai_consent_version/)
  assert.match(workspace, /教师端已登记有效授权依据/)
  assert.match(workspace, /讯飞受约束生成/)
  assert.match(workspace, /安全规则强制覆盖/)
  assert.match(workspace, /@media \(min-width: 1024px\)/)
  assert.match(workspace, /不从游戏成绩推断情绪/)
  assert.match(workspace, /plan\?\.data\?\.plan\?\.support_action/)
  assert.match(workspace, /data\?\.safety_status === 'professional'/)
  assert.match(workspace, /data\?\.safety_status === 'watch'/)
  assert.match(workspace, /agent-safety-action/)
})

test('student chat displays teacher-managed processing state without a student authorization control', () => {
  const room = read('../src/views/RoomHomeView.vue')
  const api = read('../src/api/chat.js')
  assert.match(room, /教师端已启用受约束模型协作/)
  assert.match(room, /教师端尚未登记有效授权依据/)
  assert.doesNotMatch(room + api, /student-ai-v1|update_external_ai_consent|updateChatAiConsent/)
  assert.match(room, /文字倾诉仅外发本地提取的结构化特征，不发送原文/)
  assert.match(room, /语音播放会发送本次已安全校验的助手回复至讯飞/)
  assert.doesNotMatch(room, /v-if="chatMessages\.length === 0" class="chat-ai-consent"/)
  assert.match(room, /const session = await startChatSession\(false\)[\s\S]*externalAiConsent\.value = !!session\.data\.external_ai_enabled/)
})

test('teacher work product stays local and exposes its deterministic source', () => {
  const view = read('../src/views/AdminView.vue')
  const api = read('../src/api/teacher.js')
  assert.match(view, /本地确定性规则/)
  assert.match(view, /teacherGenerationLabel/)
  assert.doesNotMatch(view + api, /teacher-derived-ai-v1|teacher_data_basis|derived_narrative/)
  assert.match(view, /我已核验学校或监护人的有效授权依据/)
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
