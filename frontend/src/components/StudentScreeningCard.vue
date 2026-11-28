<template>
  <section v-if="state === 'intro' && !paused" ref="cardEl" class="sc-screening" aria-labelledby="sc-screening-title">
    <div class="sc-screening-head">
      <span class="sc-screening-kicker">可选 · 约 2 分钟</span>
      <strong id="sc-screening-title">最近两周状态筛查</strong>
      <p>9 个问题，帮你更清楚地看看最近两周的状态。</p>
      <button
        type="button"
        class="sc-screening-more"
        :aria-expanded="introExpanded"
        aria-controls="sc-screening-intro-detail"
        @click="introExpanded = !introExpanded"
      >{{ introExpanded ? '收起说明' : '数据与边界说明' }}</button>
    </div>
    <template v-if="introExpanded">
      <p id="sc-screening-intro-detail" class="sc-screening-disclosure">{{ schema.disclosure }}</p>
      <small class="sc-screening-boundary">{{ schema.boundary || '筛查不是诊断，不能替代专业人员面谈。' }}</small>
    </template>
    <div class="sc-screening-actions">
      <button type="button" class="sc-screening-primary" @click="startForm">开始筛查</button>
      <button type="button" class="sc-screening-ghost" @click="skip">以后再说</button>
    </div>
  </section>

  <section v-else-if="state === 'form' && !paused" ref="cardEl" class="sc-screening" aria-labelledby="sc-screening-title">
    <div class="sc-screening-head">
      <div class="sc-screening-meta">
        <span class="sc-screening-kicker">{{ schema.period }}</span>
        <span class="sc-screening-count" :class="{ 'is-done': answeredCount === schema.items.length }">已答 {{ answeredCount }}/{{ schema.items.length }}</span>
      </div>
      <strong id="sc-screening-title">过去两周，这些情况出现得有多频繁？</strong>
      <div
        class="sc-screening-progress"
        role="progressbar"
        aria-label="已答题目数"
        aria-valuemin="0"
        :aria-valuemax="schema.items.length"
        :aria-valuenow="answeredCount"
      ><i :style="{ width: `${schema.items.length ? (answeredCount / schema.items.length) * 100 : 0}%` }"></i></div>
    </div>
    <ol class="sc-screening-items">
      <li v-for="item in schema.items" :key="item.id">
        <p>{{ item.text }}</p>
        <div class="sc-screening-options">
          <label v-for="option in schema.options" :key="option.value">
            <input
              type="radio"
              :name="`sc-screening-${item.id}`"
              :value="option.value"
              v-model.number="answers[item.id]"
            />
            <span>{{ option.label }}</span>
          </label>
        </div>
      </li>
    </ol>
    <label class="sc-screening-ack">
      <input v-model="disclosureAck" type="checkbox" />
      <span>我已阅读数据说明：老师可以看到分级、总分和填写时间，看不到每道题的答案；结果不发送给外部模型，保留90天且可随时删除。</span>
    </label>
    <p v-if="error" class="sc-screening-error" role="status">{{ error }}</p>
    <div class="sc-screening-actions">
      <button
        type="button"
        class="sc-screening-primary"
        :disabled="!canSubmit || submitting"
        @click="submit"
      >{{ submitting ? '正在计分…' : '提交本次筛查' }}</button>
      <button type="button" class="sc-screening-ghost" :disabled="submitting" @click="cancelForm">先不做了</button>
    </div>
    <small class="sc-screening-boundary">{{ schema.boundary }}</small>
  </section>

  <section v-else-if="state === 'result' && result" ref="cardEl" class="sc-screening" aria-labelledby="sc-screening-title">
    <div class="sc-screening-head">
      <span class="sc-screening-kicker">最近两周状态筛查</span>
      <div class="sc-screening-resultline">
        <strong id="sc-screening-title">本次结果：{{ result.band_label }}</strong>
        <p class="sc-screening-score">总分 {{ result.total_score }}/27</p>
      </div>
    </div>
    <p class="sc-screening-message">{{ result.message }}</p>
    <p v-if="result.item9_positive" class="sc-screening-urgent" role="alert">
      第9题有应答需要被认真对待。请尽快告诉一位可信成年人或学校心理老师；如果正处于危险中，请拨打 110 或 120，也可以拨打 12356。
    </p>
    <p v-else class="sc-screening-hint">可以联系一位可信成年人、学校心理老师或拨打 12356 心理援助热线；如果有即时危险，请拨打 110 或 120。</p>
    <div v-if="result.item9_positive" class="sc-screening-calls" aria-label="紧急求助电话 12356/110/120">
      <a href="tel:12356">拨打 12356</a>
      <a href="tel:110">拨打 110</a>
      <a href="tel:120">拨打 120</a>
    </div>
    <small class="sc-screening-boundary">{{ result.boundary || schema.boundary }}</small>
    <div v-if="!paused" class="sc-screening-actions">
      <button type="button" class="sc-screening-ghost" @click="startForm">重新筛查</button>
      <button
        type="button"
        class="sc-screening-ghost is-danger"
        :class="{ 'is-confirming': deleteConfirm }"
        :disabled="deleting"
        @click="removeResult"
      >
        {{ deleteConfirm ? '确认删除本次结果' : '删除本次结果' }}
      </button>
    </div>
    <small v-else class="sc-screening-hint">完成安全交接后可以重新筛查或删除本次结果。</small>
    <small v-if="deleteConfirm" class="sc-screening-hint">再次点击删除后，本次结果会被删除且答案清空。</small>
    <p v-if="deleteError" class="sc-screening-error" role="status">{{ deleteError }}</p>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import {
  deleteScreening,
  getLatestScreening,
  getScreeningSchema,
  submitScreening,
} from '../api/screening'

