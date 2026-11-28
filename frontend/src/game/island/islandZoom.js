export const ISLAND_ZOOM = Object.freeze({
  min: 1,
  max: 2.5,
  step: 1.25,
  tapSlop: 12,
  tapDuration: 700,
})

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

export function clampIslandZoom(value) {
  const zoom = Number(value)
  if (!Number.isFinite(zoom)) return ISLAND_ZOOM.min
  return clamp(zoom, ISLAND_ZOOM.min, ISLAND_ZOOM.max)
}

export function clampIslandScroll({ scrollX, scrollY, zoom, world, view }) {
  const safeZoom = clampIslandZoom(zoom)
  const maxX = Math.max(0, world.width - view.width / safeZoom)
  const maxY = Math.max(0, world.height - view.height / safeZoom)
  return {
    scrollX: clamp(Number.isFinite(scrollX) ? scrollX : 0, 0, maxX),
    scrollY: clamp(Number.isFinite(scrollY) ? scrollY : 0, 0, maxY),
  }
}

export function anchoredIslandScroll({ worldX, worldY, screenX, screenY, zoom, world, view }) {
  const safeZoom = clampIslandZoom(zoom)
  return clampIslandScroll({
    scrollX: worldX - screenX / safeZoom,
    scrollY: worldY - screenY / safeZoom,
    zoom: safeZoom,
    world,
    view,
  })
}

export function panIslandScroll({ scrollX, scrollY, deltaX, deltaY, zoom, world, view }) {
  const safeZoom = clampIslandZoom(zoom)
  return clampIslandScroll({
    scrollX: scrollX - deltaX / safeZoom,
    scrollY: scrollY - deltaY / safeZoom,
    zoom: safeZoom,
    world,
    view,
  })
}
