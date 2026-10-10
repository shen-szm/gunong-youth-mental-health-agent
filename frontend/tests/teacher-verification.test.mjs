import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'

const evidence = JSON.parse(readFileSync(new URL('../src/data/teacher-verification.json', import.meta.url), 'utf8'))
test('verification evidence is synthetic, internally consistent and bound to current engine', () => {
  assert.match(evidence.origin, /合成/)
  assert.match(evidence.boundary, /不是真实学生/)
  assert.equal(new Set(evidence.cases.map(item => item.category)).size, 8)
  assert.equal(new Set(evidence.cases.map(item => item.id)).size, evidence.cases.length)
  assert.equal(evidence.summary.total, evidence.cases.length)
  assert.equal(evidence.summary.passed, evidence.cases.filter(item => item.passed).length)
  assert.equal(evidence.summary.checks, evidence.cases.reduce((n, item) => n + Object.keys(item.checks).length, 0))
  assert.equal(evidence.summary.checks_passed, evidence.cases.reduce((n, item) => n + Object.values(item.checks).filter(Boolean).length, 0))
  const engine = readFileSync(new URL('../../backend/teacher_review_engine.py', import.meta.url), 'utf8').replaceAll('\r\n', '\n')
  assert.equal(evidence.engine_sha256, createHash('sha256').update(engine).digest('hex'), 'regenerate verification after engine changes')
  for (const item of evidence.cases) {
    assert.equal(item.passed, Object.values(item.checks).every(Boolean))
    assert.equal(item.report.agent_review.workflow.length, 7)
    assert.equal(item.report.status, 'draft')
    assert.equal(item.report.generation.external_transfer_attempted, false)
  }
})
