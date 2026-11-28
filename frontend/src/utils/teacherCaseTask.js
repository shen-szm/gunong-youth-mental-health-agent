// Store only task identifiers, never a student's name, prose, or report.
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
export function taskStorageKey(accountId, studentId, requestId) {
  return `shengyu_case_task_v1:${accountId}:${studentId}:${requestId || 0}`
}
export function readTaskReference(storage, key) {
  try {
    const value = JSON.parse(storage.getItem(key))
    if (!uuid.test(value?.requestId)) return null
    return { requestId: value.requestId, taskId: uuid.test(value.taskId) ? value.taskId : null }
  } catch { return null }
}
export function writeTaskReference(storage, key, value) {
  try {
    if (!value) storage.removeItem(key)
    else storage.setItem(key, JSON.stringify({ requestId: value.requestId, taskId: value.taskId || null }))
    return true
  } catch { return false }
}
export function matchesTaskTarget(plan, studentId, requestId) {
  return plan?.target?.student_id === studentId && (plan.target.access_request_id || null) === (requestId || null)
}
export const caseTaskSteps = [
  { id: 'query_authorized_items', title: '读取授权资料', detail: '核验职责与个案审批范围' },
  { id: 'check_evidence_gaps', title: '检查证据缺口', detail: '区分已有记录与待补充信息' },
  { id: 'render_work_product', title: '生成沟通报告', detail: '形成可下载、待审签的工作成果' },
  { id: 'verify_work_product', title: '核验交付物', detail: '检查报告归属、完整性与证据状态' },
]
export function taskStatusText(plan, receipt) {
  if (plan?.status === 'terminated') return '任务已终止'
  if (receipt?.report_status === 'reviewed') return '教师已签署'
  if (receipt?.report_status === 'revision_requested') return '待补充修订'
  if (receipt?.status === 'awaiting_report_review') return '报告待审核'
  if (receipt?.status === 'failed') return '执行中断'
  if (plan?.status === 'cancelled') return '计划已取消'
  if (plan?.status === 'plan_approved') return receipt?.attempts ? '等待恢复执行' : '计划已确认'
  return plan ? '等待教师确认' : '尚未创建任务'
}
export function taskFailureText(code) {
  return ({ source_or_artifact_changed: '资料或报告校验未通过。请先核对资料与报告版本，不要直接重复执行。', tool_failed: '工具执行失败，服务端未记录可公开的具体原因。请刷新状态；仍失败时联系管理员。' })[code] || '未记录可公开的失败原因，请联系管理员核查；不要将未知原因视为模型故障。'
}
export function taskDateText(value) {
  const date = new Date(value)
  return value && Number.isFinite(date.getTime()) ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Shanghai' }).format(date) + '（北京时间）' : '时间未记录'
}
