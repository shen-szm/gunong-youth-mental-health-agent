import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { pathToFileURL } from 'node:url'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const testDir = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(testDir, '..', '..')

async function source(relativePath) {
  return readFile(path.join(projectRoot, relativePath), 'utf8')
}

test('time of day follows the room day/dusk/night boundaries', async () => {
  const { getTimeOfDay } = await import(
    pathToFileURL(path.join(projectRoot, 'frontend/src/utils/timeOfDay.js')).href
  )

  assert.equal(getTimeOfDay(new Date(2026, 0, 1, 5, 59)), 'night')
  assert.equal(getTimeOfDay(new Date(2026, 0, 1, 6, 0)), 'day')
  assert.equal(getTimeOfDay(new Date(2026, 0, 1, 12, 0)), 'day')
  assert.equal(getTimeOfDay(new Date(2026, 0, 1, 16, 59)), 'day')
  assert.equal(getTimeOfDay(new Date(2026, 0, 1, 17, 0)), 'evening')
  assert.equal(getTimeOfDay(new Date(2026, 0, 1, 19, 59)), 'evening')
  assert.equal(getTimeOfDay(new Date(2026, 0, 1, 20, 0)), 'night')
  assert.equal(getTimeOfDay(new Date(2026, 0, 1, 0, 30)), 'night')
})

test('student subpages share the game backdrop and palette', async () => {
  for (const view of ['StudentChatView.vue', 'TrendView.vue', 'ProfileView.vue']) {
    const page = await source(`frontend/src/views/${view}`)
    assert.match(page, /game-page/, `${view} root uses .game-page`)
    assert.match(page, /:data-part="part"/, `${view} binds data-part`)
    assert.match(page, /import GameBackdrop from/, `${view} imports GameBackdrop`)
    assert.match(page, /<GameBackdrop/, `${view} renders GameBackdrop`)
    assert.match(page, /useTimeOfDay\(\)/, `${view} uses shared time of day`)
  }
})

test('chat page returns to the home page and keeps a pet companion hook', async () => {
  const chat = await source('frontend/src/views/StudentChatView.vue')

  assert.match(chat, /<router-link class="sc-back" to="\/" aria-label="返回首页">/)
  assert.match(chat, /class="sc-pet" to="\/"/)
  assert.match(chat, /readPetCompanion/)
  assert.match(chat, /petImageForStatus/)
  assert.doesNotMatch(chat, /backdrop-filter/)
})

test('chat page finishes the pending room guide after the first reply', async () => {
  const chat = await source('frontend/src/views/StudentChatView.vue')

  assert.match(chat, /const FIRST_RUN_GUIDE_VERSION = '4\.3\.0'/)
  assert.match(chat, /gy_guide_pending_chat/)
  assert.match(chat, /completePendingGuide/)
  assert.match(chat, /shengyu_first_run_guide_completed_version/)
  assert.match(chat, /回首页看看咕团/)
})

test('trend and profile link back to the home page', async () => {
  const trend = await source('frontend/src/views/TrendView.vue')
  const profile = await source('frontend/src/views/ProfileView.vue')

  assert.match(trend, /router\.push\('\/'\)/)
  assert.match(trend, /aria-label="返回首页"/)
  assert.match(trend, /class="trend-pet-note game-card"/)
  assert.match(trend, /const petLine = computed/)
  assert.match(profile, /class="profile-room-link" to="\/"/)
  assert.match(profile, /class="pet-bond-card game-card"/)
  assert.match(profile, /class="hero-art"/)
})

test('game theme defines three light levels and remaps shared tokens', async () => {
  const theme = await source('frontend/src/styles/game-theme.css')
  const main = await source('frontend/src/main.js')

  assert.match(theme, /\.game-page\[data-part="evening"\]/)
  assert.match(theme, /\.game-page\[data-part="night"\]/)
  assert.match(theme, /--game-bg/)
  assert.match(theme, /--m-surface/)
  assert.match(theme, /\.game-card/)
  assert.match(theme, /prefers-reduced-motion/)
  assert.match(main, /import "\.\/styles\/game-theme\.css"/)
})

test('pet companion state is read-only and mirrors the room key', async () => {
  const pet = await source('frontend/src/utils/petCompanion.js')
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(pet, /shengyu_guguan_v5_1_0_alpha_6/)
  assert.match(room, /shengyu_guguan_v5_1_0_alpha_6/)
  assert.doesNotMatch(pet, /localStorage\.setItem/)
  assert.doesNotMatch(pet, /localStorage\.removeItem/)
  for (const stage of ['初遇期', '熟悉期', '默契期']) {
    assert.match(pet, new RegExp(stage))
  }
})

test('app shell exposes the shared sound switch and cocoa dock', async () => {
  const app = await source('frontend/src/App.vue')

  assert.match(app, /class="nav-item nav-sound"/)
  assert.match(app, /onToggleSound/)
  assert.match(app, /toggleBgm/)
  assert.match(app, /subscribeBgm/)
  assert.match(app, /#f0d29a/)
  assert.match(app, /path === '\/admin' \|\| path === '\/teacher-login' \|\| path\.startsWith\('\/guardian'\)/)
})
