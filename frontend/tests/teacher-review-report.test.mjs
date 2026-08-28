import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const testDir = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(testDir, '..', '..')
const source = (relativePath) => readFile(path.join(projectRoot, relativePath), 'utf8')

test('teacher workbench exposes a final auditable Agent deliverable', async () => {
  const portal = await source('frontend/src/views/AdminView.vue')
  const report = await source('frontend/src/components/TeacherReviewReport.vue')
  const api = await source('frontend/src/api/teacher.js')

  assert.match(portal, /TeacherReviewReport/)
  assert.match(portal, /generateReviewReport/)
  assert.match(report, /数字员工最终交付/)
  assert.match(report, /7 阶段受约束 Agent 工作流/)
  assert.match(report, /功能影响与保护因素/)
  assert.match(report, /教师复核与签署/)
  assert.match(report, /原文外传/)
  assert.match(report, /未发送给外部模型/)
  assert.match(api, /generateStudentReviewReport/)
  assert.match(api, /getLatestStudentReviewReport/)
  assert.match(api, /decideStudentReviewReport/)
  assert.match(api, /studentReviewReportPdfUrl/)
})

test('report UI keeps clinical boundaries and human review visible', async () => {
  const report = await source('frontend/src/components/TeacherReviewReport.vue')
  assert.match(report, /Human in the loop/)
  assert.match(report, /不展示模型私有思维链/)
  assert.match(report, /退回修订/)
  assert.match(report, /确认并签署/)
  assert.doesNotMatch(report, /PHQ|GAD|确诊|治愈率|患病概率/)
})
