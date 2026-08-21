<template>
  <div class="guardian-page">
    <header class="guardian-topbar">
      <RouterLink class="guardian-brand" to="/guardian"><span class="guardian-brand-mark">咕</span><span class="guardian-brand-copy"><strong>咕哝守护者</strong><small>Agent 执行与方案</small></span></RouterLink>
      <nav class="guardian-nav"><RouterLink to="/guardian/new">新建工单</RouterLink><RouterLink to="/guardian/follow-ups">站内回访</RouterLink></nav>
    </header>

    <main class="guardian-main">
      <div v-if="loading" class="guardian-loading"><span class="guardian-loading-dot"></span>正在读取工单…</div>
      <div v-else-if="error" class="guardian-narrow"><div class="guardian-panel"><h1>暂时无法读取工单</h1><p>{{ error }}</p><button class="guardian-primary-action" type="button" @click="loadCase">重新加载</button></div></div>
      <div v-else class="guardian-container guardian-case-layout">
        <div class="guardian-case-main">
          <RouterLink class="guardian-back" to="/guardian">← 返回守护者工作台</RouterLink>
          <header class="guardian-case-heading">
            <div><h1>支持工单 {{ data.case.case_code }}</h1><p>{{ roleLabel }} · {{ data.case.age_band }}岁 · {{ data.case.district }} · 仅合成数据</p></div>
            <span :class="['guardian-risk-badge', data.case.risk_level]">{{ riskIcon }} {{ riskMeta.label }}</span>
          </header>

          <section v-if="data.case.risk_level === 'urgent'" class="guardian-urgent-panel" role="alert">
            <h2>先确保当下安全</h2>
            <p>{{ data.plan?.action_priority || '安全分流已触发：停止普通方案。请让可信成年人陪伴，不让孩子独处，并移开药物、刀具、绳索等危险物。' }}</p>
            <div class="guardian-hotlines"><a href="tel:12356">拨打 12356</a><a href="tel:110">拨打 110</a><a href="tel:120">拨打 120</a></div>
          </section>

          <p v-if="streamNotice" class="guardian-form-alert" role="status">{{ streamNotice }}</p>

          <section class="guardian-panel" aria-labelledby="agent-progress-title">
            <h2 id="agent-progress-title">Agent 执行看板 · {{ progress }}%</h2>
            <div class="guardian-agent-list">
              <article v-for="agent in data.agents" :key="agent.run_code" :class="['guardian-agent-row', agent.status]">
                <span class="guardian-agent-state">{{ stateIcon(agent.status) }}</span>
                <div><strong>{{ agentLabel(agent.agent_type) }}</strong><p>{{ agentPurpose(agent.agent_type) }}</p></div>
                <div><p>{{ agent.summary || statusLabel(agent.status) }}</p><span v-if="agent.degraded" class="guardian-degraded">模型不可用，已降级为审核模板</span></div>
                <small>{{ agent.model_name }}</small>
              </article>
            </div>
            <button v-if="data.case.status === 'failed'" class="guardian-primary-action" type="button" :disabled="retrying" @click="retry">{{ retrying ? '正在重试…' : '安全重试失败步骤' }}</button>
          </section>

          <template v-if="data.plan">
            <section class="guardian-panel">
              <h2>风险与下一步</h2>
              <div class="guardian-summary-box"><strong>{{ data.plan.risk_label }}</strong><p>{{ data.plan.observation_summary }}</p></div>
              <p>{{ data.plan.action_priority }}</p>
              <div class="guardian-review-note"><strong>评估边界：</strong>这是非标准化守护者观察摘要，未直接访谈青少年，不含 PHQ‑9、GAD‑7 等量表分数。</div>
            </section>

            <section class="guardian-panel">
              <h2>可执行支持方案</h2>
              <div class="guardian-plan-grid">
                <article class="guardian-plan-section"><h3>现在先做</h3><ul><li v-for="item in data.plan.immediate_actions" :key="item">{{ item }}</li></ul></article>
                <article v-if="data.plan.seven_day_actions.length" class="guardian-plan-section"><h3>未来7天</h3><ul><li v-for="item in data.plan.seven_day_actions" :key="item">{{ item }}</li></ul></article>
                <article class="guardian-plan-section wide"><h3>沟通话术参考</h3><ul><li v-for="item in data.plan.conversation_prompts" :key="item">“{{ item }}”</li></ul></article>
                <article class="guardian-plan-section wide"><h3>需要避免</h3><ul><li v-for="item in data.plan.avoid_actions" :key="item">{{ item }}</li></ul></article>
              </div>
            </section>

            <section class="guardian-panel">
              <h2>东莞示范资源与全国热线</h2>
              <article v-for="resource in data.plan.resources" :key="resource.resource_code" class="guardian-resource">
                <div class="guardian-resource-head"><strong>{{ resource.name }}</strong><a v-if="resource.phone" :href="`tel:${resource.phone.replace(/-/g, '')}`">{{ resource.phone }}</a></div>
                <p>{{ resource.note }}</p><small>{{ resource.availability }} · 核验 {{ resource.verified_at }} · <a :href="resource.source_url" target="_blank" rel="noreferrer">查看一手来源</a></small>
              </article>
            </section>

            <section class="guardian-panel">
              <h2>证据与结构化审查轨迹</h2>
              <article v-for="source in data.evidence" :key="source.source_code" class="guardian-evidence">
                <a :href="source.source_url" target="_blank" rel="noreferrer">{{ source.title }}</a><p>{{ source.summary }}</p><small>{{ source.issuer }} · {{ source.evidence_level }} · 核验 {{ source.reviewed_at }}</small>
              </article>
              <template v-if="data.plan.disagreements.length"><h3>Agent 分歧摘要</h3><ul><li v-for="item in data.plan.disagreements" :key="item">{{ item }}</li></ul></template>
              <div class="guardian-review-note"><strong>最终裁决：</strong>{{ data.plan.review_resolution }}</div>
            </section>

            <section class="guardian-panel">
              <h2>AI身份与适用边界</h2><p>{{ data.plan.ai_disclosure }}</p><p>{{ data.plan.boundary_notice }}</p><div class="guardian-review-note">内容状态：待专业人员审核。子 Agent 检查只能验证工程、安全规则和资料一致性，不能替代持证专家签署。</div>
            </section>
          </template>
        </div>

        <aside class="guardian-case-aside">
          <section class="guardian-aside-card"><h2>方案书</h2><p>包含版本、风险动作、行动清单、核验资源、证据和适用边界。</p><a v-if="data.plan" class="guardian-primary-action" :href="reportUrl">下载 PDF</a><button v-else class="guardian-primary-action" disabled>生成中…</button></section>
          <section class="guardian-aside-card"><h2>站内回访</h2><p v-if="!data.follow_ups.length">紧急路径不设置自动回访；请优先取得现实世界帮助。</p><template v-else><div v-for="item in data.follow_ups" :key="item.id" class="guardian-followup-mini"><span>第{{ item.day_offset }}天</span><strong>{{ followupStatus(item.status) }}</strong></div><RouterLink class="guardian-secondary-action" to="/guardian/follow-ups">查看全部回访</RouterLink></template></section>
          <section class="guardian-aside-card"><h2>处理状态</h2><p>{{ statusLabel(data.case.status) }}。事件流断开不会丢失工单，可刷新页面继续读取。</p><button class="guardian-quiet-action" type="button" @click="loadCase">刷新状态</button></section>
        </aside>
      </div>
    </main>
    <footer class="guardian-footer">{{ version }} · AI辅助生成 · 待专业人员审核 · 不展示模型私有思维链</footer>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getGuardianCase, guardianReportUrl, retryGuardianCase } from '../api/guardian'

