<template>
  <section class="wellbeing-card" aria-labelledby="wellbeing-title">
    <header class="wellbeing-head">
      <div>
        <span class="eyebrow">多 Agent 支持协作</span>
        <h3 id="wellbeing-title">近两周支持需求自评</h3>
        <p>用近两周的主动回答，整理情绪、日常影响与当前更需要的支持。</p>
      </div>
      <span v-if="result" :class="['risk-chip', `risk-${result.risk_level}`]">{{ result.risk_label }}</span>
    </header>

    <div v-if="loading" class="assessment-state" role="status">正在读取自评状态…</div>

    <aside v-else class="desktop-agent-lifecycle" aria-label="自评 Agent 当前工作阶段">
      <div>
        <span>任务编排</span>
        <strong>{{ lifecycleTitle }}</strong>
        <small>{{ lifecycleSummary }}</small>
      </div>
      <ol>
        <li v-for="step in lifecycleSteps" :key="step.label" :class="`is-${step.status}`">
          <i aria-hidden="true">{{ step.status === 'complete' ? '✓' : step.status === 'running' ? '•' : '·' }}</i>
          <span><strong>{{ step.label }}</strong><small>{{ step.status === 'complete' ? '已核验' : step.status === 'running' ? '执行中' : '等待' }}</small></span>
        </li>
      </ol>
      <p>只显示任务状态和可核验结果，不展示模型私有思维过程。</p>
    </aside>

    <template v-if="!loading && !editing && !result">
      <div class="assessment-boundary">
        <strong>它能做什么</strong>
        <p>识别你主动报告的情绪和功能影响，完成安全分流，并生成一项可以执行的下一步。</p>
        <small>{{ schema?.boundary || '这是待专业人员审核的支持需求观察，不是医学诊断或经验证量表。' }}</small>
        <details class="method-details">
          <summary>查看方法与依据</summary>
          <p>{{ schema?.method_note }}</p>
          <a v-for="source in schema?.references || []" :key="source.url" :href="source.url" target="_blank" rel="noreferrer">{{ source.title }}</a>
        </details>
      </div>
      <button class="assessment-primary" type="button" @click="editing = true">开始自评</button>
    </template>

    <form v-else-if="editing" class="assessment-form" @submit.prevent="submit">
      <p class="period-note">回答范围：{{ schema?.period }}。你可以选择“不确定／不想回答”。</p>

      <fieldset class="emotion-fieldset">
        <legend>此刻哪些词更接近你的感受？ <small>最多选3项</small></legend>
        <div class="emotion-options">
          <label v-for="emotion in schema?.emotion_options || []" :key="emotion" :class="{ selected: emotions.includes(emotion) }">
            <input :checked="emotions.includes(emotion)" type="checkbox" :value="emotion" @change="toggleEmotion(emotion)">
            <span>{{ emotion }}</span>
          </label>
        </div>
      </fieldset>

      <section v-for="group in schema?.groups || []" :key="group.id" class="question-group">
        <h4>{{ group.title }}</h4>
        <fieldset v-for="question in group.questions" :key="question.id" class="assessment-question">
          <legend>{{ question.text }}</legend>
          <div class="frequency-options">
            <label v-for="option in schema.frequency_options" :key="option.value" :class="{ selected: answers[question.id] === option.value }">
              <input v-model="answers[question.id]" type="radio" :name="question.id" :value="option.value" required>
              <span>{{ option.label }}</span>
            </label>
          </div>
        </fieldset>
      </section>

      <section class="safety-section" aria-labelledby="safety-title">
        <h4 id="safety-title">安全确认</h4>
        <p>这两项用于决定是否立即连接真人帮助，安全规则优先于其他 Agent。</p>
        <fieldset v-for="question in schema?.safety_questions || []" :key="question.id" class="assessment-question safety-question">
          <legend>{{ question.text }}</legend>
          <div class="frequency-options safety-options">
            <label v-for="option in schema.safety_options" :key="option.value" :class="{ selected: safety[question.id] === option.value }">
              <input v-model="safety[question.id]" type="radio" :name="question.id" :value="option.value" required>
              <span>{{ option.label }}</span>
            </label>
          </div>
        </fieldset>
      </section>

      <div class="ai-consent" role="status">
        <span><strong>{{ schema?.external_ai_enabled ? '受约束模型协作已启用' : '当前使用本地确定性规则' }}</strong><small>{{ schema?.external_ai_enabled ? '无需单独申请；只发送去标识化的领域等级，不发送逐题原文，风险等级始终由安全规则决定。' : '模型服务暂不可用，本次由本地规则完成。' }}</small></span>
      </div>

      <p v-if="error" class="assessment-error" role="alert">{{ error }}</p>
      <div class="assessment-actions">
        <button type="button" class="assessment-secondary" @click="cancel">取消</button>
        <button type="submit" class="assessment-primary" :disabled="submitting || !complete">{{ submitting ? 'Agent 正在整理…' : '提交并生成支持建议' }}</button>
      </div>
    </form>

    <div v-else-if="result" class="assessment-result">
      <div :class="['result-hero', `risk-${result.risk_level}`]">
        <span>本次支持需求观察</span>
        <h4>{{ result.risk_label }}</h4>
        <p>{{ result.emotion_summary }}</p>
        <small>{{ result.boundary }}</small>
        <strong class="review-status">待专业人员审核</strong>
      </div>

      <section v-if="result.risk_level === 'urgent'" class="urgent-actions" aria-labelledby="urgent-title">
        <h4 id="urgent-title">现在先保证安全</h4>
        <ol><li v-for="action in result.safety_actions" :key="action">{{ action }}</li></ol>
        <div class="hotline-actions"><a href="tel:12356">拨打 12356</a><a href="tel:110">拨打 110</a><a href="tel:120">拨打 120</a></div>
      </section>

      <div v-else class="domain-grid">
        <article v-for="domain in result.domains" :key="domain.id">
          <span>{{ domain.label }}</span>
          <strong>{{ domain.level }}</strong>
          <p>{{ domain.observation }}</p>
        </article>
      </div>

      <section class="next-action-card">
        <span>优先下一步</span>
        <h4>{{ result.priority_action }}</h4>
        <ul><li v-for="item in result.support_needs" :key="item">{{ item }}</li></ul>
      </section>

      <details class="agent-progress" open>
        <summary>查看多 Agent 工作进度</summary>
        <ol>
          <li v-for="step in result.pipeline" :key="step.id" :class="step.status">
            <span aria-hidden="true"></span>
            <div><strong>{{ step.agent }}</strong><p>{{ step.summary }}</p></div>
          </li>
        </ol>
        <small>这里只展示可核验的步骤与结果，不展示模型私有思维过程。</small>
      </details>

      <section class="review-card" aria-labelledby="review-title">
        <span>CrossReviewer</span>
        <h4 id="review-title">证据与安全复核</h4>
        <ul><li v-for="item in result.review_findings || []" :key="item">{{ item }}</li></ul>
        <article v-for="conflict in result.conflicts || []" :key="conflict.topic" class="conflict-item">
          <strong>{{ conflict.topic }}</strong>
          <p>{{ conflict.views.join('；') }}</p>
          <small>协调裁决：{{ conflict.resolution }}</small>
        </article>
      </section>

      <p v-if="result.information_gaps?.length" class="information-gaps">仍需了解：{{ result.information_gaps.join('、') }}</p>
      <div class="assessment-actions">
        <button type="button" class="assessment-secondary danger" @click="remove">删除本次结果</button>
        <button type="button" class="assessment-primary" @click="startAgain">重新自评</button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { deleteAssessment, getAssessmentSchema, getLatestAssessment, submitAssessment } from '../api/assessment'

