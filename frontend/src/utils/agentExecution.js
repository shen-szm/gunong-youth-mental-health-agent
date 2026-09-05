// Read-only projection of persisted plans/events. A replay never invokes a tool.
export function executionSnapshot(plan = [], events = [], cursor = events.length) {
  const ordered = [...events].sort((a, b) => a.sequence - b.sequence)
  const count = Math.max(0, Math.min(ordered.length, Number(cursor) || 0))
  const visible = ordered.slice(0, count)
  const planned = Array.isArray(plan) && plan.length > 0
  const steps = planned ? plan : ordered.map(event => ({ agent: event.agent, tool: event.tool }))
  const consumed = new Set()
  const rows = steps.map((step, index) => {
    const eventIndex = ordered.findIndex((event, i) => !consumed.has(i) && event.agent === step.agent)
    if (eventIndex >= 0) consumed.add(eventIndex)
    const event = eventIndex >= 0 && eventIndex < count ? ordered[eventIndex] : null
    return {
      id: `step-${index}`, agent: step.agent, plannedTool: planned ? step.tool : null,
      status: event?.status || 'unrecorded', event,
      tool: event?.tool || null, inPlan: planned,
    }
  })
  // Recovery/failure records may not have a corresponding planned role.
  visible.forEach((event, index) => {
    if (!consumed.has(index)) rows.push({
      id: `event-${event.sequence}-${index}`, agent: event.agent, plannedTool: null,
      status: event.status, event, tool: event.tool || null, inPlan: false,
    })
  })
  return {
    rows, count, total: ordered.length, planned,
    completed: rows.filter(row => row.status === 'completed').length,
    tools: [...new Set(visible.map(event => event.tool).filter(Boolean))],
  }
}

export const executionStatus = status => ({
  completed: '完成', attention: '需处理', failed: '失败', unrecorded: '尚无记录',
})[status] || '状态未知'

export const executionSource = source => ({
  model: '模型策略', deterministic: '本地规则', safety_rule: '安全规则',
})[source] || '来源未确认'
