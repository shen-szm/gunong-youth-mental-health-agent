const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

function focusWithoutScroll(el) {
  el?.focus?.({ preventScroll: true })
}

function visibleFocusable(container) {
  return Array.from(container.querySelectorAll(FOCUSABLE)).filter(el =>
    el.getAttribute('aria-hidden') !== 'true' &&
    (el.offsetWidth || el.offsetHeight || el.getClientRects().length)
  )
}

// 挂载一次弹层的键盘边界：Esc 关闭、Tab 在弹层内循环、关闭后把焦点还给触发元素。
export function activateDialog(container, { onClose, initialFocus } = {}) {
  if (!container) return () => {}
  const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null

  function onKeydown(event) {
    // 输入法候选框的 Esc/Tab 属于合成过程，不能触发弹层关闭或焦点切换。
    if (event.isComposing || event.keyCode === 229) return
    if (event.key === 'Escape') {
      event.preventDefault()
      onClose?.()
      return
    }
    if (event.key !== 'Tab') return
    const items = visibleFocusable(container)
    if (!items.length) {
      event.preventDefault()
      focusWithoutScroll(container)
      return
    }
    const first = items[0]
    const last = items[items.length - 1]
    const active = document.activeElement
    if (event.shiftKey) {
      if (active === first || !container.contains(active)) {
        event.preventDefault()
        focusWithoutScroll(last)
      }
    } else if (active === last || !container.contains(active)) {
      event.preventDefault()
      focusWithoutScroll(first)
    }
  }

  document.addEventListener('keydown', onKeydown, true)
  requestAnimationFrame(() => {
    focusWithoutScroll(initialFocus?.() || visibleFocusable(container)[0] || container)
  })

  return () => {
    document.removeEventListener('keydown', onKeydown, true)
    focusWithoutScroll(previous)
  }
}
