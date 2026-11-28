import { ref, onMounted, onUnmounted } from 'vue'

// 仅开发环境：?hour=18 预览任意时段。生产构建里 DEV 为 false，参数完全不生效。
export function devHourOverride() {
  if (typeof window === 'undefined' || !import.meta.env?.DEV) return null
  const raw = new URLSearchParams(window.location.search).get('hour')
  if (raw === null || raw === '') return null
  const hour = Number(raw)
  return Number.isInteger(hour) && hour >= 0 && hour <= 23 ? hour : null
}

// 与房间保持同一套分段：6–17 白天，17–20 傍晚，其余为夜晚。
export function getTimeOfDay(date = new Date()) {
  const hour = devHourOverride() ?? date.getHours()
  if (hour >= 6 && hour < 17) return 'day'
  if (hour >= 17 && hour < 20) return 'evening'
  return 'night'
}

export function useTimeOfDay() {
  const part = ref(getTimeOfDay())
  let timer = null

  const refresh = () => { part.value = getTimeOfDay() }
  const onVisibility = () => { if (!document.hidden) refresh() }

  onMounted(() => {
    refresh()
    timer = setInterval(refresh, 60000)
    document.addEventListener('visibilitychange', onVisibility)
  })
  onUnmounted(() => {
    if (timer) clearInterval(timer)
    timer = null
    document.removeEventListener('visibilitychange', onVisibility)
  })

  return part
}
