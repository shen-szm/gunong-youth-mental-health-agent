<script setup>
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import UiIcon from './UiIcon.vue'
import TeacherAcceptanceDesk from './TeacherAcceptanceDesk.vue'
import TeacherIntentPreview from './TeacherIntentPreview.vue'
const acceptanceOpen = ref(false)
import { getTeacherCaseHistory } from '../api/teacher'
import { taskFailureText, taskDateText } from '../utils/teacherCaseTask'
import { getTeacherTaskCapabilities, createTeacherCaseTask, getTeacherCaseTask, decideTeacherCaseTask, executeTeacherCaseTask, getTeacherCaseExecution, downloadTeacherCaseReport } from '../api/teacher'
import { taskStorageKey, readTaskReference, writeTaskReference, matchesTaskTarget, caseTaskSteps, taskStatusText } from '../utils/teacherCaseTask'
import { getExactTeacherReviewReport, decideStudentReviewReport, checkTeacherCaseRevision, createTeacherCaseRevision, terminateTeacherCaseTask } from '../api/teacher'
const TeacherReviewReport = defineAsyncComponent(() => import('./TeacherReviewReport.vue'))
const report = ref(null), reportHeading = ref(null)
const revisionCheck = ref(null)
const history = ref(null), historyOpen = ref(false)
const failure = computed(() => receipt.value?.last_failure || plan.value?.last_failure)
const terminating = ref(false), terminationReason = ref('manual')
const deliveryTitle = computed(() => ({ reviewed: '报告已由教师签署', revision_requested: '报告已退回，等待补充修订' })[receipt.value?.report_status] || '报告已生成，等待教师审核')
const deliveryDescription = computed(() => receipt.value?.report_status === 'reviewed' ? '审核决定已保存，可查看签署意见或下载对应版本。' : receipt.value?.report_status === 'revision_requested' ? '请按审核意见补充并核对资料；本任务不会自动替换报告。' : receipt.value?.evidence_status === 'review_ready' ? '证据检查已返回，仍需教师逐项核对。' : '报告存在待核对的信息，请先检查证据缺口。')

