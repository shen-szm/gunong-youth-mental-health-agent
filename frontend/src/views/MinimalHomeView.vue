<template>
  <div class="m-home">
    <!-- 轻量欢迎遮罩：一次点击进入，同时用于解锁背景音乐 -->
    <Transition name="m-splash">
      <div
        v-if="showSplash"
        class="m-splash"
        role="button"
        tabindex="0"
        aria-label="进入咕哝"
        @click="enterApp"
        @keydown.enter.prevent="enterApp"
        @keydown.space.prevent="enterApp"
      >
        <div class="m-splash-logo">咕哝<span class="m-splash-version">V{{ splashVersion }}</span></div>
        <p class="m-splash-sub">轻触，开始今天的倾诉</p>
        <p class="m-splash-hint">点击任意位置进入</p>
      </div>
    </Transition>

    <div class="m-shell">
      <header class="m-header">
        <div class="m-greeting">
          <small>{{ currentTime }}</small>
          <strong>{{ greeting }}，{{ displayNickname }}</strong>
        </div>
        <button
          type="button"
          class="m-sound"
          :aria-pressed="soundOn"
          :aria-label="soundOn ? '关闭背景音乐' : '开启背景音乐'"
          @click="onToggleSound"
        >
          <svg v-if="soundOn" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5 6 9H3v6h3l5 4V5z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M18.5 5.5a9.5 9.5 0 0 1 0 13"/></svg>
          <svg v-else viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5 6 9H3v6h3l5 4V5z"/><path d="m16 9 6 6"/><path d="m22 9-6 6"/></svg>
        </button>
      </header>

      <main class="m-main">
        <section class="m-today" :class="{ 'has-mood': !!todayMood }">
          <button type="button" class="m-today-btn" @click="showMoodSheet = true">
            <span class="m-today-emoji" aria-hidden="true">{{ todayMood ? moodEmoji(todayMood.label) : '🕊' }}</span>
            <span class="m-today-copy">
              <strong>{{ todayMood ? `今天记录过「${todayMood.label}」` : '今天还没有记录心情' }}</strong>
              <small>{{ todayMood ? '再记一条，或开始一次倾诉' : '花一分钟，留下此刻的感受' }}</small>
            </span>
            <span class="m-today-action">{{ todayMood ? '再记一条' : '记一下' }}</span>
          </button>
        </section>

        <div class="m-entries">
          <button type="button" class="m-entry is-primary" @click="goChat">
            <span class="m-entry-icon" aria-hidden="true">💬</span>
            <strong>倾诉</strong>
            <small>说说现在的感受。不用组织语言，正常聊天不会被分析面板打断。</small>
          </button>
          <button type="button" class="m-entry" @click="showMoodSheet = true">
            <span class="m-entry-icon" aria-hidden="true">📝</span>
            <strong>记录心情</strong>
            <small>选一个最接近的感受，留下此刻的标签。</small>
          </button>
        </div>

        <section class="m-more">
          <button
            type="button"
            class="m-more-toggle"
            :aria-expanded="moreOpen"
            aria-controls="m-more-grid"
            @click="moreOpen = !moreOpen"
          >
            <span>更多</span>
            <svg :class="{ open: moreOpen }" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="m6 9 6 6 6-6"/></svg>
          </button>
          <div v-if="moreOpen" id="m-more-grid" class="m-more-grid">
            <button type="button" @click="goRoom"><span aria-hidden="true">🐾</span>咕团</button>
            <button type="button" @click="openPanel('island')"><span aria-hidden="true">🏝️</span>心岛</button>
            <button type="button" @click="openPanel('music')"><span aria-hidden="true">🎵</span>音乐</button>
            <button type="button" @click="openPanel('treehole')"><span aria-hidden="true">🌳</span>树洞</button>
            <button type="button" @click="goRoom"><span aria-hidden="true">🚋</span>出去看看</button>
          </div>
        </section>
      </main>

      <footer class="m-beian">
        <a href="https://beian.mps.gov.cn/#/query/webSearch?code=44011202003950" target="_blank" rel="noopener noreferrer">
          <img src="/images/beian-icon.png" alt="公安备案" class="m-beian-icon" />
          <span>粤公网安备44011202003950号</span>
        </a>
        <span class="m-beian-divider">|</span>
        <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer" aria-label="前往工信部备案管理系统查询粤ICP备2026048986号-2">粤ICP备2026048986号-2</a>
      </footer>
    </div>

    <!-- 更多面板：心岛 / 音乐 / 树洞 独立挂载 -->
    <Transition name="m-fade">
      <div v-if="activePanel" class="m-overlay" @click.self="activePanel = ''">
        <div class="m-overlay-panel" role="dialog" aria-modal="true" :aria-label="panelLabel">
          <button type="button" class="m-overlay-close" aria-label="关闭" @click="activePanel = ''">×</button>
          <StudentIslandWorkspace
            v-if="activePanel === 'island'"
            :storage-scope="String(userStore.userId || '')"
            @close="activePanel = ''"
            @activity="onIslandActivity"
            @safety="onIslandSafety"
            @open-chat="onIslandOpenChat"
          />
          <MusicListeningShelf v-else-if="activePanel === 'music'" @playing="stopBgm" />
          <TreeHoleView v-else-if="activePanel === 'treehole'" :inline="true" @close="activePanel = ''" @open-chat="onTreeHoleOpenChat" />
          <HealingView v-else-if="activePanel === 'healing'" :inline="true" @close="activePanel = ''" />
        </div>
      </div>
    </Transition>

    <MoodRecordSheet v-if="showMoodSheet" @close="showMoodSheet = false" @saved="onMoodSaved" />
  </div>
