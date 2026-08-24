import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const testDir = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(testDir, '..', '..')

async function source(relativePath) {
  return readFile(path.join(projectRoot, relativePath), 'utf8')
}

test('frontend presents privileged users and tools as teacher-facing', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')
  const profile = await source('frontend/src/views/ProfileView.vue')
  const portal = await source('frontend/src/views/AdminView.vue')

  assert.match(room, /教师/)
  assert.match(profile, /教师/)
  assert.match(portal, /咕哝教师端/)
  assert.match(portal, /校园支持数字员工/)
  assert.match(portal, /今日工作台/)
  assert.match(portal, /请用教师账号登录/)
  assert.match(portal, /u\.role === 'admin_teacher' \? '管理员教师'/)
  assert.match(portal, /u\.is_admin \? '取消教师' : '设为教师'/)

  assert.doesNotMatch(portal, /管理员后台/)
})

test('teacher portal restores warning handling and lesson-plan workflow', async () => {
  const portal = await source('frontend/src/views/AdminView.vue')
  const api = await source('frontend/src/api/teacher.js')

  assert.match(portal, /校园支持数字员工/)
  assert.match(portal, /情绪预警/)
  assert.match(portal, /预警详情/)
  assert.match(portal, /处理记录/)
  assert.match(portal, /标记已处理/)
  assert.match(portal, /学生支持记录/)
  assert.match(portal, /AI 班会生成/)
  assert.match(portal, /生成班会方案/)
  assert.match(portal, /账号管理/)

  assert.match(api, /baseURL: '\/api\/teacher'/)
  assert.match(api, /\/class-overview/)
  assert.match(api, /\/warning-list/)
  assert.match(api, /\/warning\/\$\{warningId\}\/handle/)
  assert.match(api, /\/lesson-plan\/generate/)
  assert.match(api, /\/students\/\$\{studentId\}\/profile/)
})

test('teacher portal keeps descriptive student record analytics', async () => {
  const portal = await source('frontend/src/views/AdminView.vue')

  assert.match(portal, /emotion-detail-panel/)
  assert.match(portal, /detail-stats/)
  assert.match(portal, /trend-chart/)
  assert.match(portal, /dist-bars/)
  assert.match(portal, /word-cloud-wrap/)
  assert.match(portal, /analysis-card/)
  assert.match(portal, /\/api\/admin\/user-detail/)
  assert.match(portal, /\/api\/admin\/user-analysis/)
  assert.match(portal, /detail\.stats\.total_moods/)
  assert.match(portal, /detail\.trend/)
  assert.match(portal, /detail\.distribution/)
  assert.match(portal, /normalizedWordCloud/)
  assert.match(portal, /主动记录次数（近30天）/)
  assert.doesNotMatch(portal, /平均情绪/)
  assert.doesNotMatch(portal, /情绪记录均值/)
})

test('teacher onboarding guide is removed from the portal', async () => {
  const portal = await source('frontend/src/views/AdminView.vue')

  assert.doesNotMatch(portal, /shengyu_teacher_guide_v4_4_0/)
  assert.doesNotMatch(portal, /guide-card/)
  assert.doesNotMatch(portal, /showGuide/)
  assert.doesNotMatch(portal, /guideSteps/)
  assert.doesNotMatch(portal, /restartGuide/)
  assert.doesNotMatch(portal, /新手引导/)
})

test('teacher emotion analytics uses readable keyword chips and structured AI analysis', async () => {
  const portal = await source('frontend/src/views/AdminView.vue')

  assert.match(portal, /normal-word-cloud/)
  assert.match(portal, /word-cloud-item/)
  assert.match(portal, /normalizedWordCloud/)
  assert.doesNotMatch(portal, /wordCloudCanvas/)
  assert.doesNotMatch(portal, /renderWordCloud/)
  assert.match(portal, /analysis-sections/)
  assert.match(portal, /analysis-block/)
  assert.match(portal, /analysisSections/)
  assert.match(portal, /parseAnalysisSections/)
})
test('internal compatibility identifiers and routes remain stable', async () => {
  const store = await source('frontend/src/stores/user.js')
  const router = await source('frontend/src/router.js')
  const adminApi = await source('backend/api/admin.py')

  assert.match(store, /isAdmin/)
  assert.match(router, /path: "\/admin"/)
  assert.match(adminApi, /prefix="\/api\/admin"/)
  assert.match(adminApi, /is_admin/)
})
