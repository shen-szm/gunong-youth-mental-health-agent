<template>
  <section class="review-deliverable" :class="{ embedded, 'workspace-report': desktopWorkspace }" :data-review-section="reviewSection" :aria-labelledby="`${idPrefix}-title`">
    <div v-if="desktopWorkspace" class="pc-review-toolbar">
      <div class="pc-review-version"><span>当前报告 · 第 {{ report?.revision_number || 1 }} 版</span><strong>{{ statusLabel }}</strong><code>{{ report?.report_id }}</code></div>
      <nav aria-label="报告审核视图"><button v-for="view in reviewViews" :key="view.id" type="button" :aria-pressed="reviewSection === view.id" @click="reviewSection = view.id">{{ view.label }}</button></nav>
    </div>
    <header class="review-hero">
      <div>
        <span class="review-kicker">数字员工最终交付</span>
        <h4 :id="`${idPrefix}-title`">教师评审报告</h4>
        <p>把授权证据、风险裁决、支持任务与回访整理为可审签、可下载的工作成果。</p>
      </div>
      <button v-if="allowGenerate" class="review-primary" type="button" :disabled="loading || decisionLoading" @click="$emit('generate')">
        <UiIcon v-if="desktop" name="report" />
        {{ loading ? '报告 Agent 执行中…' : report ? '重新生成评审报告' : '生成最终评审报告' }}
      </button>
    </header>

    <div v-if="loading" class="review-running" role="status" aria-live="polite">
      <div><strong>正在生成可核验交付物</strong><small>安全规则 → 证据映射 → 情境分析 → 支持计划 → 交叉审查 → 报告快照</small></div>
      <span class="review-skeleton" aria-hidden="true"><i></i><i></i><i></i></span>
    </div>

    <template v-if="report && !loading">
      <div class="review-meta">
        <div><span>报告编号</span><strong>{{ report.report_id }}</strong></div>
        <div><span>审核状态</span><strong>{{ statusLabel }}</strong></div>
        <div><span>生成方式</span><strong>{{ generationLabel }}</strong></div>
        <div><span>数据质量</span><strong>{{ report.data_scope?.quality }}</strong></div>
      </div>

      <TeacherAgentExecution v-if="desktop" class="review-desktop-execution" :report="report" />

      <article :class="['review-decision', report.overall_decision?.risk_level]">
        <span>{{ report.overall_decision?.risk_label }} · {{ report.overall_decision?.priority }}</span>
        <strong>{{ report.overall_decision?.decision }}</strong>
        <p>{{ report.executive_summary }}</p>
        <small>{{ report.boundary }}</small>
      </article>

      <section v-if="isUrgent" class="review-safety" :aria-labelledby="`${idPrefix}-safety`">
        <div><span>安全规则强制覆盖</span><h5 :id="`${idPrefix}-safety`">普通沟通与支持计划已停止</h5><p>先确认学生当下安全，再按校内危机流程连接真人支持。</p></div>
        <ol><li v-for="action in report.safety_review?.immediate_actions || []" :key="action.title"><strong>{{ action.title }}</strong><small>{{ action.owner }} · {{ action.due }} · {{ action.guidance_codes?.join(' / ') }}</small></li></ol>
        <ul><li v-for="threshold in report.safety_review?.escalation_thresholds || []" :key="threshold">{{ threshold }}</li></ul>
      </section>

      <div class="review-columns">
        <section class="review-card">
          <span class="review-kicker">数据边界</span><h5>范围、完整性与缺口</h5>
          <dl><div><dt>观察窗口</dt><dd>{{ shortDate(report.data_scope?.period_start) }} — {{ shortDate(report.data_scope?.content_cutoff) }}</dd></div><div><dt>记录来源</dt><dd>{{ sourceCounts }}</dd></div><div><dt>原文外传</dt><dd>未发送给外部模型</dd></div><div v-if="report.generation?.external_transfer_attempted"><dt>模型处理字段</dt><dd>{{ report.generation.transferred_fields?.join('、') }}</dd></div></dl>
          <ul><li v-for="gap in report.data_scope?.information_gaps || []" :key="gap">{{ gap }}</li></ul>
        </section>
        <section class="review-card">
          <span class="review-kicker">情境评审</span><h5>功能影响与保护因素</h5>
          <div v-for="item in report.context_review?.functioning || []" :key="item.domain" class="function-row"><strong>{{ item.domain }}</strong><em>{{ item.level }}</em><p>{{ item.observation }}</p></div>
          <div class="factor-line"><strong>保护因素</strong><span>{{ factorText(report.context_review?.protective_factors) }}</span></div>
          <div class="factor-line"><strong>风险因素</strong><span>{{ factorText(report.context_review?.risk_factors) }}</span></div>
          <div class="factor-line"><strong>学生支持意愿</strong><span>{{ report.student_preferences?.status }} · {{ report.student_preferences?.allowed_share_scope }}</span></div>
        </section>
      </div>

      <section class="review-evidence-audit" :aria-labelledby="`${idPrefix}-evidence`">
        <div class="review-section-head">
          <div><span class="review-kicker">证据追溯</span><h5 :id="`${idPrefix}-evidence`">结论—证据可追溯审计</h5></div>
          <strong :class="`audit-status is-${report.evidence_audit?.status}`">{{ report.evidence_audit?.label }}</strong>
        </div>
        <p class="audit-summary">{{ report.evidence_audit?.summary }}</p>
        <div class="audit-metrics" aria-label="证据审计统计">
          <div><span>授权记录</span><strong>{{ report.evidence_audit?.record_count || 0 }}</strong></div>
          <div><span>已被引用</span><strong>{{ report.evidence_audit?.cited_record_count || 0 }}</strong></div>
          <div><span>报告主张</span><strong>{{ report.evidence_audit?.claim_count || 0 }}</strong></div>
          <div><span>未关联主张</span><strong>{{ report.evidence_audit?.unlinked_claim_count || 0 }}</strong></div>
        </div>
        <div class="audit-layout">
          <div class="audit-claims" tabindex="0" aria-label="报告主张及其关联依据，可上下滚动">
            <article v-for="claim in report.evidence_audit?.claims || []" :key="claim.claim_id" :class="`is-${claim.status}`">
              <span>{{ claim.claim_id }} · {{ claim.section }}</span><strong>{{ claim.label }}</strong>
              <small>{{ claimBasis(claim) }}</small>
            </article>
          </div>
          <div class="audit-ledger" tabindex="0" aria-label="授权证据账本，可上下滚动">
            <div class="ledger-head"><strong>授权证据账本</strong><small>仅展示本工单范围</small></div>
            <article v-for="item in report.evidence_audit?.ledger || []" :key="item.evidence_id">
              <div><code>{{ item.evidence_id }}</code><span>{{ item.source }} · {{ shortDate(item.created_at) }}</span></div>
              <small>{{ item.used_by?.length ? `用于 ${item.used_by.join('、')}` : '尚未被报告主张引用' }} · 原文仅在本页经授权证据区查看</small>
            </article>
            <p v-if="!report.evidence_audit?.ledger?.length" class="audit-empty">没有可列入账本的授权记录，应先补充信息而非扩大结论。</p>
          </div>
        </div>
        <p class="audit-boundary">{{ report.evidence_audit?.boundary || '该状态只描述可追溯程度，不是心理风险概率、诊断置信度或专业效度评分。' }}</p>
      </section>

      <section class="review-agents" aria-label="评审报告 Agent 工作流">
        <div class="review-section-head"><div><span class="review-kicker">执行结果记录</span><h5>7 阶段受约束 Agent 工作流</h5></div><small>展示工具和结果状态，不展示模型私有思维链</small></div>
        <div class="review-agent-grid">
          <article v-for="(step, index) in report.agent_review?.workflow || []" :key="step.agent" :class="step.status">
            <span>{{ String(index + 1).padStart(2, '0') }}</span><div><strong>{{ step.agent }}</strong><small>{{ step.tool }}</small><p>{{ step.result }}</p></div><em>{{ agentStatus(step.status) }}</em>
          </article>
        </div>
      </section>

      <div v-if="!isUrgent" class="review-columns support">
        <section class="review-card">
          <span class="review-kicker">沟通与行动</span><h5>教师可直接执行的支持计划</h5>
          <blockquote>“{{ report.support_plan?.conversation_opening }}”</blockquote>
          <ol><li v-for="task in report.support_plan?.tasks || []" :key="task.title"><strong>{{ task.title }}</strong><span>{{ task.owner }} · {{ task.due }} · {{ task.guidance_codes?.join(' / ') }}</span></li></ol>
        </section>
        <section class="review-card">
          <span class="review-kicker">回访与边界</span><h5>持续支持而非一次性结论</h5>
          <ul><li v-for="item in report.support_plan?.follow_up || []" :key="item.day">第 {{ item.day }} 天：{{ item.focus }}</li></ul>
          <strong class="avoid-title">沟通中避免</strong><ul><li v-for="item in report.support_plan?.avoid || []" :key="item">{{ item }}</li></ul>
        </section>
      </div>

      <section class="review-sources">
        <div class="review-section-head"><div><span class="review-kicker">权威证据注册表</span><h5>报告仅列出本次实际适用的来源</h5></div></div>
        <a v-for="source in report.evidence_sources || []" :key="source.code" :href="source.url" target="_blank" rel="noopener noreferrer"><span>{{ source.code }}</span><strong>{{ source.title }}</strong><small>{{ source.issuer }} · {{ source.use }}</small></a>
      </section>

      <section class="review-signoff">
        <div><span class="review-kicker">Human in the loop</span><h5>教师复核与签署</h5><p>AI 完成整理和交叉检查，最终责任由具备权限的教师确认。</p></div>
        <p v-if="signingBlocked" class="signoff-blocker" role="alert">当前报告存在证据不足或未关联主张，不能签署。请退回并补充证据。</p>
        <label v-for="(item, index) in report.review_checklist || []" :key="item.item" class="review-check"><input v-model="checks[index]" type="checkbox" :disabled="report.status !== 'draft' || loading || decisionLoading"><span>{{ item.item }}<em v-if="item.required">必核</em></span></label>
        <label v-if="needsGapAcknowledgement" class="review-check evidence-gap-check"><input v-model="gapAcknowledged" type="checkbox" :disabled="report.status !== 'draft' || loading || decisionLoading"><span>我已核对报告中的证据缺口，并会在审核意见中记录接受理由和线下补充安排<em>必核</em></span></label>
        <label class="review-note"><span>审核意见</span><textarea v-model="note" maxlength="1000" :disabled="report.status !== 'draft' || loading || decisionLoading" placeholder="记录线下核对结果、责任人或需要修订的内容"></textarea></label>
        <div class="review-actions">
          <button type="button" class="review-secondary" :disabled="loading" @click="$emit('download')"><UiIcon v-if="desktop" name="download" /> 下载 PDF</button>
          <button v-if="report.status === 'draft'" type="button" class="review-secondary danger" :disabled="decisionLoading || loading || note.trim().length < 4" @click="submitDecision('revision_requested')">退回修订</button>
          <button v-if="report.status === 'draft'" type="button" class="review-primary" :disabled="decisionLoading || loading || !canSign" @click="submitDecision('reviewed')">{{ decisionLoading ? '记录中…' : '确认并签署' }}</button>
          <strong v-else-if="report.status === 'revision_requested'" class="revision-label">{{ allowGenerate ? '当前版本已退回，请重新生成修订版后再签署。' : '当前版本已退回。先按审核意见补充并核对资料，再准备新的修订任务；本报告不会自动改写。' }}</strong>
          <strong v-else class="signed-label">已由教师签署 · {{ shortDate(report.reviewed_at) }}</strong>
        </div>
      </section>
    </template>
  </section>