const SKIP_KEY = 'gy_screening_skip_until'
const SKIP_DAYS = 7
const props = defineProps({ paused: { type: Boolean, default: false } })
const emit = defineEmits(['urgent', 'updated', 'form-open'])

const state = ref('loading')
watch(state, (value) => emit('form-open', value === 'form'))
const introExpanded = ref(false)
const cardEl = ref(null)
const schema = ref({ items: [], options: [], disclosure: '', boundary: '', period: '过去两周' })
const answers = reactive({})
const disclosureAck = ref(false)
const submitting = ref(false)
const error = ref('')
const result = ref(null)
const deleting = ref(false)
const deleteConfirm = ref(false)
const deleteError = ref('')

const canSubmit = computed(() => {
  if (!disclosureAck.value) return false
  return schema.value.items.every((item) => Number.isInteger(answers[item.id]))
})

const answeredCount = computed(
  () => schema.value.items.filter((item) => Number.isInteger(answers[item.id])).length,
)

async function focusCardTop() {
  await nextTick()
  const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  cardEl.value?.scrollIntoView({ block: 'start', behavior: reduceMotion ? 'auto' : 'smooth' })
}

function resetForm() {
  for (const item of schema.value.items) delete answers[item.id]
  disclosureAck.value = false
  introExpanded.value = false
  error.value = ''
  deleteConfirm.value = false
  deleteError.value = ''
}

function startForm() {
  if (props.paused) return
  resetForm()
  state.value = 'form'
  focusCardTop()
}

function cancelForm() {
  if (submitting.value) return
  resetForm()
  state.value = result.value ? 'result' : 'intro'
  focusCardTop()
}

function skip() {
  try {
    localStorage.setItem(SKIP_KEY, String(Date.now() + SKIP_DAYS * 24 * 60 * 60 * 1000))
  } catch {}
  state.value = 'hidden'
}

function skippedRecently() {
  try {
    return Number(localStorage.getItem(SKIP_KEY) || 0) > Date.now()
  } catch {
    return false
  }
}

function emitUrgent(payload) {
  if (!payload?.safety_active) return
  emit('urgent', { session_id: payload.urgent_session_id || '', item9_positive: true })
}