const route = useRoute()
const loading = ref(true)
const error = ref('')
const streamNotice = ref('')
const retrying = ref(false)
const data = ref(null)
let eventSource = null
let reconnectTimer = null
const version = import.meta.env.VITE_APP_VERSION || __APP_PACKAGE_VERSION__ || 'local'
const reportUrl = computed(() => guardianReportUrl(route.params.caseId))
const roleLabel = computed(() => data.value?.case.reporter_role === 'teacher' ? '教师观察' : '家长观察')
const riskMeta = computed(() => ({ routine: { label: '日常支持', icon: '○' }, watch: { label: '需要关注', icon: '!' }, professional: { label: '尽快获得专业支持', icon: '↑' }, urgent: { label: '立即协助', icon: '!' } }[data.value?.case.risk_level] || { label: '正在分流', icon: '…' }))
const riskIcon = computed(() => riskMeta.value.icon)
const progress = computed(() => {
  const agents = data.value?.agents || []
  if (!agents.length) return 0
  const done = agents.filter(item => ['completed', 'skipped_for_safety'].includes(item.status)).length
  return Math.round(done / agents.length * 100)
})

const labels = { SafetyGate: '安全分流', Assessor: '守护者观察摘要', KnowledgeAgent: '权威证据检索', ResourceAgent: '资源核验', InterventionAgent: '行动方案生成', CrossReviewer: '交叉审查', Coordinator: '方案统筹' }
const purposes = { SafetyGate: '确定性规则拥有最高优先级', Assessor: '不使用标准量表或疾病标签', KnowledgeAgent: '返回来源编号与证据边界', ResourceAgent: '只查询核验白名单', InterventionAgent: '生成家长或教师版行动', CrossReviewer: '检查安全、证据与角色边界', Coordinator: '组装PDF与站内回访' }
function agentLabel(type) { return labels[type] || type }
function agentPurpose(type) { return purposes[type] || '' }
function stateIcon(status) { return ({ queued: '·', running: '…', completed: '✓', failed: '×', skipped_for_safety: '—' })[status] || '·' }
function statusLabel(status) { return ({ queued: '等待执行', processing: 'Agent正在协同处理', running: '正在执行', completed: '已完成', failed: '执行失败，可重试', skipped_for_safety: '因安全规则跳过常规步骤' })[status] || status }
function followupStatus(status) { return ({ scheduled: '已安排', due: '待填写', completed: '已完成', superseded_for_safety: '安全路径接管' })[status] || status }

