<script setup>
import { computed, ref, watch } from 'vue'
import { VueFlow, Handle, Position, MarkerType } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
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
const nodes = computed(() => snapshot.value.rows.map((row, index) => ({
  id: row.id, type: 'execution',
  position: { x: (Math.floor(index / 3) % 2 ? 2 - index % 3 : index % 3) * 220, y: Math.floor(index / 3) * 112 },
  data: { ...row, ordinal: index + 1,
    targetPosition: index > 0 && index % 3 === 0 ? Position.Top : Math.floor(index / 3) % 2 ? Position.Right : Position.Left,
    sourcePosition: index % 3 === 2 ? Position.Bottom : Math.floor(index / 3) % 2 ? Position.Left : Position.Right,
  },
  selectable: false, draggable: false, connectable: false,
})))
const edges = computed(() => snapshot.value.rows.flatMap((row, index, rows) => {
  if (!index || !row.inPlan || !rows[index - 1].inPlan) return []
  return [{
    id: `edge-${index}`, source: rows[index - 1].id, target: row.id,
    type: 'smoothstep', markerEnd: MarkerType.ArrowClosed,
    style: { stroke: '#aaa193', strokeWidth: 1.5 },
  }]
}))
const icon = status => ({ completed: '✓', attention: '!', failed: '×' })[status] || '·'
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
  <section class="execution-view" aria-label="Agent 执行图与记录回看">
    <header class="execution-heading">
      <div><h3>任务执行图</h3><p>点击一个步骤，查看它的工具和执行结果。</p></div>
      <span>{{ replaying ? '记录回看' : '最新记录' }}</span>
    </header>
    <p v-if="state.riskLevel === 'urgent'" class="execution-notice">已进入真人安全支持路径，后续行动仍需真人完成。</p>
    <p v-else-if="state.source === 'degraded'" class="execution-notice">本轮使用本地安全回应；实际工具以节点记录为准。</p>
    <p v-if="!snapshot.rows.length" class="execution-empty">还没有服务端执行记录。完成一次倾诉后，可以在这里查看本轮任务。</p>
    <template v-else>
      <div class="execution-canvas" :style="{ height: `${Math.max(140, Math.ceil(snapshot.rows.length / 3) * 100)}px` }">
        <VueFlow
          :nodes="nodes" :edges="edges" :nodes-draggable="false" :nodes-connectable="false"
          :elements-selectable="false" :nodes-focusable="false" :edges-focusable="false"
          :zoom-on-scroll="false" :zoom-on-pinch="false" :zoom-on-double-click="false"
          :pan-on-drag="false" :prevent-scrolling="false" :delete-key-code="null"
          :min-zoom="0.5" :max-zoom="1" fit-view-on-init
        >
          <template #node-execution="{ data, id }">
            <Handle type="target" :position="data.targetPosition" />
            <button class="execution-node nodrag nopan" :class="[`is-${data.status}`, { 'is-selected': selected?.id === id }]"
              :aria-pressed="selected?.id === id" :aria-label="`${agentLabel(data.agent)}：${executionStatus(data.status)}`"
              @click="choose(id)">
              <span class="execution-node-top"><span>{{ String(data.ordinal).padStart(2, '0') }}</span><em>{{ icon(data.status) }} {{ executionStatus(data.status) }}</em></span>
              <strong>{{ agentLabel(data.agent) }}</strong>
            </button>
            <Handle type="source" :position="data.sourcePosition" />
          </template>
        </VueFlow>
      </div>
      <p class="execution-caption">{{ snapshot.planned ? '连线表示服务端计划顺序，节点状态来自已保存的记录。' : '历史任务未附计划，仅按已保存的事件展示步骤。' }}</p>
      <div class="execution-replay">
        <label for="agent-event-cursor">记录回看 <output>{{ snapshot.count }} / {{ snapshot.total }}</output></label>
        <input id="agent-event-cursor" type="range" min="0" :max="snapshot.total" :value="snapshot.count"
          :disabled="!snapshot.total" :aria-valuetext="`查看前 ${snapshot.count} 条，共 ${snapshot.total} 条记录`" @input="seek($event.target.value)" />
        <button type="button" :disabled="!replaying" @click="cursor = null">返回最新</button>
      </div>
      <section v-if="selected" class="execution-inspector" aria-live="polite" aria-atomic="true">
        <header><h4>{{ agentLabel(selected.agent) }}</h4><span>{{ executionStatus(selected.status) }}</span></header>
        <p>{{ selected.event?.summary || '当前回看位置尚无该步骤的完成记录，不能判断它已经执行。' }}</p>
        <dl>
          <div><dt>计划工具</dt><dd>{{ selected.plannedTool ? toolLabel(selected.plannedTool) : '未提供' }}</dd></div>
          <div><dt>实际工具</dt><dd>{{ selected.tool ? toolLabel(selected.tool) : '尚无记录' }}</dd></div>
          <div><dt>执行来源</dt><dd>{{ selected.event ? executionSource(selected.event.source) : '尚无记录' }}</dd></div>
        </dl>
      </section>
      <p class="execution-caption">已完成 {{ snapshot.completed }} 个步骤 · 已记录 {{ snapshot.tools.length }} 种工具。回看只改变视图，不会重新执行任务。</p>
    </template>
  </section>
