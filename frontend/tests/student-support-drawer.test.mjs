import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const room = fs.readFileSync(new URL('../src/views/RoomHomeView.vue', import.meta.url), 'utf8')
const chatApi = fs.readFileSync(new URL('../../backend/api/chat.py', import.meta.url), 'utf8')

test('student support drawer is additive and follows a safe chat reply', () => {
  assert.match(room, /student-support-drawer/)
  assert.match(room, /我听到的是——/)
  assert.match(room, /先被听见/)
  assert.match(room, /理清这件事/)
  assert.match(room, /做一个小行动/)
  assert.match(room, /我想找人帮忙/)
  assert.match(room, /res\.data\.emotion !== '需要立即协助'/)
  assert.match(chatApi, /_build_student_support/)
})

test('student action can be edited, cycled, declined and stored', () => {
  assert.match(room, /editingSupportSummary/)
  assert.match(room, /cycleSupportAction/)
  assert.match(room, /declineSupportAction/)
  assert.match(room, /shengyu_student_micro_actions_/)
  assert.match(room, /shengyu_student_help_cards_/)
  assert.match(room, /系统不会自动通知任何人/)
  assert.match(room, /supportCloseButton/)
})

test('student drawer uses an opaque-enough dark surface and readable secondary text', () => {
  assert.match(room, /rgba\(18, 21, 27, \.96\)/)
  assert.match(room, /rgba\(27, 25, 32, \.94\)/)
  assert.match(room, /support-needs legend[^}]+rgba\(245,240,232,\.88\)/)
  assert.match(room, /support-send-boundary[^}]+rgba\(245,240,232,\.88\)/)
})
