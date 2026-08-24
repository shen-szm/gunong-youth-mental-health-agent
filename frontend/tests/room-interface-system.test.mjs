import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

  const room = fs.readFileSync(new URL('../src/views/RoomHomeView.vue', import.meta.url), 'utf8')
const actionBar = fs.readFileSync(new URL('../src/components/RoomActionBar.vue', import.meta.url), 'utf8')

test('student room uses one scene action system instead of stacked home cards', () => {
  const template = room.slice(0, room.indexOf('<script setup>'))
  assert.match(template, /room-status-bar/)
  assert.match(template, /<RoomActionBar/)
  assert.doesNotMatch(template, /guardian-workbench-entry/)
  assert.doesNotMatch(template, /daily-return-card/)
  assert.doesNotMatch(template, /pet-companion-card/)
  assert.doesNotMatch(template, /global-music-btn/)
  assert.doesNotMatch(template, /weather-float/)
})

test('room hotspots share keyboard and selection behavior', () => {
  for (const id of ['chat', 'trend', 'window', 'music', 'pet', 'daily']) {
    assert.match(room, new RegExp(`selectRoomFeature\\('${id}'`))
  }
  assert.match(room, /<button type="button" :class="\['hot-zone zone-monitor'/)
  assert.match(room, /aria-label="床头：回顾近期情绪"/)
  assert.match(room, /aria-label="窗户：看看窗外"/)
  assert.match(room, /function runSelectedRoomFeature/)
  assert.match(actionBar, /@keydown\.esc/)
  assert.match(actionBar, /focus\(\{ preventScroll: true \}\)/)
  assert.match(actionBar, /querySelector\('\.room-action-moods button'\)/)
  assert.match(room, /focusWithoutScroll\(roomFeatureTrigger\)/)
  assert.match(actionBar, /:disabled="feature\.actionDisabled"/)
  assert.match(room, /function safeRoomPetPosition/)
  assert.match(room, /window\.innerHeight \* \.58/)
  assert.match(room, /const next = safeRoomPetPosition\(event\.clientX, event\.clientY\)/)
  assert.match(room, /\.hot-zone:focus-visible \.hover-tip/)
  assert.match(room, /\.zone-speaker-left \{ top: 46%; left: 26%; width: 12%; height: 12%; \}/)
  assert.match(room, /\.zone-speaker-right \{ display: none; \}/)
})

test('opening a primary workspace closes competing overlays', () => {
  assert.match(room, /function closeRoomWorkspaces/)
  assert.match(room, /Object\.entries\(panels\)/)
  assert.match(room, /function openWorkspacePanel/)
  assert.match(room, /closeRoomWorkspaces\(key\)/)
  assert.match(room, /function closeWorkspacePanel/)
  assert.match(room, /data-workspace="chat"/)
  assert.match(room, /workspaceTrigger\?\.isConnected \? workspaceTrigger : fallback/)
  assert.match(room, /data-workspace="profile" role="dialog"/)
  assert.match(room, /data-workspace="treehole" role="dialog"/)
  assert.match(room, /data-workspace="report" role="dialog"/)
  assert.match(room, /function toggleAgentRail[\s\S]*?closeRoomWorkspaces\('agent'\)/)
  assert.match(room, /async function openSummaryDrawer[\s\S]*?closeRoomWorkspaces\('support'\)/)
})

test('the action system adapts to mobile and reduced motion', () => {
  assert.match(actionBar, /env\(safe-area-inset-bottom\)/)
  assert.match(actionBar, /@media \(max-width: 640px\)/)
  assert.match(actionBar, /@media \(prefers-reduced-motion: reduce\)/)
  assert.match(room, /@media \(max-width: 760px\)[\s\S]*?\.room-status-bar/)
})

test('student trends remain descriptive and unassessed before any expression', () => {
  const template = room.slice(0, room.indexOf('<script setup>'))
  assert.doesNotMatch(template, /平均情绪分/)
  assert.doesNotMatch(room, /状态很好|整体不错|需要关注|近期情绪偏低落/)
  assert.match(room, /描述性整理，不是心理测评/)
  assert.match(room, /riskLevel: 'unassessed'/)
  assert.match(room, /安全信号会优先提示/)
  assert.match(room, /function resetStudentAgentState\(\)[\s\S]*?riskLevel: 'unassessed'[\s\S]*?安全信号会优先提示/)
  assert.doesNotMatch(room, /'焦虑': '😰'/)
})
