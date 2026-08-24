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

test('public footer is readable and excludes production registration details', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')
  const home = await source('frontend/src/views/HomeView.vue')

  for (const page of [room, home]) {
    assert.match(page, /心理健康教育与支持 · 不替代专业服务/)
    assert.doesNotMatch(page, /公安备案|ICP备|beian\.miit\.gov\.cn/)
  }
  assert.match(room, /\.beian-footer\s*\{[\s\S]*background:\s*rgba\(18,\s*24,\s*32,\s*0\.72\)/)
  assert.match(room, /\.beian-footer\s*\{[\s\S]*backdrop-filter:\s*blur\(10px\)/)
  assert.match(room, /\.beian-footer\s*\{[\s\S]*text-shadow:\s*0 1px 2px rgba\(0,\s*0,\s*0,\s*0\.65\)/)
})
