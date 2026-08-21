<template>
  <div class="guardian-page">
    <header class="guardian-topbar">
      <RouterLink class="guardian-brand" to="/guardian"><span class="guardian-brand-mark">咕</span><span class="guardian-brand-copy"><strong>咕哝守护者</strong><small>新建支持工单</small></span></RouterLink>
      <nav class="guardian-nav"><RouterLink to="/guardian/follow-ups">站内回访</RouterLink><RouterLink to="/">学生陪伴端</RouterLink></nav>
    </header>

    <main class="guardian-main">
      <div class="guardian-narrow">
        <header class="guardian-form-header">
          <RouterLink class="guardian-back" to="/guardian">← 返回工作台介绍</RouterLink>
          <h1>把可观察的变化说清楚</h1>
          <p>只填写你亲眼观察到的事实。不要填写姓名、学校全称、证件号、电话或精确地址；本预览只接受合成个案。</p>
        </header>

        <div class="guardian-stepper" aria-label="表单进度">
          <div v-for="item in 3" :key="item" :aria-current="step === item ? 'step' : undefined" :class="['guardian-step', { active: step === item, done: step > item }]">
            <strong>{{ step > item ? '✓' : item }}</strong><span>{{ ['守护者角色', '观察变化', '边界确认'][item - 1] }}</span>
          </div>
        </div>

        <form class="guardian-form-panel" @submit.prevent="submitCase">
          <section v-if="step === 1" aria-labelledby="step-one-title">
            <h2 id="step-one-title">你以什么角色提供观察？</h2>
            <p class="guardian-form-intro">角色会改变沟通话术和行动边界，不改变安全分流规则。</p>

            <fieldset class="guardian-field">
              <legend>守护者角色</legend>
              <div class="guardian-option-grid">
                <label :class="['guardian-option', { selected: form.reporter_role === 'parent' }]">
                  <input v-model="form.reporter_role" type="radio" value="parent">
                  <span><b>家长</b><em>家庭沟通、日常观察与求助路径</em></span>
                </label>
                <label :class="['guardian-option', { selected: form.reporter_role === 'teacher' }]">
                  <input v-model="form.reporter_role" type="radio" value="teacher">
                  <span><b>教师</b><em>校内观察、最小披露与家校协作</em></span>
                </label>
              </div>
            </fieldset>

            <fieldset class="guardian-field">
              <legend>年龄段</legend>
              <div class="guardian-option-grid">
                <label :class="['guardian-option', { selected: form.age_band === '12-14' }]">
                  <input v-model="form.age_band" type="radio" value="12-14"><span><b>12–14岁</b><em>初中阶段</em></span>
                </label>
                <label :class="['guardian-option', { selected: form.age_band === '15-18' }]">
                  <input v-model="form.age_band" type="radio" value="15-18"><span><b>15–18岁</b><em>高中阶段</em></span>
                </label>
              </div>
            </fieldset>
          </section>

          <section v-else-if="step === 2" aria-labelledby="step-two-title">
            <h2 id="step-two-title">最近出现了哪些变化？</h2>
            <p class="guardian-form-intro">选择可观察表现，不推断原因。危险项会立即切换到安全路径。</p>

            <fieldset class="guardian-field">
              <legend>可观察表现（可多选）</legend>
              <div class="guardian-option-grid">
                <label v-for="signal in signalOptions" :key="signal.value" :class="['guardian-option', { selected: form.signals.includes(signal.value) }]">
                  <input v-model="form.signals" type="checkbox" :value="signal.value">
                  <span><b>{{ signal.label }}</b><em>{{ signal.hint }}</em></span>
                </label>
              </div>
            </fieldset>

            <div v-if="hasUrgentSignal" class="guardian-form-alert" role="alert">
              <strong>这些信号需要优先确认当下安全。</strong><br>提交后系统会停止普通家庭方案，直接展示12356、110、120与可信成年人陪伴步骤。
            </div>

            <label class="guardian-field"><span>持续时间</span><select v-model="form.duration" class="guardian-select"><option value="">请选择</option><option v-for="item in durationOptions" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
            <fieldset class="guardian-field"><legend>对上学、社交或家庭生活的影响</legend><div class="guardian-option-grid">
              <label v-for="item in impactOptions" :key="item.value" :class="['guardian-option', { selected: form.functional_impact === item.value }]">
                <input v-model="form.functional_impact" type="radio" :value="item.value"><span><b>{{ item.label }}</b><em>{{ item.hint }}</em></span>
              </label>
            </div></fieldset>
          </section>

          <section v-else aria-labelledby="step-three-title">
            <h2 id="step-three-title">确认演示数据与支持边界</h2>
            <p class="guardian-form-intro">位置仅用于匹配东莞示范资源，不收集精确定位。</p>

            <label class="guardian-field"><span>东莞市区级位置</span><select v-model="form.district" class="guardian-select"><option value="">请选择</option><option v-for="district in districts" :key="district" :value="district">{{ district }}</option></select></label>
            <label class="guardian-field"><span>补充观察（选填）</span><small>只写行为、时间和场景，不写身份信息。最多500字。</small><textarea v-model="form.context" class="guardian-textarea" maxlength="500" placeholder="例如：近三周回家后常关门独处，与同伴联系减少；询问时会说很累，但仍愿意一起吃晚饭。"></textarea><small>{{ form.context.length }}/500</small></label>
            <label class="guardian-consent guardian-safety-question"><input v-model="form.guardian_may_be_source" type="checkbox"><span><strong>家庭安全项：</strong>演示场景中存在人身威胁、暴力、性伤害、无法安全回家，或监护人可能是伤害/恐惧来源。选择后将直接进入安全路径，优先建议可信教师、其他安全成年人或110。</span></label>
            <label class="guardian-consent"><input v-model="syntheticConfirmed" type="checkbox"><span>我确认这是比赛用合成个案，不包含真实未成年人姓名、学校、联系方式、精确地址或其他可识别信息。</span></label>
            <label class="guardian-consent"><input v-model="boundaryConfirmed" type="checkbox"><span>我理解系统只提供心理健康教育、支持建议和求助导航，不提供诊断、治疗或正式量表结论。</span></label>
          </section>

          <p v-if="error" class="guardian-form-error" role="alert">{{ error }}</p>
          <div class="guardian-form-actions">
            <button v-if="step > 1" class="guardian-secondary-action" type="button" @click="step--">上一步</button><span v-else></span>
            <button v-if="step < 3" class="guardian-primary-action" type="button" @click="nextStep">下一步</button>
            <button v-else class="guardian-primary-action" type="submit" :disabled="submitting">{{ submitting ? '正在创建工单…' : hasUrgentSignal ? '提交并进入安全路径' : '提交并启动 Agent' }}</button>
          </div>
        </form>
      </div>
    </main>
    <footer class="guardian-footer">只允许合成数据 · 不使用正式心理量表 · 全部输出待专业人员审核</footer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createGuardianCase } from '../api/guardian'

