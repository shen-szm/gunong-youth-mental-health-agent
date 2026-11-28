import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const read = path => fs.readFileSync(new URL(path, import.meta.url), 'utf8')

const globalStyles = read('../src/style.css')
const room = read('../src/views/RoomHomeView.vue')
const rail = read('../src/components/StudentAgentRail.vue')
const actionBar = read('../src/components/RoomActionBar.vue')
const teacher = read('../src/views/AdminView.vue')

test('desktop student room uses one restrained warm material system', () => {
  assert.match(globalStyles, /--ui-forest-950/)
  assert.match(globalStyles, /--ui-radius-panel/)
  assert.match(room, /@media \(min-width: 900px\)[\s\S]*?--room-control:/)
  assert.match(room, /\.lobby-card \{[\s\S]*?backdrop-filter: blur\(14px\)/)
  assert.match(room, /\.lobby-pet-halo \{[\s\S]*?radial-gradient\(circle, var\(--lobby-glow\)/)
  assert.match(room, /var\(--ui-gold-300/)
  assert.match(room, /\.lobby-primary-cta:focus-visible,[\s\S]*?outline: 2px solid var\(--lobby-gold\)/)
  assert.match(actionBar, /Desktop-only room command surface/)
})

test('agent remains manually opened and exposes the latest verified event while folded', () => {
  assert.doesNotMatch(room, /showAgentRail\.value = true/)
  assert.match(rail, /state\.lastEvent \|\| '等待你开始表达'/)
  assert.match(rail, /aria-expanded="open"/)
  assert.match(rail, /v-if="open"/)
  assert.match(rail, /\.agent-step-list::before/)
  assert.match(rail, /max-width: 1087px[\s\S]*?width: 188px/)
  assert.match(rail, /max-width: 1235px[\s\S]*?width: 320px/)
  const compactLeftAt900 = 900 - 18 - 188
  const centeredChatRightAt900 = (900 + 480) / 2
  assert.ok(compactLeftAt900 > centeredChatRightAt900, 'compact Agent control must not overlap a 480px centered chat panel at 900px')
  assert.match(rail, /web frosted-glass approximation/)
})

test('teacher desktop workbench keeps product density and limits glass to the toolbar', () => {
  assert.match(teacher, /@media \(min-width: 761px\)/)
  assert.match(teacher, /Product UI stays familiar and dense/)
  assert.match(teacher, /\.teacher-topbar[\s\S]*?backdrop-filter: blur\(22px\)/)
  assert.match(teacher, /\.workspace > \.panel[\s\S]*?box-shadow: none/)
  assert.match(teacher, /\.primary-btn:hover[\s\S]*?background: #28594d/)
  assert.match(teacher, /\.teacher-sidebar button:focus-visible \{ outline-color: #f5dda0/)
  assert.match(teacher, /--teacher-sidebar: var\(--ui-forest-950/)
})
