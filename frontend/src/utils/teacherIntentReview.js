const labels = Object.freeze({
  external_delivery: '对外发送或公开', approval_bypass: '代签或跳过审核',
  authorization_scope: '授权与资料范围', destructive_action: '删除或清空资料',
  clinical_action: '诊断或处方', instruction_override: '覆盖系统规则',
})

export function localIntentReview(result) {
  if (result?.source !== 'local_policy' || result?.review_reason !== 'risk_expression_requires_review') return null
  const categories = Array.isArray(result.risk_categories) ? result.risk_categories : []
  return {
    labels: [...new Set(categories.filter(key => Object.hasOwn(labels, key)).map(key => labels[key]))],
    canPrepare: false,
  }
}
