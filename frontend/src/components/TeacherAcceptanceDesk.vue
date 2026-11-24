<script setup>
import { computed } from 'vue'
import { acceptanceEvidence } from '../utils/teacherAcceptance'
import { taskDateText, taskFailureText } from '../utils/teacherCaseTask'
const props = defineProps({ plan: Object, receipt: Object, blocked: Boolean, busy: Boolean })
defineEmits(['report', 'download', 'refresh'])
const evidence = computed(() => acceptanceEvidence(props.plan, props.receipt, props.blocked))
</script>

<template>
  <section class="acceptance-desk" aria-label="比赛验收台">
    <header><div><h4>比赛验收台</h4><p>把任务、执行回执与交付物放在一起核对。</p></div><button :disabled="busy" @click="$emit('refresh')">重新读取任务证据</button></header>
    <p class="acceptance-boundary">当前能力：LangGraph 持久化受限工作流，固定四步、人工确认后执行。不是自由自主规划；本页面不生成测试分数或干预效果结论。</p>
    <p v-if="blocked" role="status">证据暂不可用：正在核验或当前状态读取失败。请完成刷新后再验收，不沿用旧结果。</p>
    <p v-else-if="!evidence">尚未创建任务。请先创建并核对沟通准备计划，验收台会随服务端回执更新。</p>
    <template v-else>
      <section><h5>任务约束与计划</h5>
        <dl><div><dt>任务编号</dt><dd><code>{{ plan.task_id }}</code></dd></div><div><dt>当前状态</dt><dd>{{ evidence.status }}</dd></div><div><dt>任务目标</dt><dd>{{ plan.contract?.objective === 'conversation_preparation' ? '个案沟通准备' : '非当前支持的执行目标' }}</dd></div><div><dt>资料范围</dt><dd>当前授权内近 {{ plan.contract?.period_days }} 天；不扩大审批范围</dd></div><div><dt>计划来源</dt><dd>{{ evidence.source }}</dd></div><div><dt>尝试次数</dt><dd>{{ evidence.attempts === null ? '未取得执行回执' : evidence.attempts + ' / 3 次' }}</dd></div></dl>
        <p>这里展示已保存的结构化合同。创建前可解析自然语言需求，但原文和解析来源尚未绑定存档；执行仍是固定四步，不支持动态计划调整。</p>
      </section>
      <section><h5>实际工具与完成证据</h5><ol><li v-for="step in evidence.steps" :key="step.id"><div><strong>{{ step.title }}</strong><code>{{ step.id }}</code></div><span>{{ step.state }}</span></li></ol><p>只标记服务端回执确认完成的步骤；无回执不等于从未调用。此处不展示模型私有思考过程。</p></section>
      <section><h5>交付物与人工验收</h5><p>{{ evidence.reportStatus }}。报告生成、审核签署均不代表线下关怀已完成。</p>
        <template v-if="evidence.delivered"><dl><div><dt>报告编号</dt><dd><code>{{ evidence.reportId }}</code></dd></div><div><dt>SHA-256</dt><dd><code>{{ evidence.reportHash }}</code></dd></div></dl><div class="acceptance-actions"><button :disabled="busy" @click="$emit('report')">核对本任务报告</button><button :disabled="busy" @click="$emit('download')">下载本任务 PDF</button></div></template>
        <p v-else>未提供下载入口。需要取得本任务成功交付回执后，再按原权限核验报告。</p>
      </section>
      <section><h5>异常与修订关联</h5>
        <p v-if="evidence.failure">{{ taskFailureText(evidence.failure.code) }} {{ taskDateText(evidence.failure.at) }}，第 {{ evidence.failure.attempt }} 次尝试。</p><p v-else>当前没有可展示的失败摘要；不代表历史从未失败。</p>
        <p v-if="plan.termination">任务已终止：{{ taskDateText(plan.termination.at) }}。终止不删除已有报告。</p>
        <p v-if="plan.revision">补充计划关联原任务 <code>{{ plan.revision.parent_task_id }}</code>，原报告 <code>{{ plan.revision.parent_report_id }}</code>；新增 {{ plan.revision.added_record_count }} 条、移出 {{ plan.revision.removed_record_count }} 条资料。原报告未被替换。</p>
        <p v-else>当前不是补充计划。可通过任务历史核对其他任务。</p>
      </section>
      <section><h5>测试证据与适用边界</h5><p>版本绑定的自动测试证据尚未接入本页面。此任务的执行回执不等同于全项目测试通过，不能据此计算成功率。</p><p>比赛使用合成账号时应明确说明数据来源。真实使用效果需要另行取得授权、设计评价方法并收集证据。</p></section>
    </template>
  </section>
</template>

<style scoped>
.acceptance-desk{display:none}
@media(min-width:1024px){
  .acceptance-desk{display:block;grid-column:1/-1;border-top:1px solid #b7d4d0;margin-top:20px;padding-top:22px;color:#263f3c;font-size:13px;line-height:1.7;min-width:0}
  header{display:flex;align-items:start;justify-content:space-between;gap:16px}h4{font-size:20px;margin:0}h5{font-size:15px;margin:0 0 10px}p{max-width:75ch;margin:8px 0;color:#47635b}
  .acceptance-boundary{background:#e8f0ed;padding:12px 16px;max-width:none;margin:18px 0}
  section>section{padding:18px 0;border-top:1px solid #d3dfd9}dl{margin:0}dl>div{display:grid;grid-template-columns:110px minmax(0,1fr);gap:16px;padding:5px 0}dt{color:#47635b}dd{margin:0}code{overflow-wrap:anywhere;font-size:12px}ol{list-style:none;padding:0;margin:0}li{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:10px 0;border-bottom:1px solid #dce7e4}li code{display:block;color:#47635b}li span{flex-shrink:0;color:#365e50}
  button{min-height:40px;padding:8px 12px;border:1px solid #b8cdc1;border-radius:6px;background:#fff;color:#315d50;font:inherit;cursor:pointer}button:hover:not(:disabled){background:#e8f2ed}button:active:not(:disabled){background:#d8e9e0}button:disabled{opacity:.55;cursor:not-allowed}button:focus-visible{outline:3px solid #367b6c;outline-offset:3px}.acceptance-actions{display:flex;gap:10px;margin-top:12px}
}
</style>
