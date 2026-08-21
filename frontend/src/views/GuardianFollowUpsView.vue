<template>
  <div class="guardian-page">
    <header class="guardian-topbar">
      <RouterLink class="guardian-brand" to="/guardian"><span class="guardian-brand-mark">咕</span><span class="guardian-brand-copy"><strong>咕哝守护者</strong><small>3 / 7 / 15天站内回访</small></span></RouterLink>
      <nav class="guardian-nav"><RouterLink to="/guardian/new">新建工单</RouterLink><RouterLink to="/guardian">工作台介绍</RouterLink></nav>
    </header>

    <main class="guardian-main">
      <div class="guardian-narrow">
        <header class="guardian-form-header">
          <RouterLink class="guardian-back" to="/guardian">← 返回守护者工作台</RouterLink>
          <h1>站内回访</h1>
          <p>这是本地演示调度，不会发送短信、微信或邮件。可使用“模拟到期”立即查看完整闭环。</p>
        </header>

        <div v-if="loading" class="guardian-loading"><span class="guardian-loading-dot"></span>正在读取回访任务…</div>
        <div v-else-if="error" class="guardian-panel"><p>{{ error }}</p><button class="guardian-primary-action" type="button" @click="load">重新加载</button></div>
        <div v-else-if="!items.length" class="guardian-panel guardian-empty"><h2>还没有回访任务</h2><p>普通支持方案生成后，会自动创建第3、7、15天站内回访。</p><RouterLink class="guardian-primary-action" to="/guardian/new">新建支持工单</RouterLink></div>
        <div v-else class="guardian-followup-list">
          <article v-for="item in items" :key="item.id" class="guardian-followup-card">
            <div class="guardian-followup-date">第 {{ item.day_offset }} 天</div>
            <div><h2>{{ item.case_code }}</h2><p>{{ formatDate(item.due_at) }} · {{ statusLabel(item.status) }}</p></div>
            <div class="guardian-actions">
              <RouterLink class="guardian-quiet-action" :to="`/guardian/cases/${item.case_code}`">查看方案</RouterLink>
              <button v-if="item.status === 'scheduled'" class="guardian-secondary-action" type="button" @click="simulate(item)">模拟到期</button>
              <button v-if="!['completed', 'superseded_for_safety'].includes(item.status)" class="guardian-primary-action" type="button" @click="toggleForm(item)">{{ openId === item.id ? '收起' : '填写回访' }}</button>
            </div>

            <form v-if="openId === item.id && !['completed', 'superseded_for_safety'].includes(item.status)" class="guardian-followup-form" @submit.prevent="submit(item)">
              <fieldset class="guardian-field"><legend>现在能否保证安全？</legend><div class="guardian-option-grid">
                <label v-for="choice in safetyChoices" :key="choice.value" :class="['guardian-option', { selected: form.current_safety === choice.value }]">
                  <input v-model="form.current_safety" type="radio" :value="choice.value"><span><b>{{ choice.label }}</b><em>{{ choice.hint }}</em></span>
                </label>
              </div></fieldset>
              <fieldset class="guardian-field"><legend>是否出现新的安全信号？</legend><div class="guardian-option-grid">
                <label class="guardian-option" :class="{ selected: form.new_self_harm_or_suicide_signal }"><input v-model="form.new_self_harm_or_suicide_signal" type="checkbox"><span><b>新的自伤、自杀或轻生表达</b></span></label>
                <label class="guardian-option" :class="{ selected: form.action_taken_or_means_available }"><input v-model="form.action_taken_or_means_available" type="checkbox"><span><b>已采取行动或危险物可获得</b></span></label>
                <label class="guardian-option" :class="{ selected: form.family_harm_or_unsafe_home }"><input v-model="form.family_harm_or_unsafe_home" type="checkbox"><span><b>家庭伤害或无法安全回家</b></span></label>
              </div></fieldset>
              <div v-if="hasFollowupUrgency" class="guardian-form-alert" role="alert"><strong>请不要等待普通回访。</strong><br>提交后会立即切换安全路径；保持陪伴并联系12356，已经采取行动或存在迫切危险时拨打110或120。</div>
              <fieldset class="guardian-field"><legend>目前整体变化</legend><div class="guardian-option-grid">
                <label v-for="choice in moodChoices" :key="choice.value" :class="['guardian-option', { selected: form.mood_change === choice.value }]">
                  <input v-model="form.mood_change" type="radio" :value="choice.value"><span><b>{{ choice.label }}</b></span>
                </label>
              </div></fieldset>
              <fieldset class="guardian-field"><legend>方案行动完成情况</legend><div class="guardian-option-grid">
                <label v-for="choice in actionChoices" :key="choice.value" :class="['guardian-option', { selected: form.action_completion === choice.value }]">
                  <input v-model="form.action_completion" type="radio" :value="choice.value"><span><b>{{ choice.label }}</b></span>
                </label>
              </div></fieldset>
              <label class="guardian-field"><span>遇到的困难（选填）</span><textarea v-model="form.difficulty" class="guardian-textarea" maxlength="300" placeholder="只写执行困难，不写真实身份信息。"></textarea></label>
              <label class="guardian-consent"><input v-model="form.needs_adjustment" type="checkbox"><span>我希望调整下一阶段方案。</span></label>
              <p v-if="formError" class="guardian-form-error" role="alert">{{ formError }}</p>
              <button class="guardian-primary-action" type="submit" :disabled="submitting">{{ submitting ? '提交中…' : '提交回访' }}</button>
            </form>

            <div v-if="item.status === 'completed'" :class="isUrgentResponse(item.response) ? 'guardian-form-alert' : 'guardian-review-note'" style="grid-column: 1 / -1;" role="status">
              <template v-if="isUrgentResponse(item.response)"><strong>已切换紧急安全路径。</strong> 请保持陪伴并立即联系12356；已经采取行动或存在迫切危险时拨打110或120。家庭不安全时联系可信教师、其他安全成年人或110。</template>
              <template v-else>已完成：{{ moodLabel(item.response?.mood_change) }}。如出现自伤、自杀或无法保证安全的新信号，请不要等待下一次回访，立即联系12356、110或120。</template>
            </div>
          </article>
        </div>
      </div>
    </main>
    <footer class="guardian-footer">站内演示调度 · 不收集联系方式 · 不发送外部通知</footer>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { getGuardianFollowUps, simulateGuardianFollowUp, submitGuardianFollowUp } from '../api/guardian'

