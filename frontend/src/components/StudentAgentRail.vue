<template>
  <section class="student-agent-shell" :class="{ 'is-open': open, 'is-graph-open': graphOpen && desktop }" aria-label="咕哝智能体工作状态">
    <button
      ref="toggleButton"
      class="student-agent-toggle"
      type="button"
      :aria-label="open ? '收起咕哝智能体进度' : `展开咕哝智能体进度，最新状态：${state.lastEvent || '等待你开始表达'}`"
      :aria-expanded="open"
      aria-controls="student-agent-rail"
      @click="$emit('toggle')"
    >
      <span class="agent-toggle-mark" :class="`is-${state.status}`" aria-hidden="true"></span>
      <span class="agent-toggle-copy">
        <span class="agent-toggle-heading"><strong>咕哝 Agent</strong><small>{{ compactStatus }}</small></span>
        <span class="agent-toggle-latest">{{ state.lastEvent || '等待你开始表达' }}</span>
      </span>
      <span class="agent-toggle-chevron" aria-hidden="true">{{ open ? '⌃' : '›' }}</span>
    </button>
    <span v-if="!open" class="agent-toggle-live" role="status" aria-live="polite">
      {{ compactStatus }}：{{ state.lastEvent || '等待你开始表达' }}
    </span>

    <Transition name="agent-rail">
      <aside
        v-if="open"
        id="student-agent-rail"
        class="student-agent-rail"
        aria-labelledby="student-agent-title"
        @keydown.esc="$emit('close')"
      >
        <header class="agent-rail-header">
          <div>
            <h2 id="student-agent-title">本轮协作</h2>
            <p>{{ taskEyebrow }}</p>
          </div>
          <button ref="closeButton" class="agent-rail-close" type="button" aria-label="收起智能体进度" @click="$emit('close')">⌄</button>
        </header>

        <p class="agent-rail-event" role="status" aria-live="polite">
          <span :class="`is-${state.status}`" aria-hidden="true"></span>
          <strong>{{ compactStatus }}</strong>
          <small>{{ state.lastEvent || '等待你开始表达' }}</small>
        </p>

        <button v-if="desktop" class="agent-graph-toggle" type="button" :aria-expanded="graphOpen" aria-controls="agent-execution-view" @click="graphOpen = !graphOpen">
          {{ graphOpen ? '收起执行图' : '查看执行图与工具记录' }}<span aria-hidden="true">{{ graphOpen ? '−' : '↗' }}</span>
        </button>
        <div v-if="graphOpen && desktop" id="agent-execution-view">
          <AgentExecutionGraph :state="state" :agent-label="agentLabel" :tool-label="toolLabel" />
        </div>

        <ol v-show="!graphOpen || !desktop" class="agent-step-list" aria-label="多 Agent 协作轨迹">
          <li v-for="step in displaySteps" :key="step.id" :class="`is-${step.status}`">
            <span class="agent-step-icon" aria-hidden="true">{{ statusIcon(step.status) }}</span>
            <div>
              <strong>{{ step.label }}</strong>
              <small>{{ step.summary }}</small>
            </div>
            <em>{{ statusLabel(step.status) }}</em>
          </li>
        </ol>

        <section v-if="hasDeliverable" class="agent-delivery" aria-labelledby="student-agent-delivery-title">
          <header class="agent-delivery-head">
            <div>
              <span>可验收交付</span>
              <h3 id="student-agent-delivery-title">最近一次任务回执</h3>
            </div>
            <strong :class="['agent-verification-status', `is-${verificationTone}`]">{{ verificationLabel }}</strong>
          </header>

          <div v-if="taskContract.objective" class="agent-delivery-objective">
            <span>任务目标</span>
            <p>{{ taskContract.objective }}</p>
          </div>

          <dl v-if="contractConstraints.length || acceptanceCriteria.length" class="agent-contract-list">
            <div v-if="contractConstraints.length">
              <dt>执行约束</dt>
              <dd><ul><li v-for="item in contractConstraints" :key="item">{{ item }}</li></ul></dd>
            </div>
            <div v-if="acceptanceCriteria.length">
              <dt>验收条件</dt>
              <dd><ul><li v-for="item in acceptanceCriteria" :key="item">{{ item }}</li></ul></dd>
            </div>
          </dl>

          <div v-if="verificationChecks.length" class="agent-checks">
            <h4>逐项核验</h4>
            <ul>
              <li v-for="check in verificationChecks" :key="check.id || check.label">
                <span :class="`is-${verificationCheckTone(check.status)}`" aria-hidden="true">{{ verificationCheckIcon(check.status) }}</span>
                <div>
                  <strong>{{ check.label || '未命名验收项' }}</strong>
                  <small v-if="evidenceText(check.evidence)">{{ evidenceText(check.evidence) }}</small>
                </div>
                <em>{{ verificationCheckLabel(check.status) }}</em>
              </li>
            </ul>
          </div>

          <div v-if="hasArtifact" class="agent-artifact">
            <span>交付物</span>
            <h4>{{ artifact.title || '本轮支持结果' }}</h4>
            <p v-if="artifact.outcome">{{ artifact.outcome }}</p>
            <dl>
              <div v-if="artifact.next_action"><dt>可选下一步</dt><dd>{{ artifact.next_action }}</dd></div>
              <div v-if="artifact.next_owner"><dt>下一责任人</dt><dd>{{ ownerLabel(artifact.next_owner) }}</dd></div>
            </dl>
          </div>
        </section>

        <details class="agent-technical-details">
          <summary>查看工作记录与数据来源</summary>
          <div class="student-agent-source" aria-label="当前 Agent 生成来源">
            <strong>{{ sourceLabel }}</strong>
            <small>{{ sourceDetail }}</small>
          </div>
          <section v-if="state.runCode" class="agent-task-brief" aria-label="本次智能体任务理解">
            <div><strong>任务编号</strong><code>{{ state.runCode }}</code></div>
            <p>{{ state.intentSummary || '等待服务端返回结构化任务摘要' }}</p>
            <div v-if="activeRoles.length" class="agent-role-row" aria-label="已核验协作角色">
              <span v-for="role in activeRoles" :key="role">{{ role }}</span>
            </div>
            <div v-if="executedTools.length" class="agent-tool-row" aria-label="实际调用工具">
              <span v-for="tool in executedTools" :key="tool">{{ toolLabel(tool) }}</span>
            </div>
          </section>
          <p class="agent-boundary">只展示可核验的工作步骤与结果摘要，不展示模型私有思维过程；情绪整理不等于心理诊断。</p>
        </details>

        <footer class="agent-rail-footer">
          <span>{{ state.messageCount ? `已核对 ${state.messageCount} 条表达` : '等待本轮表达' }}</span>
          <strong>{{ riskLabel }}</strong>
        </footer>
        <button v-if="state.runCode && state.status !== 'running'" class="agent-delete-run" type="button" @click="$emit('delete-run')">删除本次记录</button>
      </aside>
    </Transition>
  </section>
