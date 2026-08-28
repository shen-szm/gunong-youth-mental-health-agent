<template>
  <section class="review-deliverable" aria-labelledby="review-report-title">
    <header class="review-hero">
      <div>
        <span class="review-kicker">数字员工最终交付</span>
        <h4 id="review-report-title">教师评审报告</h4>
        <p>把授权证据、风险裁决、支持任务与回访整理为可审签、可下载的工作成果。</p>
      </div>
      <button class="review-primary" type="button" :disabled="loading" @click="$emit('generate')">
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

      <article :class="['review-decision', report.overall_decision?.risk_level]">
        <span>{{ report.overall_decision?.risk_label }} · {{ report.overall_decision?.priority }}</span>
        <strong>{{ report.overall_decision?.decision }}</strong>
        <p>{{ report.executive_summary }}</p>
        <small>{{ report.boundary }}</small>
      </article>

      <section v-if="isUrgent" class="review-safety" aria-labelledby="teacher-review-safety-title">
        <div><span>安全规则强制覆盖</span><h5 id="teacher-review-safety-title">普通沟通与支持计划已停止</h5><p>先确认学生当下安全，再按校内危机流程连接真人支持。</p></div>
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
        <label v-for="(item, index) in report.review_checklist || []" :key="item.item" class="review-check"><input v-model="checks[index]" type="checkbox" :disabled="report.status !== 'draft' || loading"><span>{{ item.item }}<em v-if="item.required">必核</em></span></label>
        <label class="review-note"><span>审核意见</span><textarea v-model="note" maxlength="1000" :disabled="report.status !== 'draft' || loading" placeholder="记录线下核对结果、责任人或需要修订的内容"></textarea></label>
        <div class="review-actions">
          <button type="button" class="review-secondary" :disabled="loading" @click="$emit('download')">下载 PDF</button>
          <button v-if="report.status === 'draft'" type="button" class="review-secondary danger" :disabled="decisionLoading || loading || note.trim().length < 4" @click="submitDecision('revision_requested')">退回修订</button>
          <button v-if="report.status === 'draft'" type="button" class="review-primary" :disabled="decisionLoading || loading || !allRequiredChecked" @click="submitDecision('reviewed')">{{ decisionLoading ? '记录中…' : '确认并签署' }}</button>
          <strong v-else-if="report.status === 'revision_requested'" class="revision-label">当前版本已退回，请重新生成修订版后再签署。</strong>
          <strong v-else class="signed-label">已由教师签署 · {{ shortDate(report.reviewed_at) }}</strong>
        </div>
      </section>
    </template>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({ report: { type: Object, default: null }, loading: Boolean, decisionLoading: Boolean })
const emit = defineEmits(['generate', 'decision', 'download'])
const checks = ref([])
const note = ref('')

watch(() => props.report, (report) => {
  checks.value = (report?.review_checklist || []).map(() => report?.status === 'reviewed')
  note.value = report?.review_note || ''
}, { immediate: true })

const statusLabel = computed(() => ({ draft: '待教师审核', reviewed: '教师已签署', revision_requested: '待修订' })[props.report?.status] || '待审核')
const generationLabel = computed(() => ({ xunfei_constrained: '讯飞受约束协作', safety_override: '安全规则强制覆盖', deterministic: '确定性安全模板' })[props.report?.generation?.source] || '确定性安全模板')
const sourceCounts = computed(() => Object.entries(props.report?.data_scope?.source_counts || {}).map(([key, value]) => `${key} ${value} 条`).join(' · ') || '暂无可引用记录')
const isUrgent = computed(() => props.report?.overall_decision?.risk_level === 'urgent')
const allRequiredChecked = computed(() => (props.report?.review_checklist || []).every((item, index) => !item.required || checks.value[index]))