async function loadCase() {
  error.value = ''
  try {
    const response = await getGuardianCase(route.params.caseId)
    data.value = response.data
    if (!['completed', 'failed'].includes(response.data.case.status)) connectEvents()
  } catch (err) { error.value = err.response?.data?.detail || '请确认本地后端已经启动。' }
  finally { loading.value = false }
}

function connectEvents() {
  if (eventSource || !window.EventSource) return
  eventSource = new EventSource(`/api/guardian/cases/${route.params.caseId}/events`)
  eventSource.addEventListener('snapshot', event => { data.value = JSON.parse(event.data) })
  eventSource.addEventListener('complete', () => { eventSource?.close(); eventSource = null; streamNotice.value = ''; loadCase() })
  eventSource.onerror = () => {
    eventSource?.close(); eventSource = null
    streamNotice.value = '实时事件流已断开，工单不会丢失；正在重新读取安全状态。'
    window.clearTimeout(reconnectTimer)
    reconnectTimer = window.setTimeout(loadCase, 1500)
  }
}

async function retry() {
  retrying.value = true
  streamNotice.value = ''
  try { await retryGuardianCase(route.params.caseId); await loadCase() }
  catch (err) { streamNotice.value = err.response?.data?.detail || '重试失败，工单仍保留；请稍后再次尝试。' }
  finally { retrying.value = false }
}
onMounted(loadCase)
onBeforeUnmount(() => { eventSource?.close(); window.clearTimeout(reconnectTimer) })
</script>
