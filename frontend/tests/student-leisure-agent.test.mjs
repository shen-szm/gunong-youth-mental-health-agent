import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import { isOfflineCompanionUrgent } from '../src/utils/companionSafety.js'

const roomUrl = new URL('../src/views/RoomHomeView.vue', import.meta.url)
const islandUrl = new URL('../src/components/island/StudentIslandWorkspace.vue', import.meta.url)
const gardenUrl = new URL('../src/components/island/IslandGardenGame.vue', import.meta.url)
const fishingUrl = new URL('../src/components/island/IslandFishingGame.vue', import.meta.url)
const happinessUrl = new URL('../src/components/island/IslandHappinessExchange.vue', import.meta.url)
const activityStateUrl = new URL('../src/game/island/islandActivityState.js', import.meta.url)

test('student room exposes Heart Island as the single leisure workspace', async () => {
  const [room, island] = await Promise.all([
    readFile(roomUrl, 'utf8'),
    readFile(islandUrl, 'utf8'),
  ])

  assert.doesNotMatch(room, /<StudentLeisureHub/)
  assert.match(room, /openWorkspacePanel\('leisure'(?:,|\))/)
  assert.match(room, /leisure: showLeisurePanel/)
  assert.match(room, /v-if="!showSplash && !showLeisurePanel"/)
  assert.match(room, /<StudentIslandWorkspace/)
  assert.match(room, /@safety="handleLeisureSafetySignal"/)
  assert.match(room, /createChatSafetyHandoff\('happiness_exchange'\)/)
  assert.match(room, /pendingSafetyHandoff/)
  assert.doesNotMatch(room, /leisureWorkspaceMode/)
  assert.doesNotMatch(room, /@open-island="openIslandWorkspace"/)
  assert.match(room, /background: linear-gradient\(135deg, rgba\(221, 240, 233, \.34\), rgba\(173, 168, 211, \.24\)\) !important/)
  assert.doesNotMatch(room, /background: rgba\(16, 22, 28, \.78\) !important/)
  assert.match(room, /<span class="bnav-label">探索<\/span>/)
  assert.doesNotMatch(room, /VITE_STUDENT_ISLAND_ALPHA5/)
  assert.doesNotMatch(room, /mini-app-iframe|openMiniApp/)
  assert.doesNotMatch(island, /经典休闲角/)
  assert.match(island, /IslandGardenGame/)
  assert.match(island, /IslandFishingGame/)
  assert.match(island, /IslandHappinessExchange/)
})

test('leisure games use deterministic local state and explicit student feedback', async () => {
  const [island, garden, fishing, happiness, state] = await Promise.all([
    readFile(islandUrl, 'utf8'), readFile(gardenUrl, 'utf8'), readFile(fishingUrl, 'utf8'),
    readFile(happinessUrl, 'utf8'), readFile(activityStateUrl, 'utf8'),
  ])
  assert.match(garden, /向左合并/)
  assert.match(garden, /收获成熟作物/)
  assert.match(fishing, /鱼类图鉴/)
  assert.match(fishing, /round-complete/)
  assert.match(happiness, /isOfflineCompanionUrgent\(note\)/)
  assert.match(happiness, /tel:12356/)
  assert.match(happiness, /清空此设备记录/)
  assert.match(state, /createdAt/)
  assert.match(state, /HAPPINESS_RETENTION_MS/)
  assert.match(island, /结束这一小轮后，此刻更接近/)
  assert.match(island, /finishReflection/)
  assert.doesNotMatch(`${island}${garden}${fishing}${happiness}`, /心理评分|量表分数|连续签到|排行榜/)
})

test('happiness exchange safety gate blocks direct danger but respects denial and quotation', () => {
  for (const content of ['我不想活了', '我刚刚吞了很多药', '爸爸刚才打我，我不敢回家', '朋友说他想死了，我也想死了', '我没有想死，但现在我想死了', '哥哥拿刀威胁我', '爸爸用皮带抽我', '哥哥把我关在屋里不让我出去', '我被爸爸打了', '叔叔逼我和他发生关系']) {
    assert.equal(isOfflineCompanionUrgent(content), true, content)
  }
  for (const content of ['我没有不想活，只是今天有点累', '新闻里提到有人想死，我觉得很难过', '谢谢你，我想继续交换小事']) {
    assert.equal(isOfflineCompanionUrgent(content), false, content)
  }
})

test('leisure agent reports verifiable states and keeps psychological boundaries visible', async () => {
  const island = await readFile(islandUrl, 'utf8')

  for (const step of ['理解你的选择', '确认安全边界', '组织合适玩法', '观察过程反馈', '整理下一步']) {
    assert.match(island, new RegExp(step))
  }
  assert.match(island, /不从游戏成绩推断情绪，不进行心理诊断/)
  assert.match(island, /aria-current="index === agentStepIndex \? 'step'/)
  assert.match(island, /class="sr-only" role="status" aria-live="polite">\{\{ agentText \}\}/)
  assert.match(island, /activityPlayed && !safetyLocked/)
  assert.match(island, /emit\('safety'/)
  assert.doesNotMatch(island, /进度[^\n]{0,20}\d+%/)
  assert.match(island, /@media \(prefers-reduced-motion: reduce\)/)
  assert.match(island, /button:focus-visible/)
})