const schema = ref(null)
const result = ref(null)
const loading = ref(true)
const editing = ref(false)
const submitting = ref(false)
const error = ref('')
const answers = reactive({})
const safety = reactive({ self_harm: '', unsafe_home: '' })
const emotions = ref([])

const lifecycleTitle = computed(() => {
  if (submitting.value) return '正在执行安全分流与支持编排'
  if (result.value) return '支持建议已交付，等待学生决定'
  if (editing.value) return '正在收集主动输入'
  return '等待开始本次自评'
})
const lifecycleSummary = computed(() => {
  if (submitting.value) return '后端将按固定顺序运行 SafetyGate、Assessor、Planner 与 CrossReviewer。'
  if (result.value) return `${result.value.pipeline?.length || 0} 个公开步骤已返回，风险裁决由确定性规则优先。`
  if (editing.value) return '此阶段仅构建结构化输入，尚未调用分析 Agent。'
  return '开始后先理解任务边界，提交前不生成心理结论。'
})
const lifecycleSteps = computed(() => {
  if (result.value?.pipeline?.length) return result.value.pipeline.map(step => ({ label: step.agent, status: step.status === 'completed' ? 'complete' : step.status }))
  if (submitting.value) return [
    { label: 'TaskInterpreter', status: 'complete' }, { label: 'SafetyGate', status: 'running' },
    { label: 'Assessor', status: 'waiting' }, { label: 'Planner', status: 'waiting' }, { label: 'CrossReviewer', status: 'waiting' },
  ]
  return [
    { label: 'TaskInterpreter', status: editing.value ? 'complete' : 'waiting' }, { label: 'SafetyGate', status: 'waiting' },
    { label: 'Assessor', status: 'waiting' }, { label: 'Planner', status: 'waiting' }, { label: 'CrossReviewer', status: 'waiting' },
  ]
})

