<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import { previewTeacherIntent } from '../api/teacher'
import { localIntentReview } from '../utils/teacherIntentReview'
defineProps({ disabled: Boolean })
const emit = defineEmits(['prepare'])
const goal = ref(''), consent = ref(false), result = ref(null), loading = ref(false), error = ref('')
const reviewed = ref([])
const heldReview = ref(null)
const policyReview = computed(() => localIntentReview(result.value))
const reviewItems = ['我已逐句对照原始需求，目标、时间和成果没有被擅自补充或遗漏。', '本次任务不包含自动通知、代签、删除、诊断或公开上传等额外动作。', '只使用当前账号获批的资料；此合同不会借用管理员权限或扩大授权。']
let alive = true, version = 0
onBeforeUnmount(() => { alive = false; version++ })
watch(goal, () => { version++; result.value = null; error.value = ''; consent.value = false; reviewed.value = [] })
watch(consent, () => { version++; result.value = null; reviewed.value = [] })
async function parse() {
  if (loading.value || !consent.value || goal.value.trim().length < 4) return
  const current = ++version
  loading.value = true; error.value = ''; result.value = null; reviewed.value = []
  try {
    const response = await previewTeacherIntent(goal.value.trim())
    if (alive && current === version) {
      result.value = response.data
      const review = localIntentReview(response.data)
      if (review && !heldReview.value) heldReview.value = { goal: goal.value, labels: review.labels }
    }
  } catch { if (alive && current === version) error.value = '需求解析暂不可用，请稍后重试，或使用下方标准计划入口。' }
  finally { if (alive) loading.value = false }
}
const messages = { model_unavailable: '模型未启用或暂不可用，未完成需求理解。可使用下方标准计划入口。', model_timeout: '模型响应超时，未生成候选合同。请重试或使用标准计划。', invalid_result: '模型结果未通过结构校验，请修改需求后重试。', confirmation_required: '请先确认发送需求文本。', needs_clarification: '需求需要补充或包含未支持的操作，请修改后重新解析。', unsupported_contract: '已解析需求，但当前执行链不支持该组合，不会自动改成标准任务。', ready_for_review: '候选合同已解析，请逐项核对后再准备计划。' }
function prepare() {
  if (!heldReview.value && !loading.value && consent.value && reviewed.value.length === reviewItems.length && result.value?.can_prepare === true && result.value.status === 'ready_for_review') emit('prepare', result.value.contract)
}
</script>
<template>
  <section class="intent-preview" aria-label="自然语言需求预览">
    <h5>用一句话描述准备任务</h5>
    <p>例如：根据当前授权内近30天资料，准备个案沟通报告和核对清单，不额外检索。请勿填写姓名、联系方式或学生倾诉原文。</p>
    <label for="teacher-intent-goal">任务需求</label><textarea id="teacher-intent-goal" v-model="goal" maxlength="600" rows="3" :disabled="disabled || loading" />
    <label class="intent-consent"><input v-model="consent" type="checkbox" :disabled="disabled || loading">我确认仅发送任务要求；服务启用时，此文本将交由已配置的外部模型解析。</label>
    <button :disabled="disabled || loading || !consent || goal.trim().length < 4" @click="parse">{{ loading ? '正在解析需求…' : '解析需求，不执行' }}</button>
    <p v-if="loading" role="status">正在检查需求；通过本地预检后才会请求模型。不会读取学生资料、创建任务或调用业务工具。</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <section v-if="heldReview" class="intent-policy-review" aria-label="需要人工澄清">
      <h6>这份需求需要人工澄清</h6>
      <p>本地规则发现了需要确认的表达，并非模型已理解或认定你要执行危险操作。</p>
      <ul v-if="heldReview.labels.length"><li v-for="label in heldReview.labels" :key="label">{{ label }}</li></ul>
      <p class="original-label">首次触发检查的原始要求 · 仅在当前页面保留</p>
      <blockquote>{{ heldReview.goal }}</blockquote>
      <p>“不要通知”等禁止条件和引用示例也可能触发检查。请保留这些约束，不要为通过检查而删除它们。</p>
      <p>请由负责教师核对：这是希望执行的动作、明确禁止的动作，还是引用内容？当前尚不支持解除误拦截，本轮不会继续自动准备计划；修改文本或再次解析也不会解除此限制。</p>
      <small>此记录不会保存到浏览器存储或任务档案，离开当前个案页面后清除；不代表已提交给其他教师。</small>
    </section>
    <div v-if="result" role="status">
      <p v-if="policyReview">本次由本地规则暂停，未调用外部模型，未创建任务。</p>
      <p v-else-if="heldReview">再次解析已返回，但原始要求仍待澄清；本轮不采用候选合同。</p>
      <template v-else>
        <p>{{ messages[result.status] || '结果无法识别，请重新解析。' }}</p>
        <p v-if="result.clarification">{{ { missing_scope: '请明确资料时间范围。', unsupported_action: '需求可能包含未支持的操作。请人工核对，并保留原有的禁止条件。', ambiguous: '请明确任务目标和需要的成果。' }[result.clarification] }}</p>
      </template>
      <dl v-if="result.contract && !heldReview"><div><dt>目标</dt><dd>{{ result.contract.objective === 'conversation_preparation' ? '个案沟通准备' : '每周跟进' }}</dd></div><div><dt>范围</dt><dd>当前授权内 {{ result.contract.period_days }} 天</dd></div><div><dt>成果</dt><dd>{{ result.contract.output_format === 'checklist' ? '报告与核对清单' : '一页简报' }} · 待人工审核</dd></div><div><dt>资源</dt><dd>{{ result.contract.resource_policy === 'not_needed' ? '不额外检索' : '仅审核资源' }}</dd></div></dl>
      <fieldset v-if="!heldReview && result.can_prepare === true && result.status === 'ready_for_review'">
        <legend>完整需求人工核对</legend><p>模型可能遗漏额外动作。任一项不符合，请修改需求，不要直接勾选。</p>
        <blockquote>{{ goal }}</blockquote>
        <label v-for="(item, index) in reviewItems" :key="item" class="intent-consent"><input v-model="reviewed" type="checkbox" :value="index" :disabled="disabled || loading">{{ item }}</label>
        <button :disabled="disabled || loading || reviewed.length !== reviewItems.length" @click="prepare">按核对后的合同准备计划</button>
      </fieldset>
    </div>
    <small>解析可能遗漏或误解要求，仍需人工核对；创建后还需确认计划，才可执行。原始需求不保存到本地或任务存档。</small>
  </section>