</template>

<script setup>
import { ref, computed, defineAsyncComponent, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { getTodayMood } from '../api/mood'
import { createChatSafetyHandoff } from '../api/chat'
import { isBgmMuted, isBgmOn, startBgm, stopBgm, toggleBgm } from '../utils/bgm'
import MoodRecordSheet from '../components/student/MoodRecordSheet.vue'

const StudentIslandWorkspace = defineAsyncComponent(() => import('../components/island/StudentIslandWorkspace.vue'))
const MusicListeningShelf = defineAsyncComponent(() => import('../components/MusicListeningShelf.vue'))
const TreeHoleView = defineAsyncComponent(() => import('./TreeHoleView.vue'))
const HealingView = defineAsyncComponent(() => import('./HealingView.vue'))

const router = useRouter()
const userStore = useUserStore()
const SPLASH_SEEN_KEY = 'shengyu_home_entered'

const splashVersion = (import.meta.env.VITE_APP_VERSION || __APP_PACKAGE_VERSION__ || 'local').split('+')[0]
const showSplash = ref(safeSessionGet(SPLASH_SEEN_KEY) !== '1')
const displayNickname = computed(() => (userStore.nickname || '朋友').replace(/^(?:合成|演示)+|演示$/g, '').trim() || '朋友')

const soundOn = ref(isBgmOn())
function onToggleSound() {
  soundOn.value = toggleBgm()
}

function enterApp() {
  showSplash.value = false
  try { sessionStorage.setItem(SPLASH_SEEN_KEY, '1') } catch {}
  soundOn.value = startBgm()
}

function safeSessionGet(key) {
  try { return sessionStorage.getItem(key) } catch { return null }
}

// ─── 时间与问候 ───
const currentHour = ref(new Date().getHours())
const currentTime = ref('')
let timer = null
function tick() {
  const now = new Date()
  currentHour.value = now.getHours()
  currentTime.value = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}
const greeting = computed(() => {
  const h = currentHour.value
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

// ─── 今日心情 ───
const todayMood = ref(null)
const showMoodSheet = ref(false)
function moodEmoji(label) {
  const map = { '开心': '😊', '平静': '😌', '焦虑': '😰', '难过': '😢', '愤怒': '😡' }
  return map[label] || '🙂'
}
async function refreshTodayMood() {
  try {
    const res = await getTodayMood(Number(userStore.userId))
    todayMood.value = res.data?.label ? { label: res.data.label, score: res.data.score } : null
  } catch {
    todayMood.value = null
  }
}
function onMoodSaved(saved) {
  todayMood.value = { label: saved.label, score: saved.score }
}

// ─── 更多面板 ───
const moreOpen = ref(false)
const activePanel = ref('')
const panelLabel = computed(() => ({
  island: '心岛',
  music: '音乐',
  treehole: '树洞回声',
  healing: '治愈空间',
}[activePanel.value] || '面板'))

function goChat() {
  router.push('/chat')
}

function goRoom() {
  stopBgm()
  soundOn.value = false
  router.push('/room')
}

function openPanel(name) {
  activePanel.value = name
}

// 心岛安全信号：先建立安全交接会话，再进入倾诉页（危机锁由后端会话状态决定）
let islandHandoffFailed = false
let islandHandoffPromise = null
function ensureIslandHandoff() {
  if (!islandHandoffPromise) {
    islandHandoffPromise = createChatSafetyHandoff('happiness_exchange')
      .then(response => response)
      .catch(() => {
        islandHandoffFailed = true
        return null
      })
  }
  return islandHandoffPromise
}
async function onIslandSafety() {
  await ensureIslandHandoff()
}
async function onIslandOpenChat() {
  await ensureIslandHandoff()
  activePanel.value = ''
  router.push(islandHandoffFailed ? { path: '/chat', query: { handoff: 'failed' } } : '/chat')
}
function onIslandActivity(placeId) {
  if (placeId === 'rest') {
    activePanel.value = 'healing'
    return
  }
  if (placeId === 'home') {
    activePanel.value = ''
    goRoom()
  }
}
function onTreeHoleOpenChat() {
  activePanel.value = ''
  router.push('/chat')
}

onMounted(async () => {
  tick()
  timer = setInterval(tick, 30000)
  await refreshTodayMood()
  if (!showSplash.value && !isBgmMuted()) {
    soundOn.value = startBgm()
  }
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.m-home {
  min-height: calc(100dvh - 70px);
  background: var(--m-bg);
  color: var(--m-ink);
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* ─── 欢迎遮罩 ─── */
.m-splash {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: var(--m-bg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.m-splash-logo {
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-size: 40px;
  font-weight: 700;
  letter-spacing: 6px;
  color: var(--m-ink);
}
.m-splash-version {
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0;
  color: var(--m-ink-3);
}
.m-splash-sub {
  margin: 18px 0 0;
  font-size: 15px;
  color: var(--m-ink-2);
}
.m-splash-hint {
  margin: 46px 0 0;
  font-size: 12px;
  color: var(--m-ink-3);
  animation: m-pulse 2.2s ease-in-out infinite;
}
@keyframes m-pulse {
  0%, 100% { opacity: .45; }
  50% { opacity: 1; }
}
@media (prefers-reduced-motion: reduce) {
  .m-splash-hint { animation: none; opacity: .8; }
}
.m-splash-leave-active { transition: opacity 320ms ease; }
.m-splash-leave-to { opacity: 0; }

/* ─── 主体 ─── */
.m-shell {
  width: min(680px, 100% - 32px);
  margin: 0 auto;
  padding: 18px 0 30px;
}

.m-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 2px 18px;
}
.m-greeting { display: flex; flex-direction: column; gap: 2px; }
.m-greeting small { font-size: 12px; color: var(--m-ink-3); }
.m-greeting strong { font-size: 21px; font-weight: 650; }
.m-sound {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--m-surface);
  color: var(--m-ink-2);
  border: 1px solid var(--m-line);
}

.m-main { display: flex; flex-direction: column; gap: 14px; }

/* 今日心情卡 */
.m-today-btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: var(--m-radius-lg);
  background: var(--m-surface);
  border: 1px solid var(--m-line);
  box-shadow: var(--m-shadow);
  text-align: left;
}
.m-today-emoji { font-size: 26px; }
.m-today-copy { display: flex; flex-direction: column; gap: 2px; flex: 1; min-width: 0; }
.m-today-copy strong { font-size: 14.5px; font-weight: 600; color: var(--m-ink); }
.m-today-copy small { font-size: 12px; color: var(--m-ink-3); }
.m-today-action {
  font-size: 12.5px;
  color: var(--m-accent-strong);
  background: var(--m-accent-soft);
  padding: 5px 12px;
  border-radius: 999px;
  white-space: nowrap;
}

/* 两大入口 */
.m-entries {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}
@media (min-width: 640px) {
  .m-entries { grid-template-columns: 1fr 1fr; }
}
.m-entry {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  padding: 20px 18px;
  border-radius: var(--m-radius-lg);
  background: var(--m-surface);
  border: 1px solid var(--m-line);
  box-shadow: var(--m-shadow);
  text-align: left;
  transition: transform 180ms ease, border-color 180ms ease;
}
.m-entry:hover { transform: translateY(-1px); }
.m-entry-icon { font-size: 26px; }
.m-entry strong { font-size: 17px; color: var(--m-ink); }
.m-entry small { font-size: 12.5px; line-height: 1.6; color: var(--m-ink-2); }
.m-entry.is-primary {
  background: var(--m-accent-soft);
  border-color: #CFE3DA;
}
.m-entry.is-primary strong { color: var(--m-accent-strong); }

/* 更多 */
.m-more {
  background: var(--m-surface);
  border: 1px solid var(--m-line);
  border-radius: var(--m-radius-lg);
  box-shadow: var(--m-shadow);
  overflow: hidden;
}
.m-more-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 13px 0;
  background: transparent;
  font-size: 13.5px;
  color: var(--m-ink-2);
}
.m-more-toggle svg { transition: transform 180ms ease; }
.m-more-toggle svg.open { transform: rotate(180deg); }
.m-more-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  padding: 2px 12px 16px;
}
.m-more-grid button {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 10px 2px;
  border-radius: var(--m-radius-md);
  background: var(--m-bg);
  font-size: 12px;
  color: var(--m-ink-2);
}
.m-more-grid button span { font-size: 20px; }

/* 备案 */
.m-beian {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 26px 0 4px;
  font-size: 11.5px;
}
.m-beian a {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--m-ink-3);
  text-decoration: none;
}
.m-beian-icon { width: 14px; height: 14px; }
.m-beian-divider { color: var(--m-line); }

/* 面板 overlay */
.m-overlay {
  position: fixed;
  inset: 0;
  z-index: 210;
  background: rgba(28, 38, 34, .38);
  display: flex;
  align-items: stretch;
  justify-content: center;
  padding: 0;
}
@media (min-width: 768px) {
  .m-overlay { padding: 28px; }
}
.m-overlay-panel {
  position: relative;
  width: 100%;
  max-width: 980px;
  background: var(--m-bg);
  border-radius: 0;
  overflow: auto;
}
@media (min-width: 768px) {
  .m-overlay-panel { border-radius: var(--m-radius-lg); }
}
.m-overlay-close {
  position: absolute;
  top: 10px;
  right: 12px;
  z-index: 3;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: rgba(255, 255, 255, .88);
  color: var(--m-ink-2);
  font-size: 18px;
  line-height: 1;
}
.m-fade-enter-active, .m-fade-leave-active { transition: opacity 200ms ease; }
.m-fade-enter-from, .m-fade-leave-to { opacity: 0; }

/* ─── 电脑端适配：内容加宽并垂直撑满 ─── */
@media (min-width: 768px) {
  .m-home { display: flex; flex-direction: column; }
  .m-shell {
    flex: 1;
    display: flex;
    flex-direction: column;
    width: min(1080px, 100% - 48px);
    padding: 22px 0 14px;
  }
  .m-header { padding: 8px 2px 24px; }
  .m-greeting small { font-size: 13px; }
  .m-greeting strong { font-size: 25px; }
  .m-sound { width: 42px; height: 42px; }
  .m-main { flex: 1; justify-content: center; gap: 16px; }
  .m-today-btn { padding: 18px 24px; gap: 16px; border-radius: 20px; }
  .m-today-emoji { font-size: 30px; }
  .m-today-copy strong { font-size: 16px; }
  .m-today-copy small { font-size: 13px; }
  .m-today-action { font-size: 13px; padding: 7px 16px; }
  .m-entries { gap: 16px; }
  .m-entry {
    min-height: 176px;
    justify-content: center;
    gap: 9px;
    padding: 26px 28px;
    border-radius: 20px;
  }
  .m-entry-icon { font-size: 34px; }
  .m-entry strong { font-size: 21px; }
  .m-entry small { font-size: 14px; }
  .m-more { border-radius: 20px; }
  .m-more-toggle { padding: 17px 0; font-size: 14.5px; }
  .m-more-grid { padding: 4px 16px 20px; gap: 10px; }
  .m-more-grid button { padding: 14px 2px; font-size: 13px; border-radius: 14px; }
  .m-more-grid button span { font-size: 24px; }
  .m-beian { padding: 30px 0 6px; font-size: 12px; }
}
</style>
