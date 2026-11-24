import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const source = (path) => readFile(join(root, path), 'utf8')

test('companion memory API exposes list, single delete and clear all', async () => {
  const api = await source('frontend/src/api/chat.js')
  assert.match(api, /export function getCompanionMemories/)
  assert.match(api, /instance\.get\("\/memories"\)/)
  assert.match(api, /export function deleteCompanionMemory/)
  assert.match(api, /instance\.delete\(`\/memories\/\$\{encodeURIComponent\(memoryCode\)\}`\)/)
  assert.match(api, /export function clearCompanionMemories/)
  assert.match(api, /instance\.delete\("\/memories"\)/)
})

test('both student chat surfaces expose the memory panel', async () => {
  const chat = await source('frontend/src/views/StudentChatView.vue')
  const room = await source('frontend/src/views/RoomHomeView.vue')
  assert.match(chat, /CompanionMemorySheet/)
  assert.match(chat, /查看小满记得的事/)
  assert.match(room, /CompanionMemorySheet/)
  assert.match(room, /查看小满记得的事/)
})

test('memory panel is transparent, deletable and bounded', async () => {
  const sheet = await source('frontend/src/components/student/CompanionMemorySheet.vue')
  assert.match(sheet, /小满记得的事/)
  assert.match(sheet, /全部忘记/)
  assert.match(sheet, /最多保留 180 天/)
  assert.match(sheet, /姓名、学校、联系方式和危机内容不会被记住/)
  assert.match(sheet, /deleteCompanionMemory/)
  assert.match(sheet, /clearCompanionMemories/)
  assert.match(sheet, /activateDialog/)
})

test('consent copy discloses cross-session memory before the model is used', async () => {
  const chat = await source('frontend/src/views/StudentChatView.vue')
  const room = await source('frontend/src/views/RoomHomeView.vue')
  for (const view of [chat, room]) {
    assert.match(view, /对话原文会发送给平台接入的 DeepSeek 模型，用于生成本轮回应和本次小结/)
    assert.match(view, /记住少量关于你的小事/)
    assert.match(view, /随时查看或删除/)
  }
})

test('backend keeps memory server-side, consent-gated and user-deletable', async () => {
  const models = await source('backend/models.py')
  const api = await source('backend/api/chat.py')
  const engine = await source('backend/companion_engine.py')
  assert.match(models, /class StudentCompanionMemory/)
  assert.match(models, /student_companion_memories/)
  assert.match(api, /@router\.get\("\/memories"/)
  assert.match(api, /@router\.delete\("\/memories\/\{memory_code\}"/)
  assert.match(api, /@router\.delete\("\/memories"/)
  assert.match(api, /_active_companion_memories/)
  assert.match(api, /clean_memory_candidate/)
  assert.match(engine, /可以悄悄记住的小事/)
  assert.match(engine, /MEMORY_EXPIRY_DAYS = 180/)
  assert.match(engine, /build_memory_instruction/)
})
