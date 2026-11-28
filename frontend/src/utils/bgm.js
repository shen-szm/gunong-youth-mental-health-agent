// 学生端背景音乐单例：跨路由持续播放，必须由用户手势（进入首页的点击）触发启动。
const PLAYLIST = ['/audio/bgm.mp3', '/audio/bgm-song2.mp3', '/audio/bgm-song3.mp3']
const MUTE_KEY = 'shengyu_bgm_muted'
const TARGET_VOLUME = 0.35

let audio = null
let index = 0
let on = false
let fadeTimer = null
const listeners = new Set()

function setOn(value) {
  if (on === value) return
  on = value
  listeners.forEach(listener => {
    try { listener(on) } catch {}
  })
}

export function subscribeBgm(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

function ensureAudio() {
  if (audio) return audio
  audio = new Audio()
  audio.preload = 'auto'
  audio.volume = 0
  audio.addEventListener('ended', () => {
    index = (index + 1) % PLAYLIST.length
    audio.src = PLAYLIST[index]
    if (on && !muted()) {
      audio.play().catch(() => { setOn(false) })
    }
  })
  return audio
}

function muted() {
  try { return localStorage.getItem(MUTE_KEY) === '1' } catch { return false }
}

function setMuted(value) {
  try { value ? localStorage.setItem(MUTE_KEY, '1') : localStorage.removeItem(MUTE_KEY) } catch {}
}

function cancelFade() {
  if (fadeTimer) {
    clearInterval(fadeTimer)
    fadeTimer = null
  }
}

function fadeTo(target) {
  const el = ensureAudio()
  cancelFade()
  const step = target > el.volume ? 0.04 : -0.06
  fadeTimer = setInterval(() => {
    const next = el.volume + step
    if ((step > 0 && next >= target) || (step < 0 && next <= target)) {
      el.volume = Math.max(0, Math.min(1, target))
      cancelFade()
      if (target === 0) el.pause()
      return
    }
    el.volume = Math.max(0, Math.min(1, next))
  }, 60)
}

export function isBgmMuted() {
  return muted()
}

export function isBgmOn() {
  return on
}

// 进入首页的点击手势内调用；用户曾主动静音则不启动。
export async function startBgm() {
  if (muted()) return false
  const el = ensureAudio()
  setOn(true)
  if (!el.getAttribute('src')) el.src = PLAYLIST[index]
  try {
    if (el.paused) await el.play()
  } catch {
    setOn(false)
    return false
  }
  if (!on) return false
  fadeTo(TARGET_VOLUME)
  return true
}

// 声音按钮：在开/关之间切换，并把静音偏好持久化，下次免打扰。
export async function toggleBgm() {
  const el = ensureAudio()
  if (on) {
    setMuted(true)
    setOn(false)
    fadeTo(0)
    return false
  }
  setMuted(false)
  setOn(true)
  if (!el.getAttribute('src')) el.src = PLAYLIST[index]
  try {
    await el.play()
  } catch {
    setOn(false)
    return false
  }
  if (!on) return false
  fadeTo(TARGET_VOLUME)
  return true
}

// 临时停播（如进入旧房间或打开音乐播放器），不写入静音偏好。
export function stopBgm() {
  setOn(false)
  if (!audio) return
  fadeTo(0)
}