</template>

<script setup>
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { useDesktopViewport } from '../utils/useDesktopViewport'
import UiIcon from './UiIcon.vue'
const desktop = useDesktopViewport()
const TeacherAgentExecution = defineAsyncComponent(() => import('./TeacherAgentExecution.vue'))

const props = defineProps({ report: { type: Object, default: null }, loading: Boolean, decisionLoading: Boolean, allowGenerate: { type: Boolean, default: true }, embedded: Boolean, desktopWorkspace: Boolean, idPrefix: { type: String, default: 'review-report' } })
const reviewSection = ref('overview')
const reviewViews = [{ id: 'overview', label: '报告概览' }, { id: 'evidence', label: '证据核对' }, { id: 'signoff', label: '审核签署' }]
watch(() => props.report?.report_id, () => { reviewSection.value = 'overview' })
const emit = defineEmits(['generate', 'decision', 'download'])
const checks = ref([])
const note = ref('')
const gapAcknowledged = ref(false)

watch(() => props.report, (report) => {
  checks.value = (report?.review_checklist || []).map(() => report?.status === 'reviewed')
  note.value = report?.review_note || ''
  gapAcknowledged.value = report?.status === 'reviewed' && String(report?.review_note || '').startsWith('[已确认证据缺口]')
}, { immediate: true })

