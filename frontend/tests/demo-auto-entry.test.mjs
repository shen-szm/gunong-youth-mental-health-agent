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

test('user API and store expose isolated guest-session initialization', async () => {
  const api = await source('frontend/src/api/user.js')
  const store = await source('frontend/src/stores/user.js')

  assert.match(api, /export function createGuestSession\(\)/)
  assert.match(api, /instance\.post\("\/guest-session"\)/)
  assert.match(store, /async function ensureStudentSession\(forceRefresh = false\)/)
  assert.match(store, /if \(!forceRefresh && sessionChecked\.value && isLoggedIn\.value\) return/)
  assert.match(store, /await getCurrentSession\(\)/)
  assert.match(store, /await createGuestSession\(\)/)
  assert.match(store, /login\(data\.user_id, data\.nickname, !!data\.is_admin, !!data\.is_super_admin, data\.role\)/)
  assert.match(store, /ensureStudentSession/)
})

test('router initializes isolated student identity except on the hidden login route', async () => {
  const router = await source('frontend/src/router.js')

  assert.match(router, /if \(to\.path === "\/teacher-login"\) return true/)
  assert.match(router, /path: "\/login",\s*redirect: "\/"/)
  assert.match(router, /path: "\/teacher-login", name: "Login", component: LoginView/)
  assert.match(router, /await userStore\.ensureStudentSession\(\)/)
  assert.match(router, /catch/)
  assert.match(router, /path: "\/teacher-login"/)
  assert.match(router, /redirect: to.fullPath/)
  assert.doesNotMatch(router, /next\("\/login"\)/)
})

test('App renders routed pages without an implicit login fallback', async () => {
  const app = await source('frontend/src/App.vue')

  assert.doesNotMatch(app, /import LoginView/)
  assert.doesNotMatch(app, /<LoginView/)
  assert.doesNotMatch(app, /v-if="userStore\.userId"/)
  assert.match(app, /<router-view class="page-content" \/>/)
  assert.match(app, /route\.path !== '\/teacher-login'/)
  assert.match(app, /'login-full': route\.path === '\/teacher-login'/)
})
test('ordinary logout restores isolated guest identity while teacher logout opens login', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')
  const profile = await source('frontend/src/views/ProfileView.vue')

  for (const view of [room, profile]) {
    assert.match(view, /const wasTeacher = userStore\.isAdmin/)
    assert.match(view, /await userStore\.ensureStudentSession\(\)/)
    assert.match(view, /if \(wasTeacher\).*router\.push\('\/teacher-login'\)/s)
  }
})