const props = defineProps({ accountId: { type: Number, required: true }, studentId: { type: Number, required: true }, studentLabel: String, requestId: { type: Number, default: null } })
const enabled = ref(false), busy = ref(''), error = ref(''), storageNotice = ref(''), locked = ref(false)
const plan = ref(null), receipt = ref(null)
const key = taskStorageKey(props.accountId, props.studentId, props.requestId)
let storage
try { storage = window.localStorage } catch { /* Private browsers may deny storage. */ }
let reference = readTaskReference(storage, key)
let alive = true
onBeforeUnmount(() => { alive = false })
const complete = computed(() => receipt.value?.status === 'awaiting_report_review')
const status = computed(() => taskStatusText(plan.value, receipt.value))
const done = computed(() => receipt.value?.completed_tools || [])
const attempts = computed(() => receipt.value?.attempts || 0)
function remember(value) {
  reference = value
  if (!writeTaskReference(storage, key, value)) storageNotice.value = '浏览器未允许保存任务编号；关闭页面后可能无法从这里恢复。'
}
function accept(value) {
  if (!matchesTaskTarget(value, props.studentId, props.requestId)) throw new Error('scope_mismatch')
  plan.value = value
  terminating.value = false
  if (value.status === 'terminated') { receipt.value = null; report.value = null; revisionCheck.value = null }
}
function fail(cause) {
  history.value = null
  revisionCheck.value = null
  const code = cause.response?.status
  receipt.value = null // Never retain a stale download after failed authorization/integrity checks.
  report.value = null
  if (code === 401 || code === 403 || cause.message === 'scope_mismatch') {
    locked.value = true
    error.value = '当前登录或个案权限已变化。请刷新学生列表，重新核对授权后继续。'
  } else if (code === 404) {
    plan.value = null
    remember(null)
    error.value = '任务不存在、已过期或试点已关闭。可刷新状态后重新创建。'
  } else if (code === 409) {
    locked.value = true
    error.value = '任务条件、资料或报告校验已变化。请刷新状态；不要直接重复执行。'
  } else {
    locked.value = true
    error.value = '暂未取得服务端结果，操作可能仍在处理中。请先刷新状态，确认后再重试。'
  }
}
async function action(label, operation) {
  if (busy.value) return
  busy.value = label
  error.value = ''
  try { await operation() } catch (cause) { if (alive) fail(cause) }
  finally { if (alive) busy.value = '' }
}
async function restore() {
  let capability
  try { capability = await getTeacherTaskCapabilities() }
  catch (cause) {
    if (!alive) return
    if (cause.response?.status === 404) { enabled.value = false; return }
    enabled.value = true
    throw cause
  }
  if (!alive) return
  enabled.value = capability.data.durable_case_execution === true
  if (!enabled.value) return
  if (reference?.taskId) {
    const response = await getTeacherCaseTask(reference.taskId)
    if (!alive) return
    accept(response.data)
    if (plan.value.status === 'plan_approved') {
      const result = await getTeacherCaseExecution(plan.value.task_id)
      if (!alive) return
      receipt.value = result.data
      if (report.value) await readReport()
    }
  }
  locked.value = false
}
function refresh() { return action('正在读取任务状态…', restore) }
function loadHistory() {
  historyOpen.value = true
  history.value = null
  return action('正在读取当前授权内的任务记录…', async () => {
    const response = await getTeacherCaseHistory(props.studentId, props.requestId)
    if (alive) history.value = response.data
  })
}
function openHistoryTask(taskId) {
  return action('正在读取所选任务，不会自动执行…', async () => {
    report.value = null; receipt.value = null; revisionCheck.value = null
    const response = await getTeacherCaseTask(taskId)
    if (!alive) return
    accept(response.data)
    remember({ requestId: crypto.randomUUID(), taskId })
    await restore()
    if (alive) historyOpen.value = false
  })
}
function terminateTask() {
  return action('正在请求终止；等待服务端确认…', async () => {
    const response = await terminateTeacherCaseTask(plan.value.task_id, plan.value.digest, terminationReason.value)
    if (!alive) return
    accept(response.data)
    receipt.value = null; report.value = null; revisionCheck.value = null
    locked.value = false
  })
}
function checkRevision() {
  return action('正在核验原授权内的新增资料…', async () => {
    revisionCheck.value = null
    const result = await checkTeacherCaseRevision(plan.value.task_id)
    if (!alive) return
    if (result.data.parent_task_id !== plan.value.task_id || result.data.parent_report_id !== receipt.value.report_id) throw new Error('scope_mismatch')
    revisionCheck.value = result.data
  })
}
function createRevision() {
  return action('正在创建待确认的补充计划…', async () => {
    const response = await createTeacherCaseRevision(plan.value.task_id)
    if (!alive) return
    accept(response.data)
    remember({ requestId: crypto.randomUUID(), taskId: response.data.task_id })
    receipt.value = null; report.value = null; revisionCheck.value = null
  })
}
function returnToParent() {
  return action('正在读取原任务…', async () => {
    const response = await getTeacherCaseTask(plan.value.revision.parent_task_id)
    if (!alive) return
    accept(response.data)
    remember({ requestId: crypto.randomUUID(), taskId: response.data.task_id })
    receipt.value = null; report.value = null; revisionCheck.value = null
    await restore()
  })
}
function create(candidateContract = null) {
  return action('正在准备待确认计划…', async () => {
    if (!reference) remember({ requestId: crypto.randomUUID(), taskId: null })
    const response = await createTeacherCaseTask({ request_id: reference.requestId, student_id: props.studentId, access_request_id: props.requestId,
      contract: candidateContract || { objective: 'conversation_preparation', period_days: 30, scope: 'authorized_only', output_format: 'checklist', resource_policy: 'not_needed', delivery: 'draft_for_review' } })
    if (!alive) return
    accept(response.data)
    remember({ ...reference, taskId: response.data.task_id })
  })
}
function decide(approved) {
  return action(approved ? '正在保存教师确认…' : '正在取消计划…', async () => {
    const response = await decideTeacherCaseTask(plan.value.task_id, plan.value.digest, approved)
    if (alive) accept(response.data)
  })
}
function execute() {
  return action('正在执行；等待服务端返回，不预判步骤完成…', async () => {
    const response = await executeTeacherCaseTask(plan.value.task_id)
    if (alive) { receipt.value = response.data; plan.value = { ...plan.value, last_failure: response.data.last_failure || null } }
  })
}
function download() {
  return action('正在核验权限并获取 PDF…', async () => {
    const response = await downloadTeacherCaseReport(props.studentId, receipt.value.report_id, props.requestId)
    if (!alive) return
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = `沟通准备报告-${receipt.value.report_id}.pdf`
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  })
}
async function readReport() {
  const result = await getExactTeacherReviewReport(props.studentId, receipt.value.report_id, props.requestId)
  if (!alive) return
  if (result.data.report_id !== receipt.value.report_id || result.data.content_hash !== receipt.value.report_hash) throw new Error('scope_mismatch')
  report.value = result.data
  receipt.value = { ...receipt.value, report_status: result.data.status }
}
function openReport() {
  return action('正在读取本任务绑定的报告…', async () => {
    await readReport()
    await nextTick()
    if (alive) reportHeading.value?.focus()
  })
}
function submitReview(payload) {
  return action('正在保存本报告审核意见…', async () => {
    await decideStudentReviewReport(props.studentId, receipt.value.report_id, payload.decision, payload.checklistConfirmed, payload.evidenceGapAcknowledged, payload.note, props.requestId)
    if (alive) await readReport()
  })
}
function newTask() { remember(null); plan.value = null; receipt.value = null; report.value = null; error.value = '' }
onMounted(refresh)
</script>

