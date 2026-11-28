<template>
  <section class="today-workbench" aria-labelledby="today-workbench-title">
    <header class="today-heading">
      <div>
        <p>{{ dateLabel }}</p>
        <h2 id="today-workbench-title">先处理最需要关注的事</h2>
        <span>所有结论都要回到授权记录与教师线下观察，Agent 不替代教师作决定。</span>
      </div>
      <button type="button" :disabled="refreshing" @click="$emit('refresh')">
        <UiIcon class="today-refresh-icon" name="refresh" />
        {{ refreshing ? '正在同步…' : '同步工作台' }}
      </button>
    </header>

    <dl class="today-summary" aria-label="今日工作摘要">
      <div class="metric is-urgent">
        <dt>优先安全协助</dt>
        <dd>{{ showUrgent }}</dd>
        <small>后端危机标记</small>
      </div>
      <div class="metric">
        <dt>待跟进提醒</dt>
        <dd>{{ showPending }}</dd>
        <small>尚未记录跟进</small>
      </div>
      <div v-if="superAdmin" class="metric">
        <dt>待审批申请</dt>
        <dd>{{ showApprovals }}</dd>
        <small>需要核对最小范围</small>
      </div>
      <div v-else class="metric">
        <dt>审批中工单</dt>
        <dd>{{ showApprovals }}</dd>
        <small>等待管理员教师处理</small>
      </div>
      <div class="metric">
        <dt>可继续工单</dt>
        <dd>{{ showAuthorized }}</dd>
        <small>已具备当前访问权限</small>
      </div>
    </dl>

    <section class="signal-board" aria-label="近 7 天支持信号">
      <div class="signal-trend">
        <div class="signal-head">
          <div>
            <h3>近 7 天支持信号</h3>
            <p>按提醒创建日期统计，仅反映规则分流，不代表诊断。</p>
          </div>
          <p class="signal-total">
            <strong>{{ weekTotal }}</strong>
            <span>条 · 单日峰值 {{ weekPeakValue }}</span>
          </p>
        </div>
        <div class="signal-chart" role="img" :aria-label="weekAria">
          <div
            v-for="(day, index) in weekSeries"
            :key="day.key"
            class="signal-col"
            :class="{ 'is-today': index === weekSeries.length - 1 }"
            :title="`${day.label} · ${day.count} 条`"
          >
            <span class="signal-count">{{ day.count || '' }}</span>
            <div class="signal-track">
              <span
                class="signal-bar"
                :class="{ empty: !day.count }"
                :style="{ height: barHeight(day.count) + '%', animationDelay: index * 45 + 'ms' }"
              />
            </div>
            <span class="signal-day">{{ day.weekday }}</span>
          </div>
        </div>
      </div>

      <div class="signal-mix">
        <div class="signal-head">
          <div>
            <h3>提醒风险构成</h3>
            <p>含已处理记录，按最高风险归并。</p>
          </div>
        </div>
        <div v-if="riskTotal" class="mix-bar" role="img" :aria-label="mixAria">
          <span
            v-for="(band, index) in riskBands"
            v-show="band.count"
            :key="band.key"
            class="mix-seg"
            :class="band.key"
            :style="{ flexGrow: band.count, animationDelay: index * 60 + 'ms' }"
            :title="`${band.label} ${band.count} 条`"
          />
        </div>
        <p v-else class="mix-empty">近 7 天没有新的支持提醒。</p>
        <ul class="mix-legend">
          <li v-for="band in riskBands" :key="band.key">
            <i :class="band.key" aria-hidden="true" />
            <span>{{ band.label }}</span>
            <strong>{{ band.count }}</strong>
            <em>{{ band.pct }}%</em>
          </li>
        </ul>
      </div>
    </section>

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
          <p>暂时没有需要立即处理的安全提醒或审批。可以进入支持工单查看近期记录。</p>
        </div>
      </section>

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
  </section>
</template>

<script setup>
import UiIcon from './UiIcon.vue'
import { computed, ref, onMounted, watch, onBeforeUnmount } from 'vue'

// 数字计数动画：从 0 缓动到目标值，用于工作台 KPI 数字的轻量活力反馈
const reduceMotion = typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
function countUp(target) {
  const display = ref(0)
  let raf = 0
  const run = (to) => {
    cancelAnimationFrame(raf)
    const value = Number(to) || 0
    if (reduceMotion) { display.value = value; return }
    const from = display.value
    const start = performance.now()
    const duration = 680
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3)
      display.value = Math.round(from + (value - from) * eased)
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
  }
  onMounted(() => run(target.value))
  watch(target, v => run(v))
  onBeforeUnmount(() => cancelAnimationFrame(raf))
  return display
}

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

