import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const testDir = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(testDir, '..', '..')

async function source(relativePath) {
  return readFile(path.join(projectRoot, relativePath), 'utf8')
}

test('student chat view keeps the crisis safety lock', async () => {
  const chat = await source('frontend/src/views/StudentChatView.vue')

  assert.match(chat, /先保持真人支持，不要独处/)
  assert.match(chat, /href="tel:12356"/)
  assert.match(chat, /110 或 120/)
  assert.match(chat, /不能替代真人危机干预/)
  assert.match(chat, /我现在在安全地点，身边没有危险物/)
  assert.match(chat, /我已经联系并和一位可信成年人待在一起/)
  assert.match(chat, /确认已完成安全交接，开始新话题/)
  assert.match(chat, /applyChatSessionStatus\('urgent'\)/)
  assert.match(chat, /handoff === 'failed'/)
})

test('student chat view keeps end confirmation and summary boundaries', async () => {
  const chat = await source('frontend/src/views/StudentChatView.vue')

  assert.match(chat, /要结束本次倾诉并生成小结吗？/)
  assert.match(chat, /会整理整段对话；这不是诊断或量表结果。/)
  assert.match(chat, /class="sc-endconfirm"/)
  assert.match(chat, /cancelConversationEnd">继续聊</)
  assert.match(chat, /completeConversation">生成小结</)
  assert.match(chat, /删除后将无法再次查看这份小结。聊天原文不会因此删除，确认删除吗？/)
})

test('support drawer keeps the no-auto-notify boundary', async () => {
  const chat = await source('frontend/src/views/StudentChatView.vue')

  assert.match(chat, /系统不会自动通知任何人。确认后会生成一张求助卡，由你决定何时当面给对方看。/)
  assert.match(chat, /这张卡不会自动发送/)
  assert.match(chat, /建议尽快接入真人专业支持/)
})

test('chat page sends messages with idempotency and ported lifecycle', async () => {
  const chat = await source('frontend/src/views/StudentChatView.vue')

  assert.match(chat, /const requestKey = globalThis\.crypto\?\.randomUUID\?\.\(\)/)
  assert.match(chat, /sendMessage\(Number\(userStore\.userId\), msg, 'text', chatSessionId\.value, requestKey\)/)
  assert.match(chat, /ensureStudentSession\(true\)/)
  assert.match(chat, /startChatSession/)
  assert.match(chat, /getChatHistory/)
  assert.match(chat, /loadLatestConversationSummary/)
  assert.match(chat, /基于本轮表达的非诊断性情绪线索/)
})

test('student chat view stays glass-free and notes its ported origin', async () => {
  const chat = await source('frontend/src/views/StudentChatView.vue')

  assert.doesNotMatch(chat, /backdrop-filter/)
  assert.match(chat, /RoomHomeView\.vue/)
})