const statusLabel = computed(() => ({ draft: '待教师审核', reviewed: '教师已签署', revision_requested: '待修订' })[props.report?.status] || '待审核')
const generationLabel = computed(() => ({ xunfei_constrained: '讯飞受约束协作', safety_override: '安全规则强制覆盖', deterministic: '确定性安全模板' })[props.report?.generation?.source] || '确定性安全模板')
const sourceCounts = computed(() => Object.entries(props.report?.data_scope?.source_counts || {}).map(([key, value]) => `${key} ${value} 条`).join(' · ') || '暂无可引用记录')
const isUrgent = computed(() => props.report?.overall_decision?.risk_level === 'urgent')
const allRequiredChecked = computed(() => (props.report?.review_checklist || []).every((item, index) => !item.required || checks.value[index]))
const signingBlocked = computed(() => props.report?.evidence_audit?.status === 'insufficient' || Number(props.report?.evidence_audit?.unlinked_claim_count || 0) > 0)
const needsGapAcknowledgement = computed(() => props.report?.evidence_audit?.status === 'partial' && !signingBlocked.value)
const canSign = computed(() => allRequiredChecked.value && !signingBlocked.value && (!needsGapAcknowledgement.value || (gapAcknowledged.value && note.value.trim().length >= 10)))

function shortDate(value) { return value ? String(value).replace('T', ' ').slice(0, 16) : '--' }
function factorText(items = []) { return items.map(item => item.factor).join('；') || '需在线下沟通中补充确认' }
function agentStatus(status) { return ({ completed: '完成', attention: '需复核', blocked: '安全停止', degraded: '已降级' })[status] || status }
function claimBasis(claim) {
  if (claim.status === 'record_linked') return `学生记录：${claim.evidence_ids.join('、')}`
  if (claim.status === 'guidance_linked') return `权威指南：${claim.guidance_codes.join('、')}`
  if (claim.status === 'declared_gap') return '已明确标记为信息缺口，不据此扩大结论'
  return '尚未关联证据，签署前必须补充或删除该主张'
}
function submitDecision(decision) { emit('decision', { decision, checklistConfirmed: allRequiredChecked.value, evidenceGapAcknowledged: gapAcknowledged.value, note: note.value.trim() }) }
</script>

