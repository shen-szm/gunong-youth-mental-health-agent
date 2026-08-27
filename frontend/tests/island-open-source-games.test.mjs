import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import { actOnGardenPlot, createGardenLifeState, fulfillGardenOrder, usePetGardenHelp } from '../src/game/island/gardenLifeEngine.js'
import { activityStorageKey, loadActivityState, normalizeActivityState, saveActivityState } from '../src/game/island/islandActivityState.js'

const workspaceUrl = new URL('../src/components/island/StudentIslandWorkspace.vue', import.meta.url)
const gardenUrl = new URL('../src/components/island/IslandGardenGame.vue', import.meta.url)
const fishingUrl = new URL('../src/components/island/IslandFishingGame.vue', import.meta.url)
const happinessUrl = new URL('../src/components/island/IslandHappinessExchange.vue', import.meta.url)
const fishingGameUrl = new URL('../src/game/island/createFishingGame.js', import.meta.url)
const packageUrl = new URL('../package.json', import.meta.url)

test('garden life engine supports tilling planting growth harvesting orders and pet help', () => {
  let state = createGardenLifeState()
  state = actOnGardenPlot(state, 0, 'hoe').state
  state = actOnGardenPlot(state, 0, 'seed', 'sunflower').state
  state = actOnGardenPlot(state, 0, 'water').state
  assert.equal(state.plots[0].crop, 'sunflower')
  assert.equal(state.plots[0].watered, true)
  const helped = usePetGardenHelp(state)
  assert.equal(helped.changed, true)
  state = helped.state
  for (let index = 1; index < 8; index += 1) state = actOnGardenPlot(state, index, 'hoe').state
  state.plots[0].stage = 3
  state = actOnGardenPlot(state, 0, 'harvest').state
  assert.equal(state.harvests, 1)
  state.produce.sunflower = 2
  assert.equal(fulfillGardenOrder(state).changed, true)
})

test('garden actions accept Vue-style proxy state without mutating the source', () => {
  const source = createGardenLifeState()
  const reactiveLikeState = new Proxy(source, {})
  const result = actOnGardenPlot(reactiveLikeState, 0, 'hoe')
  assert.equal(result.changed, true)
  assert.equal(result.state.plots[0].soil, 'tilled')
  assert.equal(source.plots[0].soil, 'grass')
})

test('activity saves are student-scoped and expire happiness text after 30 days', () => {
  const data = new Map()
  const storage = { getItem: key => data.get(key) || null, setItem: (key, value) => data.set(key, value) }
  const now = Date.now()
  const state = normalizeActivityState({ happiness: { notes: [{ text: '今天看见晚霞', createdAt: now }], exchanges: 1 } }, now)
  assert.equal(saveActivityState('101', state, storage), true)
  assert.notEqual(activityStorageKey('101'), activityStorageKey('102'))
  assert.equal(activityStorageKey('student/1'), '')
  assert.deepEqual(loadActivityState('101', storage).happiness.notes, [{ text: '今天看见晚霞', createdAt: now }])
  const expired = normalizeActivityState({ happiness: { notes: [{ text: '旧记录', createdAt: now - 31 * 24 * 60 * 60 * 1000 }, { text: '新记录', createdAt: now }] } }, now)
  assert.deepEqual(expired.happiness.notes, [{ text: '新记录', createdAt: now }])
  assert.equal(saveActivityState('101', expired, storage), true)
  assert.doesNotMatch(data.get(activityStorageKey('101')), /旧记录/)
  const legacy = normalizeActivityState({ happiness: { notes: ['旧格式'], updatedAt: now } }, now)
  assert.deepEqual(legacy.happiness.notes, [{ text: '旧格式', createdAt: now }])
  const failedStorage = { getItem: () => null, setItem: () => { throw new Error('blocked') } }
  assert.equal(saveActivityState('101', state, failedStorage), false)
  const expiredLegacy = normalizeActivityState({ happiness: { notes: ['旧记录'], updatedAt: now - 31 * 24 * 60 * 60 * 1000 } }, now)
  assert.deepEqual(expiredLegacy.happiness.notes, [])
})

test('heart island embeds three full game workflows and audited open-source runtimes', async () => {
  const [workspace, garden, fishing, happiness, fishingGame, pkgText] = await Promise.all([
    readFile(workspaceUrl, 'utf8'), readFile(gardenUrl, 'utf8'), readFile(fishingUrl, 'utf8'), readFile(happinessUrl, 'utf8'), readFile(fishingGameUrl, 'utf8'), readFile(packageUrl, 'utf8'),
  ])
  const pkg = JSON.parse(pkgText)
  assert.equal(pkg.dependencies.phaser, '3.90.0')
  assert.equal(pkg.dependencies.swiper, '^12.2.0')
  assert.match(workspace, /IslandGardenGame/)
  assert.match(workspace, /IslandFishingGame/)
  assert.match(workspace, /IslandHappinessExchange/)
  assert.match(garden, /岛民委托/)
  assert.match(garden, /请咕团帮忙浇水/)
  assert.doesNotMatch(garden, /合并种植|向上合并|2048/)
  assert.match(fishingGame, /Phaser\.Scene/)
  assert.match(fishingGame, /this\.time\.delayedCall/)
  assert.match(fishing, /控落点、抢提竿、稳住鱼线/)
  assert.match(happiness, /from 'swiper\/vue'/)
  assert.match(happiness, /place-self: center/)
  assert.match(happiness, /isOfflineCompanionUrgent/)
  assert.match(happiness, /卡片由系统预写，不是其他学生的实时分享/)
  assert.doesNotMatch(workspace, /经典休闲角<\/button>/)
})

test('clicking the current island destination immediately opens its arrival interaction', async () => {
  const islandGame = await readFile(new URL('../src/game/island/createIslandGame.js', import.meta.url), 'utf8')
  assert.match(islandGame, /if \(!this\.target\) this\.interact\(\)/)
})
