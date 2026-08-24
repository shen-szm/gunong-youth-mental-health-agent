export const ISLAND_WORLD = Object.freeze({ width: 960, height: 540 })

export const ISLAND_SPAWN = Object.freeze({ x: 480, y: 398 })

export const ISLAND_PLACES = Object.freeze([
  { id: 'home', label: '潮汐小屋', x: 480, y: 398, hint: '回到安静的起点，整理一下再出发。' },
  { id: 'garden', label: '心田', x: 286, y: 270, hint: '照料一块小田，也照料当下的自己。' },
  { id: 'dock', label: '慢钓码头', x: 750, y: 338, hint: '沿着海面慢下来，等待一次轻轻的回应。' },
  { id: 'exchange', label: '幸福交换站', x: 600, y: 185, hint: '交换一件令你幸福的小事。' },
])

const clamp = (value, min, max) => Math.min(max, Math.max(min, value))

export function clampIslandPosition(position = ISLAND_SPAWN) {
  const rawX = Number(position?.x)
  const rawY = Number(position?.y)
  let x = clamp(Number.isFinite(rawX) ? rawX : ISLAND_SPAWN.x, 158, 802)
  let y = clamp(Number.isFinite(rawY) ? rawY : ISLAND_SPAWN.y, 140, 424)
  const dx = (x - 480) / 322
  const dy = (y - 282) / 142
  const distance = Math.sqrt(dx * dx + dy * dy)
  if (distance > 1) {
    x = 480 + (dx / distance) * 322
    y = 282 + (dy / distance) * 142
  }
  return { x: Math.round(x), y: Math.round(y) }
}

export function islandStorageKey(scope) {
  const safeScope = String(scope || '').replace(/[^a-zA-Z0-9_-]/g, '').slice(0, 48)
  return safeScope ? `shengyu_island_v5_1_${safeScope}` : ''
}

export function loadIslandState(scope, storage = globalThis.localStorage) {
  const key = islandStorageKey(scope)
  if (!storage || !key) return { position: { ...ISLAND_SPAWN }, lastPlace: 'home' }
  try {
    const parsed = JSON.parse(storage.getItem(key) || '{}')
    const lastPlace = ISLAND_PLACES.some(place => place.id === parsed.lastPlace) ? parsed.lastPlace : 'home'
    return { position: clampIslandPosition(parsed.position), lastPlace }
  } catch {
    return { position: { ...ISLAND_SPAWN }, lastPlace: 'home' }
  }
}

export function saveIslandState(scope, state, storage = globalThis.localStorage) {
  const key = islandStorageKey(scope)
  if (!storage || !key) return
  try {
    storage.setItem(key, JSON.stringify({
      version: 1,
      position: clampIslandPosition(state?.position),
      lastPlace: ISLAND_PLACES.some(place => place.id === state?.lastPlace) ? state.lastPlace : 'home',
    }))
  } catch {
    // Storage can be unavailable in private/restricted contexts; the island stays usable in memory.
  }
}