async function load() {
  try {
    const [schemaRes, latestRes] = await Promise.all([getScreeningSchema(), getLatestScreening()])
    schema.value = schemaRes.data
    const latest = latestRes.data?.screening
    if (latest) {
      result.value = latest
      state.value = 'result'
      emitUrgent(latest)
      emit('updated', latest)
      return
    }
    emit('updated', null)
    state.value = skippedRecently() ? 'hidden' : 'intro'
  } catch {
    state.value = 'hidden'
  }
}

async function refresh() {
  try {
    const res = await getLatestScreening()
    const latest = res.data?.screening
    if (!latest) {
      emit('updated', null)
      return
    }
    result.value = latest
    state.value = 'result'
    emitUrgent(latest)
    emit('updated', latest)
  } catch {}
}

async function submit() {
  if (!canSubmit.value || submitting.value) return
  const payloadAnswers = {}
  for (const item of schema.value.items) payloadAnswers[String(item.id)] = answers[item.id]
  submitting.value = true
  error.value = ''
  try {
    const res = await submitScreening({
      answers: payloadAnswers,
      disclosure_ack: disclosureAck.value,
    })
    result.value = res.data
    deleteConfirm.value = false
    state.value = 'result'
    emitUrgent(res.data)
    emit('updated', res.data)
    focusCardTop()
  } catch (err) {
    const detail = err?.response?.data?.detail
    error.value = typeof detail === 'string' ? detail : '提交失败，请稍后再试。'
  } finally {
    submitting.value = false
  }
}

async function removeResult() {
  if (props.paused || !result.value || deleting.value) return
  if (!deleteConfirm.value) {
    deleteConfirm.value = true
    return
  }
  deleting.value = true
  deleteError.value = ''
  try {
    await deleteScreening(result.value.run_code)
    result.value = null
    deleteConfirm.value = false
    state.value = 'hidden'
    emit('updated', null)
  } catch (err) {
    const detail = err?.response?.data?.detail
    deleteError.value = typeof detail === 'string' ? detail : '暂时无法删除，请稍后再试。'
    deleteConfirm.value = false
  } finally {
    deleting.value = false
  }
}

defineExpose({ refresh })

onMounted(load)
</script>

