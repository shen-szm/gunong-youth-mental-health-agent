import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const room = fs.readFileSync(new URL('../src/views/RoomHomeView.vue', import.meta.url), 'utf8')
const api = fs.readFileSync(new URL('../src/api/chat.js', import.meta.url), 'utf8')
const moodApi = fs.readFileSync(new URL('../src/api/mood.js', import.meta.url), 'utf8')
const backend = fs.readFileSync(new URL('../../backend/api/chat.py', import.meta.url), 'utf8')

test('ordinary student messages never directly open the summary drawer', () => {
  const sendBody = room.slice(room.indexOf('async function sendChatMsg'), room.indexOf('function requestConversationEnd'))
  assert.doesNotMatch(sendBody, /showSupportDrawer\.value = true/)
  assert.match(sendBody, /conversation_signal === 'end_candidate'/)
  assert.match(sendBody, /showEndConfirmation\.value = res\.data\.conversation_signal === 'end_candidate'/)
  assert.match(room, /要结束本次倾诉并生成小结吗/)
  assert.match(room, /生成小结/)
  assert.match(room, /继续聊/)
})

test('summary orb exposes complete, restore, delete and accessible states', () => {
  assert.match(room, /student-summary-orb/)
  assert.match(room, /summaryOrbLabel/)
  assert.match(room, /aria-expanded="showSupportDrawer"/)
  assert.match(room, /getLatestChatSummary/)
  assert.match(room, /deleteChatSummary/)
  assert.match(room, /startChatSession\(true, summarySessionId\.value \|\| null\)/)
  assert.match(room, /aria-label="关闭倾诉面板"/)
  assert.match(room, /:disabled="summaryStatus === 'processing'"/)
  assert.match(room, /prefers-reduced-motion: reduce/)
  assert.match(api, /completeChatSession/)
  assert.match(api, /latest-summary/)
  assert.match(room, /return '\/images\/白天\.png'/)
  assert.match(room, /return '\/images\/夜晚\.png'/)
  assert.doesNotMatch(room, /手机版-(?:白天|傍晚|夜晚)\.jpg/)
})

test('backend uses whole-session strict non-clinical summary workflow', () => {
  for (const agent of ['StudentSafetyGate', 'ConversationObserver', 'EmotionSynthesizer', 'NextStepPlanner', 'StudentResponseReviewer', 'StudentCoordinator']) {
    assert.match(backend, new RegExp(agent))
  }
  assert.match(backend, /StudentConversationSummaryPayload/)
  assert.match(backend, /extra="forbid"/)
  assert.match(backend, /不是心理诊断或量表结果/)
  assert.match(backend, /SUMMARY_TTL_DAYS = 30/)
})

test('student emotion report combines constrained conversation signals and explicit activity feedback', () => {
  assert.match(room, /externalAiConsent/)
  assert.match(room, /student-ai-v1/)
  assert.match(room, /emotion_intensity/)
  assert.match(room, /emotion_basis/)
  assert.match(room, /getEmotionReport\(30\)/)
  assert.match(room, /reportData\.sources/)
  assert.match(room, /latest_conversation\.trajectory/)
  assert.match(moodApi, /baseURL: "\/api\/mood"/)
  assert.match(moodApi, /post\('\/activity-reflection'/)
  assert.match(moodApi, /get\('\/report'/)
})
