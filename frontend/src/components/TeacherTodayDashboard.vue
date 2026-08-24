<template>
  <section class="today-workbench" aria-labelledby="today-workbench-title">
    <header class="today-heading">
      <div>
        <p>{{ dateLabel }}</p>
        <h2 id="today-workbench-title">先处理最需要关注的事</h2>
        <span>所有结论都要回到授权记录与教师线下观察，Agent 不替代教师作决定。</span>
      </div>
      <button type="button" :disabled="refreshing" @click="$emit('refresh')">
        {{ refreshing ? '正在同步…' : '同步工作台' }}
      </button>
    </header>

    <dl class="today-summary" aria-label="今日工作摘要">
      <div>
        <dt>优先安全协助</dt>
        <dd>{{ urgentWarnings.length }}</dd>
        <small>后端危机标记</small>
      </div>
      <div>
        <dt>待处理预警</dt>
        <dd>{{ pendingWarnings.length }}</dd>
        <small>尚未记录跟进</small>
      </div>
      <div v-if="superAdmin">
        <dt>待审批申请</dt>
        <dd>{{ pendingApprovals.length }}</dd>
        <small>需要核对最小范围</small>
      </div>
      <div v-else>
        <dt>审批中工单</dt>
        <dd>{{ pendingCases.length }}</dd>
        <small>等待管理员教师处理</small>
      </div>
      <div>
        <dt>可继续工单</dt>
        <dd>{{ authorizedCases.length }}</dd>
        <small>已具备当前访问权限</small>
      </div>
    </dl>

    <div class="today-layout">
      <section class="priority-queue" aria-labelledby="priority-queue-title">
        <div class="section-heading">
          <div>
            <h3 id="priority-queue-title">今日任务队列</h3>
            <p>按安全优先、审批阻塞和更新时间排列。</p>
          </div>
          <button type="button" @click="$emit('open-tab', 'cases')">查看全部工单</button>
        </div>

        <div v-if="queueItems.length" class="queue-list">
          <button
            v-for="item in queueItems"
            :key="item.key"
            type="button"
            :class="['queue-item', `is-${item.tone}`]"
            @click="$emit('open-item', item)"
          >
            <span class="queue-state" aria-hidden="true">{{ item.mark }}</span>
            <span class="queue-copy">
              <strong>{{ item.title }}</strong>
              <small>{{ item.description }}</small>
            </span>
            <em>{{ item.action }}</em>
          </button>
        </div>
        <div v-else class="queue-empty">
          <strong>当前队列已清空</strong>
          <p>暂时没有需要立即处理的预警或审批。可以进入支持工单查看近期记录。</p>
        </div>
      </section>

      <aside class="agent-briefing" aria-labelledby="agent-briefing-title">
        <div class="section-heading compact">
          <div>
            <h3 id="agent-briefing-title">当前队列状态</h3>
            <p>基于当前已加载列表汇总，不代表一次 Agent 运行。</p>
          </div>
        </div>
        <ol>
          <li v-for="step in agentSteps" :key="step.name" :class="`is-${step.status}`">
            <span aria-hidden="true">{{ step.icon }}</span>
            <div><strong>{{ step.name }}</strong><small>{{ step.summary }}</small></div>
            <em>{{ step.label }}</em>
          </li>
        </ol>
        <p class="agent-boundary">支持工单中的 Agent 进度只在真实执行后展示；系统不展示私有思维过程，也不会自动联系学生或家长。</p>
      </aside>
    </div>

    <section class="recent-roster" aria-labelledby="recent-roster-title">
      <div class="section-heading compact">
        <div>
          <h3 id="recent-roster-title">近期支持对象</h3>
          <p>记录次数只是数据覆盖度，不代表心理状态。</p>
        </div>
      </div>
      <div class="roster-row">
        <button v-for="student in students.slice(0, 6)" :key="student.id" type="button" @click="$emit('open-student', student)">
          <span>{{ firstChar(studentName(student)) }}</span>
          <strong>{{ studentName(student) }}</strong>
          <small>{{ student.mood_count || 0 }} 条自愿记录 · {{ accessLabel(student) }}</small>
        </button>
        <p v-if="!students.length">当前职责范围内暂无学生记录。</p>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  warnings: { type: Array, default: () => [] },
  students: { type: Array, default: () => [] },
  approvals: { type: Array, default: () => [] },
  superAdmin: { type: Boolean, default: false },
  refreshing: { type: Boolean, default: false },
})

defineEmits(['refresh', 'open-tab', 'open-item', 'open-student'])

const dateLabel = new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' }).format(new Date())
const pendingWarnings = computed(() => props.warnings.filter(item => item.status !== 'handled'))
const urgentWarnings = computed(() => pendingWarnings.value.filter(item => item.urgent === true))
const pendingApprovals = computed(() => props.approvals.filter(item => item.status === 'pending'))
const pendingCases = computed(() => props.students.filter(item => item.access?.status === 'pending'))
const authorizedCases = computed(() => props.students.filter(item => ['approved', 'direct'].includes(item.access?.status)))