<style scoped>
.sc-screening {
  position: relative;
  overflow: hidden;
  display: grid;
  gap: 10px;
  padding: 14px 16px;
  border-radius: var(--m-radius-md);
  border: 1px solid var(--m-line);
  background: var(--m-surface);
  box-shadow: 0 1px 2px rgba(34, 48, 43, .04), 0 10px 26px rgba(34, 48, 43, .05);
  scroll-margin-top: 12px;
  animation: m-rise var(--m-enter-dur) var(--m-ease) 90ms backwards;
}
.sc-screening::before {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 3px;
  background: linear-gradient(90deg, var(--m-accent) 0%, rgba(74, 122, 108, .2) 58%, transparent 100%);
}
.sc-screening-head { display: grid; gap: 5px; }
.sc-screening-meta { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.sc-screening-kicker {
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: .08em;
  color: var(--m-accent-strong);
}
.sc-screening-count {
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: .04em;
  color: var(--m-ink-3);
  font-variant-numeric: tabular-nums;
}
.sc-screening-count.is-done { color: var(--m-accent-strong); }
.sc-screening-progress {
  height: 3px;
  margin-top: 4px;
  border-radius: 999px;
  background: rgba(74, 122, 108, .12);
  overflow: hidden;
}
.sc-screening-progress i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--m-accent);
  transition: width var(--m-dur-slow) var(--m-ease);
}
.sc-screening-head strong { font-size: 14px; color: var(--m-ink); }
.sc-screening-head > p, .sc-screening-message {
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--m-ink-2);
}
.sc-screening-resultline { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.sc-screening-resultline strong { font-size: 15px; }
.sc-screening-more {
  justify-self: start;
  padding: 0;
  background: transparent;
  font-size: 11px;
  font-weight: 600;
  color: var(--m-ink-3);
  text-decoration: underline;
  text-decoration-style: dashed;
  text-underline-offset: 3px;
}
.sc-screening-more:hover { color: var(--m-accent-strong); }
.sc-screening-disclosure { font-size: 12px; line-height: 1.7; color: var(--m-ink-2); }
.sc-screening-boundary, .sc-screening-hint { font-size: 11px; line-height: 1.6; color: var(--m-ink-3); }
.sc-screening-score {
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--m-accent-soft);
  font-size: 12.5px;
  font-weight: 700;
  color: var(--m-accent-strong);
  font-variant-numeric: tabular-nums;
}
.sc-screening-items { display: grid; gap: 12px; margin: 0; padding: 0; list-style: none; counter-reset: screening; }
.sc-screening-items > li { counter-increment: screening; display: grid; gap: 7px; }
.sc-screening-items > li > p { font-size: 13px; line-height: 1.6; color: var(--m-ink); }
.sc-screening-items > li > p::before {
  content: counter(screening) ". ";
  color: var(--m-accent-strong);
  font-weight: 600;
}
.sc-screening-options { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }
.sc-screening-options label {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 9px;
  border-radius: 10px;
  border: 1px solid var(--m-line);
  font-size: 12px;
  color: var(--m-ink-2);
  cursor: pointer;
  transition: border-color var(--m-dur-fast) var(--m-ease),
              background var(--m-dur-fast) var(--m-ease),
              color var(--m-dur-fast) var(--m-ease);
}
.sc-screening-options label:hover { border-color: var(--m-accent); background: var(--m-accent-soft); }
.sc-screening-options label:has(input:checked) {
  border-color: var(--m-accent);
  background: var(--m-accent-soft);
  color: var(--m-ink);
  box-shadow: inset 0 0 0 1px var(--m-accent);
}
.sc-screening-options label:focus-within {
  outline: 2px solid rgba(74, 122, 108, .5);
  outline-offset: 2px;
}
.sc-screening-options input { accent-color: var(--m-accent-strong); }
.sc-screening-ack {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--m-ink-2);
}
.sc-screening-ack input { margin-top: 3px; flex: none; }
.sc-screening-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.sc-screening-primary,
.sc-screening-ghost {
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 12.5px;
  border: 1px solid var(--m-line);
  background: var(--m-surface);
  color: var(--m-ink-2);
  transition: border-color var(--m-dur-fast) var(--m-ease),
              background var(--m-dur-fast) var(--m-ease),
              color var(--m-dur-fast) var(--m-ease),
              transform var(--m-dur-fast) var(--m-ease);
}
.sc-screening-ghost:not(:disabled):hover {
  border-color: var(--m-accent);
  background: var(--m-accent-soft);
  color: var(--m-accent-strong);
}
.sc-screening-primary {
  border-color: var(--m-accent);
  background: var(--m-accent);
  color: var(--m-surface);
  font-weight: 600;
}
.sc-screening-primary:not(:disabled):hover {
  border-color: var(--m-accent-strong);
  background: var(--m-accent-strong);
}
.sc-screening-primary:not(:disabled):active,
.sc-screening-ghost:not(:disabled):active { transform: translateY(1px); }
.sc-screening-primary:disabled { opacity: .5; cursor: not-allowed; }
.sc-screening-primary:focus-visible,
.sc-screening-ghost:focus-visible,
.sc-screening-calls a:focus-visible {
  outline: 2px solid rgba(74, 122, 108, .55);
  outline-offset: 2px;
}
.sc-screening-ghost.is-danger { color: #b4544a; }
.sc-screening-ghost.is-danger:not(:disabled):hover {
  border-color: #d9a29a;
  background: #fdf0ed;
  color: #8f3f36;
}
.sc-screening-ghost.is-danger.is-confirming {
  border-color: #d9a29a;
  background: #fdf0ed;
  color: #8f3f36;
  font-weight: 600;
}
.sc-screening-urgent {
  padding: 10px 12px;
  border-radius: 10px;
  background: #FDEEEA;
  border: 1px solid #EFC9C0;
  font-size: 12.5px;
  line-height: 1.7;
  color: #7A3A32;
}
.sc-screening-calls { display: flex; flex-wrap: wrap; gap: 8px; }
.sc-screening-calls a {
  padding: 7px 12px;
  border-radius: 999px;
  border: 1px solid var(--m-line);
  font-size: 12px;
  color: var(--m-accent-strong);
  text-decoration: none;
}
.sc-screening-error { font-size: 12px; color: #b4544a; }

@media (max-width: 480px) {
  .sc-screening { padding: 13px 13px; }
  .sc-screening-options { gap: 5px; }
  .sc-screening-options label { padding: 9px 10px; font-size: 12.5px; }
  .sc-screening-primary,
  .sc-screening-ghost { padding: 9px 14px; }
}

/* 像素皮肤 3.0 · 状态筛查卡 */
.sc-screening {
  border: 2px solid var(--px-line, var(--m-line));
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow, var(--m-shadow));
}
.sc-screening::before { height: 2px; }
.sc-screening-kicker { font-family: var(--px-font); font-size: 11px; }
.sc-screening-more { font-family: var(--px-font); }
.sc-screening-more:focus-visible {
  outline: 3px dashed var(--px-gold, var(--m-accent));
  outline-offset: 3px;
}
.sc-screening-head strong { font-family: var(--px-font); font-size: 15px; }
.sc-screening-count { font-family: var(--px-font); }
.sc-screening-progress {
  height: 6px;
  border: 1px solid var(--px-line, var(--m-line));
  border-radius: 0;
}
.sc-screening-progress i { border-radius: 0; }
.sc-screening-score { border-radius: 4px; font-family: var(--px-font); }
.sc-screening-options label {
  border: 2px solid var(--px-line, var(--m-line));
  border-radius: 4px;
  transition: border-color 160ms steps(2, end), background 160ms steps(2, end), color 160ms steps(2, end), transform 160ms steps(2, end);
}
.sc-screening-options label:hover { transform: translate(-1px, -1px); }
.sc-screening-options label:has(input:checked) {
  border-color: var(--px-gold, var(--m-accent));
  box-shadow: 2px 2px 0 var(--px-shadow, var(--m-shadow));
}
.sc-screening-options label:focus-within {
  outline: 3px dashed var(--px-gold, var(--m-accent));
  outline-offset: 3px;
}
.sc-screening-primary,
.sc-screening-ghost {
  border: 2px solid var(--px-line, var(--m-line));
  border-radius: 4px;
  box-shadow: 3px 3px 0 var(--px-shadow, var(--m-shadow));
  font-family: var(--px-font);
  transition: border-color 160ms steps(2, end), background 160ms steps(2, end), color 160ms steps(2, end), transform 160ms steps(2, end), box-shadow 160ms steps(2, end);
}
.sc-screening-primary {
  border-color: var(--px-gold, var(--m-accent));
  background: var(--px-gold, var(--m-accent));
  color: #221a12;
}
.sc-screening-ghost { background: transparent; }
.sc-screening-primary:not(:disabled):hover {
  border-color: var(--px-gold, var(--m-accent-strong));
  background: var(--px-gold, var(--m-accent-strong));
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 var(--px-shadow, var(--m-shadow));
}
.sc-screening-ghost:not(:disabled):hover {
  border-color: var(--px-gold, var(--m-accent));
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 var(--px-shadow, var(--m-shadow));
}
.sc-screening-primary:not(:disabled):active,
.sc-screening-ghost:not(:disabled):active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--px-shadow, var(--m-shadow));
}
.sc-screening-urgent { border-radius: 4px; border-width: 2px; }
.sc-screening-calls a {
  border: 2px solid var(--px-line, var(--m-line));
  border-radius: 4px;
  box-shadow: 3px 3px 0 var(--px-shadow, var(--m-shadow));
  font-family: var(--px-font);
}
.sc-screening-primary:focus-visible,
.sc-screening-ghost:focus-visible,
.sc-screening-calls a:focus-visible {
  outline: 3px dashed var(--px-gold, var(--m-accent));
  outline-offset: 3px;
}
</style>
