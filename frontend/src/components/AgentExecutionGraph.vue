<script setup>
import { computed, ref, watch } from 'vue'
import { executionSnapshot, executionStatus, executionSource } from '../utils/agentExecution'

const props = defineProps({
  state: { type: Object, required: true },
  agentLabel: { type: Function, required: true },
  toolLabel: { type: Function, required: true },
})
const cursor = ref(null)
const selectedId = ref('step-0')
const snapshot = computed(() => executionSnapshot(props.state.plan || [], props.state.events || [], cursor.value ?? props.state.events?.length ?? 0))
const selected = computed(() => snapshot.value.rows.find(row => row.id === selectedId.value) || snapshot.value.rows[0])
const replaying = computed(() => cursor.value !== null && cursor.value < snapshot.value.total)
const stepNumber = index => String(index + 1).padStart(2, '0')
function choose(id) { selectedId.value = id }
function seek(value) {
  cursor.value = Number(value)
  const rows = executionSnapshot(props.state.plan || [], props.state.events || [], cursor.value).rows
  const recorded = rows.filter(row => row.event)
  selectedId.value = recorded.at(-1)?.id || rows[0]?.id || ''
}
watch(() => props.state.runCode, () => { cursor.value = null; selectedId.value = 'step-0' })
</script>

<template>
  <section class="execution-view" aria-label="Agent 执行步骤与记录回看">
    <header class="execution-heading">
      <div><h3>任务执行记录</h3><p>点击一行，查看它用的工具和执行结果。</p></div>
      <span>{{ replaying ? '记录回看' : '最新记录' }}</span>
    </header>
    <p v-if="state.riskLevel === 'urgent'" class="execution-notice">已进入真人安全支持路径，后续行动仍需真人完成。</p>
    <p v-else-if="state.source === 'degraded'" class="execution-notice">本轮使用本地安全回应；实际工具以步骤记录为准。</p>
    <p v-if="!snapshot.rows.length" class="execution-empty">还没有服务端执行记录。完成一次倾诉后，可以在这里查看本轮任务。</p>
    <template v-else>
      <div class="execution-replay">
        <label for="agent-event-cursor">记录回看 <output>{{ snapshot.count }} / {{ snapshot.total }}</output></label>
        <input id="agent-event-cursor" type="range" min="0" :max="snapshot.total" :value="snapshot.count"
          :disabled="!snapshot.total" :aria-valuetext="`查看前 ${snapshot.count} 条，共 ${snapshot.total} 条记录`" @input="seek($event.target.value)" />
        <button type="button" :disabled="!replaying" @click="cursor = null">返回最新</button>
      </div>
      <div class="execution-body">
        <ol class="execution-rail" aria-label="执行步骤">
          <li v-for="(row, index) in snapshot.rows" :key="row.id" :class="['execution-row', `is-${row.status}`]">
            <button
              type="button"
              :aria-pressed="selected?.id === row.id"
              :aria-label="`第 ${index + 1} 步 ${agentLabel(row.agent)}：${executionStatus(row.status)}`"
              @click="choose(row.id)"
            >
              <span class="execution-index">{{ stepNumber(index) }}</span>
              <strong>{{ agentLabel(row.agent) }}</strong>
              <em class="execution-status">{{ executionStatus(row.status) }}</em>
            </button>
          </li>
        </ol>
        <section v-if="selected" class="execution-inspector" aria-live="polite" aria-atomic="true">
          <header><h4>{{ agentLabel(selected.agent) }}</h4><span :class="`is-${selected.status}`">{{ executionStatus(selected.status) }}</span></header>
          <p>{{ selected.event?.summary || '当前回看位置尚无该步骤的完成记录，不能判断它已经执行。' }}</p>
          <dl>
            <div><dt>计划工具</dt><dd>{{ selected.plannedTool ? toolLabel(selected.plannedTool) : '未提供' }}</dd></div>
            <div><dt>实际工具</dt><dd>{{ selected.tool ? toolLabel(selected.tool) : '尚无记录' }}</dd></div>
            <div><dt>执行来源</dt><dd>{{ selected.event ? executionSource(selected.event.source) : '尚无记录' }}</dd></div>
          </dl>
        </section>
      </div>
      <p class="execution-caption">{{ snapshot.planned ? '顺序按服务端计划排列，' : '历史任务未附计划，仅按已保存的事件展示；' }}已完成 {{ snapshot.completed }} 个步骤 · 已记录 {{ snapshot.tools.length }} 种工具。回看只改变视图，不会重新执行任务。</p>
    </template>
  </section>
