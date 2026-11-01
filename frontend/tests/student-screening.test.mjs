import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const component = await readFile(new URL('../src/components/StudentScreeningCard.vue', import.meta.url), 'utf8')
const api = await readFile(new URL('../src/api/screening.js', import.meta.url), 'utf8')
const chatView = await readFile(new URL('../src/views/StudentChatView.vue', import.meta.url), 'utf8')
const adminView = await readFile(new URL('../src/views/AdminView.vue', import.meta.url), 'utf8')
const engine = await readFile(new URL('../../backend/screening_engine.py', import.meta.url), 'utf8')

test('screening card renders the nine standard items and four frequency options', () => {
  assert.match(component, /v-for="item in schema\.items"/)
  assert.match(component, /v-for="option in schema\.options"/)
  assert.match(component, /v-model\.number="answers\[item\.id\]"/)
  const itemCount = (engine.match(/\{"id": \d, "text":/g) || []).length
  assert.equal(itemCount, 9)
  assert.match(engine, /完全不会/)
  assert.match(engine, /好几天/)
  assert.match(engine, /一半以上的天数/)
  assert.match(engine, /几乎每天/)
})

test('screening card discloses teacher visibility, local scoring, retention and deletion', () => {
  assert.match(component, /老师可以看到分级、总分和填写时间/)
  assert.match(component, /看不到每道题的答案/)
  assert.match(component, /不发送给外部模型/)
  assert.match(component, /90天/)
  assert.match(component, /筛查不是诊断/)
  assert.match(component, /总分 \{\{ result\.total_score \}\}\/27/)
  assert.match(component, /12356/)
  assert.match(component, /12356\/110\/120/)
  assert.match(component, /删除本次结果/)
  assert.match(component, /以后再说/)
  assert.match(component, /gy_screening_skip_until/)
  assert.match(component, /deleteScreening/)
  assert.match(component, /数据与边界说明/)
  assert.match(component, /<template v-if="introExpanded">[\s\S]*?sc-screening-disclosure[\s\S]*?sc-screening-boundary/)
})

test('screening items9 hands off to the existing urgent safety flow', () => {
  assert.match(component, /emit\('urgent'/)
  assert.match(component, /urgent_session_id/)
  assert.match(chatView, /import StudentScreeningCard from '\.\.\/components\/StudentScreeningCard\.vue'/)
  assert.match(chatView, /<StudentScreeningCard/)
  assert.match(chatView, /@urgent="handleScreeningUrgent"/)
  assert.match(chatView, /function handleScreeningUrgent/)
  assert.match(chatView, /applyChatSessionStatus\('urgent'\)/)
  assert.match(chatView, /screeningCard\.value\?\.refresh\(\)/)
})

test('screening API client is session scoped and supports delete', () => {
  assert.match(api, /baseURL: '\/api\/screening'/)
  assert.match(api, /get\('\/schema'\)/)
  assert.match(api, /post\('\/submit'/)
  assert.match(api, /get\('\/latest'\)/)
  assert.match(api, /delete\(`\/\$\{runCode\}`\)/)
  assert.doesNotMatch(api, /user_id/)
})

test('high screening scores can be acknowledged to restore chat without deleting the result', () => {
  assert.match(api, /acknowledgeScreening/)
  assert.match(api, /post\('\/acknowledge'/)
  assert.match(api, /contacted_trusted_adult/)
  assert.match(component, /emit\('updated'/)
  assert.match(chatView, /@updated="handleScreeningUpdated"/)
  assert.match(chatView, /getLatestScreening/)
  assert.match(chatView, /acknowledgeScreening/)
  assert.match(chatView, /showProfessionalNotice/)
  assert.match(chatView, /risk_level === 'professional'/)
  assert.match(chatView, /我已知晓并已联系可信成年人/)
  assert.match(chatView, /筛查结果正在影响聊天/)
  assert.match(chatView, /确认后会恢复普通对话，筛查结果仍保留/)
  assert.match(chatView, /acknowledgeProfessionalScreening/)
  assert.match(chatView, /await loadScreeningNotice\(\)/)
})

test('urgent safety panel explains why resolve stays disabled', () => {
  assert.match(chatView, /sc-resolve-hint/)
  assert.match(chatView, /请先勾选以上两项，确认你已在安全地点并已联系可信成年人/)
})

test('screening form shows progress and selected answers', () => {
  assert.match(component, /已答 \{\{ answeredCount \}\}\/\{\{ schema\.items\.length \}\}/)
  assert.match(component, /role="progressbar"/)
  assert.match(component, /label:has\(input:checked\)/)
  assert.match(component, /scrollIntoView/)
})

test('screening result stays visible during a screening-triggered urgent handoff', () => {
  assert.match(chatView, /screeningUrgentActive/)
  assert.match(chatView, /:paused="chatUrgentLocked"/)
  assert.match(chatView, /!chatUrgentLocked \|\| screeningUrgentActive/)
  assert.match(component, /state === 'intro' && !paused/)
  assert.match(component, /state === 'form' && !paused/)
  assert.match(component, /完成安全交接后可以重新筛查或删除本次结果/)
})

test('teacher portal shows screening band and total without answers or risk grades', () => {
  assert.match(adminView, /筛查 \{\{ student\.screening\.band_label \}\} \{\{ student\.screening\.total_score \}\}\/27/)
  assert.match(adminView, /workProduct\.screening_summary/)
  assert.match(adminView, /本次筛查结果|最近一次筛查结果/)
  assert.match(adminView, /screening_summary\.band_label/)
  assert.match(adminView, /screening_summary\.total_score/)
  assert.match(adminView, /第9题安全标记/)
  assert.match(adminView, /标准筛查/)
  assert.match(adminView, /不是诊断/)
  assert.match(adminView, /不得用于纪律处理或贴标签/)
  assert.doesNotMatch(adminView, /做事时提不起劲/)
  assert.doesNotMatch(adminView, /高风险|中风险|低风险/)
  assert.doesNotMatch(adminView, /screening_summary\.answers/)
})