const complete = computed(() => {
  const questionIds = (schema.value?.groups || []).flatMap(group => group.questions.map(item => item.id))
  return questionIds.every(id => answers[id]) && safety.self_harm && safety.unsafe_home
})

function toggleEmotion(emotion) {
  if (emotions.value.includes(emotion)) {
    emotions.value = emotions.value.filter(item => item !== emotion)
  } else if (emotions.value.length < 3) {
    emotions.value = [...emotions.value, emotion]
  }
}

function resetForm() {
  Object.keys(answers).forEach(key => delete answers[key])
  safety.self_harm = ''
  safety.unsafe_home = ''
  emotions.value = []
  error.value = ''
}

function cancel() {
  editing.value = false
  resetForm()
}

function startAgain() {
  resetForm()
  editing.value = true
}

async function submit() {
  if (!complete.value || submitting.value) return
  submitting.value = true
  error.value = ''
  try {
    const response = await submitAssessment({
      answers: { ...answers },
      emotions: emotions.value,
      self_harm: safety.self_harm,
      unsafe_home: safety.unsafe_home,
    })
    result.value = response.data
    editing.value = false
  } catch (requestError) {
    error.value = requestError.response?.data?.detail || '自评暂时无法完成，请保留当前回答后重试。'
  } finally {
    submitting.value = false
  }
}

async function remove() {
  if (!result.value?.assessment_code) return
  await deleteAssessment(result.value.assessment_code)
  result.value = null
  resetForm()
}

