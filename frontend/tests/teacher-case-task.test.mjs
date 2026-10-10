import assert from 'node:assert/strict'
import test from 'node:test'
import { taskStorageKey, readTaskReference, writeTaskReference, matchesTaskTarget, taskStatusText, caseTaskSteps, taskFailureText, taskDateText } from '../src/utils/teacherCaseTask.js'

test('failure copy does not expose unknown raw errors and timestamps are explicit', () => {
  assert.ok(taskFailureText('tool_failed').includes('未记录'))
  assert.ok(taskFailureText('source_or_artifact_changed').includes('校验'))
  assert.equal(taskFailureText('private raw error').includes('private'), false)
  assert.equal(taskDateText('invalid'), '时间未记录')
  assert.ok(taskDateText('2026-09-08T15:00:00Z').includes('北京时间'))
})

test('task references isolate account, student and approval without saving sensitive data', () => {
  const data = new Map()
  const storage = { getItem: key => data.get(key), setItem: (key, value) => data.set(key, value), removeItem: key => data.delete(key) }
  const key = taskStorageKey(2, 1, 5)
  const reference = { requestId: '11111111-1111-4111-8111-111111111111', taskId: '22222222-2222-4222-8222-222222222222' }
  assert.equal(writeTaskReference(storage, key, { ...reference, studentName: 'must not persist', report: 'private' }), true)
  assert.deepEqual(readTaskReference(storage, key), reference)
  assert.equal(data.get(key).includes('private'), false)
  for (const otherKey of [taskStorageKey(3, 1, 5), taskStorageKey(2, 3, 5), taskStorageKey(2, 1, 6)]) assert.equal(readTaskReference(storage, otherKey), null)
  writeTaskReference(storage, key, null)
  assert.equal(readTaskReference(storage, key), null)
})

test('invalid or denied storage is recoverable', () => {
  assert.equal(readTaskReference({ getItem: () => '{' }, 'key'), null)
  assert.equal(readTaskReference({ getItem: () => '{"requestId":"unexpected"}' }, 'key'), null)
  assert.equal(readTaskReference(undefined, 'key'), null)
  assert.equal(writeTaskReference(undefined, 'key', {}), false)
})

test('restored tasks must match both student and exact approval', () => {
  const plan = { target: { student_id: 1, access_request_id: 5 } }
  assert.equal(matchesTaskTarget(plan, 1, 5), true)
  assert.equal(matchesTaskTarget(plan, 2, 5), false)
  assert.equal(matchesTaskTarget(plan, 1, null), false)
  assert.equal(matchesTaskTarget({}, 1, null), false)
})

test('status distinguishes plan confirmation, execution failure and human review', () => {
  assert.equal(taskStatusText(null, null), '尚未创建任务')
  assert.equal(taskStatusText({ status: 'terminated' }, { status: 'failed' }), '任务已终止')
  assert.equal(taskStatusText({ status: 'waiting_approval' }, null), '等待教师确认')
  assert.equal(taskStatusText({ status: 'plan_approved' }, null), '计划已确认')
  assert.equal(taskStatusText({}, { status: 'failed', attempts: 1 }), '执行中断')
  assert.equal(taskStatusText({}, { status: 'awaiting_report_review' }), '报告待审核')
  assert.equal(taskStatusText({}, { status: 'awaiting_report_review', report_status: 'reviewed' }), '教师已签署')
  assert.equal(taskStatusText({}, { status: 'awaiting_report_review', report_status: 'revision_requested' }), '待补充修订')
  assert.equal(caseTaskSteps.length, 4)
})
