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

test('router exposes student login and gates feature pages', async () => {
  const router = await source('frontend/src/router.js')

  assert.match(router, /import StudentLoginView from "\.\/views\/StudentLoginView\.vue"/)
  assert.match(router, /path: "\/login", name: "StudentLogin", component: StudentLoginView/)
  assert.match(router, /requiresRealUser: true/)
  assert.match(router, /requiresTeacher: true/)
  assert.match(router, /path: "\/login", query: \{ redirect: to\.fullPath \}/)
  assert.doesNotMatch(router, /createGuestSession/)
})

test('user store separates guests from real accounts', async () => {
  const store = await source('frontend/src/stores/user.js')

  assert.match(store, /isGuest/)
  assert.match(store, /isRealUser = computed/)
  assert.match(store, /function enterGuestMode/)
  assert.match(store, /shengyu_is_guest/)
  assert.doesNotMatch(store, /createGuestSession/)
})

test('api layer turns login_required 403 into a global prompt event', async () => {
  const http = await source('frontend/src/api/http.js')

  assert.match(http, /login_required/)
  assert.match(http, /shengyu:login-required/)
  assert.match(http, /export function createApi/)
})

test('student login page validates register and offers guest browsing', async () => {
  const view = await source('frontend/src/views/StudentLoginView.vue')

  assert.match(view, /先随便逛逛/)
  assert.match(view, /密码至少需要 10 位/)
  assert.match(view, /enterGuestMode/)
  assert.match(view, /redirect/)
  assert.match(view, /student-realname/)
  assert.match(view, /student-class/)
  assert.match(view, /student-no/)
})

test('teacher login is restricted to teacher accounts', async () => {
  const view = await source('frontend/src/views/LoginView.vue')

  assert.match(view, /教师登录/)
  assert.match(view, /该账号不是教师账号/)
  assert.doesNotMatch(view, /mode === 'register'/)
})

test('backend enforces real-user dependency on feature routes', async () => {
  const auth = await source('backend/auth.py')
  const chat = await source('backend/api/chat.py')

  assert.match(auth, /def require_real_user/)
  assert.match(auth, /"code": "login_required"/)
  assert.match(chat, /Depends\(require_real_user\)/)
})
