const PET_STATE_KEY = 'shengyu_guguan_v5_1_0_alpha_6'

const DEFAULT_PET = {
  bond: 2,
  comfort: 72,
  fullness: 68,
  energy: 76,
  status: 'okay',
  mood: '',
  message: '咕。想靠近时就来坐坐，我不会催你。',
}

const INTERACTION_FIELDS = ['pettedDate', 'fedDate', 'restedDate', 'groomedDate', 'playedDate', 'talkDate', 'taskDate', 'hideDate']

function clamp(value, min, max, fallback) {
  const number = Number(value)
  return Number.isFinite(number) ? Math.min(max, Math.max(min, Math.round(number))) : fallback
}

function localDateKey(date = new Date()) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

export function petStageForBond(bond) {
  if (bond >= 18) return { name: '默契期', startAt: 18, nextAt: 40, copy: '它开始熟悉你照顾彼此的节奏。' }
  if (bond >= 6) return { name: '熟悉期', startAt: 6, nextAt: 18, copy: '一次次轻松互动，会慢慢积累默契。' }
  return { name: '初遇期', startAt: 0, nextAt: 6, copy: '先认识彼此，不需要完成打卡任务。' }
}

// 只读房间写入的宠物状态，用于子页面展示，不修改房间数据。
export function readPetCompanion(userId) {
  let saved = null
  try {
    saved = JSON.parse(localStorage.getItem(`${PET_STATE_KEY}:${userId || 'guest'}`) || 'null')
  } catch {}

  const bond = clamp(saved?.bond ?? (Number(saved?.affinity || 1) * 2), 1, 40, DEFAULT_PET.bond)
  const stage = petStageForBond(bond)
  const today = localDateKey()
  const progress = Math.round(((bond - stage.startAt) / Math.max(1, stage.nextAt - stage.startAt)) * 100)
  const interactedToday = Boolean(saved) && INTERACTION_FIELDS.some(field => saved[field] === today)

  return {
    bond,
    stage: stage.name,
    stageCopy: stage.copy,
    nextAt: stage.nextAt,
    progress: Math.max(0, Math.min(100, progress)),
    checkedInToday: Boolean(saved) && saved.taskDate === today,
    interactedToday,
    status: saved?.status || DEFAULT_PET.status,
    mood: saved?.mood || DEFAULT_PET.mood,
    message: saved?.message || DEFAULT_PET.message,
    comfort: clamp(saved?.comfort, 0, 100, DEFAULT_PET.comfort),
    fullness: clamp(saved?.fullness, 0, 100, DEFAULT_PET.fullness),
    energy: clamp(saved?.energy, 0, 100, DEFAULT_PET.energy),
  }
}

export function petImageForStatus(status = 'idle') {
  const map = {
    idle: '/images/guguan/guguan-idle.webp',
    happy: '/images/guguan/guguan-happy.webp',
    eating: '/images/guguan/guguan-eating.webp',
    sleeping: '/images/guguan/guguan-sleeping.webp',
  }
  return map[status] || map.idle
}