// KPI 数字的计数动画展示值
const showUrgent = countUp(computed(() => urgentWarnings.value.length))
const showPending = countUp(computed(() => pendingWarnings.value.length))
const showApprovals = countUp(computed(() => (props.superAdmin ? pendingApprovals.value : pendingCases.value).length))
const showAuthorized = countUp(computed(() => authorizedCases.value.length))

const DAY_MS = 86400000
function parseRecordTime(item) {
  const raw = item?.created_at || item?.updated_at
  if (!raw) return null
  const time = new Date(String(raw).replace(' ', 'T'))
  return Number.isNaN(time.getTime()) ? null : time
}
const weekSeries = computed(() => {
  const now = new Date()
  const midnight = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const days = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(midnight.getTime() - (6 - index) * DAY_MS)
    return {
      key: `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`,
      label: `${date.getMonth() + 1}/${date.getDate()}`,
      weekday: '日一二三四五六'[date.getDay()],
      date,
      count: 0,
    }
  })
  props.warnings.forEach(item => {
    const time = parseRecordTime(item)
    if (!time) return
    const day = days.find(entry => time >= entry.date && time < new Date(entry.date.getTime() + DAY_MS))
    if (day) day.count += 1
  })
  return days
})
const weekTotal = computed(() => weekSeries.value.reduce((sum, day) => sum + day.count, 0))
const weekPeakValue = computed(() => Math.max(0, ...weekSeries.value.map(day => day.count)))
function barHeight(count) {
  if (!count) return 0
  return Math.max(8, Math.round((count / Math.max(1, weekPeakValue.value)) * 100))
}
const weekAria = computed(() => `近 7 天每日提醒数：${weekSeries.value.map(day => `${day.label} ${day.count} 条`).join('；')}`)
const weekWarnings = computed(() => {
  const first = weekSeries.value[0].date
  const end = weekSeries.value[weekSeries.value.length - 1].date.getTime() + DAY_MS
  return props.warnings.filter(item => {
    const time = parseRecordTime(item)
    return time && time >= first && time < end
  })
})
const riskBands = computed(() => {
  const counts = { urgent: 0, high: 0, middle: 0, low: 0 }
  weekWarnings.value.forEach(item => {
    if (item.urgent === true) counts.urgent += 1
    else if (item.risk_level === 'high' || item.risk_level === 'professional') counts.high += 1
    else if (item.risk_level === 'middle' || item.risk_level === 'medium') counts.middle += 1
    else counts.low += 1
  })
  const total = Object.values(counts).reduce((sum, value) => sum + value, 0)
  return [
    { key: 'urgent', label: '危急', count: counts.urgent },
    { key: 'high', label: '高风险', count: counts.high },
    { key: 'middle', label: '需关注', count: counts.middle },
    { key: 'low', label: '低 / 其他', count: counts.low },
  ].map(band => ({ ...band, pct: total ? Math.round((band.count / total) * 100) : 0 }))
})
const riskTotal = computed(() => riskBands.value.reduce((sum, band) => sum + band.count, 0))
const mixAria = computed(() => `近 7 天提醒风险构成：${riskBands.value.map(band => `${band.label} ${band.count} 条`).join('，')}`)

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
    action: item.urgent === true ? '立即核实安全' : item.risk_level === 'high' ? '尽快核实' : '持续关注',
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
.today-refresh-icon { display: none; margin-right: 5px; }
@media (min-width: 1024px) { .today-refresh-icon { display: inline-block; } }
.today-workbench { display: grid; gap: 22px; }
.today-heading { display: flex; justify-content: space-between; gap: 24px; align-items: flex-end; }
.today-heading p, .today-heading h2, .today-heading span { margin: 0; }
.today-heading p { color: var(--t-faint); font: 500 11px/1.5 var(--t-mono); letter-spacing: .04em; }
.today-heading h2 { margin-top: 4px; color: var(--t-ink); font-size: 20px; font-weight: 600; letter-spacing: -.015em; text-wrap: balance; }
.today-heading span { display: block; max-width: 68ch; margin-top: 5px; color: var(--t-muted); font-size: 12.5px; line-height: 1.65; }
.today-heading > button,
.section-heading > button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  min-height: 32px;
  padding: 5px 11px;
  border: 1px solid var(--t-line-2);
  border-radius: var(--t-r-sm);
  color: var(--t-ink-2);
  background: var(--t-surface);
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.today-heading > button:hover:not(:disabled),
.section-heading > button:hover:not(:disabled) { border-color: #868C9B; background: var(--t-surface-2); }
.today-heading > button:disabled { opacity: .55; cursor: wait; }

.today-summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin: 0; border-block: 1px solid var(--t-line); background: none; }
.today-summary div { min-width: 0; padding: 13px 16px; border-inline-end: 1px solid var(--t-line); }
.today-summary div:last-child { border-inline-end: 0; }
.today-summary .metric { position: relative; padding-left: 18px; transition: background-color 160ms ease; }
.today-summary .metric::before { content: ""; position: absolute; left: 0; top: 16px; bottom: 16px; width: 3px; border-radius: 2px; background: var(--t-accent); }
.today-summary .metric:hover { background: var(--t-surface-2); }
.today-summary .metric:hover dd { transform: translateY(-1px) scale(1.05); }
.today-summary .metric.is-urgent::before { background: var(--t-red); }
.today-summary dt { color: var(--t-muted); font-size: 11.5px; }
.today-summary dd { margin: 3px 0 1px; color: var(--t-accent-ink); font-size: 24px; font-weight: 600; letter-spacing: -.02em; font-variant-numeric: tabular-nums; transform-origin: left center; transition: color 140ms ease, transform 220ms cubic-bezier(.22, 1, .36, 1); }
.today-summary .metric.is-urgent dd { color: var(--t-red-ink); }
.today-summary small { color: var(--t-faint); font-size: 11px; }

