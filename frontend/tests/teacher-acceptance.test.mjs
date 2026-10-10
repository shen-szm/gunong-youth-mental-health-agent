import test from 'node:test'
import assert from 'node:assert/strict'
import { acceptanceEvidence } from '../src/utils/teacherAcceptance.js'
const plan = { task_id: 'task-a', status: 'plan_approved', source: 'local_rules' }
const receipt = { task_id: 'task-a', status: 'awaiting_report_review', report_id: 'report-a', report_hash: 'a'.repeat(64), report_status: 'reviewed', completed_tools: ['query_authorized_items'], attempts: 1 }
test('acceptance requires matching delivery evidence and never promotes confirmation', () => {
  assert.equal(acceptanceEvidence(plan, null).delivered, false)
  assert.equal(acceptanceEvidence(plan, { ...receipt, task_id: 'other' }).reportId, null)
  assert.equal(acceptanceEvidence(plan, { ...receipt, report_hash: 'bad' }).delivered, false)
  assert.equal(acceptanceEvidence({ ...plan, status: 'terminated' }, receipt).delivered, false)
  const result = acceptanceEvidence(plan, receipt)
  assert.equal(result.reportStatus, '教师已签署')
  assert.equal(result.steps.filter(step => step.state === '回执确认完成').length, 1)
  assert.ok(result.source.includes('固定四步'))
})
test('blocked and missing evidence is hidden, not recycled as success', () => {
  assert.equal(acceptanceEvidence(plan, receipt, true), null)
  assert.equal(acceptanceEvidence(null, receipt), null)
  assert.ok(acceptanceEvidence(plan, null).steps.every(step => step.state === '尚未读取执行回执'))
  assert.equal(acceptanceEvidence(plan, { ...receipt, status: 'failed' }).delivered, false)
})