const queueItems = computed(() => {
  const warningItems = [...pendingWarnings.value]
    .sort((a, b) => Number(b.urgent === true) - Number(a.urgent === true)
      || riskRank(b.risk_level) - riskRank(a.risk_level)
      || String(b.updated_at || b.created_at || '').localeCompare(String(a.updated_at || a.created_at || '')))
    .slice(0, 5).map(item => ({
    key: `warning-${item.id}`,
    type: 'warning',
    payload: item,
    tone: item.urgent === true ? 'urgent' : item.risk_level === 'high' ? 'professional' : 'watch',
    mark: item.urgent === true ? '!' : '•',
    title: cleanName(item.student_name || item.nickname || `学生 ${item.student_id}`),
    description: item.reason || item.summary || '出现需要教师核对的近期记录',
    action: item.urgent === true ? '立即核实安全' : item.risk_level === 'high' ? '尽快关注' : '处理预警',
  }))
  const approvalItems = props.superAdmin
    ? pendingApprovals.value.slice(0, 3).map(item => ({
      key: `approval-${item.id}`,
      type: 'approval',
      payload: item,
      tone: 'blocked',
      mark: '◇',
      title: `${cleanName(item.teacher_name)} 的原文查看申请`,
      description: `对象：${cleanName(item.student_name)} · 需要核对目的和最小范围`,
      action: '进入审批',
    }))
    : pendingCases.value.slice(0, 2).map(item => ({
      key: `case-${item.id}`,
      type: 'case',
      payload: item,
      tone: 'blocked',
      mark: '◇',
      title: `${studentName(item)} 的工单正在审批`,
      description: '审批完成前不展示个案摘要或原文',
      action: '查看状态',
    }))
  return [...warningItems, ...approvalItems]
})

const agentSteps = computed(() => [
  {
    name: '权限队列',
    summary: props.superAdmin
      ? `${pendingApprovals.value.length} 项申请等待人工审批`
      : `${pendingCases.value.length} 项申请等待管理员教师处理`,
    status: (props.superAdmin ? pendingApprovals.value.length : pendingCases.value.length) ? 'attention' : 'ready',
    icon: (props.superAdmin ? pendingApprovals.value.length : pendingCases.value.length) ? '!' : '✓',
    label: (props.superAdmin ? pendingApprovals.value.length : pendingCases.value.length) ? '有阻塞' : '无阻塞',
  },
  {
    name: '危机标记',
    summary: urgentWarnings.value.length ? `${urgentWarnings.value.length} 项被后端标记为危机，需要优先线下核实` : '当前加载列表中没有未处理的危机标记',
    status: urgentWarnings.value.length ? 'urgent' : 'ready',
    icon: urgentWarnings.value.length ? '!' : '✓',
    label: urgentWarnings.value.length ? '立即处理' : '当前列表',
  },
  {
    name: '工单权限',
    summary: `${authorizedCases.value.length} 个工单已具备当前访问权限`,
    status: authorizedCases.value.length ? 'ready' : 'waiting',
    icon: authorizedCases.value.length ? '✓' : '·',
    label: authorizedCases.value.length ? '可执行' : '等待工单',
  },
  {
    name: '教师裁决',
    summary: '联系学生、升级处置和支持任务均等待教师确认',
    status: 'waiting',
    icon: '·',
    label: '人工确认',
  },
])

function cleanName(value) {
  return String(value || '').trim() || '未命名'
}

function riskRank(level) {
  return ({ high: 3, professional: 3, middle: 2, medium: 2, low: 1 })[level] || 0
}

function studentName(student) {
  return cleanName(student?.nickname || student?.username || student?.name || `学生 ${student?.id || ''}`)
}

function firstChar(value) {
  return String(value || '?').slice(0, 1)
}

function accessLabel(student) {
  return ({ approved: '已授权', direct: '管理员可直达', pending: '审批中', not_requested: '未申请' })[student.access?.status] || '待核对权限'
}
</script>

