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

  assert.match(room, />教师<\/span>/)
  assert.match(room, /教师端 <span class="arrow">/)
  assert.match(profile, /class="admin-badge">教师<\/span>/)
  assert.match(profile, /<span>教师端<\/span>/)
  assert.match(portal, /<h2>教师端<\/h2>/)
  assert.match(portal, /u\.is_admin \? '教师' : '普通用户'/)
  assert.match(portal, /u\.is_admin \? '取消教师' : '设为教师'/)
  assert.match(portal, /请用教师账号登录/)

  assert.doesNotMatch(room, />管理员<\/span>/)
  assert.doesNotMatch(room, /管理后台 <span class="arrow">/)
  assert.doesNotMatch(profile, /class="admin-badge">管理员<\/span>/)
  assert.doesNotMatch(profile, /<span>管理后台<\/span>/)
  assert.doesNotMatch(portal, /<h2>管理后台<\/h2>/)
  assert.doesNotMatch(portal, /u\.is_admin \? '管理员' : '普通用户'/)
  assert.doesNotMatch(portal, /请用管理员账号登录/)
})

test('backend exposes teacher-facing permission and support messages', async () => {
  const adminApi = await source('backend/api/admin.py')
  const userApi = await source('backend/api/user.py')

  assert.match(adminApi, /需要教师权限/)
  assert.match(adminApi, /"设为教师" if target\.is_admin else "取消教师"/)
  assert.match(adminApi, /给教师的建议/)
  assert.match(userApi, /联系教师重置/)
  assert.match(userApi, /需要教师权限/)

  assert.doesNotMatch(adminApi, /需要管理员权限/)
  assert.doesNotMatch(adminApi, /"设为管理员" if target\.is_admin else "取消管理员"/)
  assert.doesNotMatch(adminApi, /给管理者的建议/)
  assert.doesNotMatch(userApi, /联系管理员重置/)
  assert.doesNotMatch(userApi, /需要管理员权限/)
})

test('internal admin compatibility identifiers and routes remain unchanged', async () => {
  const store = await source('frontend/src/stores/user.js')
  const router = await source('frontend/src/router.js')
  const portal = await source('frontend/src/views/AdminView.vue')
  const adminApi = await source('backend/api/admin.py')

  assert.match(store, /isAdmin/)
  assert.match(router, /path: "\/admin"/)
  assert.match(portal, /\/api\/admin/)
  assert.match(adminApi, /prefix="\/api\/admin"/)
  assert.match(adminApi, /is_admin/)
})


test('teacher portal route redirects non-teachers to hidden teacher login', async () => {
  const router = await source('frontend/src/router.js')

  assert.match(router, /if \(to\.path === "\/admin" && !userStore\.isAdmin\)/)
  assert.match(router, /path: "\/teacher-login"/)
  assert.match(router, /redirect: to.fullPath/)
})

test('teacher login returns teachers to requested portal path', async () => {
  const login = await source('frontend/src/views/LoginView.vue')

  assert.match(login, /useRoute/)
  assert.match(login, /const route = useRoute\(\)/)
  assert.match(login, /const redirect = route.query.redirect/)
  assert.match(login, /router\.push\(data\.is_admin \? \(redirect \|\| '\/admin'\) : '\/'\)/)
})

test('teacher portal prioritizes student emotion status dashboard', async () => {
  const portal = await source('frontend/src/views/AdminView.vue')

  assert.match(portal, /student-emotion-board/)
  assert.match(portal, /学生情绪状态/)
  assert.match(portal, /点击学生查看情绪趋势、分布与AI分析/)
  assert.match(portal, /student-mood-summary/)
  assert.match(portal, /detail\.stats\.avg_score/)

  const adminApi = await source('backend/api/admin.py')
  assert.match(adminApi, /latest_mood_label/)
  assert.match(adminApi, /avg_mood_score/)
  assert.match(adminApi, /mood_count/)
})
