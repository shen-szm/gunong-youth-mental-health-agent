<script setup>
import { computed, ref, watch } from 'vue'
import UiIcon from './UiIcon.vue'

const props = defineProps({ report: { type: Object, required: true } })
const selected = ref(0)
const labels = { TaskInterpreter: '理解任务与权限', SafetyGate: '安全分流', EvidenceMapper: '定位授权证据', ContextAnalyst: '整理支持情境', SupportPlanner: '规划行动与回访', CrossReviewer: '交叉核验', ReportCoordinator: '交付报告快照' }
const statusLabel = status => ({ completed: '完成', attention: '需复核', blocked: '安全停止', degraded: '已降级', failed: '失败' })[status] || '状态未确认'
const steps = computed(() => props.report.agent_review?.workflow || [])
const active = computed(() => steps.value[selected.value])
const completed = computed(() => steps.value.filter(step => step.status === 'completed').length)
const stepNumber = index => String(index + 1).padStart(2, '0')
watch(() => props.report, () => { selected.value = 0 })
</script>

<template>
  <section class="teacher-execution" aria-label="教师 Agent 执行核查">
    <header><div><h5><UiIcon name="cases" /> 教师 Agent 执行核查</h5><p>任务理解 → 工具处理 → 结果校验 → 人工验收</p></div><span>{{ completed }} / {{ steps.length }} 阶段完成</span></header>
    <p class="execution-boundary">按报告记录的工作流顺序排列，状态来自本份报告快照；不是实时运行画面或模型思维链。</p>
    <ol v-if="steps.length" class="execution-rail" aria-label="执行步骤">
      <li v-for="(step, index) in steps" :key="index" class="execution-cell" :class="step.status">
        <button
          type="button"
          :aria-pressed="selected === index"
          :aria-label="`第 ${index + 1} 步 ${labels[step.agent] || step.agent}：${statusLabel(step.status)}`"
          @click="selected = index"
        >
          <span class="execution-index">{{ stepNumber(index) }}</span>
          <strong>{{ labels[step.agent] || step.agent }}</strong>
          <em class="execution-status">{{ statusLabel(step.status) }}</em>
        </button>
      </li>
    </ol>
    <p v-else>这份历史报告没有执行步骤记录，不能据此确认工具已执行。</p>
    <div v-if="active" class="teacher-step-detail" aria-live="polite" aria-atomic="true">
      <div><strong>{{ labels[active.agent] || active.agent }}</strong><code>{{ active.agent }}</code></div>
      <dl><div><dt>工具</dt><dd>{{ active.tool }}</dd></div><div><dt>执行状态</dt><dd>{{ statusLabel(active.status) }}</dd></div><div><dt>记录结果</dt><dd>{{ active.result }}</dd></div></dl>
    </div>
    <footer><UiIcon name="report" /><div><strong>{{ report.status === 'reviewed' ? '教师已签署' : report.status === 'revision_requested' ? '已退回修订' : '报告已生成，等待教师复核' }}</strong><p>授权记录 {{ report.evidence_audit?.record_count ?? '—' }} 条 · 报告主张 {{ report.evidence_audit?.claim_count ?? '—' }} 项 · 未关联主张 {{ report.evidence_audit?.unlinked_claim_count ?? '—' }} 项。线下支持行动不会被自动标记为完成。</p></div></footer>
  </section>
</template>

<style scoped>
.teacher-execution { margin: 16px 0; padding: 16px 0; border-block: 1px solid var(--t-line); color: var(--t-ink); font-size: 12.5px; }
.teacher-execution header { display: flex; justify-content: space-between; gap: 16px; align-items: baseline; }
.teacher-execution h5 { display: flex; align-items: center; gap: 7px; margin: 0; font-size: 14px; font-weight: 600; }
.teacher-execution p { margin: 4px 0 0; color: var(--t-muted); font-size: 11.5px; line-height: 1.6; }
.teacher-execution header > span { color: var(--t-faint); font: 500 11px/1.5 var(--t-mono); white-space: nowrap; }
.execution-boundary { color: var(--t-faint); font-size: 10.5px; }
.execution-rail { margin: 10px 0 0; padding: 0; list-style: none; border-top: 1px solid var(--t-line); }
.execution-cell { border-bottom: 1px solid var(--t-line); }
.execution-cell > button { display: grid; grid-template-columns: 34px minmax(0, 1fr) auto; align-items: center; gap: 12px; width: 100%; padding: 7px 10px; border: 0; border-left: 2px solid transparent; color: var(--t-ink); background: transparent; text-align: left; cursor: pointer; font: inherit; transition: background-color 140ms ease, border-color 140ms ease; }
.execution-cell > button:hover { background: var(--t-surface-2); }
.execution-cell > button[aria-pressed="true"] { border-left-color: var(--t-accent); background: var(--t-accent-soft); }
.execution-index { color: var(--t-faint); font: 500 10px/1.4 var(--t-mono); letter-spacing: .04em; }
.execution-cell strong { font-size: 12px; font-weight: 600; line-height: 1.5; }
.execution-status { color: var(--t-muted); font-style: normal; font-size: 10.5px; white-space: nowrap; }
.execution-cell.completed .execution-status { color: var(--t-green-ink); }
.execution-cell.attention .execution-status, .execution-cell.degraded .execution-status { color: var(--t-amber-ink); }
.execution-cell.blocked .execution-status, .execution-cell.failed .execution-status { color: var(--t-red); }
.teacher-step-detail { padding-top: 12px; }
.teacher-step-detail > div { display: flex; gap: 10px; align-items: baseline; }
.teacher-step-detail strong { font-size: 12.5px; font-weight: 600; }
.teacher-step-detail code { color: var(--t-faint); font-size: 10.5px; }
.teacher-step-detail dl { display: grid; grid-template-columns: 1fr .6fr 2fr; gap: 14px; margin: 8px 0 0; }
.teacher-step-detail dt { color: var(--t-faint); font-size: 10.5px; }
.teacher-step-detail dd { margin: 2px 0 0; color: var(--t-ink-2); line-height: 1.55; overflow-wrap: anywhere; }
.teacher-execution footer { display: flex; gap: 10px; margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--t-line); }
.teacher-execution footer > svg { flex: 0 0 auto; margin-top: 1px; color: var(--t-muted); }
.teacher-execution footer strong { display: block; font-size: 12px; font-weight: 600; }
.teacher-execution footer p { font-size: 10.5px; }
.teacher-execution :focus-visible { outline: 2px solid var(--t-accent); outline-offset: 2px; }
</style>
