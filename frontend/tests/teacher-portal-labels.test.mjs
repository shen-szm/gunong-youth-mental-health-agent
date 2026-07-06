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
  assert.match(portal, /<h2>教师端<\/h2>/)
  assert.match(portal, /请用教师账号登录/)
  assert.match(portal, /u\.is_admin \? '教师' : '普通用户'/)
  assert.match(portal, /u\.is_admin \? '取消教师' : '设为教师'/)

  assert.doesNotMatch(portal, /管理员后台/)
})

test('teacher portal restores warning handling and lesson-plan workflow', async () => {
  const portal = await source('frontend/src/views/AdminView.vue')
  const api = await source('frontend/src/api/teacher.js')

  assert.match(portal, /教师端工作台/)
  assert.match(portal, /情绪预警/)
  assert.match(portal, /预警详情/)
  assert.match(portal, /处理记录/)
  assert.match(portal, /标记已处理/)
  assert.match(portal, /学生画像/)
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

test('teacher onboarding is replayable and guides the core workflow', async () => {
  const portal = await source('frontend/src/views/AdminView.vue')

  assert.match(portal, /shengyu_teacher_guide_v4_4_0/)
  assert.match(portal, /新手引导/)
  assert.match(portal, /第一步：先看待处理预警/)
  assert.match(portal, /第二步：打开一个预警详情/)
  assert.match(portal, /第三步：查看学生画像/)
  assert.match(portal, /第四步：生成班会方案/)
  assert.match(portal, /重新引导/)
  assert.match(portal, /localStorage\.setItem\(GUIDE_KEY, 'done'\)/)
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
