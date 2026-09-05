import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const read = path => fs.readFileSync(new URL(path, import.meta.url), 'utf8')

test('student chat returns a persisted auditable orchestrator run', () => {
  const chat = read('../../backend/api/chat.py')
  const engine = read('../../backend/student_support_engine.py')
  const models = read('../../backend/models.py')
  for (const name of ['StudentSupportRun', 'StudentSupportEvent']) assert.match(models, new RegExp(`class ${name}`))
  for (const tool of [
    'derived_feature_extractor', 'deterministic_safety_rules', 'emotion_feature_synthesizer',
    'local_support_resource_registry', 'xunfei_response_strategy_selector', 'generated_content_validator',
    'student_delivery_formatter', 'urgent_support_router',
  ]) assert.match(engine, new RegExp(tool))
  assert.match(chat, /agent_run: ChatAgentRun/)
  assert.match(chat, /start_chat_support_run/)
  assert.match(chat, /complete_chat_support_run/)
  assert.doesNotMatch(engine, /content=req\.message|message_text|raw_message/)
})

test('student agent API is session scoped and exposes latest run and support timeline', () => {
  const api = read('../../backend/api/student_agent.py')
  assert.match(api, /@router\.get\("\/runs\/latest"/)
  assert.match(api, /@router\.get\("\/runs\/\{run_code\}"/)
  assert.match(api, /run\.user_id != current_user\.id/)
  assert.match(api, /@router\.get\("\/timeline"/)
  assert.match(api, /StudentWellbeingAssessment/)
  assert.match(api, /MoodRecord/)
})

test('desktop agent rail renders verified server events, tools, source and task identity', () => {
  const room = read('../src/views/RoomHomeView.vue')
  const rail = read('../src/components/StudentAgentRail.vue')
  const api = read('../src/api/studentAgent.js')
  assert.match(room, /applyVerifiedAgentRun\(res\.data\.agent_run\)/)
  assert.match(room, /restoreLatestStudentAgentRun/)
  assert.match(rail, /state\.runCode/)
  assert.match(rail, /state\.intentSummary/)
  assert.match(rail, /state\.events/)
  assert.match(rail, /executedTools/)
  assert.match(rail, /map\(event => event\.tool\)/)
  assert.match(rail, /不展示模型私有思维过程/)
  assert.match(api, /\/runs\/latest/)
  assert.match(api, /\/timeline/)
})
