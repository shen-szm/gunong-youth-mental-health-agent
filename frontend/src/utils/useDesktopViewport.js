import { ref, onMounted, onBeforeUnmount } from 'vue'

export function useDesktopViewport() {
  const desktop = ref(false)
  let query
  const sync = () => {
    // A minimized/capture surface can briefly report 1 × 1; do not discard
    // the user's active desktop task for a non-interactive viewport.
    if (window.innerWidth <= 1 || window.innerHeight <= 1) return
    desktop.value = query.matches
  }
  onMounted(() => {
    query = window.matchMedia('(min-width: 1024px)')
    sync()
    query.addEventListener('change', sync)
  })
  onBeforeUnmount(() => query?.removeEventListener('change', sync))
  return desktop
}
