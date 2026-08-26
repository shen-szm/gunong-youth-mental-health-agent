import { createGardenBoard, normalizeGardenBoard } from './gardenMergeEngine.js'

export const HAPPINESS_RETENTION_MS = 30 * 24 * 60 * 60 * 1000

export const FISH_TYPES = Object.freeze([
  { id: 'silver', label: '银尾小鱼', rarity: '常见' },
  { id: 'square', label: '方鳍鱼', rarity: '少见' },
  { id: 'moon', label: '月光鱼', rarity: '稀有' },
])

export const HAPPINESS_CARDS = Object.freeze([
  '热牛奶上浮着一层细细的奶泡。',
  '公交车到站时，雨刚好变小了。',
  '写完最后一道题，窗外还有晚霞。',
  '朋友记得我随口提过的一首歌。',
  '晒过太阳的被子有很好闻的味道。',
  '回家时，一小片云在路上陪了我很久。',
])

export function activityStorageKey(scope) {
  const safeScope = String(scope || '').trim()
  return /^\d+$/.test(safeScope) ? `shengyu_island_activities_v5_1_${safeScope}` : ''
}

export function createActivityState() {
  return {
    garden: { board: createGardenBoard(), previous: null, score: 0, harvests: 0, moves: 0 },
    fishing: { catches: 0, fishBook: Object.fromEntries(FISH_TYPES.map(fish => [fish.id, 0])) },
    happiness: { exchanges: 0, notes: [], cardIndex: 0 },
    reflection: '',
  }
}

export function normalizeActivityState(saved = {}, now = Date.now()) {
  const base = createActivityState()
  const legacyUpdatedAt = Math.max(0, Number(saved.happiness?.updatedAt) || 0)
  const notes = Array.isArray(saved.happiness?.notes) ? saved.happiness.notes : []
  const currentNotes = notes.flatMap(note => {
    const text = typeof note === 'string' ? note : note?.text
    const createdAt = typeof note === 'string' ? legacyUpdatedAt : Math.max(0, Number(note?.createdAt) || 0)
    if (typeof text !== 'string' || !createdAt || now - createdAt >= HAPPINESS_RETENTION_MS) return []
    const cleaned = text.trim().slice(0, 80)
    return cleaned ? [{ text: cleaned, createdAt }] : []
  }).slice(-12)
  return {
    garden: {
      board: normalizeGardenBoard(saved.garden?.board),
      previous: Array.isArray(saved.garden?.previous) ? normalizeGardenBoard(saved.garden.previous) : null,
      score: Math.max(0, Number(saved.garden?.score) || 0),
      harvests: Math.max(0, Number(saved.garden?.harvests) || 0),
      moves: Math.max(0, Number(saved.garden?.moves) || 0),
    },
    fishing: {
      catches: Math.max(0, Number(saved.fishing?.catches) || 0),
      fishBook: Object.fromEntries(FISH_TYPES.map(fish => [fish.id, Math.max(0, Number(saved.fishing?.fishBook?.[fish.id]) || 0)])),
    },
    happiness: {
      exchanges: Math.max(0, Number(saved.happiness?.exchanges) || 0),
      notes: currentNotes,
      cardIndex: Math.max(0, Number(saved.happiness?.cardIndex) || 0) % HAPPINESS_CARDS.length,
    },
    reflection: ['lighter', 'same', 'switch'].includes(saved.reflection) ? saved.reflection : '',
  }
}

export function loadActivityState(scope, storage = globalThis.localStorage) {
  const key = activityStorageKey(scope)
  if (!storage || !key) return createActivityState()
  try {
    const raw = storage.getItem(key)
    if (!raw) return createActivityState()
    const parsed = JSON.parse(raw)
    const normalized = normalizeActivityState(parsed)
    if (parsed.happiness?.notes?.length !== normalized.happiness.notes.length
        || parsed.happiness?.notes?.some(note => typeof note === 'string')) {
      try { storage.setItem(key, JSON.stringify({ version: 1, ...normalized })) } catch { /* UI still withholds expired text */ }
    }
    return normalized
  } catch {
    return createActivityState()
  }
}

export function saveActivityState(scope, state, storage = globalThis.localStorage) {
  const key = activityStorageKey(scope)
  if (!storage || !key) return false
  try {
    storage.setItem(key, JSON.stringify({ version: 1, ...normalizeActivityState(state) }))
    return true
  } catch {
    return false
  }
}
