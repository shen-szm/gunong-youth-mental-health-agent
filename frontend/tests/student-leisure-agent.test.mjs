import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const roomUrl = new URL('../src/views/RoomHomeView.vue', import.meta.url)
const hubUrl = new URL('../src/components/StudentLeisureHub.vue', import.meta.url)

test('student room exposes one leisure workspace without restoring the old iframe mini app', async () => {
  const [room, hub] = await Promise.all([
    readFile(roomUrl, 'utf8'),
    readFile(hubUrl, 'utf8'),
  ])

  assert.match(room, /<StudentLeisureHub/)
  assert.match(room, /openWorkspacePanel\('leisure'\)/)
  assert.match(room, /leisure: showLeisurePanel/)
  assert.match(room, /v-if="!showSplash && !showLeisurePanel"/)
  assert.match(room, /<span class="bnav-label">休闲<\/span>/)
  assert.doesNotMatch(room, /mini-app-iframe|openMiniApp/)
  assert.match(hub, /小田园/)
  assert.match(hub, /慢钓台/)
  assert.match(hub, /\$emit\('open-healing'\)/)
})

test('leisure games use deterministic local state and explicit student feedback', async () => {
  const hub = await readFile(hubUrl, 'utf8')

  assert.match(hub, /function tendPlot/)
  assert.match(hub, /function castLine/)
  assert.match(hub, /function reelLine/)
  assert.match(hub, /localStorage\.setItem\(storageKey\.value/)
  assert.match(hub, /此刻更想/)
  assert.match(hub, /玩完后，此刻更接近/)
  assert.match(hub, /finishReflection/)
  assert.doesNotMatch(hub, /抑郁|焦虑|心理评分|量表分数|连续签到|排行榜/)
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
})
