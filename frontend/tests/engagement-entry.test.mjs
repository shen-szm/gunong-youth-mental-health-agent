import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const GUIDE_TITLE = '\u8ddf\u7740\u63d0\u793a\u70b9\u4e24\u4e0b\uff0c\u9a6c\u4e0a\u4f1a\u7528\u5495\u54dd'
const CLICK_COMPUTER = '\u8bf7\u70b9\u51fb\u623f\u95f4\u91cc\u7684\u7535\u8111'
const CLICK_TREEHOLE = '\u8bf7\u70b9\u51fb\u5e95\u90e8\u5bfc\u822a\u7684\u6811\u6d1e'

async function source(path) {
  return readFile(join(root, path), 'utf8')
}

test('room home offers first-run teaching for new visitors', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /first-run-guide/)
  assert.match(room, new RegExp(GUIDE_TITLE))
  assert.match(room, /handleGuideChatTarget/)
  assert.match(room, /handleGuideTreeholeTarget/)
  assert.match(room, /shengyu_first_run_guide_completed_version/)
})

test('room home provides a daily emotional ritual card after onboarding', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /daily-ritual-card" v-else/)
  assert.match(room, /dailyRitual/)
  assert.match(room, /dailyRitualSeed/)
  assert.match(room, /openDailyRitualAction/)
  assert.match(room, /showTreeHolePanel\.value = true/)
  assert.match(room, /localStorage\.setItem\('shengyu_daily_ritual_seen'/)
})

test('engagement cards are responsive and do not block core room interactions', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /\.engagement-stack/)
  assert.match(room, /pointer-events:\s*none/)
  assert.match(room, /\.daily-ritual-card,[\s\S]*?\.first-run-guide[\s\S]*?pointer-events:\s*auto/)
  assert.match(room, /@media \(max-width: 520px\)[\s\S]*?\.engagement-stack/)
})

test('onboarding highlights the exact room target users should click', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /guide-target-hint/)
  assert.match(room, new RegExp(CLICK_COMPUTER))
  assert.match(room, new RegExp(CLICK_TREEHOLE))
  assert.match(room, /:class="\['hot-zone zone-monitor'/)
  assert.match(room, /'is-guide-target': showFirstRunGuide && onboardingStep === 'chat'/)
  assert.match(room, /@click="handleGuideChatTarget"/)
  assert.match(room, /@click="handleGuideTreeholeTarget"/)
  assert.match(room, /guide-target-badge/)
})

test('air-conditioner and TV mini tools are removed completely', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.doesNotMatch(room, /mini-tools-bar/)
  assert.doesNotMatch(room, /openMiniApp/)
  assert.doesNotMatch(room, /miniAppUrl/)
  assert.doesNotMatch(room, /mini-app-iframe/)
  assert.doesNotMatch(room, /giao\.me\/air/)
  assert.doesNotMatch(room, /giao\.me\/itv/)
})