.signal-board { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(260px, .8fr); border-block: 1px solid var(--t-line); }
.signal-trend { min-width: 0; padding: 16px 22px 14px 0; border-inline-end: 1px solid var(--t-line); }
.signal-mix { min-width: 0; padding: 16px 0 14px 22px; }
.signal-head { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }
.signal-head h3 { margin: 0; color: var(--t-ink); font-size: 13.5px; font-weight: 600; }
.signal-head p { margin: 2px 0 0; color: var(--t-muted); font-size: 11px; line-height: 1.5; }
.signal-total { display: flex; align-items: baseline; gap: 3px; margin: 0; color: var(--t-muted); font: 500 10.5px/1.5 var(--t-mono); white-space: nowrap; }
.signal-total strong { color: var(--t-ink); font-size: 19px; font-weight: 600; font-variant-numeric: tabular-nums; }
.signal-chart { display: flex; align-items: flex-end; gap: 8px; height: 100px; margin-top: 10px; }
.signal-col { display: flex; flex-direction: column; justify-content: flex-end; flex: 1; height: 100%; min-width: 0; text-align: center; }
.signal-count { display: inline-block; height: 13px; color: var(--t-faint); font: 500 9.5px/1.3 var(--t-mono); opacity: .7; transition: opacity 140ms ease, color 140ms ease, transform 160ms ease; }
.signal-track { position: relative; display: flex; align-items: flex-end; height: 68px; border-bottom: 1px solid var(--t-line-2); }
.signal-track::before,
.signal-track::after { content: ""; position: absolute; z-index: 0; left: 0; right: 0; border-top: 1px dashed var(--t-line); pointer-events: none; }
.signal-track::before { top: 33%; }
.signal-track::after { top: 66%; }
.signal-bar { position: relative; z-index: 1; width: 62%; max-width: 30px; margin: 0 auto; border-radius: 2px 2px 0 0; background: var(--t-accent); opacity: .78; transform-origin: bottom; animation: signal-grow 480ms cubic-bezier(.22, 1, .36, 1) both; transition: opacity 140ms ease, background-color 140ms ease; }
.signal-bar.empty { background: none; }
.signal-day { margin-top: 5px; color: var(--t-faint); font-size: 10px; }
.signal-col:hover .signal-count { opacity: 1; color: var(--t-ink-2); transform: translateY(-1px); }
.signal-col:hover .signal-bar { opacity: 1; background: var(--t-accent-ink); }
.signal-col.is-today .signal-day { color: var(--t-ink-2); font-weight: 600; }
.signal-col.is-today .signal-bar { background: var(--t-accent-ink); opacity: 1; }
@keyframes signal-grow { from { transform: scaleY(0); } to { transform: scaleY(1); } }

