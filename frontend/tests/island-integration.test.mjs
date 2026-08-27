import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const roomUrl = new URL('../src/views/RoomHomeView.vue', import.meta.url)
const workspaceUrl = new URL('../src/components/island/StudentIslandWorkspace.vue', import.meta.url)
const gameUrl = new URL('../src/game/island/createIslandGame.js', import.meta.url)
const stateUrl = new URL('../src/game/island/islandState.js', import.meta.url)
const navigationUrl = new URL('../src/game/island/islandNavigation.js', import.meta.url)
const packageUrl = new URL('../package.json', import.meta.url)

test('heart island is lazy loaded and Phaser is not imported by the student room', async () => {
  const [room, workspace, state, pkgText] = await Promise.all([
    readFile(roomUrl, 'utf8'),
    readFile(workspaceUrl, 'utf8'),
    readFile(stateUrl, 'utf8'),
    readFile(packageUrl, 'utf8'),
  ])
  const pkg = JSON.parse(pkgText)
  assert.equal(pkg.dependencies.phaser, '3.90.0')
  assert.doesNotMatch(room, /from ['"]phaser['"]/)
  assert.match(room, /openWorkspacePanel\('leisure', \$event\.currentTarget, 'island'\)/)
  assert.match(workspace, /await import\('\.\.\/\.\.\/game\/island\/createIslandGame\.js'\)/)
  assert.match(workspace, /game\?\.destroy\(true\)/)
  assert.match(workspace, /role="dialog"/)
  assert.match(workspace, /aria-modal="true"/)
  assert.match(workspace, /aria-hidden="true"/)
  assert.match(workspace, /role="status"/)
  assert.doesNotMatch(workspace, /经典休闲角/)
  assert.match(workspace, /心岛光景随本地时间自动变化/)
  assert.match(workspace, /schedulePhaseSync/)
  assert.match(workspace, /millisecondsUntilNextIslandPhase/)
  assert.doesNotMatch(workspace, /@click="setTimePhase/)
  assert.match(state, /白天/)
  assert.match(state, /傍晚/)
  assert.match(state, /夜晚/)
})

test('island provides real movement, destinations and non-diagnostic agent boundaries', async () => {
  const [workspace, game, state, navigation] = await Promise.all([
    readFile(workspaceUrl, 'utf8'),
    readFile(gameUrl, 'utf8'),
    readFile(stateUrl, 'utf8'),
    readFile(navigationUrl, 'utf8'),
  ])
  for (const label of ['咕团家园', '云顶暖房', '月光钓鱼湾', '幸福交换树', '星灯休息台']) assert.match(workspace + game + state, new RegExp(label))
  assert.match(workspace, /ArrowUp/)
  assert.match(workspace, /pointercancel/)
  assert.match(workspace, /setPointerCapture/)
  assert.match(workspace, /window\.addEventListener\('pointerup', stopPointerMoving\)/)
  assert.match(workspace, /const pressedDirections = new Set\(\)/)
  assert.match(workspace, /function handleGameKeyup/)
  assert.match(workspace, /const agentExpanded = ref\(!compactViewport\)/)
  assert.match(workspace, /targetPlaceLabel\.value = place\.label/)
  assert.match(workspace, /正在前往\$\{targetPlaceLabel\.value/)
  assert.match(workspace, /watch\(\(\) => props\.storageScope/)
  assert.match(workspace, /currentState\.value = loadIslandState\(nextScope\)/)
  assert.match(workspace, /let gameGeneration = 0/)
  assert.match(workspace, /let startingPromise = null/)
  assert.match(workspace, /generation === gameGeneration/)
  assert.match(workspace, /activeBridge !== bridge/)
  assert.match(workspace, /createdGame\?\.destroy\(true\)/)
  assert.match(workspace, /bridge = createIslandBridge\(\)/)
  assert.match(workspace, /game\?\.destroy\(true\)/)
  assert.match(game, /this\.input\.on\('pointerdown'/)
  assert.doesNotMatch(game, /createCursorKeys|addKeys\('W,A,S,D'\)/)
  assert.match(game, /Phaser\.Scale\.FIT/)
  assert.match(game, /heart-island-base\.png/)
  assert.match(game, /guguan-idle\.png/)
  assert.match(game, /PHASE_LIGHTING/)
  assert.match(game, /findIslandPath/)
  assert.match(game, /resolveIslandMovement/)
  assert.match(navigation, /ISLAND_BLOCKERS/)
  assert.match(navigation, /directions = \[/)
  assert.match(workspace, /向左上移动/)
  assert.match(workspace, /向右下移动/)
  assert.match(workspace, /garden: 'garden', dock: 'beach', exchange: 'exchange'/)
  assert.match(workspace, /selectActivity\(placeToActivity\[place\]\)/)
  assert.match(workspace, /emit\('activity', place\)/)
  assert.match(workspace, /activityBack\.value\?\.focus/)
  assert.match(workspace, /function dismissArrival/)
  assert.match(game, /targetLabel: place\.label/)
  assert.match(workspace, /不从游戏成绩推断情绪/)
  assert.match(workspace, /不进行心理诊断/)
  assert.match(workspace, /aria-label="心岛地图控制区"/)
  assert.doesNotMatch(workspace + game, /抑郁评分|焦虑评分|量表分数|心理概率/)
})

test('legacy room panels retain focusable dialog boundaries', async () => {
  const room = await readFile(roomUrl, 'utf8')
  for (const key of ['profile', 'treehole', 'report']) {
    assert.match(room, new RegExp(`data-workspace="${key}"[\\s\\S]{0,160}role="dialog"`))
    assert.match(room, new RegExp(`closeWorkspacePanel\\('${key}'\\)`))
  }
})