<style scoped>
.review-deliverable { margin-top: 20px; padding-top: 18px; border-top: 1px solid var(--t-line); color: var(--t-ink); font-size: 13px; }
.review-deliverable.embedded { margin-top: 16px; padding: 0; border-top: 0; background: none; }
.review-deliverable *,
.review-deliverable *::before,
.review-deliverable *::after { box-sizing: border-box; }
.review-kicker { display: inline-block; color: var(--t-faint); font-size: 10.5px; font-weight: 600; letter-spacing: .06em; }
.review-hero { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; }
.review-hero h4 { margin: 4px 0 5px; color: var(--t-ink); font-size: 20px; font-weight: 600; letter-spacing: -.015em; }
.review-hero p { max-width: 70ch; margin: 0; color: var(--t-muted); font-size: 12.5px; line-height: 1.65; }
.review-primary, .review-secondary { min-height: 32px; padding: 5px 13px; border-radius: var(--t-r-sm); font: inherit; font-size: 12.5px; font-weight: 600; cursor: pointer; white-space: nowrap; }
.review-primary { color: #fff; border: 1px solid var(--t-accent); background: var(--t-accent); }
.review-primary:hover:not(:disabled) { border-color: var(--t-accent-ink); background: var(--t-accent-ink); }
.review-secondary { color: var(--t-ink-2); border: 1px solid var(--t-line-2); background: var(--t-surface); }
.review-secondary:hover:not(:disabled) { border-color: #868C9B; background: var(--t-surface-2); }
.review-secondary.danger { color: var(--t-red); border-color: #E9C4C8; }
.review-secondary.danger:hover:not(:disabled) { background: var(--t-red-bg); }
.review-primary:disabled, .review-secondary:disabled { opacity: .5; cursor: not-allowed; }
.review-running { display: grid; gap: 10px; margin-top: 16px; padding: 12px 14px; border-left: 2px solid var(--t-amber); background: var(--t-amber-bg); color: var(--t-amber-ink); }
.review-running div { display: grid; gap: 2px; }
.review-running strong { font-size: 12.5px; }
.review-running small { color: #B8903E; font-size: 11px; }
.review-skeleton { display: grid; grid-template-columns: 1.5fr 1fr .7fr; gap: 6px; }
.review-skeleton i { height: 3px; border-radius: 2px; background: #E8C783; opacity: .8; }
.review-skeleton i:nth-child(2) { opacity: .55; }
.review-skeleton i:nth-child(3) { opacity: .35; }

.review-meta { display: grid; grid-template-columns: 1.4fr repeat(3, 1fr); margin: 16px 0 0; border-block: 1px solid var(--t-line); }
.review-meta div { min-width: 0; padding: 10px 14px; border-inline-end: 1px solid var(--t-line); }
.review-meta div:first-child { padding-left: 0; }
.review-meta div:last-child { border-inline-end: 0; }
.review-meta span, .review-meta strong { display: block; }
.review-meta span { margin-bottom: 2px; color: var(--t-faint); font-size: 10.5px; }
.review-meta strong { color: var(--t-ink); font-size: 12px; font-weight: 600; overflow-wrap: anywhere; }

.review-decision { margin: 18px 0 0; padding: 2px 0 2px 14px; border: 0; border-left: 3px solid var(--t-line-2); background: none; }
.review-decision > span { display: inline-block; color: var(--t-muted); font-size: 11px; font-weight: 600; letter-spacing: .02em; }
.review-decision > strong { display: block; margin: 6px 0 5px; color: var(--t-ink); font-size: 16px; font-weight: 600; line-height: 1.5; }
.review-decision p { max-width: 78ch; margin: 0; color: var(--t-ink-2); font-size: 12.5px; line-height: 1.75; }
.review-decision small { display: block; margin-top: 6px; color: var(--t-faint); font-size: 11px; line-height: 1.6; }
.review-decision.watch { border-left-color: #D9B46A; }
.review-decision.watch > span { color: var(--t-amber-ink); }
.review-decision.professional { border-left-color: #CF9AA1; }
.review-decision.professional > span { color: #B95C66; }
.review-decision.urgent { border-left-color: var(--t-red); }
.review-decision.urgent > span { color: var(--t-red); }

.review-safety { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 26px; margin-top: 16px; padding: 14px 16px; border: 1px solid #E9C4C8; border-left: 3px solid var(--t-red); border-radius: var(--t-r); background: #F7E7E9; color: var(--t-ink-2); }
.review-safety > div { grid-column: 1 / -1; }
.review-safety span { color: var(--t-red); font-size: 10.5px; font-weight: 600; letter-spacing: .03em; }
.review-safety h5 { margin: 3px 0 4px; color: #B95C66; font-size: 15px; font-weight: 600; }
.review-safety p { margin: 0; color: #B95C66; font-size: 12px; line-height: 1.6; }
.review-safety ol, .review-safety ul { margin: 4px 0 0; padding-left: 16px; }
.review-safety li { margin: 4px 0; font-size: 12px; line-height: 1.55; }
.review-safety li strong { display: block; font-weight: 600; }
.review-safety li small { display: block; margin-top: 1px; color: #CF9AA1; font-size: 10.5px; }

.review-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 0 30px; margin-top: 4px; }
.review-card { min-width: 0; padding: 16px 0; border: 0; border-top: 1px solid var(--t-line); border-radius: 0; background: none; }
.review-card h5, .review-section-head h5, .review-signoff h5 { margin: 3px 0 5px; color: var(--t-ink); font-size: 14px; font-weight: 600; }
.review-card dl { margin: 8px 0; }
.review-card dl div { display: flex; justify-content: space-between; gap: 14px; padding: 5px 0; border-bottom: 1px solid var(--t-line); }
.review-card dt { color: var(--t-muted); font-size: 12px; }
.review-card dd { margin: 0; color: var(--t-ink-2); font-size: 12px; text-align: right; overflow-wrap: anywhere; }
.review-card ul, .review-card ol { margin: 6px 0; padding-left: 16px; color: var(--t-muted); font-size: 12px; }
.review-card li { margin: 4px 0; line-height: 1.6; }
.review-card ol strong, .review-card ol span { display: block; }
.review-card ol strong { color: var(--t-ink-2); font-weight: 600; }
.review-card ol span { color: var(--t-faint); font-size: 10.5px; }
.review-card blockquote { margin: 10px 0; padding: 10px 12px; border-left: 2px solid #E8C783; color: #B8903E; background: var(--t-amber-bg); font-size: 12.5px; line-height: 1.7; }
.function-row { display: grid; grid-template-columns: 1fr auto; gap: 1px 10px; padding: 7px 0; border-bottom: 1px solid var(--t-line); }
.function-row strong { color: var(--t-ink-2); font-size: 12px; font-weight: 600; }
.function-row em { color: var(--t-amber-ink); font-size: 11px; font-style: normal; }
.function-row p { grid-column: 1 / -1; margin: 0; color: var(--t-muted); font-size: 11.5px; }
.factor-line { display: grid; gap: 2px; margin-top: 8px; }
.factor-line strong { color: var(--t-ink-2); font-size: 12px; font-weight: 600; }
.factor-line span { color: var(--t-muted); font-size: 11.5px; line-height: 1.55; }
.avoid-title { display: block; margin-top: 10px; color: #B95C66; font-size: 12px; font-weight: 600; }

.review-evidence-audit, .review-agents, .review-sources, .review-signoff { margin-top: 4px; padding: 16px 0; border-top: 1px solid var(--t-line); }
.review-section-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.review-section-head small { color: var(--t-faint); font-size: 10.5px; }
.audit-status { padding: 1px 7px; border: 1px solid #EBD4A4; border-radius: 3px; color: var(--t-amber-ink); background: var(--t-amber-bg); font-size: 10.5px; font-weight: 600; white-space: nowrap; }
.audit-status.is-review_ready { color: var(--t-green-ink); border-color: #C5E3D1; background: var(--t-green-bg); }
.audit-status.is-insufficient { color: var(--t-red); border-color: #E9C4C8; background: var(--t-red-bg); }
.audit-summary { margin: 6px 0 10px; color: var(--t-muted); font-size: 12px; line-height: 1.65; }
.audit-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border-block: 1px solid var(--t-line); }
.audit-metrics div { padding: 9px 12px; border-inline-end: 1px solid var(--t-line); }
.audit-metrics div:first-child { padding-left: 0; }
.audit-metrics div:last-child { border-inline-end: 0; }
.audit-metrics span, .audit-metrics strong { display: block; }
.audit-metrics span { color: var(--t-muted); font-size: 10.5px; }
.audit-metrics strong { margin-top: 1px; color: var(--t-ink); font-size: 17px; font-weight: 600; font-variant-numeric: tabular-nums; }
.audit-layout { display: grid; grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr); gap: 12px; margin-top: 12px; }
.audit-claims, .audit-ledger { max-height: 340px; padding: 0 12px; border: 1px solid var(--t-line); border-radius: var(--t-r-sm); background: var(--t-surface-2); overflow: auto; }
.audit-claims article, .audit-ledger article { display: grid; gap: 2px; padding: 9px 0; border-bottom: 1px solid var(--t-line); }
.audit-claims article:last-child, .audit-ledger article:last-child { border-bottom: 0; }
.audit-claims article > span, .audit-claims small, .audit-ledger small, .ledger-head small { color: var(--t-faint); font-size: 10px; }
.audit-claims article > strong { color: var(--t-ink-2); font-size: 11.5px; font-weight: 600; }
.audit-claims article.is-unlinked { padding-left: 10px; border-left: 2px solid var(--t-red); background: #F7E7E9; }
.audit-claims article.is-declared_gap { padding-left: 10px; border-left: 2px solid #D9B46A; background: var(--t-amber-bg); }
.ledger-head { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--t-line); color: var(--t-ink-2); font-size: 11.5px; }
.audit-ledger article > div { display: flex; justify-content: space-between; gap: 8px; }
.audit-ledger code { color: var(--t-accent); font-size: 10px; }
.audit-ledger span { color: var(--t-faint); font-size: 10px; }
.audit-ledger p { margin: 2px 0; color: var(--t-muted); font-size: 11px; line-height: 1.5; }
.audit-empty { margin: 10px 0; color: var(--t-muted); font-size: 11.5px; }
.audit-boundary { margin: 10px 0 0; color: var(--t-faint); font-size: 10.5px; line-height: 1.6; }

.review-agent-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 10px; }
.review-agent-grid article { display: grid; grid-template-columns: 22px minmax(0, 1fr) auto; gap: 9px; padding: 10px 12px; border: 1px solid var(--t-line); border-radius: var(--t-r-sm); background: var(--t-surface); }
.review-agent-grid article > span { color: var(--t-faint); font: 500 10px/1.6 var(--t-mono); }
.review-agent-grid article div { display: grid; gap: 1px; min-width: 0; }
.review-agent-grid strong { color: var(--t-ink-2); font-size: 12px; font-weight: 600; }
.review-agent-grid small, .review-agent-grid p { margin: 0; color: var(--t-muted); font-size: 10.5px; line-height: 1.5; }
.review-agent-grid em { color: var(--t-green-ink); font-size: 10px; font-style: normal; font-weight: 600; white-space: nowrap; }
.review-agent-grid .attention { border-left: 2px solid #D9B46A; }
.review-agent-grid .attention em { color: var(--t-amber-ink); }
.review-agent-grid .blocked { border-left: 2px solid var(--t-red); }
.review-agent-grid .blocked em { color: var(--t-red); }

.review-sources { display: grid; gap: 0; }
.review-sources > .review-section-head { margin-bottom: 6px; }
.review-sources a { display: grid; grid-template-columns: 92px 1fr; gap: 2px 12px; padding: 9px 0; border-bottom: 1px solid var(--t-line); color: inherit; text-decoration: none; }
.review-sources a:hover strong { color: var(--t-accent); }
.review-sources a span { grid-row: 1 / 3; color: var(--t-faint); font: 500 10.5px/1.6 var(--t-mono); }
.review-sources a strong { color: var(--t-ink-2); font-size: 12px; font-weight: 600; }
.review-sources a small { color: var(--t-muted); font-size: 11px; }

.review-signoff { display: grid; grid-template-columns: 1fr 1.05fr; gap: 4px 30px; }
.review-signoff > div:first-child { grid-row: span 6; }
.review-signoff p { margin: 0; color: var(--t-muted); font-size: 12px; line-height: 1.65; }
.signoff-blocker { grid-column: 2; margin: 6px 0 0; padding: 8px 10px; border-left: 2px solid var(--t-red); color: var(--t-red); background: var(--t-red-bg); font-size: 11.5px; line-height: 1.55; }
.review-check { display: flex; align-items: flex-start; gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--t-line); color: var(--t-ink-2); font-size: 12px; line-height: 1.6; }
.review-check input { flex: 0 0 auto; margin-top: 4px; accent-color: var(--t-accent); }
.review-check em { margin-left: 6px; padding: 0 4px; border: 1px solid var(--t-line-2); border-radius: 2px; color: var(--t-faint); font-size: 9.5px; font-style: normal; }
.evidence-gap-check { padding: 8px 10px; border-left: 2px solid #D9B46A; background: var(--t-amber-bg); border-bottom: 0; }
.review-note { display: grid; gap: 5px; padding: 10px 0 0; border: 0; color: var(--t-muted); font-size: 11.5px; font-weight: 600; }
.review-note textarea { min-height: 72px; padding: 8px 10px; border: 1px solid var(--t-line-2); border-radius: var(--t-r-sm); color: var(--t-ink); background: var(--t-surface); font: inherit; font-size: 12px; resize: vertical; }
.review-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; align-items: center; gap: 8px; grid-column: 1 / -1; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--t-line); }
.signed-label { color: var(--t-green-ink); font-size: 12px; }
.revision-label { color: var(--t-amber-ink); font-size: 12px; line-height: 1.6; }
.review-deliverable :focus-visible { outline: 2px solid var(--t-accent); outline-offset: 2px; }

.review-deliverable.embedded .review-card,
.review-deliverable.embedded .review-signoff,
.review-deliverable.embedded .review-evidence-audit,
.review-deliverable.embedded .review-sources,
.review-deliverable.embedded .review-agents { padding: 16px 0; border: 0; border-top: 1px solid var(--t-line); }
.review-deliverable.embedded .review-note textarea { width: 100%; }
.review-deliverable.embedded .review-primary,
.review-deliverable.embedded .review-secondary { min-height: 36px; }

.pc-review-toolbar { display: none; }
@media (min-width: 1024px) {
  .workspace-report .pc-review-toolbar { display: block; position: sticky; top: 64px; z-index: 5; padding-top: 10px; border-bottom: 1px solid var(--t-line); background: var(--t-surface); }
  .pc-review-version { display: grid; grid-template-columns: 1fr auto; gap: 2px 12px; color: var(--t-faint); font-size: 11px; }
  .pc-review-version strong { color: var(--t-ink-2); font-weight: 600; }
  .pc-review-version code { grid-column: 1 / -1; color: var(--t-faint); font-size: 10.5px; overflow-wrap: anywhere; }
  .pc-review-toolbar nav { display: flex; gap: 18px; margin-top: 8px; }
  .pc-review-toolbar button { min-height: 30px; padding: 6px 0; border: 0; border-bottom: 2px solid transparent; color: var(--t-muted); background: none; font: inherit; font-size: 12.5px; cursor: pointer; }
  .pc-review-toolbar button[aria-pressed=true] { color: var(--t-ink); border-bottom-color: var(--t-accent); font-weight: 600; }
  .pc-review-toolbar button:hover { color: var(--t-ink); }
  .workspace-report[data-review-section] > .review-hero,
  .workspace-report[data-review-section] .review-desktop-execution,
  .workspace-report[data-review-section] .review-agents { display: none; }
  .workspace-report[data-review-section=overview] .review-evidence-audit,
  .workspace-report[data-review-section=overview] .review-signoff { display: none; }
  .workspace-report[data-review-section=evidence] > .review-meta,
  .workspace-report[data-review-section=evidence] > .review-decision,
  .workspace-report[data-review-section=evidence] > .review-safety,
  .workspace-report[data-review-section=evidence] > .review-columns,
  .workspace-report[data-review-section=evidence] > .review-sources,
  .workspace-report[data-review-section=evidence] > .review-signoff { display: none; }
  .workspace-report[data-review-section=signoff] > .review-meta,
  .workspace-report[data-review-section=signoff] > .review-decision,
  .workspace-report[data-review-section=signoff] > .review-safety,
  .workspace-report[data-review-section=signoff] > .review-columns,
  .workspace-report[data-review-section=signoff] > .review-sources,
  .workspace-report[data-review-section=signoff] > .review-evidence-audit { display: none; }
  .workspace-report .review-columns { grid-template-columns: 1fr; }
  .workspace-report .review-meta { grid-template-columns: 1fr 1fr; }
  .workspace-report .review-meta div:nth-child(2) { border-inline-end: 0; }
  .workspace-report .audit-layout { grid-template-columns: 1fr; }
  .workspace-report .review-signoff { scroll-margin-top: 180px; }
}
@media (min-width: 1024px) { .review-agents { display: none; } }
@media (max-width: 1023px) {
  .review-desktop-execution { display: none; }
  .embedded .review-evidence-audit { display: block; }
}
@media (max-width: 700px) {
  .embedded .review-columns, .embedded .audit-layout, .embedded .review-agent-grid, .embedded .review-signoff, .embedded .review-safety { grid-template-columns: 1fr; }
  .review-hero { flex-direction: column; gap: 10px; }
  .review-meta { grid-template-columns: 1fr 1fr; }
  .review-meta div { border-inline-end: 0; border-bottom: 1px solid var(--t-line); padding-left: 0; }
  .review-meta div:nth-child(odd) { padding-right: 12px; }
  .review-safety { grid-template-columns: 1fr; }
  .embedded .review-signoff > div:first-child,
  .review-signoff > div:first-child { grid-row: auto; }
  .review-signoff { grid-template-columns: 1fr; }
  .signoff-blocker { grid-column: auto; }
  .embedded .audit-metrics, .audit-metrics { grid-template-columns: 1fr 1fr; }
  .embedded .review-sources a { grid-template-columns: 1fr; }
  .embedded .review-sources a span { grid-row: auto; }
  .review-actions button { flex: 1 1 auto; }
}
</style>
