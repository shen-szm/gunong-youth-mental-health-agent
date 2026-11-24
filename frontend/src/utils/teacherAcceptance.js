import { caseTaskSteps, taskStatusText } from './teacherCaseTask.js'

// A presentation of observed evidence, not an evaluation score or execution engine.
export function acceptanceEvidence(plan, receipt, blocked = false) {
  if (!plan || blocked) return null
  const matched = receipt?.task_id === plan.task_id ? receipt : null
  const delivered = plan.status === 'plan_approved' && matched?.status === 'awaiting_report_review' && !!matched.report_id && /^[a-f0-9]{64}$/.test(matched.report_hash || '')
  const knownSteps = new Set(matched?.completed_tools || [])
  return {
    status: taskStatusText(plan, matched),
    steps: caseTaskSteps.map(step => ({ ...step, state: knownSteps.has(step.id) ? '回执确认完成' : matched ? '未取得完成回执' : '尚未读取执行回执' })),
    delivered,
    reportId: delivered ? matched.report_id : null,
    reportHash: delivered ? matched.report_hash : null,
    reportStatus: delivered ? ({ draft: '等待教师审核', reviewed: '教师已签署', revision_requested: '教师已退回补充' }[matched.report_status] || '审核状态未记录') : '尚无已核验交付物',
    attempts: matched?.attempts ?? null,
    failure: matched?.last_failure || plan.last_failure || null,
    source: plan.source === 'local_rules' ? '规则生成的固定四步计划' : '计划来源未识别',
  }
}