</template>

<style scoped>
.execution-view { color: var(--agent-ink); font-size: 12px; container-type: inline-size; }
.execution-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.execution-heading h3 { margin: 0; font-size: 16px; }
.execution-heading p { margin: 5px 0 0; color: var(--agent-muted); line-height: 1.5; }
.execution-heading > span { color: var(--agent-accent); font-size: 11px; white-space: nowrap; }
.execution-notice { margin-top: 12px; padding: 10px 12px; background: var(--agent-raised); color: var(--agent-warning); line-height: 1.6; }
.execution-empty { padding: 25px 0; color: var(--agent-muted); line-height: 1.7; }
.execution-replay { display: flex; align-items: center; gap: 14px; padding: 14px 0 12px; }
.execution-replay label { white-space: nowrap; }
.execution-replay output { margin-left: 6px; color: var(--agent-accent); font-variant-numeric: tabular-nums; }
.execution-replay input { flex: 1; min-width: 40px; accent-color: var(--agent-accent); cursor: pointer; }
.execution-replay button { min-height: 32px; padding: 5px 12px; border: 1px solid var(--agent-line); border-radius: 6px; color: var(--agent-ink); background: var(--agent-raised); font: inherit; cursor: pointer; }
.execution-replay button:disabled { opacity: .55; cursor: default; }
.execution-body { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; }
.execution-rail { margin: 0; padding: 0; list-style: none; border-top: 1px solid var(--agent-line); }
.execution-row { border-bottom: 1px solid var(--agent-line); }
.execution-row > button { display: grid; grid-template-columns: 30px minmax(0, 1fr) auto; align-items: center; gap: 10px; width: 100%; padding: 8px 8px 8px 10px; border: 0; border-left: 2px solid transparent; color: var(--agent-ink); background: transparent; text-align: left; cursor: pointer; font: inherit; transition: background-color 140ms ease, border-color 140ms ease; }
.execution-row > button:hover { background: var(--agent-hover); }
.execution-row > button[aria-pressed="true"] { border-left-color: var(--agent-accent); background: var(--agent-raised); }
.execution-index { color: var(--agent-subtle); font: 500 10px/1.4 ui-monospace, SFMono-Regular, Consolas, monospace; letter-spacing: .04em; }
.execution-row strong { font-size: 12.5px; font-weight: 600; line-height: 1.5; }
.execution-row.is-unrecorded strong { color: var(--agent-muted); }
.execution-status { color: var(--agent-muted); font-style: normal; font-size: 11px; white-space: nowrap; }
.execution-row.is-completed .execution-status, .execution-inspector .is-completed { color: var(--agent-success); }
.execution-row.is-attention .execution-status, .execution-inspector .is-attention { color: var(--agent-warning); }
.execution-row.is-failed .execution-status, .execution-inspector .is-failed { color: var(--agent-danger); }
.execution-inspector { padding-top: 12px; border-top: 1px solid var(--agent-line); }
.execution-inspector header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.execution-inspector h4 { margin: 0; font-size: 14px; }
.execution-inspector header span { color: var(--agent-accent); font-size: 11px; white-space: nowrap; }
.execution-inspector p { margin: 9px 0 12px; color: var(--agent-muted); line-height: 1.7; }
.execution-inspector dl { display: grid; gap: 0; margin: 0; }
.execution-inspector dl > div { display: grid; grid-template-columns: 68px minmax(0, 1fr); gap: 10px; padding: 6px 0; border-top: 1px solid var(--agent-line); }
.execution-inspector dt { color: var(--agent-muted); font-size: 11px; }
.execution-inspector dd { margin: 0; line-height: 1.5; overflow-wrap: anywhere; }
.execution-caption { margin: 12px 0 0; color: var(--agent-muted); font-size: 11px; line-height: 1.6; }
.execution-view :focus-visible { outline: 2px solid var(--agent-accent); outline-offset: 2px; }
@container (min-width: 560px) {
  .execution-body { grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); gap: 22px; }
  .execution-inspector { padding: 0 0 0 18px; border-top: 0; border-left: 1px solid var(--agent-line); }
}
@media (prefers-reduced-motion: reduce) { .execution-row > button { transition: none; } }
</style>
