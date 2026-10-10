import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const component = await readFile(new URL('../src/components/StudentWellbeingAssessment.vue', import.meta.url), 'utf8')
const trend = await readFile(new URL('../src/views/TrendView.vue', import.meta.url), 'utf8')
const api = await readFile(new URL('../src/api/assessment.js', import.meta.url), 'utf8')

test('student assessment exposes a complete non-diagnostic multi-agent workflow', () => {
  assert.match(component, /近两周支持需求自评/)
  assert.match(component, /证据与安全复核/)
  assert.match(component, /result\.conflicts/)
  assert.match(component, /step\.agent/)
  assert.match(component, /多 Agent 工作进度/)
  assert.match(component, /不是医学诊断/)
  assert.match(component, /拨打 12356/)
  assert.match(component, /不展示模型私有思维过程/)
  assert.match(trend, /StudentWellbeingAssessment/)
})

test('assessment client is session scoped and supports active deletion', () => {
  assert.match(api, /baseURL: '\/api\/assessment'/)
  assert.match(api, /post\('\/submit'/)
  assert.match(api, /get\('\/latest'/)
  assert.match(api, /delete\(`\/\$\{code\}`\)/)
  assert.doesNotMatch(api, /user_id/)
})

test('emotion review does not present a synthetic average score', () => {
  assert.doesNotMatch(trend, /平均情绪分|avg_score|总分/)
  assert.match(trend, /较常记录的情绪/)
  assert.match(trend, /主动记录时间线|近期主动记录/)
})
