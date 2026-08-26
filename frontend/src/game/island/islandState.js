export const ISLAND_WORLD = Object.freeze({ width: 960, height: 540 })

export const ISLAND_SPAWN = Object.freeze({ x: 480, y: 492 })

export const ISLAND_PHASES = Object.freeze([
  { id: 'day', label: '白天', shortLabel: '晴光', period: '06:00–16:59' },
  { id: 'dusk', label: '傍晚', shortLabel: '暮色', period: '17:00–19:59' },
  { id: 'night', label: '夜晚', shortLabel: '星灯', period: '20:00–05:59' },
])

export const ISLAND_PLACES = Object.freeze([
  { id: 'home', label: '咕团家园', x: 505, y: 307, hint: '陪咕团喂食、梳毛，或者安静坐一会儿。' },
  { id: 'garden', label: '云顶暖房', x: 465, y: 112, hint: '照料一株正在生长的小植物。' },
  { id: 'dock', label: '月光钓鱼湾', x: 793, y: 340, hint: '听着水声慢慢抛竿，不设置输赢。' },
  { id: 'exchange', label: '幸福交换树', x: 215, y: 326, hint: '交换一件令你幸福的小事。' },
  { id: 'rest', label: '星灯休息台', x: 692, y: 120, hint: '坐下来看看海，跟着星灯放慢呼吸。' },
])

const clamp = (value, min, max) => Math.min(max, Math.max(min, value))

export function clampIslandPosition(position = ISLAND_SPAWN) {
  const rawX = Number(position?.x)
  const rawY = Number(position?.y)
  return {
    x: Math.round(clamp(Number.isFinite(rawX) ? rawX : ISLAND_SPAWN.x, 92, 872)),
    y: Math.round(clamp(Number.isFinite(rawY) ? rawY : ISLAND_SPAWN.y, 82, 506)),
  }
}

export function resolveIslandPhase(hour = new Date().getHours()) {
  const normalizedHour = Number.isFinite(Number(hour)) ? Number(hour) : 12
  if (normalizedHour >= 6 && normalizedHour < 17) return 'day'
  if (normalizedHour >= 17 && normalizedHour < 20) return 'dusk'
  return 'night'
}

export function normalizeIslandPhase(value, fallback = resolveIslandPhase()) {
  return ISLAND_PHASES.some(phase => phase.id === value) ? value : fallback
}

export function islandStorageKey(scope) {
  const safeScope = String(scope || '').replace(/[^a-zA-Z0-9_-]/g, '').slice(0, 48)
  return safeScope ? `shengyu_island_v5_1_${safeScope}` : ''
}

export function loadIslandState(scope, storage = globalThis.localStorage) {
  const key = islandStorageKey(scope)
  const defaultState = { position: { ...ISLAND_SPAWN }, lastPlace: 'home', timePhase: resolveIslandPhase() }
  if (!storage || !key) return defaultState
  try {
    const parsed = JSON.parse(storage.getItem(key) || '{}')
    const lastPlace = ISLAND_PLACES.some(place => place.id === parsed.lastPlace) ? parsed.lastPlace : 'home'
    return { position: clampIslandPosition(parsed.position), lastPlace, timePhase: normalizeIslandPhase(parsed.timePhase) }
  } catch {
    return defaultState
  }
}

export function saveIslandState(scope, state, storage = globalThis.localStorage) {
  const key = islandStorageKey(scope)
  if (!storage || !key) return
  try {
    storage.setItem(key, JSON.stringify({
      version: 2,
      position: clampIslandPosition(state?.position),
      lastPlace: ISLAND_PLACES.some(place => place.id === state?.lastPlace) ? state.lastPlace : 'home',
      timePhase: normalizeIslandPhase(state?.timePhase),
    }))
  } catch {
    // Storage can be unavailable in private/restricted contexts; the island stays usable in memory.
  }
}