.mix-bar { display: flex; height: 10px; margin-top: 14px; border-radius: 2px; overflow: hidden; background: var(--t-surface-2); }
.mix-seg { display: block; transform-origin: left; animation: mix-grow 520ms cubic-bezier(.22, 1, .36, 1) both; }
.mix-seg.urgent { background: #B95C66; }
.mix-seg.high { background: #CF9AA1; }
.mix-seg.middle { background: #D9B46A; }
.mix-seg.low { background: #A9AEB9; }
@keyframes mix-grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
.mix-legend { display: grid; margin: 10px 0 0; padding: 0; list-style: none; }
.mix-legend li { display: flex; align-items: center; gap: 8px; padding: 5px 0; border-top: 1px solid var(--t-line); color: var(--t-ink-2); font-size: 11.5px; }
.mix-legend i { flex: 0 0 auto; width: 6px; height: 6px; border-radius: 1px; }
.mix-legend i.urgent { background: #B95C66; }
.mix-legend i.high { background: #CF9AA1; }
.mix-legend i.middle { background: #D9B46A; }
.mix-legend i.low { background: #A9AEB9; }
.mix-legend strong { margin-left: auto; color: var(--t-ink); font: 600 12px/1.4 var(--t-mono); }
.mix-legend em { min-width: 32px; color: var(--t-faint); font: 500 10.5px/1.4 var(--t-mono); font-style: normal; text-align: right; }
.mix-empty { margin: 14px 0 0; padding: 14px 0; color: var(--t-muted); font-size: 11.5px; }

.today-layout { display: grid; grid-template-columns: minmax(0, 1.45fr) minmax(280px, .75fr); gap: 26px; align-items: start; }
.today-layout > .priority-queue { grid-column: 1; grid-row: 1; }
.today-layout > .recent-roster { grid-column: 1; grid-row: 2; }
.today-layout > .agent-briefing { grid-column: 2; grid-row: 1 / 3; }
.priority-queue, .agent-briefing, .recent-roster { padding: 0; border: 0; border-radius: 0; background: none; box-shadow: none; }
.section-heading { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 0; padding-bottom: 8px; border-bottom: 1px solid var(--t-line); }
.section-heading.compact { margin-bottom: 0; }
.section-heading h3, .section-heading p { margin: 0; }
.section-heading h3 { color: var(--t-ink); font-size: 14px; font-weight: 600; }
.section-heading p { margin-top: 2px; color: var(--t-muted); font-size: 11.5px; line-height: 1.5; }

.queue-list { display: grid; }
.queue-item {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  width: 100%;
  min-height: 58px;
  padding: 10px 6px;
  border: 0;
  border-bottom: 1px solid var(--t-line);
  color: var(--t-ink);
  background: none;
  text-align: left;
  cursor: pointer;
}
.queue-item { transition: background-color 140ms ease, box-shadow 160ms ease; }
.queue-item:hover { background: var(--t-surface-2); box-shadow: inset 3px 0 0 var(--t-accent); }
.queue-item.is-urgent:hover { box-shadow: inset 3px 0 0 var(--t-red); }
.queue-item.is-professional:hover, .queue-item.is-blocked:hover { box-shadow: inset 3px 0 0 var(--t-amber); }
.queue-state { display: grid; place-items: center; width: 20px; height: 20px; border-radius: 3px; color: var(--t-muted); background: var(--t-surface-2); font: 600 11px/1 var(--t-mono); }
.queue-item.is-urgent .queue-state { color: var(--t-red); background: var(--t-red-bg); animation: queue-pulse 1.9s ease-in-out infinite; }
@keyframes queue-pulse { 0%, 100% { box-shadow: 0 0 0 0 rgba(207, 154, 161, 0); } 50% { box-shadow: 0 0 0 4px rgba(207, 154, 161, .22); } }
.queue-item.is-professional .queue-state,
.queue-item.is-blocked .queue-state { color: var(--t-amber-ink); background: var(--t-amber-bg); }
.queue-copy { display: grid; gap: 2px; min-width: 0; }
.queue-copy strong { overflow: hidden; color: var(--t-ink); font-size: 13px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.queue-copy small { overflow: hidden; color: var(--t-muted); font-size: 11.5px; line-height: 1.5; text-overflow: ellipsis; white-space: nowrap; }
.queue-item em { color: var(--t-accent); font-size: 11.5px; font-style: normal; font-weight: 600; white-space: nowrap; }
.queue-item.is-urgent em { color: var(--t-red); }
.queue-item.is-professional em, .queue-item.is-blocked em { color: var(--t-amber-ink); }
.queue-empty { padding: 28px 16px; border-bottom: 1px solid var(--t-line); color: var(--t-muted); text-align: center; }
.queue-empty strong { display: block; margin-bottom: 4px; color: var(--t-ink-2); font-size: 13px; }
.queue-empty p { max-width: 52ch; margin: 0 auto; font-size: 12px; line-height: 1.65; }

.agent-briefing { padding: 14px 16px; border: 1px solid var(--t-line); border-radius: var(--t-r-lg); background: var(--t-surface); }
.agent-briefing ol { display: grid; gap: 0; margin: 0; padding: 0; list-style: none; }
.agent-briefing li { display: grid; grid-template-columns: 20px minmax(0, 1fr) auto; gap: 9px; align-items: start; padding: 9px 0; border-top: 1px solid var(--t-line); }
.agent-briefing li:first-child { border-top: 0; }
.agent-briefing li > span { display: grid; place-items: center; width: 18px; height: 18px; border-radius: 2px; color: var(--t-muted); background: var(--t-surface-2); font: 600 10px/1 var(--t-mono); }
.agent-briefing li.is-attention > span { color: var(--t-amber-ink); background: var(--t-amber-bg); }
.agent-briefing li.is-urgent > span { color: var(--t-red); background: var(--t-red-bg); }
.agent-briefing li.is-ready > span { color: var(--t-green-ink); background: var(--t-green-bg); }
.agent-briefing li div { display: grid; gap: 1px; }
.agent-briefing li strong { color: var(--t-ink); font-size: 12.5px; font-weight: 600; }
.agent-briefing li small { color: var(--t-muted); font-size: 11px; line-height: 1.5; }
.agent-briefing li em { color: var(--t-faint); font-size: 10px; font-style: normal; white-space: nowrap; }
.agent-boundary { margin: 10px 0 0; padding-top: 10px; border-top: 1px solid var(--t-line); color: var(--t-faint); font-size: 10.5px; line-height: 1.6; }

.recent-roster { display: grid; gap: 0; margin-top: 4px; }
.roster-row { display: flex; flex-wrap: wrap; gap: 8px; overflow-x: auto; padding: 12px 0 2px; }
.roster-row button {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 1px 9px;
  align-items: center;
  flex: 1 1 186px;
  min-width: 172px;
  padding: 9px 10px;
  border: 1px solid var(--t-line);
  border-radius: var(--t-r);
  color: var(--t-ink);
  background: var(--t-surface);
  text-align: left;
  cursor: pointer;
  transition: border-color 140ms ease, background-color 140ms ease, transform 140ms ease;
}
.roster-row button:hover { border-color: var(--t-line-2); background: var(--t-surface-2); transform: translateY(-1px); }
.roster-row button:hover > span { background: var(--t-accent); color: #fff; transform: scale(1.06); }
.roster-row button > span { display: grid; place-items: center; grid-row: 1 / 3; width: 28px; height: 28px; border-radius: 3px; color: var(--t-accent-ink); background: var(--t-accent-soft); font-size: 12px; font-weight: 600; transition: background-color 160ms ease, color 160ms ease, transform 160ms ease; }
.roster-row strong { overflow: hidden; font-size: 12.5px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.roster-row small { overflow: hidden; color: var(--t-muted); font-size: 10.5px; text-overflow: ellipsis; white-space: nowrap; }
.roster-row > p { margin: 0; color: var(--t-muted); font-size: 12px; }

.today-workbench button:focus-visible { outline: 2px solid var(--t-accent); outline-offset: 2px; }
@media (max-width: 1080px) {
  .today-layout { grid-template-columns: 1fr; }
  .today-layout > .priority-queue,
  .today-layout > .recent-roster,
  .today-layout > .agent-briefing { grid-column: auto; grid-row: auto; }
}
@media (max-width: 900px) {
  .signal-board { grid-template-columns: 1fr; }
  .signal-trend { padding: 14px 0; border-inline-end: 0; border-bottom: 1px solid var(--t-line); }
  .signal-mix { padding: 14px 0; }
}
@media (max-width: 760px) {
  .today-heading { flex-direction: column; align-items: stretch; gap: 12px; }
  .today-heading > button { width: 100%; min-height: 40px; }
  .today-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .today-summary div:nth-child(2n) { border-inline-end: 0; }
  .today-summary div:nth-child(-n+2) { border-bottom: 1px solid var(--t-line); }
  .queue-item { min-height: 52px; }
}
@media (max-width: 480px) {
  .today-heading h2 { font-size: 18px; }
  .queue-item { grid-template-columns: 20px minmax(0, 1fr); }
  .queue-item em { grid-column: 2; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition: none !important; animation: none !important; }
}
</style>
