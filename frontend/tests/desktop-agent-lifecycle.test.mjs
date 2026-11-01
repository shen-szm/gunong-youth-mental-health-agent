import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const read = path => fs.readFileSync(new URL(path, import.meta.url), 'utf8')

test('desktop chat exposes a real workflow rail only after the student opens it', () => {
  const room = read('../src/views/RoomHomeView.vue')
  const rail = read('../src/components/StudentAgentRail.vue')

  assert.match(room, /studentAgentState\.verifiedSteps = Array\.isArray\(res\.data\.workflow\)/)
  assert.match(room, /function toggleAgentRail\(\)[\s\S]*?showAgentRail\.value = next/)
  assert.doesNotMatch(room, /showAgentRail\.value = true/)
  assert.match(room, /const agentChatPair = \(except === 'agent' && key === 'chat'\)/)
  assert.match(room, /if \(except !== 'agent'\) showAgentRail\.value = false/)
  assert.match(room, /function openChatPanel\(\)[\s\S]*?openWorkspacePanel\('chat'\)/)
  assert.match(room, /:disabled="chatLoading \|\| !voiceInputEnabled"/)
  assert.match(room, /对话原文会发送给平台接入的 DeepSeek 模型/)
  assert.match(rail, /agent-toggle-latest[^>]*>\{\{ state\.lastEvent/)
  assert.match(rail, /最新状态：\$\{state\.lastEvent/)
  assert.match(rail, /class="agent-toggle-live" role="status" aria-live="polite"/)
  assert.match(rail, /width: min\(270px, calc\(100vw - 48px\)\)/)
  assert.match(rail, /if \(value && !previous\) closeButton\.value\?\.focus/)
  assert.match(rail, /@media \(min-width: 900px\) and \(max-width: 1163px\)/)
  assert.match(room, /agent-rail-open/)
  assert.match(room, /@media \(min-width: 900px\) and \(max-width: 1199px\)[\s\S]*?translateX\(calc\(\(100vw - 1200px\) \/ 2\)\)/)
  assert.match(rail, /本轮协作/)
  assert.match(rail, /查看工作记录与数据来源/)
  assert.match(rail, /不展示模型私有思维过程/)
  assert.doesNotMatch(rail, /百分比|思维链|专家会诊/)
})

test('assessment and teacher lifecycle distinguish real execution from waiting', () => {
  const assessment = read('../src/components/StudentWellbeingAssessment.vue')
  const teacher = read('../src/views/AdminView.vue')

  assert.match(assessment, /尚未调用分析 Agent/)
  assert.match(assessment, /result\.value\.pipeline/)
  assert.match(assessment, /SafetyGate/)
  assert.match(assessment, /CrossReviewer/)
  assert.match(assessment, /@media \(min-width:1024px\)/)
  assert.match(teacher, /服务端执行状态/)
  assert.match(teacher, /接口返回前不预先宣称任何 Agent 步骤已完成/)
  assert.match(teacher, /pipelineStatusText\(step\.status\)/)
  assert.match(teacher, /@media \(min-width:1024px\)/)
})