<style scoped>
.today-workbench { display: grid; gap: 18px; }
.today-heading { display: flex; justify-content: space-between; gap: 24px; align-items: end; padding: 4px 2px 8px; }
.today-heading p, .today-heading h2, .today-heading span { margin: 0; }
.today-heading p { color: #547066; font-size: 13px; font-weight: 700; }
.today-heading h2 { margin-top: 6px; color: #1f302b; font-size: 26px; letter-spacing: -.025em; text-wrap: balance; }
.today-heading span { display: block; max-width: 70ch; margin-top: 7px; color: #5c6f68; font-size: 13px; line-height: 1.6; }
.today-heading > button, .section-heading > button { min-height: 40px; padding: 8px 13px; border: 0; border-radius: 9px; color: #f7faf8; background: #315e51; font: inherit; font-weight: 700; cursor: pointer; }
.today-heading > button:disabled { opacity: .58; cursor: wait; }
.today-summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin: 0; border-block: 1px solid #d8e1dd; background: rgba(255,255,255,.6); }
.today-summary div { min-width: 0; padding: 17px 18px; border-inline-end: 1px solid #d8e1dd; }
.today-summary div:last-child { border-inline-end: 0; }
.today-summary dt { color: #5b6c66; font-size: 12px; }
.today-summary dd { margin: 5px 0 2px; color: #20342e; font-size: 25px; font-weight: 800; }
.today-summary small { color: #667872; font-size: 11px; }
.today-layout { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(290px, .6fr); gap: 18px; align-items: start; }
.priority-queue, .agent-briefing, .recent-roster { padding: 18px; border-radius: 14px; background: #fff; box-shadow: 0 4px 8px rgba(34, 55, 48, .07); }
.section-heading { display: flex; justify-content: space-between; gap: 16px; align-items: start; margin-bottom: 13px; }
.section-heading.compact { margin-bottom: 10px; }
.section-heading h3, .section-heading p { margin: 0; }
.section-heading h3 { color: #253a33; font-size: 17px; }
.section-heading p { margin-top: 4px; color: #667872; font-size: 12px; line-height: 1.5; }
.section-heading > button { min-height: 36px; color: #315e51; background: #edf4f1; font-size: 12px; }
.queue-list { display: grid; }
.queue-item { display: grid; grid-template-columns: 32px minmax(0, 1fr) auto; gap: 11px; align-items: center; width: 100%; min-height: 68px; padding: 12px 4px; border: 0; border-top: 1px solid #e6ece9; color: #263a34; background: transparent; text-align: left; cursor: pointer; }
.queue-item:first-child { border-top: 0; }
.queue-item:hover { background: #f5f8f7; }
.queue-state { display: grid; place-items: center; width: 28px; height: 28px; border-radius: 8px; color: #41665b; background: #e7f0ec; font-weight: 900; }
.queue-item.is-urgent .queue-state { color: #893c34; background: #fae7e3; }
.queue-item.is-professional .queue-state { color: #765b20; background: #fff2cf; }
.queue-item.is-blocked .queue-state { color: #765b20; background: #fff2cf; }
.queue-copy { min-width: 0; display: grid; gap: 4px; }
.queue-copy strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.queue-copy small { color: #60736c; line-height: 1.45; }
.queue-item em { color: #315e51; font-size: 12px; font-style: normal; font-weight: 800; }
.queue-empty { padding: 30px 18px; color: #4d625b; background: #f5f8f7; text-align: center; }
.queue-empty p { max-width: 52ch; margin: 7px auto 0; font-size: 13px; line-height: 1.6; }
.agent-briefing ol { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; }
.agent-briefing li { display: grid; grid-template-columns: 24px minmax(0,1fr) auto; gap: 9px; align-items: start; padding: 10px 0; border-top: 1px solid #e8edeb; }
.agent-briefing li:first-child { border-top: 0; }
.agent-briefing li > span { display: grid; place-items: center; width: 22px; height: 22px; border-radius: 7px; color: #315e51; background: #e6f0ec; font-weight: 900; }
.agent-briefing li.is-attention > span { color: #74591c; background: #fff0c8; }
.agent-briefing li.is-urgent > span { color: #843b34; background: #f9e5e1; }
.agent-briefing li div { display: grid; gap: 3px; }
.agent-briefing li strong { font-size: 13px; }
.agent-briefing li small { color: #61736c; font-size: 11px; line-height: 1.45; }
.agent-briefing li em { color: #587068; font-size: 10px; font-style: normal; white-space: nowrap; }
.agent-boundary { margin: 12px 0 0; padding-top: 12px; border-top: 1px solid #e4ebe8; color: #60716b; font-size: 11px; line-height: 1.55; }
.recent-roster { display: grid; gap: 6px; }
.roster-row { display: flex; gap: 9px; overflow-x: auto; padding-bottom: 3px; }
.roster-row button { flex: 0 0 190px; display: grid; grid-template-columns: 34px minmax(0,1fr); gap: 2px 9px; align-items: center; padding: 10px; border: 0; border-radius: 10px; color: #263a34; background: #f3f7f5; text-align: left; cursor: pointer; }
.roster-row button > span { grid-row: 1 / 3; display: grid; place-items: center; width: 34px; height: 34px; border-radius: 10px; color: #f7faf8; background: #4f7d70; font-weight: 800; }
.roster-row strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.roster-row small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #667872; font-size: 10px; }
.today-workbench button:focus-visible { outline: 3px solid #245f82; outline-offset: 2px; }
@media (max-width: 980px) { .today-layout { grid-template-columns: 1fr; } }
@media (max-width: 720px) {
  .today-heading { align-items: start; flex-direction: column; }
  .today-heading > button { width: 100%; }
  .today-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .today-summary div:nth-child(2) { border-inline-end: 0; }
  .today-summary div:nth-child(-n+2) { border-block-end: 1px solid #d8e1dd; }
}
@media (max-width: 760px) {
  .today-workbench button { min-height: 44px; }
}
@media (max-width: 480px) {
  .today-heading h2 { font-size: 22px; }
  .priority-queue, .agent-briefing, .recent-roster { padding: 14px; }
  .queue-item { grid-template-columns: 28px minmax(0, 1fr); }
  .queue-item em { grid-column: 2; }
}
@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto !important; transition: none !important; } }
</style>