function shortDate(value) { return value ? String(value).replace('T', ' ').slice(0, 16) : '--' }
function factorText(items = []) { return items.map(item => item.factor).join('；') || '需在线下沟通中补充确认' }
function agentStatus(status) { return ({ completed: '完成', attention: '需复核', blocked: '安全停止', degraded: '已降级' })[status] || status }
function submitDecision(decision) { emit('decision', { decision, checklistConfirmed: allRequiredChecked.value, note: note.value.trim() }) }
</script>

<style scoped>
.review-deliverable{margin-top:18px;padding:22px;border:1px solid rgba(69,105,91,.24);border-radius:16px;background:linear-gradient(145deg,rgba(255,252,244,.94),rgba(233,244,238,.9))}
.review-hero,.review-section-head,.review-actions{display:flex;align-items:center;justify-content:space-between;gap:20px}.review-hero h4,.review-section-head h5,.review-card h5,.review-signoff h5{margin:4px 0 6px;color:#263f36;font-size:21px}.review-hero p,.review-section-head p,.review-signoff p{margin:0;color:#62736c}.review-kicker{color:#4f7868;font-size:12px;font-weight:800}.review-primary,.review-secondary{min-height:42px;padding:0 16px;border:1px solid #b9ccc3;border-radius:12px;background:#fff;color:#315b4d;font-weight:800;cursor:pointer}.review-primary{border-color:#315f50;background:#315f50;color:#fff}.review-primary:disabled,.review-secondary:disabled{cursor:not-allowed;opacity:.5}.review-running{display:grid;gap:12px;margin-top:18px;padding:16px;border-radius:14px;background:#fff8e7;color:#5f5128}.review-running div{display:grid;gap:3px}.review-running small{color:#746a4a}.review-skeleton{display:grid;grid-template-columns:1.5fr 1fr .7fr;gap:7px}.review-skeleton i{height:5px;border-radius:5px;background:#d8c586;opacity:.78}.review-skeleton i:nth-child(2){opacity:.55}.review-skeleton i:nth-child(3){opacity:.35}
.review-meta{display:grid;grid-template-columns:1.5fr repeat(3,1fr);gap:8px;margin:18px 0 10px}.review-meta div{padding:12px;border-radius:12px;background:rgba(255,255,255,.76)}.review-meta span,.review-meta strong{display:block}.review-meta span{margin-bottom:4px;color:#6c7c74;font-size:11px}.review-meta strong{color:#30483f;font-size:13px;overflow-wrap:anywhere}.review-decision{padding:20px;border:1px solid #8aa99b;border-radius:16px;background:#fff}.review-decision.watch{border-color:#cba14b;background:#fffaf0}.review-decision.professional{border-color:#c56a40;background:#fff7f2}.review-decision.urgent{border-color:#b54a46;background:#fff4f3}.review-decision>span{display:inline-block;padding:4px 8px;border-radius:8px;background:#e8f2ed;color:#3f6658;font-size:12px;font-weight:800}.review-decision.watch>span{background:#f7e9bd;color:#715415}.review-decision.professional>span{background:#f6dfd2;color:#80442b}.review-decision.urgent>span{background:#f2d7d4;color:#873934}.review-decision>strong{display:block;margin:9px 0 7px;color:#253f36;font-size:18px}.review-decision p{max-width:75ch;color:#40584f;line-height:1.7}.review-decision small{color:#687771}
.review-safety{display:grid;grid-template-columns:.8fr 1.2fr;gap:16px;margin-top:12px;padding:18px;border:2px solid #b54a46;border-radius:14px;background:#fff4f3;color:#4d302e}.review-safety>div{grid-row:span 2}.review-safety span{color:#8b3934;font-size:12px;font-weight:800}.review-safety h5{margin:6px 0;font-size:18px}.review-safety p{margin:0;line-height:1.55}.review-safety ol,.review-safety ul{margin:0;padding-left:20px}.review-safety li{margin:7px 0;line-height:1.5}.review-safety li strong,.review-safety li small{display:block}.review-safety li small{margin-top:3px;color:#76504c}
.review-columns{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}.review-card,.review-agents,.review-sources,.review-signoff{padding:18px;border:1px solid rgba(70,104,91,.15);border-radius:16px;background:rgba(255,255,255,.82)}.review-card h5,.review-section-head h5,.review-signoff h5{font-size:17px}.review-card dl{margin:12px 0}.review-card dl div{display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-bottom:1px solid #e7eee9}.review-card dt{color:#78877f}.review-card dd{margin:0;color:#354d44;text-align:right}.review-card ul,.review-card ol{margin:10px 0;padding-left:20px;color:#4b5e57}.review-card li{margin:7px 0;line-height:1.5}.function-row{display:grid;grid-template-columns:1fr auto;gap:3px 10px;padding:9px 0;border-bottom:1px solid #e7eee9}.function-row strong{color:#344e44}.function-row em{color:#95652d;font-size:12px;font-style:normal}.function-row p{grid-column:1/-1;margin:0;color:#687971;font-size:12px}.factor-line{display:grid;gap:4px;margin-top:11px}.factor-line span{color:#5b6e66;line-height:1.5}
.review-agents,.review-sources,.review-signoff{margin-top:12px}.review-section-head small{color:#687971}.review-agent-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:14px}.review-agent-grid article{display:grid;grid-template-columns:30px minmax(0,1fr) auto;gap:9px;padding:12px;border:1px solid #e0eae5;border-radius:13px;background:#f9fbfa}.review-agent-grid article>span{color:#647e74;font:700 11px monospace}.review-agent-grid article div{display:grid;gap:2px}.review-agent-grid strong{color:#304b41}.review-agent-grid small,.review-agent-grid p{margin:0;color:#5f7169;font-size:11px;line-height:1.45}.review-agent-grid em{color:#43715f;font-size:11px;font-style:normal;font-weight:800}.review-agent-grid .attention{background:#fff9e9}.review-agent-grid .blocked{background:#fff1ef}.review-card blockquote{margin:13px 0;padding:12px 14px;border:1px solid #dbc77e;border-radius:10px;background:#fff8e6;color:#4e4937;line-height:1.6}.review-card ol li{padding-left:3px}.review-card ol strong,.review-card ol span{display:block}.review-card ol span{color:#687971;font-size:11px}.avoid-title{display:block;margin-top:14px;color:#704f43}
.review-sources{display:grid;gap:8px}.review-sources a{display:grid;grid-template-columns:105px 1fr;gap:3px 12px;padding:11px 12px;border:1px solid #e1eae6;border-radius:11px;color:inherit;text-decoration:none}.review-sources a:hover{border-color:#8eac9f;background:#f7fbf9}.review-sources a span{grid-row:1/3;color:#527565;font:700 11px monospace}.review-sources a strong{color:#304b41}.review-sources a small{color:#62746b}.review-signoff{display:grid;grid-template-columns:1.1fr 1fr;gap:10px 24px}.review-signoff>div:first-child{grid-row:span 5}.review-check{display:flex;align-items:flex-start;gap:9px;color:#41574f}.review-check input{margin-top:3px}.review-check em{margin-left:7px;padding:2px 6px;border-radius:7px;background:#edf4f0;color:#537266;font-size:10px;font-style:normal}.review-note{display:grid;gap:6px}.review-note span{color:#536860;font-weight:700}.review-note textarea{min-height:76px;padding:10px;border:1px solid #cbd8d2;border-radius:10px;background:#fff;font:inherit;resize:vertical}.review-actions{grid-column:1/-1;justify-content:flex-end;padding-top:8px;border-top:1px solid #e1e9e5}.review-secondary.danger{color:#91493f}.signed-label{color:#36705b}.revision-label{color:#8a5d28}.review-deliverable :focus-visible{outline:3px solid #e2bd5e;outline-offset:3px}
</style>
