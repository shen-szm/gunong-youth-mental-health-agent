import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const room = fs.readFileSync(new URL('../src/views/RoomHomeView.vue', import.meta.url), 'utf8')
const rail = fs.readFileSync(new URL('../src/components/StudentAgentRail.vue', import.meta.url), 'utf8')

test('student room exposes a truthful agent workflow rail', () => {
  assert.match(room, /StudentAgentRail/)
  assert.match(room, /studentAgentState/)
  assert.match(room, /studentAgentSteps/)
  for (const label of ['理解本轮表达', '安全优先分流', '本轮情绪线索', '支持回应编排', '倾诉后小结']) {
    assert.match(room, new RegExp(label))
  }
  assert.match(room, /conversation_signal/)
  assert.match(room, /res\.data\.metadata\?\.degraded/)
  assert.match(room, /res\.data\.workflow/)
  assert.match(room, /res\.data\.risk_level/)
  assert.match(room, /studentAgentState\.phase = 'chat'[\s\S]{0,120}studentAgentState\.source = 'pending'[\s\S]{0,120}studentAgentState\.verifiedSteps = \[\]/)
  const railTemplate = rail.slice(0, rail.indexOf('<style scoped>'))
  assert.doesNotMatch(railTemplate, /\d+%/)
  assert.match(rail, /不展示模型私有思维过程/)
})

test('agent rail communicates urgent, failure and accessible states', () => {
  assert.match(room, /studentAgentState\.status = 'urgent'/)
  assert.match(room, /普通分析已停止/)
  assert.match(room, /status === 'urgent'[\s\S]*?showAgentRail\.value = false/)
  assert.match(room, /studentAgentState\.status = 'error'/)
  assert.match(room, /async function openSummaryDrawer\(\)[\s\S]*?closeRoomWorkspaces\('support'\)/)
  assert.match(rail, /aria-live="polite"/)
  assert.match(rail, /aria-expanded="open"/)
  assert.match(rail, /收起咕哝智能体进度/)
  assert.match(rail, /@keydown\.esc/)
  assert.match(rail, /prefers-reduced-motion: reduce/)
})
