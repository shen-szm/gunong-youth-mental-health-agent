import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const read = path => fs.readFileSync(new URL(path, import.meta.url), 'utf8')

test('desktop chat opens a real workflow rail without changing mobile breakpoints', () => {
  const room = read('../src/views/RoomHomeView.vue')
  const rail = read('../src/components/StudentAgentRail.vue')

  assert.match(room, /matchMedia\('\(min-width: 1024px\)'\)/)
  assert.match(room, /studentAgentState\.verifiedSteps = Array\.isArray\(res\.data\.workflow\)/)
  assert.match(room, /if \(isDesktopAgentViewport\(\)\) showAgentRail\.value = true/)
  assert.match(rail, /多 Agent 协作轨迹/)
  assert.match(rail, /不展示模型私有思维过程/)
  assert.match(rail, /@media \(min-width: 1024px\)/)
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
