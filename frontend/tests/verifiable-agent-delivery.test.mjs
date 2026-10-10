import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const read = path => fs.readFileSync(new URL(path, import.meta.url), 'utf8')
const room = read('../src/views/RoomHomeView.vue')
const rail = read('../src/components/StudentAgentRail.vue')
const teacher = read('../src/views/AdminView.vue')

test('student desktop rail renders only server-returned task contracts, verification and artifacts', () => {
  assert.match(room, /studentAgentState\.deliverable = run\.deliverable/)
  assert.match(room, /deliverable: null/)
  assert.match(rail, /deliverable\.value\.task_contract/)
  assert.match(rail, /deliverable\.value\.verification/)
  assert.match(rail, /deliverable\.value\.artifact/)
  assert.match(rail, /最近一次任务回执/)
  assert.match(rail, /逐项核验/)
  assert.match(rail, /needs_attention.*attention/)
  assert.match(rail, /下一责任人/)
  assert.match(room, /studentAgentState\.lastEvent = '安全分流进行中；通过后才会理解表达并规划支持'/)
  assert.ok(room.indexOf("id: 'safety'") < room.indexOf("id: 'understand'"))
  assert.match(rail, /\.agent-delivery \{ display: none; \}/)
  assert.match(rail, /@media \(min-width: 900px\)[\s\S]*?\.agent-delivery \{[\s\S]*?display: block/)
  assert.doesNotMatch(room, /showAgentRail\.value = true/)
})

test('student rail names planning and delivery verification roles without exposing private reasoning', () => {
  for (const name of ['StudentTaskPlanner', 'bounded_support_planner', 'OutcomeVerifier', 'DeliveryVerifier']) {
    assert.match(rail, new RegExp(name))
  }
  assert.match(rail, /受限支持规划/)
  assert.match(rail, /交付结果核验/)
  assert.match(rail, /不展示模型私有思维过程/)
})

test('teacher desktop workbench exposes an authorized structured Agent handoff ledger', () => {
  assert.match(teacher, /workProduct\.value\?\.agent_handoff/)
  assert.match(teacher, /agentHandoff\.verified_count/)
  assert.match(teacher, /agentHandoff\.run_count/)
  assert.match(teacher, /recentAgentHandoffs/)
  assert.match(teacher, /needs_attention.*attention/)
  assert.match(teacher, /run\.artifact\?\.next_action/)
  assert.match(teacher, /结构化接力不等于心理诊断，也不表示教师已完成线下行动/)
  assert.match(teacher, /\.agent-handoff-ledger \{ display: none; \}/)
  assert.match(teacher, /@media \(min-width:1024px\)[\s\S]*?\.agent-handoff-ledger \{ display: block/)
  assert.match(teacher, /prefers-reduced-motion: reduce/)
})