<template>
  <section v-if="enabled" class="case-task" :class="{ 'has-report': !!report, 'has-acceptance': acceptanceOpen }" aria-label="个案准备 Agent">
    <div class="case-task-summary">
    <header class="case-task-head">
      <div><span class="case-task-eyebrow"><UiIcon name="cases" :size="16" /> 个案准备 Agent · 受限工作流试点</span><h4>把一次沟通，准备成可审核的报告</h4></div>
      <span class="case-task-status" :class="{ delivered: complete }">{{ status }}</span>
    </header>
    <p class="case-task-intent">为{{ studentLabel }}准备一次个案沟通：读取授权范围内近 30 天资料，核对信息缺口，生成标准报告与核对清单。</p>
    <section v-if="plan?.revision" class="pc-revision-plan" aria-label="补充计划差异">
      <h5>补充计划 · 等待独立核对</h5>
      <p>基于原报告退回结果，使用已核验的新增授权资料重新准备沟通报告。</p>
      <dl><div><dt>原报告</dt><dd>{{ plan.revision.parent_report_id }}</dd></div><div><dt>资料变化</dt><dd>新增 {{ plan.revision.added_record_count }} 条，移出 {{ plan.revision.removed_record_count }} 条</dd></div><div><dt>保持不变</dt><dd>学生、审批范围、四步执行顺序与人工审核要求</dd></div></dl>
      <p>原报告保持不变。新增记录不代表缺口已解决；确认后资料再次变化，将停止执行。</p>
      <button class="ghost-btn" :disabled="!!busy" @click="returnToParent">返回原任务</button>
    </section>
    <ol v-if="plan?.status !== 'terminated'" class="case-task-steps" aria-label="执行计划与真实完成状态">
      <li v-for="(step, index) in caseTaskSteps" :key="step.id" :class="{ done: done.includes(step.id) }">
        <span class="case-task-step-number"><UiIcon v-if="done.includes(step.id)" name="check" :size="16" /><template v-else>{{ index + 1 }}</template></span>
        <div><strong>{{ step.title }}</strong><small>{{ step.detail }}</small></div>
        <em>{{ done.includes(step.id) ? '已完成' : '未执行' }}</em>
      </li>
    </ol>
    <div v-if="complete" class="case-task-delivery">
      <UiIcon name="report" :size="24" />
      <div><strong>{{ deliveryTitle }}</strong><p>{{ deliveryDescription }}不代表已完成线下关怀。</p><small>报告编号：{{ receipt.report_id }}</small><details><summary>查看交付校验信息</summary><code>SHA-256：{{ receipt.report_hash }}</code></details></div>
    </div>
    <p v-if="receipt?.status === 'failed'" class="case-task-warning" role="status">执行中断。已完成的步骤已保存；恢复时从服务端断点继续。已尝试 {{ attempts }}/3 次。</p>
    <p v-if="attempts >= 3 && !complete" class="case-task-warning">已达到本任务重试上限，请联系管理员检查失败原因。</p>
    <section v-if="!complete && (failure || receipt?.status === 'failed')" class="pc-task-history" aria-label="失败记录">
      <h5>最近一次已记录的失败</h5><p>{{ taskFailureText(failure?.code || receipt?.error) }}</p>
      <small v-if="failure">第 {{ failure.attempt }} 次尝试 · {{ taskDateText(failure.at) }}</small>
      <p>这里只显示受限错误分类，不展示学生正文或服务商原始错误。终止原因是教师选择，与失败记录分别保存。</p>
    </section>
    <p v-if="busy" class="case-task-live" role="status" aria-live="polite">{{ busy }}</p>
    <p v-if="error" class="case-task-warning" role="alert">{{ error }}</p>
    <p v-if="storageNotice" class="case-task-note">{{ storageNotice }}</p>
    <TeacherIntentPreview v-if="!plan" :disabled="!!busy || locked" @prepare="create" />
    <div class="case-task-actions">
      <button v-if="!plan" class="primary-btn" :disabled="!!busy || locked" @click="create()">创建沟通准备计划</button>
      <template v-else-if="plan.status === 'waiting_approval'">
        <button class="primary-btn" :disabled="!!busy || locked" @click="decide(true)">确认这份计划</button>
        <button class="ghost-btn" :disabled="!!busy || locked" @click="decide(false)">取消计划</button>
      </template>
      <button v-else-if="plan.status === 'plan_approved' && !complete" class="primary-btn" :disabled="!!busy || locked || attempts >= 3" @click="execute">{{ attempts ? '从断点继续执行' : '执行已确认计划' }}</button>
      <button v-else-if="plan.status === 'cancelled' && !plan.revision" class="ghost-btn" :disabled="!!busy || locked" @click="newTask">准备另一份计划</button>
      <button v-if="complete" class="primary-btn" :disabled="!!busy || locked" @click="openReport"><UiIcon name="report" :size="16" /> 查看报告与审签</button>
      <button v-if="complete" class="ghost-btn" :disabled="!!busy || locked" @click="download"><UiIcon name="download" :size="16" /> {{ receipt.report_status === 'reviewed' ? '下载已签署报告' : receipt.report_status === 'revision_requested' ? '下载退回版本' : '下载待审核报告' }}</button>
      <button class="ghost-btn" :disabled="!!busy" @click="refresh"><UiIcon name="refresh" :size="16" /> 刷新任务状态</button>
    </div>
    <footer class="case-task-note">LangGraph 持久化执行 · 仅保存任务编号到本机 · 不自动发送通知或作出诊断。<span v-if="plan">任务 {{ plan.task_id }}</span></footer>
    <section v-if="plan && !complete" class="pc-task-termination" aria-label="任务终止">
      <template v-if="plan.status === 'terminated'">
        <strong>任务已安全终止</strong><p>旧任务不会恢复执行。已有报告与任务记录保留，仍受原权限和有效期约束。</p>
        <small>终止时间：{{ taskDateText(plan.termination?.at) }}<br>所选原因：{{ { manual: '不再需要执行', source_changed: '资料或任务条件变化', retry_exhausted: '执行失败，停止尝试' }[plan.termination?.reason] }}</small>
        <div v-if="!plan.revision" class="termination-actions"><button type="button" :disabled="!!busy" @click="newTask">准备新的任务</button></div>
      </template>
      <template v-else-if="['waiting_approval', 'plan_approved'].includes(plan.status)">
        <button v-if="!terminating" type="button" :disabled="!!busy" @click="terminating = true">终止此任务</button>
        <div v-else>
          <strong>确认终止当前任务？</strong><p>此操作不可恢复，也不会删除报告。若任务仍在运行，需等待服务端释放执行锁。</p>
          <label :for="`termination-reason-${studentId}`">终止原因</label>
          <select :id="`termination-reason-${studentId}`" v-model="terminationReason" :disabled="!!busy"><option value="manual">不再需要执行</option><option value="source_changed">资料或任务条件变化</option><option value="retry_exhausted">执行失败，停止尝试</option></select>
          <div class="termination-actions"><button type="button" :disabled="!!busy" @click="terminating = false">继续保留</button><button type="button" :disabled="!!busy" @click="terminateTask">确认终止任务</button></div>
        </div>
      </template>
    </section>
    <section class="pc-task-history" aria-label="当前个案任务历史">
      <button class="ghost-btn" :aria-expanded="acceptanceOpen" :disabled="!!busy" @click="acceptanceOpen = !acceptanceOpen">{{ acceptanceOpen ? '收起比赛验收台' : '打开比赛验收台' }}</button>
      <button class="ghost-btn" :disabled="!!busy" @click="loadHistory">{{ historyOpen ? '刷新历史记录' : '查看任务历史' }}</button>
      <template v-if="historyOpen">
        <button class="ghost-btn" :disabled="!!busy" @click="historyOpen = false">收起历史</button>
        <p>仅列出本人在当前学生与当前授权下、有效期内最近 30 个任务。状态为计划状态；打开后重新核验执行与报告状态。</p>
        <p v-if="history && !history.items.length">尚无可查看的记录。创建计划后，可在这里找回任务；过期或已删除的任务不会显示。</p>
        <ul v-if="history?.items.length">
          <li v-for="item in history.items" :key="item.task_id">
            <div><strong>{{ item.is_revision ? '补充计划' : '沟通准备计划' }} · {{ taskStatusText(item, null) }}</strong><small>{{ taskDateText(item.updated_at) }} · 存档更新</small><code>{{ item.task_id }}</code></div>
            <button class="ghost-btn" :disabled="!!busy || plan?.task_id === item.task_id" @click="openHistoryTask(item.task_id)">{{ plan?.task_id === item.task_id ? '当前任务' : '查看任务' }}</button>
          </li>
        </ul>
        <p v-if="history?.has_more">还有更早的任务未展示；本轮入口仅支持最近 30 条。</p>
      </template>
    </section>
    <section v-if="report?.status === 'revision_requested'" class="pc-revision-brief" aria-label="退回补充事项">
      <h5>待补充与核对</h5><p>{{ report.review_note }}</p>
      <ul><li v-for="gap in report.data_scope?.information_gaps || []" :key="gap">{{ gap }}</li></ul>
      <button class="ghost-btn" :disabled="!!busy || locked" @click="checkRevision">检查补充资料</button>
      <div v-if="revisionCheck" class="revision-check-result" role="status">
        <strong>{{ { waiting_for_material: '等待补充资料', ready_for_plan_review: '发现新增资料，可准备补充计划', requires_human_support: '需要先处理当前安全问题' }[revisionCheck.status] || '请重新核对状态' }}</strong>
        <p>原授权范围内新增 {{ revisionCheck.added_record_count }} 条、移出 {{ revisionCheck.removed_record_count }} 条记录。</p>
        <small>{{ revisionCheck.boundary }}</small>
        <button v-if="revisionCheck.status === 'ready_for_plan_review'" class="primary-btn" :disabled="!!busy || locked" @click="createRevision">准备补充计划</button>
      </div>
      <small>检查不会生成报告或扩大授权；补充计划仍需再次确认。</small>
    </section>
    </div>
    <section v-if="report" class="task-report-review" aria-label="本任务报告审核">
      <div class="task-review-heading"><h4 ref="reportHeading" tabindex="-1">核对报告，再记录审核决定</h4><button class="ghost-btn" :disabled="!!busy" @click="report = null">收起报告</button></div>
      <p>只审核本任务绑定的报告版本。退回意见会保存到该版本，不会触发自动生成或扩大数据授权。</p>
      <TeacherReviewReport :report="report" :allow-generate="false" embedded desktop-workspace :id-prefix="`task-report-${studentId}`" :decision-loading="!!busy || locked" @decision="submitReview" @download="download" />
    </section>
    <TeacherAcceptanceDesk v-if="acceptanceOpen" :plan="plan" :receipt="receipt" :blocked="locked || !!busy" :busy="!!busy" @refresh="refresh" @report="openReport" @download="download" />
  </section>
