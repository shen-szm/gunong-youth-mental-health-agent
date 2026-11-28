import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const view = readFileSync(new URL('../src/views/AdminView.vue', import.meta.url), 'utf8')
const api = readFileSync(new URL('../src/api/teacher.js', import.meta.url), 'utf8')
const store = readFileSync(new URL('../src/stores/user.js', import.meta.url), 'utf8')

test('teacher workbench exposes approval-gated case flow', () => {
  assert.match(view, /校园心理支持工单/)
  assert.match(view, /提交个案查看申请/)
  assert.match(view, /等待管理员教师审批/)
  assert.match(view, /经授权的证据/)
  assert.match(view, /每次打开均已审计/)
})

test('admin teacher approval and direct access are explicit', () => {
  assert.match(view, /管理员教师 · 可直达/)
  assert.match(view, /审核并批准/)
  assert.match(view, /确认开放固定原文范围/)
  assert.match(view, /userStore\.isSuperAdmin/)
  assert.match(store, /isSuperAdmin/)
})

test('teacher client uses dedicated access endpoints while student model access is globally governed', () => {
  assert.match(api, /students\/\$\{studentId\}\/access-requests/)
  assert.match(api, /access-requests\/\$\{requestId\}\/decision/)
  assert.match(api, /students\/\$\{studentId\}\/case-context/)
  assert.match(api, /students\/\$\{studentId\}\/work-product/)
  assert.match(api, /work-product\/task-decisions/)
  assert.match(api, /post\('\/assignments'/)
  assert.match(api, /external-ai-authorization/)
  assert.match(view, /学生端受约束模型对话全局启用/)
  assert.doesNotMatch(view, /撤回模型协作授权/)
})
