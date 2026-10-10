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

test('public login route is hidden and teacher login uses a separate path', async () => {
  const router = await source('frontend/src/router.js')
  const app = await source('frontend/src/App.vue')

  assert.match(router, /path: "\/login",\s*redirect: "\/"/)
  assert.match(router, /path: "\/teacher-login", name: "Login", component: LoginView/)
  assert.match(router, /if \(to\.path === "\/teacher-login"\) return true/)
  assert.doesNotMatch(router, /if \(to\.path === "\/login"\) return true/)
  assert.match(app, /'login-full': route\.path === '\/teacher-login'/)
  assert.match(app, /route\.path !== '\/teacher-login'/)
  assert.doesNotMatch(app, /route\.path !== '\/login'/)
})

test('handheld game mini app is removed from the room UI', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.doesNotMatch(room, /小掌机/)
  assert.doesNotMatch(room, /openMiniApp\('ikk'\)/)
  assert.doesNotMatch(room, /giao\.me\/ikk/)
  assert.doesNotMatch(room, /miniAppKey === 'ikk'/)
  assert.doesNotMatch(room, /\.ikk-bottom-mask/)
})

test('beian footer is readable over the room background', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')
  const home = await source('frontend/src/views/HomeView.vue')

  for (const page of [room, home]) {
    assert.match(page, /href="https:\/\/beian\.miit\.gov\.cn\/"/)
    assert.match(page, />粤ICP备2026048986号-2<\/a>/)
  }
  assert.match(room, /\.beian-footer\s*\{[\s\S]*background:\s*rgba\(18,\s*24,\s*32,\s*0\.72\)/)
  assert.match(room, /\.beian-footer\s*\{[\s\S]*backdrop-filter:\s*blur\(10px\)/)
  assert.match(room, /\.beian-footer\s*\{[\s\S]*text-shadow:\s*0 1px 2px rgba\(0,\s*0,\s*0,\s*0\.65\)/)
  assert.match(room, /\.beian-footer a\s*\{[\s\S]*color:\s*#fff/)
  assert.match(room, /\.beian-footer a\s*\{[\s\S]*font-weight:\s*700/)
})