</template>

<style scoped>
.case-task { margin: 0; padding: 18px 0 0; border-top: 1px solid var(--t-line); color: var(--t-ink); font-size: 13px; }
.case-task-summary { min-width: 0; }
.case-task-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.case-task-eyebrow { display: inline-flex; align-items: center; gap: 6px; color: var(--t-muted); font-size: 11px; font-weight: 600; letter-spacing: .03em; }
.case-task-head h4 { margin: 6px 0 0; font-size: 17px; font-weight: 600; line-height: 1.45; letter-spacing: -.01em; text-wrap: balance; }
.case-task-status { flex: 0 0 auto; padding: 2px 8px; border: 1px solid var(--t-line-2); border-radius: 3px; color: var(--t-muted); background: var(--t-surface-2); font-size: 11px; white-space: nowrap; }
.case-task-status.delivered { color: var(--t-green-ink); border-color: #C5E3D1; background: var(--t-green-bg); }
.case-task-intent { max-width: 76ch; margin: 8px 0 0; color: var(--t-muted); font-size: 12.5px; line-height: 1.7; }
.case-task-steps { display: grid; grid-template-columns: 1fr 1fr; gap: 0 26px; margin: 12px 0 0; padding: 0; list-style: none; }
.case-task-steps li { display: flex; align-items: center; gap: 10px; padding: 9px 0; border-top: 1px solid var(--t-line); }
.case-task-step-number { display: grid; place-items: center; flex: 0 0 auto; width: 20px; height: 20px; border: 1px solid var(--t-line-2); border-radius: 50%; color: var(--t-muted); font: 500 10.5px/1 var(--t-mono); }
.case-task-steps .done .case-task-step-number { color: #fff; border-color: var(--t-green-ink); background: var(--t-green-ink); }
.case-task-steps strong { display: block; font-size: 12.5px; font-weight: 600; }
.case-task-steps small { display: block; margin-top: 1px; color: var(--t-muted); font-size: 11px; line-height: 1.5; }
.case-task-steps em { margin-left: auto; color: var(--t-faint); font-size: 10.5px; font-style: normal; white-space: nowrap; }
.case-task-steps .done em { color: var(--t-green-ink); }
.case-task-delivery { display: flex; gap: 12px; margin: 14px 0 0; padding: 12px 14px; border: 1px solid var(--t-line); border-left: 2px solid var(--t-green); border-radius: var(--t-r); background: var(--t-surface-2); }
.case-task-delivery > svg { flex: 0 0 auto; margin-top: 2px; color: var(--t-green-ink); }
.case-task-delivery strong { display: block; font-size: 13px; font-weight: 600; }
.case-task-delivery p { margin: 3px 0; color: var(--t-muted); font-size: 12px; line-height: 1.65; }
.case-task-delivery small, .case-task-delivery details { color: var(--t-faint); font-size: 11px; overflow-wrap: anywhere; }
.case-task-delivery summary { margin-top: 6px; cursor: pointer; }
.case-task-delivery code { display: block; margin-top: 6px; color: var(--t-muted); font-size: 10.5px; }
.case-task-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
.case-task button { display: inline-flex; align-items: center; justify-content: center; gap: 5px; min-height: 32px; padding: 5px 12px; border: 1px solid var(--t-line-2); border-radius: var(--t-r-sm); color: var(--t-ink-2); background: var(--t-surface); font: inherit; font-size: 12px; font-weight: 600; cursor: pointer; }
.case-task button:hover:not(:disabled) { border-color: #868C9B; background: var(--t-surface-2); }
.case-task button.primary-btn { color: #fff; border-color: var(--t-accent); background: var(--t-accent); }
.case-task button.primary-btn:hover:not(:disabled) { border-color: var(--t-accent-ink); background: var(--t-accent-ink); }
.case-task button:disabled { opacity: .5; cursor: not-allowed; }
.case-task :focus-visible { outline: 2px solid var(--t-accent); outline-offset: 2px; }
.case-task-live { margin: 10px 0 0; color: var(--t-accent); font-size: 12px; line-height: 1.6; }
.case-task-warning { margin: 10px 0 0; padding: 9px 12px; border-left: 2px solid var(--t-amber); color: var(--t-amber-ink); background: var(--t-amber-bg); font-size: 12px; line-height: 1.65; }
.case-task-note { margin: 12px 0 0; color: var(--t-faint); font-size: 10.5px; line-height: 1.7; overflow-wrap: anywhere; }
.case-task-note span { display: block; margin-top: 2px; }

.pc-task-history, .pc-task-termination, .pc-revision-plan, .pc-revision-brief { display: none; }
@media (min-width: 1024px) {
  .pc-task-history { display: block; margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--t-line); color: var(--t-muted); font-size: 12px; line-height: 1.7; }
  .pc-task-history h5 { margin: 0; color: var(--t-ink); font-size: 12.5px; font-weight: 600; }
  .pc-task-history p { max-width: 72ch; margin: 7px 0; }
  .pc-task-history > button + button { margin-left: 8px; }
  .pc-task-history ul { max-height: 340px; margin: 10px 0; padding: 0; overflow: auto; list-style: none; }
  .pc-task-history li { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 0; border-top: 1px solid var(--t-line); }
  .pc-task-history li > div { min-width: 0; }
  .pc-task-history small, .pc-task-history code { display: block; color: var(--t-faint); overflow-wrap: anywhere; }
  .pc-task-history code { font-size: 10.5px; }
  .pc-task-termination { display: block; margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--t-line); color: var(--t-muted); font-size: 12px; line-height: 1.65; }
  .pc-task-termination p { margin: 6px 0; }
  .pc-task-termination small { color: var(--t-faint); overflow-wrap: anywhere; }
  .pc-task-termination label { display: grid; gap: 5px; margin: 8px 0; }
  .pc-task-termination select { max-width: 100%; min-height: 32px; padding: 4px 8px; border: 1px solid var(--t-line-2); border-radius: var(--t-r-sm); color: var(--t-ink); background: var(--t-surface); font: inherit; font-size: 12px; }
  .termination-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
  .pc-revision-plan { display: block; margin: 14px 0; padding: 12px 0; border-block: 1px solid var(--t-line); color: var(--t-muted); font-size: 12px; line-height: 1.7; }
  .pc-revision-plan h5 { margin: 0; color: var(--t-ink); font-size: 13px; font-weight: 600; }
  .pc-revision-plan dl { margin: 8px 0; }
  .pc-revision-plan dl > div { display: grid; grid-template-columns: 76px minmax(0, 1fr); gap: 8px; padding: 3px 0; }
  .pc-revision-plan dt { color: var(--t-faint); }
  .pc-revision-plan dd { margin: 0; overflow-wrap: anywhere; }
  .pc-revision-brief { display: block; margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--t-line); }
  .pc-revision-brief h5 { margin: 0 0 6px; color: var(--t-ink); font-size: 13px; font-weight: 600; }
  .pc-revision-brief p, .pc-revision-brief li { color: var(--t-muted); font-size: 12px; line-height: 1.65; overflow-wrap: anywhere; }
  .pc-revision-brief ul { margin: 6px 0; padding-left: 16px; }
  .pc-revision-brief small { color: var(--t-amber-ink); font-size: 11px; line-height: 1.6; }
  .revision-check-result { margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--t-line); }
  .revision-check-result strong { color: var(--t-ink); font-size: 12.5px; }
  .revision-check-result p { margin: 4px 0; }

  .case-task.has-report { display: grid; grid-template-columns: 272px minmax(0, 1fr); gap: 26px; align-items: start; }
  .case-task.has-report .case-task-summary { position: sticky; top: 84px; max-height: calc(100dvh - 104px); overflow: auto; padding-right: 6px; }
  .case-task.has-report .case-task-head { flex-direction: column; gap: 8px; }
  .case-task.has-report .case-task-head h4 { font-size: 16px; }
  .case-task.has-report .case-task-steps { grid-template-columns: 1fr; margin-top: 10px; }
  .case-task.has-report .case-task-delivery { padding: 10px 0 0; border: 0; border-top: 1px solid var(--t-line); border-radius: 0; background: none; }
  .case-task.has-report .case-task-delivery > svg { display: none; }
  .case-task.has-acceptance .case-task-summary { position: static; max-height: none; }
  .case-task.has-acceptance .acceptance-desk { position: relative; z-index: 1; background: var(--t-surface); }
}
.task-report-review { min-width: 0; margin-top: 20px; padding-top: 18px; border-top: 1px solid var(--t-line); }
.task-review-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.task-review-heading h4 { margin: 0; font-size: 15px; font-weight: 600; line-height: 1.5; scroll-margin-top: 220px; }
.task-review-heading button { flex-shrink: 0; min-height: 30px; }
.task-report-review > p { margin: 8px 0 0; color: var(--t-muted); font-size: 12px; line-height: 1.7; }
@media (min-width: 1024px) {
  .has-report .task-report-review { margin: 0; padding: 0 0 0 26px; border: 0; border-left: 1px solid var(--t-line); }
  .has-report .task-review-heading h4 { font-size: 15px; scroll-margin-top: 84px; }
}
@media (max-width: 700px) {
  .case-task { padding-top: 14px; }
  .case-task-head { flex-direction: column; gap: 8px; }
  .case-task-head h4 { font-size: 16px; }
  .case-task-steps { grid-template-columns: 1fr; }
  .case-task-actions button { flex: 1 1 auto; min-height: 38px; }
  .case-task-delivery { padding: 12px; }
}
</style>