const items = ref([])
const loading = ref(true)
const error = ref('')
const openId = ref(null)
const submitting = ref(false)
const formError = ref('')
const form = reactive({ mood_change: '', action_completion: '', difficulty: '', needs_adjustment: false, current_safety: '', new_self_harm_or_suicide_signal: false, action_taken_or_means_available: false, family_harm_or_unsafe_home: false })
const safetyChoices = [
  { value: 'safe', label: '目前可以保证安全', hint: '没有新增危险信号，且有可信成年人可联系' },
  { value: 'unsure', label: '无法确定', hint: '需要立即由可信成年人一起核实' },
  { value: 'immediate_danger', label: '存在迫切危险', hint: '已经采取行动、无法停止或无法保证安全' },
]
const moodChoices = [{ value: 'improved', label: '明显好转' }, { value: 'slightly_improved', label: '略有改善' }, { value: 'unchanged', label: '没有变化' }, { value: 'worse', label: '有所加重' }]
const actionChoices = [{ value: 'most', label: '大部分完成' }, { value: 'some', label: '完成一部分' }, { value: 'none', label: '尚未执行' }]

const hasFollowupUrgency = computed(() => form.current_safety === 'unsure' || form.current_safety === 'immediate_danger' || form.new_self_harm_or_suicide_signal || form.action_taken_or_means_available || form.family_harm_or_unsafe_home)
function isUrgentResponse(response = {}) { return response.current_safety === 'unsure' || response.current_safety === 'immediate_danger' || response.new_self_harm_or_suicide_signal || response.action_taken_or_means_available || response.family_harm_or_unsafe_home }
function resetForm() { Object.assign(form, { mood_change: '', action_completion: '', difficulty: '', needs_adjustment: false, current_safety: '', new_self_harm_or_suicide_signal: false, action_taken_or_means_available: false, family_harm_or_unsafe_home: false }); formError.value = '' }
function toggleForm(item) { openId.value = openId.value === item.id ? null : item.id; resetForm() }
function statusLabel(status) { return ({ scheduled: '已安排', due: '现在可填写', completed: '已完成', superseded_for_safety: '已由安全路径接管' })[status] || status }
function moodLabel(value) { return moodChoices.find(item => item.value === value)?.label || '已记录' }
function formatDate(value) { return new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value)) }

async function load() {
  loading.value = true; error.value = ''
  try { items.value = (await getGuardianFollowUps()).data.items || [] }
  catch (err) { error.value = err.response?.data?.detail || '回访任务加载失败。' }
  finally { loading.value = false }
}
async function simulate(item) {
  try { await simulateGuardianFollowUp(item.id); await load() }
  catch (err) { error.value = err.response?.data?.detail || '模拟到期失败，请重试。' }
}
async function submit(item) {
  formError.value = ''
  if (!form.current_safety || !form.mood_change || !form.action_completion) { formError.value = '请先确认当前安全，并选择整体变化和行动完成情况。'; return }
  submitting.value = true
  try { await submitGuardianFollowUp(item.id, { ...form }); openId.value = null; resetForm(); await load() }
  catch (err) { formError.value = err.response?.data?.detail || '提交失败，请重试。' }
  finally { submitting.value = false }
}

load()
</script>
