import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const roomUrl = new URL('../src/views/RoomHomeView.vue', import.meta.url)
const workspaceUrl = new URL('../src/components/island/StudentIslandWorkspace.vue', import.meta.url)
const gameUrl = new URL('../src/game/island/createIslandGame.js', import.meta.url)
const stateUrl = new URL('../src/game/island/islandState.js', import.meta.url)
const packageUrl = new URL('../package.json', import.meta.url)

test('heart island is lazy loaded and Phaser is not imported by the student room', async () => {
  const [room, workspace, pkgText] = await Promise.all([
    readFile(roomUrl, 'utf8'),
    readFile(workspaceUrl, 'utf8'),
    readFile(packageUrl, 'utf8'),
  ])
  const pkg = JSON.parse(pkgText)
  assert.equal(pkg.dependencies.phaser, '3.90.0')
  assert.doesNotMatch(room, /from ['"]phaser['"]/)
  assert.match(workspace, /await import\('\.\.\/\.\.\/game\/island\/createIslandGame\.js'\)/)
  assert.match(workspace, /game\?\.destroy\(true\)/)
  assert.match(workspace, /role="dialog"/)
  assert.match(workspace, /aria-modal="true"/)
  assert.match(workspace, /aria-hidden="true"/)
  assert.match(workspace, /role="status"/)
})

test('island provides real movement, destinations and non-diagnostic agent boundaries', async () => {
  const [workspace, game, state] = await Promise.all([
    readFile(workspaceUrl, 'utf8'),
    readFile(gameUrl, 'utf8'),
    readFile(stateUrl, 'utf8'),
  ])
  for (const label of ['潮汐小屋', '心田', '慢钓码头', '幸福交换站']) assert.match(workspace + game + state, new RegExp(label))
  assert.match(workspace, /ArrowUp/)
  assert.match(workspace, /pointercancel/)
  assert.match(workspace, /setPointerCapture/)
  assert.match(workspace, /window\.addEventListener\('pointerup', stopPointerMoving\)/)
  assert.match(workspace, /const pressedDirections = new Set\(\)/)
  assert.match(workspace, /function handleGameKeyup/)
  assert.match(game, /this\.input\.on\('pointerdown'/)
  assert.doesNotMatch(game, /createCursorKeys|addKeys\('W,A,S,D'\)/)
  assert.match(game, /Phaser\.Scale\.FIT/)
  assert.match(workspace, /不从走路与成绩推断情绪/)
  assert.match(workspace, /不进行心理诊断/)
  assert.match(workspace, /aria-label="心岛地图控制区"/)
  assert.doesNotMatch(workspace + game, /抑郁评分|焦虑评分|量表分数|心理概率/)
})

test('fallback and legacy panels retain focusable dialog boundaries', async () => {
  const room = await readFile(roomUrl, 'utf8')
  assert.match(room, /function handleIslandFallback/)
  assert.match(room, /focusWithoutScroll\(document\.querySelector\('\.leisure-hub \.leisure-close'\)\)/)
  for (const key of ['profile', 'treehole', 'report']) {
    assert.match(room, new RegExp(`data-workspace="${key}"[\\s\\S]{0,160}role="dialog"`))
    assert.match(room, new RegExp(`closeWorkspacePanel\\('${key}'\\)`))
  }
})