const router = useRouter()
const route = useRoute()
const step = ref(1)
const submitting = ref(false)
const error = ref('')
const syntheticConfirmed = ref(false)
const boundaryConfirmed = ref(false)
const form = reactive({ reporter_role: '', age_band: '', signals: [], duration: '', functional_impact: '', district: '', context: '', guardian_may_be_source: false })

const signalOptions = [
  { value: 'mood_low', label: '情绪持续低落', hint: '比平时更沉默、难过或缺少兴趣' },
  { value: 'irritability', label: '易怒或波动明显', hint: '更容易激动、冲突或情绪骤变' },
  { value: 'school_refusal', label: '抗拒或回避上学', hint: '迟到、缺课或反复表达不愿到校' },
  { value: 'social_withdrawal', label: '社交退缩', hint: '减少与同伴联系或回避集体活动' },
  { value: 'sleep_change', label: '睡眠明显变化', hint: '入睡困难、早醒或昼夜颠倒' },
  { value: 'performance_drop', label: '学习表现明显下降', hint: '作业、课堂参与或成绩持续变化' },
  { value: 'family_conflict', label: '家庭冲突增加', hint: '沟通更频繁地升级为争执或回避' },
  { value: 'self_harm_sign', label: '发现自伤痕迹', hint: '需要立即确认当下安全' },
  { value: 'death_talk', label: '谈到死亡或不想活', hint: '需要立即确认当下安全' },
]
const durationOptions = [
  { value: 'under_1_week', label: '不足1周' }, { value: '1_2_weeks', label: '1–2周' }, { value: '2_4_weeks', label: '2–4周' }, { value: '1_3_months', label: '1–3个月' }, { value: 'over_3_months', label: '3个月以上' },
]
const impactOptions = [
  { value: 'none', label: '尚未明显影响', hint: '基本能维持日常学习和生活' },
  { value: 'partial', label: '部分影响', hint: '某些场景已受到影响' },
  { value: 'significant', label: '明显影响', hint: '持续缺课、严重退缩或家庭生活明显受损' },
]
const districts = ['莞城街道', '东城街道', '南城街道', '万江街道', '中堂镇', '其他镇街']
const hasUrgentSignal = computed(() => form.guardian_may_be_source || form.signals.includes('self_harm_sign') || form.signals.includes('death_talk'))

function applyPreset(name) {
  if (name === 'parent-watch') Object.assign(form, { reporter_role: 'parent', age_band: '15-18', signals: ['mood_low', 'social_withdrawal', 'performance_drop'], duration: '2_4_weeks', functional_impact: 'partial', district: '南城街道', context: '近三周回家后常独处，与同伴联系减少，学习表现下降；仍愿意和家人一起吃饭。' })
  if (name === 'teacher-support') Object.assign(form, { reporter_role: 'teacher', age_band: '12-14', signals: ['irritability', 'school_refusal', 'performance_drop'], duration: '1_2_weeks', functional_impact: 'significant', district: '莞城街道', context: '近两周迟到增多，课堂参与下降，课间常独处；没有已知危险表达。' })
}

function nextStep() {
  error.value = ''
  if (step.value === 1 && (!form.reporter_role || !form.age_band)) { error.value = '请选择守护者角色和年龄段。'; return }
  if (step.value === 2 && (!form.signals.length || !form.duration || !form.functional_impact)) { error.value = '请至少选择一项可观察表现，并补充持续时间和功能影响。'; return }
  step.value++
  const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  window.scrollTo({ top: 0, behavior: reducedMotion ? 'auto' : 'smooth' })
}

async function submitCase() {
  error.value = ''
  if (!form.district) { error.value = '请选择区级位置。'; return }
  if (!syntheticConfirmed.value || !boundaryConfirmed.value) { error.value = '请确认合成数据和产品边界后再提交。'; return }
  submitting.value = true
  try {
    const response = await createGuardianCase({ ...form, consent_version: 'guardian-demo-v1', synthetic_data_confirmed: true })
    router.push(`/guardian/cases/${response.data.case_id}`)
  } catch (err) {
    const detail = err.response?.data?.detail
    error.value = Array.isArray(detail) ? detail.map(item => item.msg).join('；') : detail || '工单创建失败，请稍后重试。'
  } finally { submitting.value = false }
}

onMounted(() => applyPreset(route.query.preset))
</script>
