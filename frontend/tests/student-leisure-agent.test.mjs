import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import { isOfflineCompanionUrgent } from '../src/utils/companionSafety.js'

const roomUrl = new URL('../src/views/RoomHomeView.vue', import.meta.url)
const hubUrl = new URL('../src/components/StudentLeisureHub.vue', import.meta.url)
const islandUrl = new URL('../src/components/island/StudentIslandWorkspace.vue', import.meta.url)

test('student room exposes one leisure workspace without restoring the old iframe mini app', async () => {
  const [room, hub, island] = await Promise.all([
    readFile(roomUrl, 'utf8'),
    readFile(hubUrl, 'utf8'),
    readFile(islandUrl, 'utf8'),
  ])

  assert.match(room, /<StudentLeisureHub/)
  assert.match(room, /openWorkspacePanel\('leisure'(?:,|\))/)
  assert.match(room, /leisure: showLeisurePanel/)
  assert.match(room, /v-if="!showSplash && !showLeisurePanel"/)
  assert.match(room, /<StudentIslandWorkspace/)
  assert.match(room, /const leisureWorkspaceMode = ref\('games'\)/)
  assert.match(room, /@open-island="openIslandWorkspace"/)
  assert.match(room, /<KeepAlive>/)
  assert.match(room, /background: linear-gradient\(135deg, rgba\(221, 240, 233, \.34\), rgba\(173, 168, 211, \.24\)\) !important/)
  assert.doesNotMatch(room, /background: rgba\(16, 22, 28, \.78\) !important/)
  assert.match(room, /<span class="bnav-label">探索<\/span>/)
  assert.match(room, /VITE_STUDENT_ISLAND_ALPHA5/)
  assert.doesNotMatch(room, /mini-app-iframe|openMiniApp/)
  assert.match(hub, /小田园/)
  assert.match(hub, /慢钓台/)
  assert.match(hub, /幸福交换树/)
  assert.match(hub, /initialGame/)
  assert.match(hub, /进入心岛漫游/)
  assert.match(hub, /seedTypes/)
  assert.match(hub, /fishBook/)
  assert.match(hub, /role="dialog"/)
  assert.match(hub, /handleDialogKeydown/)
  assert.match(hub, /\$emit\('open-healing'\)/)
  assert.match(island, /打开经典休闲角/)
})

test('leisure games use deterministic local state and explicit student feedback', async () => {
  const hub = await readFile(hubUrl, 'utf8')

  assert.match(hub, /function tendPlot/)
  assert.match(hub, /function castLine/)
  assert.match(hub, /function reelLine/)
  assert.match(hub, /三类|向日葵|胡萝卜|莓果/)
  assert.match(hub, /鱼类图鉴/)
  assert.match(hub, /localStorage\.setItem\(storageKey\.value/)
  assert.match(hub, /const storageKey = computed\(\(\) => normalizedScope\.value \? `shengyu_leisure_v5_\$\{normalizedScope\.value\}` : ''\)/)
  assert.match(hub, /happinessNotes/)
  assert.match(hub, /exchangeHappiness/)
  assert.match(hub, /isOfflineCompanionUrgent\(note\)/)
  assert.match(hub, /tel:12356/)
  assert.match(hub, /tel:110/)
  assert.match(hub, /tel:120/)
  assert.match(hub, /happinessUpdatedAt/)
  assert.match(hub, /HAPPINESS_RETENTION_MS/)
  assert.match(hub, /clearHappinessBook/)
  assert.match(hub, /storageError/)
  assert.match(hub, /if \(!storageKey\.value\) return/)
  assert.match(hub, /watch\(storageKey/)
  assert.doesNotMatch(hub, /props\.storageScope \|\| 'student'/)
  assert.match(hub, /onDeactivated\(clearFishingTimers\)/)
  assert.match(hub, /此刻更想/)
  assert.match(hub, /玩完后，此刻更接近/)
  assert.match(hub, /finishReflection/)
  assert.doesNotMatch(hub, /抑郁|焦虑|心理评分|量表分数|连续签到|排行榜/)
})

test('happiness exchange safety gate blocks direct danger but respects denial and quotation', () => {
  for (const content of ['我不想活了', '我刚刚吞了很多药', '爸爸刚才打我，我不敢回家']) {
    assert.equal(isOfflineCompanionUrgent(content), true, content)
  }
  for (const content of ['我没有不想活，只是今天有点累', '新闻里提到有人想死，我觉得很难过', '谢谢你，我想继续交换小事']) {
    assert.equal(isOfflineCompanionUrgent(content), false, content)
  }
})

test('leisure agent reports verifiable states and keeps psychological boundaries visible', async () => {
  const hub = await readFile(hubUrl, 'utf8')

  for (const step of ['理解主动选择', '确认安全边界', '安排合适玩法', '完成后回看']) {
    assert.match(hub, new RegExp(step))
  }
  assert.match(hub, /不从成绩推断情绪，不做诊断，不设置失败惩罚/)
  assert.match(hub, /不会仅凭游戏成绩判断心理状态/)
  assert.match(hub, /不会自动提供给教师端/)
  assert.doesNotMatch(hub, /进度[^\n]{0,20}\d+%/)
  assert.match(hub, /@media \(prefers-reduced-motion: reduce\)/)
  assert.match(hub, /button:focus-visible/)
  assert.doesNotMatch(hub, /\.leisure-agent \{ order: -1; \}/)
})
