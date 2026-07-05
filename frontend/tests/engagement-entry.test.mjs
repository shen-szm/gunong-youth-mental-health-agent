import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..')

async function source(path) {
  return readFile(join(root, path), 'utf8')
}

test('room home offers first-run guidance for new visitors', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /first-run-guide/)
  assert.match(room, /第一次来这里，可以这样开始/)
  assert.match(room, /点电脑，说一句今天的感受/)
  assert.match(room, /goToChat\(\)/)
  assert.match(room, /dismissFirstRunGuide/)
  assert.match(room, /shengyu_first_run_guide_dismissed/)
})

test('room home provides a daily emotional ritual card with return reasons', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /daily-ritual-card/)
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
