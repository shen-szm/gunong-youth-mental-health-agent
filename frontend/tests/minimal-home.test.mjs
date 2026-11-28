import assert from 'node:assert/strict'
import { access, readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const testDir = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(testDir, '..', '..')

async function source(relativePath) {
  return readFile(path.join(projectRoot, relativePath), 'utf8')
}

test('room is the single student entry and legacy /room redirects home', async () => {
  const router = await source('frontend/src/router.js')

  assert.match(router, /path: "\/", name: "Home", component: RoomHomeView/)
  assert.match(router, /path: "\/room", redirect: "\/"/)
  assert.match(router, /path: "\/chat", name: "Chat", component: StudentChatView/)
  assert.doesNotMatch(router, /MinimalHomeView/)
})

test('minimal home view is removed', async () => {
  await assert.rejects(access(path.join(projectRoot, 'frontend/src/views/MinimalHomeView.vue')))
})

test('app shell treats the room as full bleed and docks only subpages', async () => {
  const app = await source('frontend/src/App.vue')

  assert.match(app, /'room-full': route\.path === '\/'/)
  assert.doesNotMatch(app, /'home-full'/)
  assert.doesNotMatch(app, /'room-full': route\.path === '\/room'/)
  assert.match(app, /'chat-full': route\.path === '\/chat'/)
  assert.match(app, /\['\/chat', '\/trend', '\/profile'\]\.includes\(route\.path\)/)
  assert.match(app, /<span class="nav-label">首页<\/span>/)
  assert.match(app, /<span class="nav-label">倾诉<\/span>/)
  assert.match(app, /<span class="nav-label">回顾<\/span>/)
  assert.match(app, /<span class="nav-label">我的<\/span>/)
  assert.match(app, /<span class="nav-label">声音<\/span>/)
  assert.match(app, /import \{ isBgmOn, stopBgm, subscribeBgm, toggleBgm \} from "\.\/utils\/bgm"/)
  assert.match(app, /\.room-full \.build-badge,[\s\S]*\.profile-full \.build-badge/)
})

test('profile hosts the quick mood entry and bond card', async () => {
  const profile = await source('frontend/src/views/ProfileView.vue')

  assert.match(profile, /import MoodRecordSheet from '\.\.\/components\/student\/MoodRecordSheet\.vue'/)
  assert.match(profile, /<MoodRecordSheet v-if="showMoodSheet"/)
  assert.match(profile, /class="menu-card mood-entry-card"/)
  assert.match(profile, /showMoodSheet = true/)
  assert.match(profile, /class="pet-bond-card game-card"/)
  assert.match(profile, /@saved="onMoodSaved"/)
  assert.match(profile, /loadStats\(\)/)
})

test('mood record sheet uses the seven standard emotions in order', async () => {
  const sheet = await source('frontend/src/components/student/MoodRecordSheet.vue')
  const labels = ['愤怒', '厌恶', '恐惧', '开心', '中性', '悲伤', '惊讶']

  let lastIndex = -1
  for (const label of labels) {
    const index = sheet.indexOf(`label: '${label}'`)
    assert.ok(index > lastIndex, `${label} should appear in the requested order`)
    lastIndex = index
  }
  assert.equal((sheet.match(/\{ label: '/g) || []).length, 7)
  for (const emoji of ['😠', '🤢', '😨', '😊', '😐', '😢', '😲']) {
    assert.match(sheet, new RegExp(emoji))
  }
  assert.doesNotMatch(sheet, /label: '平静'|label: '焦虑'|label: '难过'/)
  assert.match(sheet, /grid-template-columns: repeat\(4, 1fr\)/)
  assert.match(sheet, /记录只用于你自己的情绪回顾，不是心理测评。/)
  assert.match(sheet, /import \{ recordMood \} from '\.\.\/\.\.\/api\/mood'/)
})
