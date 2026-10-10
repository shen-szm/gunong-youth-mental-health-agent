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
.intent-preview{display:none}
.intent-policy-review{margin:16px 0;padding:16px;background:#e8f0ed;color:#263f3c;border:1px solid #b9ccc3;border-radius:6px}.intent-policy-review h6{margin:0 0 8px;font-size:15px}.intent-policy-review p{margin:8px 0}.intent-policy-review ul{padding-left:20px;margin:8px 0}.intent-policy-review blockquote{white-space:pre-wrap;margin:8px 0;background:#fff}.original-label{font-weight:600}
fieldset{margin:16px 0;padding:14px;border:1px solid #b9ccc3;border-radius:6px}legend{font-weight:600}blockquote{margin:12px 0;padding:10px;background:#e8f0ed;overflow-wrap:anywhere}
@media(min-width:1024px){.intent-preview{display:block;padding:16px 0;border-top:1px solid #cbd8d2;color:#344f48;font-size:13px;line-height:1.7}h5{font-size:15px;margin:0}p{max-width:72ch}label{display:block}textarea{box-sizing:border-box;width:100%;font:inherit;padding:10px;border:1px solid #b9ccc3;border-radius:6px;background:white;color:#263f3c;resize:vertical}.intent-consent{display:flex;align-items:start;gap:8px;margin:12px 0}input{margin-top:5px}button{min-height:40px;padding:8px 12px;border:1px solid #b8cdc1;border-radius:6px;background:#fff;color:#315d50;font:inherit;cursor:pointer}button:hover:not(:disabled){background:#e8f2ed}button:disabled{opacity:.55;cursor:not-allowed}:focus-visible{outline:3px solid #367b6c;outline-offset:3px}small{display:block;margin-top:12px;color:#506662}dl>div{display:flex;gap:16px}dt{min-width:45px}dd{margin:0}}
</style>