</template>
<style scoped>
.intent-preview { display: none; }
.intent-policy-review { margin: 12px 0; padding: 10px 12px; border-left: 2px solid var(--t-amber); background: var(--t-amber-bg); color: var(--t-amber-ink); }
.intent-policy-review h6 { margin: 0 0 5px; font-size: 12.5px; font-weight: 600; }
.intent-policy-review p, .intent-policy-review li { color: #B8903E; font-size: 11.5px; }
.intent-policy-review ul { margin: 5px 0; padding-left: 16px; }
.intent-policy-review blockquote { margin: 6px 0; padding: 7px 10px; border: 1px solid #EBD4A4; border-radius: 2px; background: #fff; color: var(--t-ink-2); font-size: 11.5px; white-space: pre-wrap; overflow-wrap: anywhere; }
.original-label { font-weight: 600; }
fieldset { margin: 12px 0; padding: 10px 12px; border: 1px solid var(--t-line); border-radius: var(--t-r-sm); }
legend { padding: 0 5px; color: var(--t-ink); font-size: 12px; font-weight: 600; }
blockquote { margin: 8px 0; padding: 8px 10px; border-left: 2px solid var(--t-line-2); background: var(--t-surface-2); color: var(--t-ink-2); white-space: pre-wrap; overflow-wrap: anywhere; }
@media (min-width: 1024px) {
  .intent-preview { display: block; margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--t-line); color: var(--t-ink); font-size: 12.5px; line-height: 1.7; }
  .intent-preview h5 { margin: 0; font-size: 13px; font-weight: 600; }
  .intent-preview p { max-width: 76ch; margin: 5px 0; color: var(--t-muted); font-size: 12px; }
  .intent-preview > label { display: block; margin-top: 8px; color: var(--t-ink-2); font-size: 12px; font-weight: 600; }
  .intent-preview textarea { box-sizing: border-box; width: 100%; margin-top: 5px; padding: 8px 10px; border: 1px solid var(--t-line-2); border-radius: var(--t-r-sm); color: var(--t-ink); background: var(--t-surface); font: inherit; font-size: 12.5px; resize: vertical; }
  .intent-consent { display: flex; align-items: flex-start; gap: 7px; margin: 10px 0; color: var(--t-muted); font-size: 11.5px; font-weight: 400; line-height: 1.6; }
  .intent-preview input { margin-top: 3px; accent-color: var(--t-accent); }
  .intent-preview button { min-height: 32px; padding: 5px 12px; border: 1px solid var(--t-line-2); border-radius: var(--t-r-sm); color: var(--t-ink-2); background: var(--t-surface); font: inherit; font-size: 12px; font-weight: 600; cursor: pointer; }
  .intent-preview button:hover:not(:disabled) { border-color: #868C9B; background: var(--t-surface-2); }
  .intent-preview button:disabled { opacity: .5; cursor: not-allowed; }
  .intent-preview small { display: block; margin-top: 10px; color: var(--t-faint); font-size: 10.5px; }
  .intent-preview dl { margin: 8px 0; }
  .intent-preview dl > div { display: flex; gap: 14px; padding: 4px 0; border-bottom: 1px solid var(--t-line); }
  .intent-preview dt { min-width: 46px; color: var(--t-muted); }
  .intent-preview dd { margin: 0; color: var(--t-ink-2); }
}
.intent-preview :focus-visible { outline: 2px solid var(--t-accent); outline-offset: 2px; }
</style>
