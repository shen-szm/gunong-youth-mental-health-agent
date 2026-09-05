import test from 'node:test'
import assert from 'node:assert/strict'
import { executionSnapshot } from '../src/utils/agentExecution.js'

const plan = [
  { agent: 'StudentSafetyGate', tool: 'deterministic_safety_rules' },
  { agent: 'ResponseAgent', tool: 'xunfei_response_strategy_selector' },
]
const events = [
  { sequence: 1, agent: 'StudentSafetyGate', tool: 'deterministic_safety_rules', status: 'completed' },
  { sequence: 2, agent: 'ResponseAgent', tool: 'deterministic_response_template', status: 'completed', summary: '本地回应', source: 'deterministic' },
]

test('replay hides future outcomes and tools without mutating persisted events', () => {
  const original = JSON.stringify(events)
  const before = executionSnapshot(plan, events, 0)
  assert.equal(before.completed, 0)
  assert.deepEqual(before.tools, [])
  assert.ok(before.rows.every(row => row.event === null && row.tool === null))
  const partial = executionSnapshot(plan, events, 1)
  assert.equal(partial.rows[1].status, 'unrecorded')
  assert.equal(partial.rows[1].event, null)
  assert.equal(JSON.stringify(events), original)
})

test('fallback records actual local tool separately from planned external tool', () => {
  const result = executionSnapshot(plan, events)
  assert.equal(result.rows[1].plannedTool, 'xunfei_response_strategy_selector')
  assert.equal(result.rows[1].tool, 'deterministic_response_template')
  assert.ok(!result.tools.includes('xunfei_response_strategy_selector'))
})

test('urgent path does not invent normal generation and preserves human attention', () => {
  const urgent = [{ sequence: 1, agent: 'SafetyCoordinator', tool: 'urgent_support_router', status: 'attention' }]
  const result = executionSnapshot([{ agent: 'SafetyCoordinator', tool: 'urgent_support_router' }], urgent)
  assert.equal(result.rows.length, 1)
  assert.equal(result.rows[0].status, 'attention')
  assert.equal(result.completed, 0)
})

test('legacy records remain viewable without claiming a plan or leaking later tools', () => {
  const result = executionSnapshot([], [...events].reverse(), 1)
  assert.equal(result.planned, false)
  assert.equal(result.rows[0].event.sequence, 1)
  assert.equal(result.rows[1].plannedTool, null)
  assert.equal(result.rows[1].tool, null)
})

test('failure recovery outside the plan is visible and remains failed', () => {
  const failed = [...events.slice(0, 1), { sequence: 3, agent: 'Recovery', tool: 'stale_run_recovery', status: 'failed' }]
  const result = executionSnapshot(plan, failed)
  assert.equal(result.rows.at(-1).status, 'failed')
  assert.equal(result.rows.at(-1).inPlan, false)
  assert.equal(result.rows[1].status, 'unrecorded')
  assert.deepEqual(executionSnapshot(plan, events, -1).tools, [])
})
