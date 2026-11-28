import { ref, onMounted, watch, onBeforeUnmount } from 'vue'

// 数字计数动画：从当前值缓动到目标值，用于学生端统计数字的轻量活力反馈。
// 系统开启「减少动态效果」时直接显示最终值。
export function useCountUp(target, duration = 680) {
  const display = ref(0)
  let raf = 0
  const reduceMotion = typeof window !== 'undefined' && window.matchMedia
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const run = (to) => {
    cancelAnimationFrame(raf)
    const value = Number(to) || 0
    if (reduceMotion) { display.value = value; return }
    const from = display.value
    const start = performance.now()
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3)
      display.value = Math.round(from + (value - from) * eased)
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
  }
  onMounted(() => run(target.value))
  watch(target, v => run(v))
  onBeforeUnmount(() => cancelAnimationFrame(raf))
  return display
}