onMounted(async () => {
  try {
    const [schemaResponse, latestResponse] = await Promise.all([getAssessmentSchema(), getLatestAssessment()])
    schema.value = schemaResponse.data
    result.value = latestResponse.data.assessment
  } catch {
    error.value = '暂时无法读取自评功能，请稍后重试。'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.wellbeing-card { margin: 18px 0; padding: 22px; border-radius: 16px; background: linear-gradient(145deg, rgba(255,250,241,.96), rgba(247,230,207,.88)); box-shadow: 0 4px 8px rgba(31,24,20,.18); color: #3f3026; }
.wellbeing-head { display:flex; align-items:flex-start; justify-content:space-between; gap:18px; }
.wellbeing-head h3 { margin:4px 0 6px; font-size:22px; }
.wellbeing-head p,.assessment-boundary p { margin:0; color:#746255; line-height:1.65; }
.eyebrow,.next-action-card>span,.result-hero>span { color:#854f2a; font-size:12px; font-weight:800; }
.assessment-boundary { margin:18px 0; padding:16px; border-radius:16px; background:rgba(255,255,255,.62); }
.assessment-boundary small,.result-hero small,.agent-progress>small { display:block; margin-top:8px; color:#796b61; line-height:1.55; }
.method-details { margin-top:12px; }.method-details summary { cursor:pointer; font-weight:750; }.method-details p { margin:8px 0; }.method-details a { display:block; margin-top:6px; color:#70401f; text-decoration:underline; text-underline-offset:3px; }
.assessment-primary,.assessment-secondary,.hotline-actions a { border:0; border-radius:14px; padding:11px 17px; font-weight:800; cursor:pointer; text-decoration:none; }
.assessment-primary { background:#805538; color:#fffaf2; box-shadow:0 8px 18px rgba(91,57,34,.18); }
.assessment-primary:disabled { opacity:.55; cursor:not-allowed; }
.assessment-secondary { background:rgba(255,255,255,.7); color:#5e493b; border:1px solid rgba(96,67,47,.16); }
.assessment-form { margin-top:18px; }
.period-note { padding:10px 12px; border-left:3px solid #d4a36f; background:rgba(255,255,255,.55); }
fieldset { border:0; padding:0; margin:0; }
legend { width:100%; font-weight:750; line-height:1.55; }
legend small { color:#8a7769; font-weight:500; }
.emotion-fieldset,.question-group,.safety-section { margin-top:22px; }
.question-group h4,.safety-section h4 { margin:0 0 12px; font-size:16px; }
.assessment-question { padding:15px 0; border-top:1px solid rgba(100,71,50,.12); }
.frequency-options,.emotion-options { display:flex; flex-wrap:wrap; gap:8px; margin-top:11px; }
.frequency-options label,.emotion-options label { position:relative; }
.frequency-options input,.emotion-options input { position:absolute; opacity:0; pointer-events:none; }
.frequency-options span,.emotion-options span { display:block; padding:8px 11px; border:1px solid rgba(104,74,51,.18); border-radius:12px; background:rgba(255,255,255,.58); cursor:pointer; }
.frequency-options label.selected span,.emotion-options label.selected span { color:#fff; background:#8a6041; border-color:#8a6041; }
.safety-section { padding:17px; border:1px solid rgba(170,83,62,.2); border-radius:18px; background:rgba(255,245,239,.65); }
.safety-section>p { color:#7b5d50; font-size:13px; }
.ai-consent { display:flex; gap:10px; margin:20px 0; padding:14px; border-radius:15px; background:rgba(255,255,255,.55); }
.ai-consent span { display:grid; gap:4px; }.ai-consent small { color:#77685e; line-height:1.5; }
.assessment-actions { display:flex; justify-content:flex-end; gap:10px; margin-top:18px; }
.assessment-error { color:#a33e32; font-weight:700; }.assessment-state { padding:28px 0; color:#78685d; }
.risk-chip { border-radius:999px; padding:7px 11px; font-size:12px; font-weight:800; white-space:nowrap; border:1px solid currentColor; }
.risk-routine { color:#42725c; }.risk-watch { color:#91601e; }.risk-professional { color:#a04f2d; }.risk-urgent { color:#a32929; }
.assessment-result { margin-top:18px; }.result-hero { padding:18px; border-radius:14px; background:rgba(255,255,255,.62); border:1px solid currentColor; }
.result-hero h4 { margin:5px 0; font-size:22px; }.result-hero p { margin:0; line-height:1.6; font-weight:650; }
.review-status { display:inline-flex; margin-top:10px; padding:5px 9px; border-radius:8px; background:#fff7e8; color:#7a4b22; font-size:12px; }
.review-card { margin-top:14px; padding:16px; border-radius:14px; background:rgba(255,250,240,.72); }
.review-card>span { color:#854f2a; font-size:12px; font-weight:800; }
.review-card h4 { margin:4px 0 8px; }.review-card ul { margin:0; padding-left:20px; line-height:1.65; }
.conflict-item { margin-top:10px; padding-top:10px; border-top:1px solid rgba(120,82,48,.18); }.conflict-item p,.conflict-item small { margin:4px 0 0; line-height:1.55; }
.domain-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:11px; margin-top:14px; }
.domain-grid article { padding:14px; border-radius:15px; background:rgba(255,255,255,.56); }.domain-grid span { display:block; color:#806b5d; font-size:12px; }.domain-grid strong { display:block; margin:4px 0; }.domain-grid p { margin:0; color:#6f6056; line-height:1.5; font-size:13px; }
.next-action-card { margin-top:14px; padding:17px; border-radius:17px; background:#4e5949; color:#fffaf2; }.next-action-card h4 { margin:5px 0 10px; line-height:1.55; }.next-action-card ul { margin:0; padding-left:20px; line-height:1.7; }
.agent-progress { margin-top:14px; padding:15px; border-radius:17px; background:rgba(255,255,255,.55); }.agent-progress summary { cursor:pointer; font-weight:800; }.agent-progress ol { list-style:none; padding:0; margin:14px 0; }.agent-progress li { display:flex; gap:10px; padding:9px 0; border-top:1px solid rgba(94,69,50,.1); }.agent-progress li>span { width:9px; height:9px; margin-top:5px; border-radius:50%; background:#6f9c7e; }.agent-progress li.attention>span { background:#d47348; }.agent-progress li.blocked>span { background:#a69d96; }.agent-progress strong,.agent-progress p { display:block; margin:0; }.agent-progress p { margin-top:2px; color:#6c5e54; font-size:13px; line-height:1.5; }
.urgent-actions { margin-top:14px; padding:17px; border-radius:17px; background:#fff1ed; border:1px solid #d89c8e; }.urgent-actions ol { padding-left:20px; line-height:1.7; }.hotline-actions { display:flex; flex-wrap:wrap; gap:8px; }.hotline-actions a { background:#9e332d; color:#fff; }
.information-gaps { color:#6f6258; font-size:13px; }.danger { color:#9a3b34; }
.desktop-agent-lifecycle { display:none; }
@media (min-width:1024px) {
  .desktop-agent-lifecycle { display:grid; grid-template-columns:minmax(220px,.8fr) minmax(0,2fr); gap:18px; margin:18px 0 4px; padding:16px 18px; border:1px solid rgba(111,78,53,.15); border-radius:16px; background:rgba(255,255,255,.52); }
  .desktop-agent-lifecycle>div { align-self:center; }
  .desktop-agent-lifecycle>div>span { color:#854f2a; font-size:11px; font-weight:850; }
  .desktop-agent-lifecycle>div>strong,.desktop-agent-lifecycle>div>small { display:block; }
  .desktop-agent-lifecycle>div>strong { margin:5px 0; font-size:15px; }
  .desktop-agent-lifecycle>div>small,.desktop-agent-lifecycle>p { color:#746559; line-height:1.5; }
  .desktop-agent-lifecycle ol { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:6px; margin:0; padding:0; list-style:none; }
  .desktop-agent-lifecycle li { display:flex; gap:7px; min-width:0; padding:10px; border-radius:12px; background:rgba(255,255,255,.82); border:1px solid rgba(111,78,53,.12); }
  .desktop-agent-lifecycle li i { display:grid; place-items:center; width:20px; height:20px; flex:0 0 auto; border-radius:7px; color:#9a8a7c; background:#efe7de; font-size:11px; font-style:normal; }
  .desktop-agent-lifecycle li.is-complete i { color:#fff; background:#62836e; }
  .desktop-agent-lifecycle li.is-running i { color:#4a321f; background:#e4bc78; }
  .desktop-agent-lifecycle li span,.desktop-agent-lifecycle li strong,.desktop-agent-lifecycle li small { display:block; min-width:0; }
  .desktop-agent-lifecycle li strong { overflow:hidden; font-size:11.5px; font-weight:700; color:#4a3f36; text-overflow:ellipsis; white-space:nowrap; }
  .desktop-agent-lifecycle li small { margin-top:2px; color:#8a7b6e; font-size:10.5px; }
  .desktop-agent-lifecycle>p { grid-column:1/-1; margin:0; font-size:11px; }
}
@media (max-width:720px) { .wellbeing-card { padding:16px; border-radius:20px; }.wellbeing-head { display:block; }.risk-chip { display:inline-block; margin-top:10px; }.domain-grid { grid-template-columns:1fr; }.frequency-options { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); }.frequency-options span { text-align:center; }.assessment-actions { flex-direction:column-reverse; }.assessment-actions button { width:100%; } }

/* 像素皮肤 3.0 · 支持需求自评 */
.wellbeing-card {
  --px-line: rgba(104, 74, 51, .28);
  --px-gold: #8a6041;
  --px-shadow: rgba(74, 52, 32, .24);
  border: 2px solid var(--px-line);
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.wellbeing-head h3 { font-family: var(--px-font); font-size: 21px; }
.eyebrow, .next-action-card > span, .result-hero > span { font-family: var(--px-font); font-size: 12px; }
.assessment-boundary,
.ai-consent {
  border: 2px solid var(--px-line);
  border-radius: 6px;
}
.method-details summary { font-family: var(--px-font); }
.assessment-primary,
.assessment-secondary,
.hotline-actions a {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: 3px 3px 0 var(--px-shadow);
  font-family: var(--px-font);
  transition: transform 160ms steps(2, end), box-shadow 160ms steps(2, end), background 160ms steps(2, end);
}
.assessment-primary { border-color: var(--px-gold); background: var(--px-gold); color: #fffaf2; }
.assessment-secondary { background: rgba(255, 255, 255, .7); }
.assessment-primary:not(:disabled):hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 var(--px-shadow);
  background: #7a5238;
}
.assessment-secondary:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.assessment-primary:not(:disabled):active,
.assessment-secondary:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--px-shadow);
}
.period-note { border: 2px solid var(--px-line); border-left: 4px solid #d4a36f; border-radius: 4px; }
.frequency-options span,
.emotion-options span {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: 2px 2px 0 var(--px-shadow);
  transition: transform 160ms steps(2, end), box-shadow 160ms steps(2, end), background 160ms steps(2, end), color 160ms steps(2, end);
}
.frequency-options label:hover span,
.emotion-options label:hover span {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 var(--px-shadow);
}
.frequency-options label.selected span,
.emotion-options label.selected span {
  border-color: var(--px-gold);
  background: var(--px-gold);
}
.frequency-options input:focus-visible + span,
.emotion-options input:focus-visible + span {
  outline: 3px dashed var(--px-gold);
  outline-offset: 3px;
}
.safety-section {
  border-width: 2px;
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.safety-section h4 { font-family: var(--px-font); }
.result-hero {
  border-width: 2px;
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.result-hero h4 { font-family: var(--px-font); }
.risk-chip { border-radius: 4px; border-width: 2px; font-family: var(--px-font); }
.review-card,
.domain-grid article,
.next-action-card,
.agent-progress,
.urgent-actions {
  border: 2px solid var(--px-line);
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.next-action-card,
.urgent-actions { border-color: rgba(255, 250, 242, .28); }
.next-action-card { background: #4e5949; }
.desktop-agent-lifecycle {
  border-width: 2px;
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.desktop-agent-lifecycle li { border-radius: 4px; }
.desktop-agent-lifecycle li i { border-radius: 4px; }
.agent-progress li > span { border-radius: 0; }
.assessment-primary:focus-visible,
.assessment-secondary:focus-visible,
.hotline-actions a:focus-visible,
.method-details summary:focus-visible,
.method-details a:focus-visible {
  outline: 3px dashed var(--px-gold);
  outline-offset: 3px;
}
@media (prefers-reduced-motion:reduce) { * { scroll-behavior:auto!important; transition:none!important; animation:none!important; } }
</style>
