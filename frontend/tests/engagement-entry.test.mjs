import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..')

async function source(path) {
  return readFile(join(root, path), 'utf8')
}

test('room home offers first-run teaching for new visitors', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /first-run-guide/)
  assert.match(room, /跟着做两步，就知道怎么用咕哝/)
  assert.match(room, /advanceFirstRunGuide\('chat'\)/)
  assert.match(room, /finishFirstRunGuide\('treehole'\)/)
  assert.match(room, /shengyu_first_run_guide_completed_version/)
})

test('room home provides a daily emotional ritual card after onboarding', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /daily-ritual-card" v-else/)
  assert.match(room, /今日咕哝/)
  assert.match(room, /dailyRitual/)
  assert.match(room, /dailyRitualSeed/)
  assert.match(room, /openDailyRitualAction/)
  assert.match(room, /showTreeHolePanel = true/)
  assert.match(room, /localStorage\.setItem\('shengyu_daily_ritual_seen'/)
})

test('engagement cards are responsive and do not block core room interactions', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /\.engagement-stack/)
  assert.match(room, /pointer-events:\s*none/)
  assert.match(room, /\.daily-ritual-card,[\s\S]*?\.first-run-guide[\s\S]*?pointer-events:\s*auto/)
  assert.match(room, /@media \(max-width: 520px\)[\s\S]*?\.engagement-stack/)
})