</template>

<style scoped>
.execution-view { color: var(--agent-ink); font-size: 12px; }
.execution-heading, .execution-inspector header { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.execution-heading h3 { margin: 0; font-size: 16px; }
.execution-heading p { margin: 5px 0 0; color: var(--agent-muted); line-height: 1.5; }
.execution-heading > span { color: var(--agent-accent); white-space: nowrap; }
.execution-notice { padding: 10px 12px; background: var(--agent-raised); color: var(--agent-warning); line-height: 1.6; }
.execution-empty { padding: 25px 0; color: var(--agent-muted); line-height: 1.7; }
.execution-canvas { height: 300px; margin-top: 16px; background: #211b18; border-radius: 10px; }
.execution-node { width: 186px; padding: 12px; text-align: left; border: 1px solid #8e8476; border-radius: 9px; color: #e9e0d4; background: #302925; cursor: pointer; pointer-events: auto; font: inherit; transition: background .16s ease; }
.execution-node-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 7px; font-size: 11px; }
.execution-node em { font-style: normal; }
.execution-node strong { display: block; font-size: 14px; line-height: 1.4; }
.execution-node.is-completed .execution-node-top { color: #b9e1cf; }
.execution-node.is-attention .execution-node-top { color: #f0cf82; }
.execution-node.is-failed .execution-node-top { color: #efa291; }
.execution-node.is-selected { border-color: #efd79c; background: #42372b; }
.execution-node:hover { background: #493e35; }
.execution-node:focus-visible, .execution-replay button:focus-visible, .execution-replay input:focus-visible { outline: 2px solid #efd79c; outline-offset: 3px; }
.execution-canvas :deep(.vue-flow__handle) { width: 5px; height: 5px; background: #aaa193; border: none; pointer-events: none; }
.execution-caption { margin: 9px 0 0; color: var(--agent-muted); font-size: 11px; line-height: 1.6; }
.execution-replay { display: flex; align-items: center; gap: 16px; padding: 16px 0; }
.execution-replay label { white-space: nowrap; }
.execution-replay output { margin-left: 6px; color: var(--agent-accent); font-variant-numeric: tabular-nums; }
.execution-replay input { flex: 1; min-width: 40px; accent-color: #efd79c; cursor: pointer; }
.execution-replay button { background: var(--agent-raised); color: var(--agent-ink); border: 0; border-radius: 6px; min-height: 36px; padding: 6px 12px; font: inherit; cursor: pointer; }
.execution-replay button:disabled { opacity: .55; cursor: default; }
.execution-inspector { border-top: 1px solid var(--agent-line); padding-top: 14px; }
.execution-inspector h4 { margin: 0; font-size: 14px; }
.execution-inspector header span { color: var(--agent-accent); }
.execution-inspector p { color: var(--agent-muted); line-height: 1.7; margin: 9px 0 12px; }
.execution-inspector dl { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin: 0; }
.execution-inspector dt { color: var(--agent-muted); font-size: 11px; }
.execution-inspector dd { margin: 5px 0 0; line-height: 1.5; overflow-wrap: anywhere; }
@media (prefers-reduced-motion: reduce) { .execution-node { transition: none; } }
</style>
