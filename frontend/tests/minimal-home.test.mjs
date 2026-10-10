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

test('minimal home keeps two primary entries and legacy room stays reachable', async () => {
  const router = await source('frontend/src/router.js')
  const home = await source('frontend/src/views/MinimalHomeView.vue')

  assert.match(router, /path: "\/", name: "Home", component: MinimalHomeView/)
  assert.match(router, /path: "\/room", name: "Room", component: RoomHomeView/)
  assert.match(router, /path: "\/chat", name: "Chat", component: StudentChatView/)

  assert.match(home, /class="m-entry is-primary" @click="goChat"/)
  assert.match(home, /<strong>倾诉<\/strong>/)
  assert.match(home, /class="m-entry" @click="showMoodSheet = true"/)
  assert.match(home, /<strong>记录心情<\/strong>/)
  assert.match(home, /router\.push\('\/chat'\)/)
})

test('secondary features collapse into the more panel', async () => {
  const home = await source('frontend/src/views/MinimalHomeView.vue')

  assert.match(home, /class="m-more-toggle"/)
  assert.match(home, /id="m-more-grid" class="m-more-grid"/)
  for (const label of ['咕团', '心岛', '音乐', '树洞', '出去看看']) {
    assert.match(home, new RegExp(`>${label}<`))
  }
  assert.match(home, /import MoodRecordSheet from '\.\.\/components\/student\/MoodRecordSheet\.vue'/)
})

test('minimal home drops glassmorphism but keeps splash and beian footer', async () => {
  const home = await source('frontend/src/views/MinimalHomeView.vue')

  assert.doesNotMatch(home, /backdrop-filter/)
  assert.match(home, /class="m-splash"/)
  assert.match(home, /轻触，开始今天的倾诉/)
  assert.match(home, /href="https:\/\/beian\.miit\.gov\.cn\/"/)
  assert.match(home, />粤ICP备2026048986号-2<\/a>/)
  assert.match(home, /粤公网安备44011202003950号/)
})

test('bottom navigation shrinks to three items', async () => {
  const app = await source('frontend/src/App.vue')

  assert.match(app, /'home-full': route\.path === '\/'/)
  assert.match(app, /'room-full': route\.path === '\/room'/)
  assert.match(app, /'chat-full': route\.path === '\/chat'/)
  assert.match(app, /<span class="nav-label">首页<\/span>/)
  assert.match(app, /<span class="nav-label">回顾<\/span>/)
  assert.match(app, /<span class="nav-label">我的<\/span>/)
  assert.doesNotMatch(app, /<span class="nav-label">倾诉<\/span>/)
})

test('mood record sheet keeps five non-diagnostic emotions', async () => {
  const sheet = await source('frontend/src/components/student/MoodRecordSheet.vue')

  for (const label of ['开心', '平静', '焦虑', '难过', '愤怒']) {
    assert.match(sheet, new RegExp(`label: '${label}'`))
  }
  assert.match(sheet, /记录只用于你自己的情绪回顾，不是心理测评。/)
  assert.match(sheet, /import \{ recordMood \} from '\.\.\/\.\.\/api\/mood'/)
})
