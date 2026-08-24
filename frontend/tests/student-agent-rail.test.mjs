import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const room = fs.readFileSync(new URL('../src/views/RoomHomeView.vue', import.meta.url), 'utf8')
const rail = fs.readFileSync(new URL('../src/components/StudentAgentRail.vue', import.meta.url), 'utf8')
const treehole = fs.readFileSync(new URL('../src/views/TreeHoleView.vue', import.meta.url), 'utf8')

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
  assert.match(room, /studentAgentState\.phase = 'chat'\s+studentAgentState\.verifiedSteps = \[\]/)
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

test('every free-text companion entry uses the shared backend safety gate', () => {
  assert.match(room, /sendPetCompanionMsg[\s\S]*?sendMessage\(Number\(userStore\.userId\), content\)/)
  assert.match(treehole, /sendCompanionMsg[\s\S]*?sendMessage\(Number\(userStore\.userId\), content\)/)
  assert.doesNotMatch(room, /\/api\/companion\/chat/)
  assert.doesNotMatch(treehole, /\/api\/companion\/chat/)
  assert.match(room, /12356、110或120/)
  assert.match(treehole, /12356、110或120/)
})

test('student companion modes keep a continuous AI identity without embodied promises', () => {
  assert.match(treehole, /温柔倾听模式（AI）/)
  assert.match(treehole, /行动陪伴模式（AI）/)
  assert.match(treehole, /不是真人或心理医生/)
  assert.doesNotMatch(treehole, /学姐|学弟|学妹|邻家大哥哥|哥哥给|哥在|哥顶|哥保证|哥帮|哥陪|哥给|老弟|老妹/)
})
