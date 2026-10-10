<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { VueFlow, Handle, Position, MarkerType } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import UiIcon from './UiIcon.vue'

const props = defineProps({ report: { type: Object, required: true } })
const selected = ref(0)
const canvas = ref(null)
const width = ref(800)
const columns = computed(() => Math.max(1, Math.min(4, Math.floor((width.value - 32) / 190))))
let observer
onMounted(() => {
  observer = new ResizeObserver(entries => { width.value = entries[0].contentRect.width })
  if (canvas.value) observer.observe(canvas.value)
})
onBeforeUnmount(() => observer?.disconnect())
const labels = { TaskInterpreter: '理解任务与权限', SafetyGate: '安全分流', EvidenceMapper: '定位授权证据', ContextAnalyst: '整理支持情境', SupportPlanner: '规划行动与回访', CrossReviewer: '交叉核验', ReportCoordinator: '交付报告快照' }
const statusLabel = status => ({ completed: '完成', attention: '需复核', blocked: '安全停止', degraded: '已降级', failed: '失败' })[status] || '状态未确认'
const steps = computed(() => props.report.agent_review?.workflow || [])
const active = computed(() => steps.value[selected.value])
const completed = computed(() => steps.value.filter(step => step.status === 'completed').length)
const nodes = computed(() => steps.value.map((step, index) => ({
  id: String(index), type: 'teacher-step', position: { x: (Math.floor(index / columns.value) % 2 ? columns.value - 1 - index % columns.value : index % columns.value) * 190, y: Math.floor(index / columns.value) * 105 },
  data: { ...step, index, target: index > 0 && index % columns.value === 0 ? Position.Top : Math.floor(index / columns.value) % 2 ? Position.Right : Position.Left, source: index % columns.value === columns.value - 1 ? Position.Bottom : Math.floor(index / columns.value) % 2 ? Position.Left : Position.Right },
  draggable: false, selectable: false, connectable: false,
})))
const edges = computed(() => steps.value.slice(1).map((_, index) => ({ id: `t-${index}`, source: String(index), target: String(index + 1), type: 'smoothstep', markerEnd: MarkerType.ArrowClosed, style: { stroke: '#77968a' } })))
watch(() => props.report, () => { selected.value = 0 })
</script>

<template>
  <section class="teacher-execution" aria-label="教师 Agent 执行核查">
    <header><div><h5><UiIcon name="cases" /> 教师 Agent 执行核查</h5><p>任务理解 → 工具处理 → 结果校验 → 人工验收</p></div><span>{{ completed }} / {{ steps.length }} 阶段完成</span></header>
    <p class="execution-boundary">连线表示报告工作流顺序，状态来自本份报告快照；不是实时运行画面或模型思维链。</p>
    <div v-if="steps.length" ref="canvas" class="teacher-flow" :style="{ height: `${Math.ceil(steps.length / columns) * 105 + 20}px` }">
      <VueFlow :key="columns" :nodes="nodes" :edges="edges" :nodes-draggable="false" :nodes-connectable="false" :elements-selectable="false" :nodes-focusable="false" :edges-focusable="false" :zoom-on-scroll="false" :zoom-on-pinch="false" :zoom-on-double-click="false" :pan-on-drag="false" :prevent-scrolling="false" :delete-key-code="null" :min-zoom="0.3" :max-zoom="1" fit-view-on-init>
        <template #node-teacher-step="{ data }">
          <Handle type="target" :position="data.target" />
          <button type="button" class="teacher-flow-node nodrag nopan" :class="[data.status, { selected: selected === data.index }]" :aria-pressed="selected === data.index" :aria-label="`${labels[data.agent] || data.agent}：${statusLabel(data.status)}`" @click="selected = data.index">
            <span>{{ data.index + 1 }}<em>{{ statusLabel(data.status) }}</em></span><strong>{{ labels[data.agent] || data.agent }}</strong>
          </button>
          <Handle type="source" :position="data.source" />
        </template>
      </VueFlow>
    </div>
    <p v-else>这份历史报告没有执行步骤记录，不能据此确认工具已执行。</p>
    <div v-if="active" class="teacher-step-detail" aria-live="polite" aria-atomic="true">
      <div><strong>{{ labels[active.agent] || active.agent }}</strong><code>{{ active.agent }}</code></div>
      <dl><div><dt>工具</dt><dd>{{ active.tool }}</dd></div><div><dt>执行状态</dt><dd>{{ statusLabel(active.status) }}</dd></div><div><dt>记录结果</dt><dd>{{ active.result }}</dd></div></dl>
    </div>
    <footer><UiIcon name="report" /><div><strong>{{ report.status === 'reviewed' ? '教师已签署' : report.status === 'revision_requested' ? '已退回修订' : '报告已生成，等待教师复核' }}</strong><p>授权记录 {{ report.evidence_audit?.record_count ?? '—' }} 条 · 报告主张 {{ report.evidence_audit?.claim_count ?? '—' }} 项 · 未关联主张 {{ report.evidence_audit?.unlinked_claim_count ?? '—' }} 项。线下支持行动不会被自动标记为完成。</p></div></footer>
  </section>
</template>

<style scoped>
.teacher-execution{color:#263f36;padding:20px 0;border-top:1px solid #d5e2db;border-bottom:1px solid #d5e2db;margin:16px 0;font-size:13px}.teacher-execution header{display:flex;justify-content:space-between;gap:16px;align-items:center}.teacher-execution h5{font-size:17px;margin:0;display:flex;gap:8px;align-items:center}.teacher-execution p{margin:6px 0 0;color:#4b6358;line-height:1.6}.teacher-execution header>span{white-space:nowrap;font-variant-numeric:tabular-nums}.execution-boundary{font-size:12px}.teacher-flow{height:230px;background:#f3f7f5;margin-top:12px;border-radius:8px}.teacher-flow-node{width:166px;min-height:74px;padding:12px;text-align:left;border:1px solid #97aea2;border-radius:8px;background:white;color:#263f36;pointer-events:auto;cursor:pointer;font:inherit}.teacher-flow-node>span{display:flex;justify-content:space-between;font-size:11px;margin-bottom:8px}.teacher-flow-node em{font-style:normal}.teacher-flow-node strong{font-size:14px}.teacher-flow-node.selected{border:2px solid #315f50;padding:11px;background:#e6f1eb}.teacher-flow-node.attention em{color:#79560a}.teacher-flow-node.blocked em,.teacher-flow-node.failed em{color:#95382f}.teacher-flow-node:hover{background:#e6f1eb}.teacher-flow-node:focus-visible{outline:3px solid #315f50;outline-offset:3px}.teacher-flow :deep(.vue-flow__handle){width:4px;height:4px;background:#77968a;border:0;pointer-events:none}.teacher-step-detail{padding:14px 0}.teacher-step-detail>div{display:flex;gap:12px;align-items:center}.teacher-step-detail code{font-size:11px;color:#4b6358}.teacher-step-detail dl{display:grid;grid-template-columns:1fr .6fr 2fr;gap:16px;margin:12px 0 0}.teacher-step-detail dt{font-size:12px;color:#4b6358}.teacher-step-detail dd{margin:4px 0 0;line-height:1.6;overflow-wrap:anywhere}.teacher-execution footer{display:flex;gap:12px;padding-top:14px;border-top:1px solid #d5e2db}.teacher-execution footer p{font-size:12px}
</style>
