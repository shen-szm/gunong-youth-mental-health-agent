import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const source = (path) => readFile(join(root, path), 'utf8')

test('guardian routes keep existing student and teacher surfaces while adding the workbench', async () => {
  const router = await source('frontend/src/router.js')
  assert.match(router, /path: "\/"/)
  assert.match(router, /path: "\/admin"/)
  assert.match(router, /path: "\/guardian"/)
  assert.match(router, /path: "\/guardian\/new"/)
  assert.match(router, /path: "\/guardian\/cases\/:caseId"/)
  assert.match(router, /path: "\/guardian\/follow-ups"/)
})

test('guardian intake is synthetic-only and never claims a standardized scale', async () => {
  const intake = await source('frontend/src/views/GuardianIntakeView.vue')
  const caseView = await source('frontend/src/views/GuardianCaseView.vue')
  assert.match(intake, /synthetic_data_confirmed/)
  assert.match(intake, /不写身份信息/)
  assert.match(caseView, /未直接访谈青少年/)
  assert.doesNotMatch(caseView, /PHQ-9.*分/)
  assert.doesNotMatch(intake, /诊断结果/)
})

test('guardian urgent path exposes real-world help and structured agent trace', async () => {
  const caseView = await source('frontend/src/views/GuardianCaseView.vue')
  const home = await source('frontend/src/views/GuardianHomeView.vue')
  assert.match(caseView, /tel:12356/)
  assert.match(caseView, /tel:110/)
  assert.match(caseView, /tel:120/)
  assert.match(caseView, /不展示模型私有思维链/)
  assert.match(home, /安全规则优先/)
})

test('guardian API includes cases, SSE, report and follow-up contracts', async () => {
  const api = await source('backend/api/guardian.py')
  assert.match(api, /@router\.post\("\/cases"/)
  assert.match(api, /@router\.get\("\/cases\/\{case_code\}\/events"/)
  assert.match(api, /text\/event-stream/)
  assert.match(api, /@router\.get\("\/cases\/\{case_code\}\/report\.pdf"/)
  assert.match(api, /@router\.post\("\/follow-ups\/\{followup_id\}\/simulate-due"/)
})

test('alpha release is synchronized and business UI omits development labels', async () => {
  const pkg = JSON.parse(await source('frontend/package.json'))
  const lock = JSON.parse(await source('frontend/package-lock.json'))
  const changelog = await source('CHANGELOG.md')
  const backend = await source('backend/config.py')
  const currentReleaseNotes = changelog.split('## [5.1.0-alpha.1]')[0]
  assert.equal(pkg.version, '5.1.0-alpha.11')
  assert.equal(lock.version, '5.1.0-alpha.11')
  assert.equal(lock.packages[''].version, '5.1.0-alpha.11')
  assert.match(currentReleaseNotes, /\[5\.1\.0-alpha\.11\]/)
  assert.match(currentReleaseNotes, /\[5\.1\.0-alpha\.7\]/)
  assert.match(currentReleaseNotes, /\[5\.1\.0-alpha\.6\]/)
  assert.match(currentReleaseNotes, /\[5\.1\.0-alpha\.3\]/)
  assert.match(currentReleaseNotes, /\[5\.1\.0-alpha\.2\]/)
  assert.match(currentReleaseNotes, /未部署、未推送远端/)
  assert.match(backend, /RELEASE_VERSION: str = "5\.1\.0-alpha\.11"/)
})

test('plaintext password recovery and hard-coded weak admin are removed', async () => {
  const models = await source('backend/models.py')
  const initAdmin = await source('backend/init_admin.py')
  const login = await source('frontend/src/views/LoginView.vue')
  assert.doesNotMatch(models, /plain_password/)
  assert.doesNotMatch(initAdmin, /admin123/)
  assert.doesNotMatch(login, /你的密码是/)
  assert.match(login, /密码不会被系统展示/)
})

test('urgent UI never waits for a completed plan and reports SSE recovery', async () => {
  const caseView = await source('frontend/src/views/GuardianCaseView.vue')
  assert.match(caseView, /data\.case\.risk_level === 'urgent'/)
  assert.doesNotMatch(caseView, /risk_level === 'urgent' && data\.plan/)
  assert.match(caseView, /实时事件流已断开/)
  assert.match(caseView, /重试失败，工单仍保留/)
})

test('follow-up rechecks immediate safety and family harm', async () => {
  const followups = await source('frontend/src/views/GuardianFollowUpsView.vue')
  assert.match(followups, /current_safety/)
  assert.match(followups, /new_self_harm_or_suicide_signal/)
  assert.match(followups, /family_harm_or_unsafe_home/)
  assert.match(followups, /已切换紧急安全路径/)
})

test('guardian primary links and non-text focus indicators keep explicit accessible colors', async () => {
  const css = await source('frontend/src/guardian.css')
  assert.match(css, /\.guardian-page \.guardian-primary-action \{[^}]*color: #fff/)
  assert.match(css, /--guardian-focus: #765000/)
  assert.match(css, /border: 2px solid #63786f/)
  assert.match(css, /guardian-urgent-panel \.guardian-hotlines a/)
})