</template>

<script setup>
import { computed, defineAsyncComponent, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

const AgentExecutionGraph = defineAsyncComponent(() => import('./AgentExecutionGraph.vue'))
const graphOpen = ref(false)
const desktop = ref(false)
let desktopQuery
function updateDesktop() { desktop.value = desktopQuery.matches }
onMounted(() => {
  desktopQuery = window.matchMedia('(min-width: 900px)')
  updateDesktop()
  desktopQuery.addEventListener('change', updateDesktop)
})
onUnmounted(() => desktopQuery?.removeEventListener('change', updateDesktop))

const props = defineProps({
  open: { type: Boolean, default: false },
  state: {
    type: Object,
    required: true,
  },
  steps: {
    type: Array,
    required: true,
  },
})

const emit = defineEmits(['toggle', 'close', 'delete-run'])
const toggleButton = ref(null)
const closeButton = ref(null)

const compactStatus = computed(() => {
  const labels = {
    standby: '等待倾听',
    running: '正在协作',
    ready: '本轮完成',
    attention: '需要处理',
    urgent: '安全流程优先',
    error: '等待重试',
  }
  return labels[props.state.status] || '等待倾听'
})

const taskEyebrow = computed(() => ({
  waiting: '当前任务 · 等待学生表达',
  chat: '当前任务 · 本轮倾诉回应',
  responded: '当前任务 · 继续倾听',
  end_candidate: '当前任务 · 等待学生决定',
  summary: '当前任务 · 完整会话小结',
  complete: '已交付 · 情绪小结与下一步',
  delivery_attention: '交付核验 · 等待补充处理',
  urgent: '安全任务 · 真人支持交接',
  chat_error: '当前任务 · 等待安全重试',
})[props.state.phase] || '当前任务 · 学生支持')

const activeRoles = computed(() => {
  const verifiedRoles = [...new Set((props.state.events || []).map(event => event.agent).filter(Boolean))]
  if (verifiedRoles.length) return verifiedRoles
  return []
})
const executedTools = computed(() => [...new Set((props.state.events || []).map(event => event.tool).filter(Boolean))])

const deliverable = computed(() => props.state.deliverable && typeof props.state.deliverable === 'object'
  ? props.state.deliverable
  : {})
const taskContract = computed(() => deliverable.value.task_contract && typeof deliverable.value.task_contract === 'object'
  ? deliverable.value.task_contract
  : {})
const verification = computed(() => deliverable.value.verification && typeof deliverable.value.verification === 'object'
  ? deliverable.value.verification
  : {})
const artifact = computed(() => deliverable.value.artifact && typeof deliverable.value.artifact === 'object'
  ? deliverable.value.artifact
  : {})
const contractConstraints = computed(() => listValues(taskContract.value.constraints))
const acceptanceCriteria = computed(() => listValues(taskContract.value.acceptance_criteria))
const verificationChecks = computed(() => Array.isArray(verification.value.checks) ? verification.value.checks : [])
const hasArtifact = computed(() => Boolean(artifact.value.title || artifact.value.outcome || artifact.value.next_action || artifact.value.next_owner))
const hasDeliverable = computed(() => Boolean(
  taskContract.value.objective
  || contractConstraints.value.length
  || acceptanceCriteria.value.length
  || verification.value.status
  || verificationChecks.value.length
  || hasArtifact.value,
))
const verificationTone = computed(() => verificationCheckTone(verification.value.status))
const verificationLabel = computed(() => verificationCheckLabel(verification.value.status))

const displaySteps = computed(() => {
  if (!props.state.events?.length) return props.steps
  return props.state.events.map(event => ({
    id: `${event.sequence}-${event.agent}`,
    label: agentLabel(event.agent),
    summary: event.summary,
    status: event.status === 'failed' ? 'error' : event.status,
  }))
})

function agentLabel(agent) {
  return ({
    ConversationObserver: '理解表达',
    StudentSafetyGate: '安全检查',
    StudentTaskPlanner: '规划受限任务',
    bounded_support_planner: '规划受限任务',
    EmotionSynthesizer: '情绪整理',
    ResourceNavigator: '匹配支持资源',
    ResponseAgent: '生成回应',
    StudentResponseReviewer: '输出复核',
    OutcomeVerifier: '核验交付结果',
    DeliveryVerifier: '核验交付结果',
    SafetyCoordinator: '交付安全路径',
    StudentCoordinator: '完成交付',
    StudentRunRecovery: '恢复任务状态',
    StudentSupportRecovery: '恢复任务状态',
  })[agent] || agent
}

const riskLabel = computed(() => {
  const labels = {
    unassessed: '尚未分流',
    routine: '日常支持',
    watch: '建议持续留意',
    professional: '建议专业支持',
    urgent: '立即安全协助',
  }
  return labels[props.state.riskLevel] || labels.unassessed
})

const sourceLabel = computed(() => ({
  deepseek_companion: 'DeepSeek 小满对话',
  xunfei_constrained: '讯飞策略协作',
  safety_override: '安全规则强制覆盖',
  degraded: '规则安全降级',
  deterministic: '本地确定性规则',
  pending: '来源等待确认',
  unavailable: '来源未确认',
})[props.state.source] || '来源未确认')

const sourceDetail = computed(() => props.state.source === 'deepseek_companion'
  ? '本轮回应由 DeepSeek 小满对话生成，会话原文按隐私说明发送，也用于生成小结；安全规则仍具有最终裁决权'
  : props.state.source === 'xunfei_constrained'
    ? '模型依据去标识化结构线索选择情绪、支持需要与回应策略；学生可见文字由后端审核话术库实现'
    : props.state.source === 'safety_override'
      ? '普通生成已停止，当前只执行确定性安全路径'
      : props.state.source === 'degraded'
        ? '模型结果不可用或未通过校验，已使用可审核规则模板'
      : props.state.source === 'pending'
        ? '等待后端返回可核验的执行结果'
        : props.state.source === 'unavailable'
          ? '本轮未获得有效执行结果，不能判断生成来源'
          : '本轮未使用外部模型')

function statusIcon(status) {
  return ({ completed: '✓', running: '•', attention: '!', blocked: '停', waiting: '·', error: '×' })[status] || '·'
}

function statusLabel(status) {
  return ({ completed: '完成', running: '进行中', attention: '需确认', blocked: '已停止', waiting: '等待', error: '需重试' })[status] || '等待'
}

function toolLabel(tool) {
  return ({
    derived_feature_extractor: '结构特征提炼',
    deterministic_safety_rules: '安全规则',
    bounded_support_planner: '受限支持规划',
    student_task_planner: '受限支持规划',
    emotion_feature_synthesizer: '情绪综合',
    local_support_resource_registry: '本地审计资源库',
    xunfei_response_strategy_selector: '讯飞回应策略选择',
    xunfei_structured_synthesizer: '讯飞结构化综合',
    deterministic_response_template: '本地回应模板',
    generated_content_validator: '输出安全校验',
    outcome_verifier: '交付结果核验',
    delivery_verifier: '交付结果核验',
    student_outcome_verifier: '交付结果核验',
    student_delivery_verifier: '交付结果核验',
    student_delivery_formatter: '结果交付',
    urgent_support_router: '真人安全路径',
  })[tool] || tool
}

function listValues(value) {
  const values = Array.isArray(value) ? value : [value]
  return values.map((item) => {
    if (typeof item === 'string' || typeof item === 'number') return String(item).trim()
    if (!item || typeof item !== 'object') return ''
    return String(item.label || item.text || item.description || '').trim()
  }).filter(Boolean)
}

function verificationCheckTone(status) {
  if (['verified', 'passed', 'completed'].includes(status)) return 'verified'
  if (['failed', 'blocked', 'rejected'].includes(status)) return 'failed'
  if (['needs_attention', 'attention'].includes(status)) return 'attention'
  return 'pending'
}

function verificationCheckIcon(status) {
  return ({ verified: '✓', failed: '×', attention: '!', pending: '·' })[verificationCheckTone(status)]
}

function verificationCheckLabel(status) {
  return ({ verified: '已核验', failed: '未通过', attention: '需处理', pending: '待核验' })[verificationCheckTone(status)]
}

function evidenceText(evidence) {
  if (Array.isArray(evidence)) return evidence.map(item => evidenceText(item)).filter(Boolean).join('；')
  if (typeof evidence === 'string' || typeof evidence === 'number') return String(evidence)
  if (!evidence || typeof evidence !== 'object') return ''
  return Object.values(evidence).filter(value => typeof value === 'string' || typeof value === 'number').join(' · ')
}

function ownerLabel(owner) {
  return ({
    student: '由你自主决定',
    student_choice: '由你自主决定',
    student_with_trusted_adult: '由你与可信成年人共同决定',
    teacher: '教师确认后接力',
    counselor: '校内心理支持人员',
    school_support: '校内支持人员',
    trusted_adult_or_school_support: '可信成年人或校内支持人员',
    trusted_adult_or_emergency_support: '可信成年人或紧急支持',
  })[owner] || String(owner).replaceAll('_', ' ')
}

watch(() => props.open, async (value, previous) => {
  if (!value) graphOpen.value = false
  await nextTick()
  if (value && !previous) closeButton.value?.focus({ preventScroll: true })
  if (!value && previous) toggleButton.value?.focus({ preventScroll: true })
})
</script>

<style scoped>
.student-agent-shell {
  --agent-ink: oklch(96% .012 76);
  --agent-muted: oklch(79% .019 68);
  --agent-subtle: oklch(66% .018 60);
  --agent-accent: oklch(82% .09 76);
  --agent-success: oklch(79% .08 154);
  --agent-warning: oklch(83% .105 82);
  --agent-danger: oklch(73% .13 31);
  --agent-base: oklch(17% .013 43);
  --agent-raised: oklch(23% .017 47);
  --agent-hover: oklch(27% .02 51);
  --agent-line: oklch(45% .026 59 / .62);
  position: fixed;
  top: 88px;
  right: 24px;
  z-index: 230;
  display: flex;
  align-items: flex-start;
  color: var(--agent-ink);
  font-family: 'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', system-ui, sans-serif;
  pointer-events: none;
}
.student-agent-toggle,
.student-agent-rail { pointer-events: auto; }
.agent-toggle-live {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.student-agent-toggle {
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr) 16px;
  align-items: center;
  gap: 9px;
  width: min(270px, calc(100vw - 48px));
  min-height: 54px;
  padding: 8px 11px;
  border: 1px solid var(--agent-line);
  border-radius: 13px;
  color: var(--agent-ink);
  background: linear-gradient(135deg, oklch(20% .017 46 / .94), oklch(16% .012 38 / .96));
  backdrop-filter: blur(20px) saturate(1.08);
  cursor: pointer;
  text-align: left;
  transition: background .18s ease, border-color .18s ease, transform .18s cubic-bezier(.22, 1, .36, 1);
}
.student-agent-toggle:hover { background: oklch(23% .02 49 / .97); border-color: oklch(62% .045 68 / .8); transform: translateY(-1px); }
.agent-toggle-mark {
  width: 8px;
  height: 8px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--agent-subtle);
}
.agent-toggle-mark.is-running { background: var(--agent-warning); animation: agent-pulse 1.2s ease-in-out infinite; }
.agent-toggle-mark.is-attention { background: var(--agent-warning); }
.agent-toggle-mark.is-ready { background: var(--agent-success); }
.agent-toggle-mark.is-urgent, .agent-toggle-mark.is-error { background: var(--agent-danger); }
.agent-toggle-copy { display: grid; gap: 3px; min-width: 0; }
.agent-toggle-heading { display: flex; align-items: baseline; gap: 7px; min-width: 0; }
.agent-toggle-heading strong { color: var(--agent-ink); font-size: 11px; line-height: 1.2; }
.agent-toggle-heading small { color: var(--agent-accent); font-size: 9px; }
.agent-toggle-latest { overflow: hidden; color: var(--agent-muted); font-size: 10px; line-height: 1.35; text-overflow: ellipsis; white-space: nowrap; }
.agent-toggle-chevron { color: var(--agent-accent); font-size: 16px; line-height: 1; transition: transform .18s ease; }
.student-agent-toggle:hover .agent-toggle-chevron { transform: translateY(-2px); }
.student-agent-rail {
  width: min(336px, calc(100vw - 48px));
  max-height: calc(100vh - 120px);
  overflow-y: auto;
  padding: 16px;
  border: 1px solid var(--agent-line);
  border-radius: 15px;
  background: linear-gradient(155deg, oklch(20% .017 47 / .975), oklch(15% .011 39 / .985));
  backdrop-filter: blur(26px) saturate(1.06);
  scrollbar-color: var(--agent-line) transparent;
}
.agent-rail-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.agent-rail-header h2 { margin: 0; color: var(--agent-ink); font-size: 16px; line-height: 1.3; letter-spacing: -.02em; }
.agent-rail-header p { margin: 3px 0 0; color: var(--agent-muted); font-size: 10px; line-height: 1.4; }
.agent-rail-close {
  width: 36px;
  height: 36px;
  border: 1px solid var(--agent-line);
  border-radius: 10px;
  color: var(--agent-ink);
  background: var(--agent-raised);
  font-size: 17px;
  cursor: pointer;
}
.agent-rail-close:hover { background: var(--agent-hover); border-color: oklch(62% .045 68 / .8); }
.agent-rail-event {
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr);
  align-items: center;
  column-gap: 9px;
  margin: 14px 0 10px;
  padding: 10px 11px;
  border-radius: 11px;
  color: var(--agent-ink);
  background: var(--agent-raised);
  line-height: 1.4;
}
.agent-rail-event span { width: 8px; height: 8px; flex: 0 0 auto; border-radius: 50%; background: var(--agent-subtle); }
.agent-rail-event span.is-running { background: var(--agent-warning); }
.agent-rail-event span.is-attention { background: var(--agent-warning); }
.agent-rail-event span.is-ready { background: var(--agent-success); }
.agent-rail-event span.is-urgent, .agent-rail-event span.is-error { background: var(--agent-danger); }
.agent-rail-event strong,
.agent-rail-event small { grid-column: 2; display: block; }
.agent-rail-event strong { font-size: 11px; }
.agent-rail-event small { margin-top: 2px; color: var(--agent-muted); font-size: 10px; }
.agent-role-row { display: flex; flex-wrap: wrap; gap: 5px; margin: 9px 0 0; }
.agent-role-row span { padding: 4px 6px; border-radius: 6px; color: var(--agent-muted); background: var(--agent-raised); font: 650 8px/1.2 ui-monospace, SFMono-Regular, Consolas, monospace; }
.student-agent-source { display: grid; gap: 3px; margin-top: 10px; }
.student-agent-source strong { color: var(--agent-accent); font-size: 10px; }
.student-agent-source small { color: var(--agent-muted); font-size: 10px; line-height: 1.5; }
.agent-task-brief { margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--agent-line); }
.agent-task-brief > div:first-child { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.agent-task-brief strong { color: var(--agent-accent); font-size: 11px; }
.agent-task-brief code { overflow: hidden; color: var(--agent-subtle); font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
.agent-task-brief p { margin: 7px 0 0; color: var(--agent-muted); font-size: 10px; line-height: 1.55; }
.agent-tool-row { display: flex; flex-wrap: wrap; gap: 5px; }
.agent-tool-row { margin-top: 8px; }
.agent-tool-row span { padding: 4px 6px; border-radius: 6px; color: var(--agent-muted); background: var(--agent-raised); font-size: 8px; }
.agent-step-list { display: grid; gap: 2px; margin: 0; padding: 0; list-style: none; }
.agent-step-list li {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  gap: 9px;
  align-items: start;
  padding: 9px 2px;
  border-bottom: 1px solid var(--agent-line);
}
.agent-step-list li:last-child { border-bottom: 0; }
.agent-step-icon {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: 6px;
  color: var(--agent-muted);
  background: var(--agent-raised);
  font-size: 12px;
  font-weight: 800;
}
.agent-step-list li.is-completed .agent-step-icon { color: oklch(20% .03 150); background: var(--agent-success); }
.agent-step-list li.is-running .agent-step-icon { color: oklch(24% .04 72); background: var(--agent-warning); animation: agent-pulse 1.2s ease-in-out infinite; }
.agent-step-list li.is-attention .agent-step-icon,
.agent-step-list li.is-error .agent-step-icon { color: oklch(20% .04 30); background: var(--agent-danger); }
.agent-step-list li.is-blocked { opacity: .6; }
.agent-step-list strong,
.agent-step-list small { display: block; }
.agent-step-list strong { color: var(--agent-ink); font-size: 11px; line-height: 1.4; }
.agent-step-list small { margin-top: 2px; color: var(--agent-muted); font-size: 10px; line-height: 1.45; }
.agent-step-list em { color: var(--agent-subtle); font-size: 9px; font-style: normal; white-space: nowrap; }
.agent-delivery { display: none; }
.agent-technical-details { margin-top: 10px; border-top: 1px solid var(--agent-line); }
.agent-technical-details summary { min-height: 40px; padding: 11px 1px 8px; color: var(--agent-muted); font-size: 10px; cursor: pointer; }
.agent-technical-details summary:hover { color: var(--agent-ink); }
.agent-technical-details summary:focus-visible { outline: 3px solid var(--agent-accent); outline-offset: 3px; border-radius: 6px; }
.agent-boundary { margin: 10px 0 0; color: var(--agent-subtle); font-size: 10px; line-height: 1.55; }
.agent-rail-footer { display: flex; justify-content: space-between; gap: 10px; margin-top: 10px; color: var(--agent-muted); font-size: 9px; }
.agent-rail-footer strong { color: var(--agent-accent); font-weight: 650; }
.agent-delete-run { width:100%; min-height:36px; margin-top:10px; padding:7px 9px; border:1px solid var(--agent-line); border-radius:9px; color:var(--agent-muted); background:transparent; font-size:10px; cursor:pointer; }
.agent-delete-run:hover { color:var(--agent-ink); border-color:oklch(55% .045 65); background:var(--agent-raised); }
.student-agent-toggle:focus-visible,
.student-agent-rail button:focus-visible { outline: 3px solid var(--agent-accent); outline-offset: 3px; }
.agent-rail-enter-active,
.agent-rail-leave-active { transition: opacity .2s ease, transform .2s cubic-bezier(.22, 1, .36, 1); }
.agent-rail-enter-from,
.agent-rail-leave-to { opacity: 0; transform: translateX(12px); }
@keyframes agent-pulse { 50% { opacity: .58; } }

@media (min-width: 900px) {
  .student-agent-shell.is-open .student-agent-toggle { display: none; }
  .agent-delivery {
    display: block;
    margin-top: 12px;
    padding-top: 13px;
    border-top: 1px solid var(--agent-line);
  }
  .agent-delivery-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
  .agent-delivery-head > div > span,
  .agent-delivery-objective > span,
  .agent-artifact > span { color: var(--agent-accent); font-size: 9px; font-weight: 750; }
  .agent-delivery-head h3 { margin: 3px 0 0; color: var(--agent-ink); font-size: 13px; line-height: 1.35; }
  .agent-verification-status { flex: 0 0 auto; padding: 4px 7px; border-radius: 999px; font-size: 9px; }
  .agent-verification-status.is-verified { color: oklch(22% .04 150); background: var(--agent-success); }
  .agent-verification-status.is-failed { color: oklch(20% .04 30); background: var(--agent-danger); }
  .agent-verification-status.is-attention { color: oklch(24% .04 72); background: var(--agent-warning); }
  .agent-verification-status.is-pending { color: oklch(24% .04 72); background: var(--agent-warning); }
  .agent-delivery-objective { margin-top: 11px; }
  .agent-delivery-objective p { margin: 4px 0 0; color: var(--agent-ink); font-size: 11px; font-weight: 650; line-height: 1.5; }
  .agent-contract-list { display: grid; gap: 8px; margin: 10px 0 0; }
  .agent-contract-list > div { display: grid; grid-template-columns: 62px minmax(0, 1fr); gap: 8px; }
  .agent-contract-list dt { color: var(--agent-subtle); font-size: 9px; }
  .agent-contract-list dd { margin: 0; }
  .agent-contract-list ul { margin: 0; padding-left: 15px; color: var(--agent-muted); font-size: 9px; line-height: 1.55; }
  .agent-contract-list li + li { margin-top: 3px; }
  .agent-checks { margin-top: 11px; }
  .agent-checks h4 { margin: 0 0 4px; color: var(--agent-subtle); font-size: 9px; }
  .agent-checks ul { margin: 0; padding: 0; list-style: none; }
  .agent-checks li { display: grid; grid-template-columns: 18px minmax(0, 1fr) auto; gap: 7px; align-items: start; padding: 7px 0; border-top: 1px solid var(--agent-line); }
  .agent-checks li > span { display: grid; place-items: center; width: 17px; height: 17px; border-radius: 5px; color: var(--agent-muted); background: var(--agent-raised); font-size: 10px; font-weight: 800; }
  .agent-checks li > span.is-verified { color: oklch(20% .03 150); background: var(--agent-success); }
  .agent-checks li > span.is-failed { color: oklch(20% .04 30); background: var(--agent-danger); }
  .agent-checks li > span.is-attention { color: oklch(24% .04 72); background: var(--agent-warning); }
  .agent-checks strong,
  .agent-checks small { display: block; }
  .agent-checks strong { color: var(--agent-ink); font-size: 10px; line-height: 1.4; }
  .agent-checks small { margin-top: 2px; color: var(--agent-muted); font-size: 9px; line-height: 1.45; overflow-wrap: anywhere; }
  .agent-checks em { color: var(--agent-subtle); font-size: 9px; font-style: normal; white-space: nowrap; }
  .agent-artifact { margin-top: 10px; padding: 10px 11px; border-radius: 10px; background: var(--agent-raised); }
  .agent-artifact h4 { margin: 3px 0 0; color: var(--agent-ink); font-size: 12px; line-height: 1.4; }
  .agent-artifact > p { margin: 5px 0 0; color: var(--agent-muted); font-size: 10px; line-height: 1.5; }
  .agent-artifact dl { display: grid; gap: 5px; margin: 8px 0 0; }
  .agent-artifact dl > div { display: grid; grid-template-columns: 70px minmax(0, 1fr); gap: 7px; }
  .agent-artifact dt { color: var(--agent-subtle); font-size: 9px; }
  .agent-artifact dd { margin: 0; color: var(--agent-ink); font-size: 9px; line-height: 1.45; }
}

@media (min-width: 900px) and (max-width: 1163px) {
  .student-agent-toggle { width: 220px; }
  .student-agent-shell.is-open .student-agent-rail { width: min(320px, calc(100vw - 92px)); }
}

@media (max-width: 899px) {
  .student-agent-shell {
    top: 12px;
    right: 12px;
    bottom: auto;
    align-items: flex-end;
    flex-direction: column;
  }
  .student-agent-toggle { width: min(300px, calc(100vw - 24px)); min-height: 58px; }
  .student-agent-rail {
    width: min(360px, calc(100vw - 24px));
    max-height: min(66vh, 560px);
  }
  .agent-rail-enter-from,
  .agent-rail-leave-to { opacity: 0; transform: translateY(12px); }
}

/* v5.1.0-alpha.30 desktop visual pass guided by taste-skill.
   This is a restrained web frosted-glass approximation. */
@media (min-width: 900px) {
  .student-agent-shell {
    --agent-ink: #fffaf0;
    --agent-muted: #d7cec1;
    --agent-subtle: #afa69b;
    --agent-accent: var(--ui-gold-300, #efd79c);
    --agent-success: var(--ui-mint-200, #abd8c2);
    --agent-warning: #f0cf82;
    --agent-danger: #efa291;
    --agent-base: rgba(35, 27, 24, .82);
    --agent-raised: rgba(255, 250, 240, .075);
    --agent-hover: rgba(255, 250, 240, .12);
    --agent-line: rgba(255, 248, 235, .13);
    top: 76px;
    right: 18px;
  }

  .student-agent-toggle {
    grid-template-columns: 8px minmax(0, 1fr) 18px;
    gap: 10px;
    width: 286px;
    min-height: 58px;
    padding: 9px 12px;
    border: 0;
    border-radius: 14px;
    background: rgba(35, 27, 24, .8);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, .16), 0 6px 8px rgba(10, 7, 6, .24);
    -webkit-backdrop-filter: blur(24px) saturate(1.18);
    backdrop-filter: blur(24px) saturate(1.18);
  }
  .student-agent-toggle:hover {
    border-color: transparent;
    background: rgba(42, 33, 29, .9);
    transform: translateY(-1px);
  }
  .agent-toggle-heading strong { font-size: 12px; letter-spacing: -.01em; }
  .agent-toggle-heading small { color: var(--agent-accent); font-size: 11px; font-weight: 700; }
  .agent-toggle-latest { color: var(--agent-muted); font-size: 11px; }
  .agent-toggle-chevron { color: var(--agent-accent); font-size: 20px; }

  .student-agent-rail {
    width: 360px;
    max-height: calc(100vh - 96px);
    padding: 18px;
    border: 0;
    border-radius: 15px;
    background: rgba(31, 25, 23, .91);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, .14), 0 6px 8px rgba(9, 6, 5, .3);
    -webkit-backdrop-filter: blur(30px) saturate(1.16);
    backdrop-filter: blur(30px) saturate(1.16);
  }
  .agent-rail-header { align-items: center; }
  .agent-rail-header h2 { font-size: 17px; letter-spacing: -.02em; }
  .agent-rail-header p { color: var(--agent-muted); }
  .agent-rail-close {
    width: 38px;
    height: 38px;
    border: 0;
    border-radius: 10px;
    background: rgba(255, 250, 240, .08);
  }
  .agent-rail-event {
    margin: 14px 0 8px;
    padding: 11px 12px;
    border-radius: 10px;
    background: rgba(255, 250, 240, .07);
  }
  .agent-step-list { position: relative; gap: 0; }
  .agent-step-list::before {
    content: '';
    position: absolute;
    top: 18px;
    bottom: 18px;
    left: 11px;
    width: 1px;
    background: rgba(255, 248, 235, .13);
  }
  .agent-step-list li {
    position: relative;
    grid-template-columns: 24px minmax(0, 1fr) auto;
    gap: 10px;
    padding: 10px 0;
    border: 0;
  }
  .agent-step-icon { z-index: 1; width: 22px; height: 22px; border-radius: 7px; }
  .agent-step-list strong { font-size: 12px; }
  .agent-step-list small { max-width: 29ch; color: var(--agent-muted); }
  .agent-technical-details { margin-top: 8px; }
  .agent-technical-details summary { min-height: 42px; }
  .agent-delete-run { border-color: rgba(255, 248, 235, .14); }
}

@media (min-width: 900px) and (max-width: 1087px) {
  .student-agent-toggle { width: 188px; }
  .agent-toggle-heading small { display: none; }
}

@media (min-width: 900px) and (max-width: 1235px) {
  .student-agent-shell.is-open .student-agent-rail { width: 320px; }
}

@media (prefers-reduced-motion: reduce) {
  .agent-rail-enter-active,
  .agent-rail-leave-active { transition: none; }
  .agent-toggle-mark.is-running,
  .agent-step-list li.is-running .agent-step-icon { animation: none; }
  .student-agent-toggle,
  .agent-toggle-chevron { transition: none; }
}

@media (min-width: 900px) {
  .agent-graph-toggle { display: flex; align-items: center; justify-content: space-between; gap: 12px; width: 100%; padding: 11px 12px; margin: 12px 0 16px; color: var(--agent-ink); background: var(--agent-raised); border: 1px solid var(--agent-line); border-radius: 8px; font: inherit; font-size: 12px; cursor: pointer; }
  .agent-graph-toggle:hover { background: var(--agent-hover); }
  .agent-graph-toggle span { color: var(--agent-accent); font-size: 18px; }
  .agent-graph-toggle:focus-visible { outline: 2px solid var(--agent-accent); outline-offset: 3px; }
  .student-agent-shell.is-open.is-graph-open .student-agent-rail { width: min(740px, calc(100vw - 60px)); }
  .is-graph-open .agent-delivery { margin-top: 20px; }
  .is-graph-open .agent-delivery-head h3 { font-size: 15px; }
  .is-graph-open .agent-contract-list { grid-template-columns: 1fr 1fr; gap: 24px; }
  .is-graph-open .agent-checks strong, .is-graph-open .agent-artifact > p, .is-graph-open .agent-artifact dd, .is-graph-open .agent-contract-list ul { font-size: 12px; }
  .is-graph-open .agent-checks small, .is-graph-open .agent-contract-list dt, .is-graph-open .agent-checks em { font-size: 11px; }
}

/* 收起态只留一枚状态胶囊：房间是主画面，协作细节点开再看。 */
.student-agent-shell { top: 14px; right: 14px; }
.student-agent-toggle {
  grid-template-columns: 8px minmax(0, 1fr) 14px;
  gap: 7px;
  width: 196px;
  min-height: 46px;
  padding: 6px 10px;
  border-radius: 12px;
}
.agent-toggle-latest { display: none; }
.agent-toggle-heading { gap: 5px; }
.agent-toggle-heading strong { font-size: 11px; }
.agent-toggle-heading small { font-size: 9px; }
.agent-toggle-chevron { font-size: 14px; }

@media (min-width: 900px) {
  .student-agent-shell { top: 16px; right: 18px; }
  .student-agent-toggle { width: 196px; min-height: 48px; padding: 6px 11px; }
  .agent-toggle-heading strong { font-size: 11.5px; }
}

@media (max-width: 899px) {
  .student-agent-shell { top: 10px; right: 10px; }
  .student-agent-toggle {
    grid-template-columns: 8px minmax(0, 1fr) 10px;
    gap: 5px;
    width: 108px;
    min-width: 108px;
    min-height: 44px;
    padding: 0 8px;
    border-radius: 999px;
  }
  .student-agent-toggle .agent-toggle-heading small,
  .student-agent-toggle .agent-toggle-latest { display: none; }
  .student-agent-toggle .agent-toggle-heading strong { font-size: 10px; }
  .student-agent-toggle .agent-toggle-chevron { font-size: 12px; }
}

/* 像素皮肤 3.0 · 咕哝 Agent 栏 */
.student-agent-shell {
  --px-line: rgba(255, 248, 235, .2);
  --px-gold: #efd79c;
  --px-shadow: rgba(0, 0, 0, .46);
}
.student-agent-toggle {
  border: 2px solid var(--px-line);
  border-radius: 6px;
  box-shadow: 3px 3px 0 var(--px-shadow);
  transition: background 160ms steps(2, end), border-color 160ms steps(2, end), transform 160ms steps(2, end), box-shadow 160ms steps(2, end);
}
.student-agent-toggle:hover {
  border-color: var(--px-gold);
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.student-agent-toggle:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--px-shadow);
}
.agent-toggle-heading strong { font-family: var(--px-font); }
.student-agent-rail {
  border: 2px solid var(--px-line);
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.agent-rail-header h2 { font-family: var(--px-font); font-size: 17px; }
.agent-rail-close {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: 3px 3px 0 var(--px-shadow);
  transition: background 160ms steps(2, end), border-color 160ms steps(2, end), transform 160ms steps(2, end), box-shadow 160ms steps(2, end);
}
.agent-rail-close:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.agent-rail-close:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--px-shadow);
}
.agent-rail-event { border: 2px solid var(--px-line); border-radius: 4px; }
.agent-step-icon { border-radius: 4px; }
.agent-verification-status { border-radius: 4px; }
.agent-graph-toggle {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: 3px 3px 0 var(--px-shadow);
}
.agent-graph-toggle:hover { transform: translate(-1px, -1px); box-shadow: 4px 4px 0 var(--px-shadow); }
.agent-delete-run { border-width: 2px; border-radius: 4px; }
.agent-artifact { border-radius: 4px; }
.student-agent-toggle:focus-visible,
.student-agent-rail button:focus-visible,
.agent-technical-details summary:focus-visible { outline: 3px dashed var(--px-gold); outline-offset: 3px; }

@media (prefers-reduced-motion: reduce) {
  .student-agent-toggle,
  .agent-rail-close { transition: none; }
  .student-agent-toggle:hover,
  .student-agent-toggle:active,
  .agent-rail-close:hover,
  .agent-rail-close:active,
  .agent-graph-toggle:hover { transform: none; }
}
</style>
