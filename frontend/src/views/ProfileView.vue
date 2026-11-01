<template>
  <div class="profile-page game-page" :data-part="part">
    <GameBackdrop :part="part" variant="page" />
    <!-- 顶部背景 + 头像 -->
    <div class="profile-hero">
      <div class="hero-bg">
        <img class="hero-art" :src="heroScene" alt="" />
      </div>
      <router-link class="profile-room-link" to="/">‹ 回首页</router-link>
      <div class="hero-content">
        <div class="avatar">
          <span>{{ (userStore.nickname || '你')[0] }}</span>
        </div>
        <h3>{{ userStore.nickname || '未设置昵称' }}</h3>
        <p class="uid">ID {{ userStore.userId }}</p>
        <span v-if="userStore.isAdmin" class="admin-badge">教师</span>
      </div>
    </div>

    <!-- 数据统计 -->
    <div class="stats-row">
      <button type="button" class="stat-item" @click="router.push('/trend')">
        <div class="stat-val">{{ stats.moodCount }}</div>
        <div class="stat-lbl">情绪记录</div>
      </button>
      <div class="stat-divider"></div>
      <button type="button" class="stat-item" @click="router.push('/chat')">
        <div class="stat-val">{{ stats.chatCount }}</div>
        <div class="stat-lbl">倾诉次数</div>
      </button>
      <div class="stat-divider"></div>
      <button type="button" class="stat-item" @click="router.push('/trend')">
        <div class="stat-val">{{ stats.days }}</div>
        <div class="stat-lbl">记录天数</div>
      </button>
    </div>

    <div class="profile-body">
      <div class="profile-col">
        <!-- 咕团羁绊 -->
        <div class="section pet-bond-section">
          <div class="section-title">我的咕团</div>
          <router-link class="pet-bond-card game-card" to="/">
            <div class="pet-bond-avatar"><img :src="petAvatar" alt="咕团" /></div>
            <div class="pet-bond-copy">
              <div class="pet-bond-head">
                <strong>咕团 · {{ petState.stage }}</strong>
                <span class="game-pill">默契 {{ petState.bond }}</span>
              </div>
              <p>{{ petState.stageCopy }}</p>
              <div class="pet-bond-track"><div :style="{ width: petState.progress + '%' }"></div></div>
              <small>{{ petState.checkedInToday ? '今天已经一起完成签到' : petState.interactedToday ? '今天已经互动过了，回首页还能再坐一会儿' : '回首页摸摸它，默契会慢慢长起来' }}</small>
            </div>
            <span class="pet-bond-arrow" aria-hidden="true">›</span>
          </router-link>
        </div>

        <!-- 快速心情记录 -->
        <div class="section">
          <div class="section-title">今天的心情</div>
          <div class="menu-card mood-entry-card">
            <div class="mood-entry-copy">
              <span class="mood-entry-emoji" aria-hidden="true">{{ todayMood ? getEmoji(todayMood.label) : '🕊' }}</span>
              <div>
                <strong>{{ todayMood ? `今天记录过「${todayMood.label}」` : '今天还没有记录心情' }}</strong>
                <small>{{ todayMood ? '再记一条，也可以回首页和咕团说说。' : '花一分钟，留下此刻的感受。' }}</small>
              </div>
            </div>
            <button type="button" class="save-btn" @click="showMoodSheet = true">{{ todayMood ? '再记一条' : '记一下' }}</button>
          </div>
        </div>

        <!-- 今日状态 -->
        <div class="section">
          <div class="section-title">今天的状态</div>
          <div class="menu-card status-card">
            <div class="status-chips" role="group" aria-label="选择今天的状态">
              <button v-for="s in statusOptions" :key="s" type="button" :aria-pressed="todayStatus === s" :class="{ active: todayStatus === s }" @click="pickStatus(s)">{{ s }}</button>
            </div>
            <p class="status-hint">只是给今天留一个注脚，不是心理测评。</p>
          </div>
        </div>

        <!-- 近14天情绪日历 -->
        <div class="section">
          <div class="section-title">近14天情绪日历</div>
          <div class="menu-card">
            <div class="mini-calendar">
              <div v-for="day in miniCalendar" :key="day.date" class="mini-cell" :class="{ 'has-mood': !!day.mood }">
                <span>{{ day.label }}</span>
                <em aria-hidden="true">{{ day.mood ? getEmoji(day.mood) : '' }}</em>
              </div>
            </div>
          </div>
        </div>

        <!-- 情绪分布 -->
        <div class="section" v-if="Object.keys(distribution).length">
          <div class="section-title">情绪分布</div>
          <div class="mood-dist">
            <div class="dist-row" v-for="(count, label) in distribution" :key="label">
              <span class="dist-emoji">{{ getEmoji(label) }}</span>
              <span class="dist-label">{{ label }}</span>
              <div class="dist-track">
                <div class="dist-fill" :style="{ width: getPercent(count)+'%' }"></div>
              </div>
              <span class="dist-pct">{{ getPercent(count) }}%</span>
            </div>
          </div>
        </div>

        <!-- 设置 -->
        <div class="section">
          <div class="section-title">个人设置</div>
          <div class="menu-card">
            <div class="setting-row">
              <span class="setting-icon">✏️</span>
              <span class="setting-label">昵称</span>
              <input class="setting-input" v-model="nickname" placeholder="输入昵称" />
              <button class="save-btn" @click="saveNickname">保存</button>
            </div>
          </div>
        </div>

      </div>

      <div class="profile-col">
        <!-- 成就徽章 -->
        <div class="section">
          <div class="section-title">成就</div>
          <div class="badges">
            <div v-for="b in badges" :key="b.name" :class="['badge', { unlocked: b.unlocked }]">
              <div class="badge-icon">{{ b.icon }}</div>
              <div class="badge-name">{{ b.name }}</div>
              <div class="badge-desc">{{ b.desc }}</div>
              <div v-if="b.unlocked" class="badge-check">✓</div>
            </div>
          </div>
        </div>

        <!-- 账号管理 -->
        <div class="section">
          <div class="section-title">账号管理</div>
          <div class="menu-card">
            <div class="setting-row">
              <span class="setting-icon">🔑</span>
              <span class="setting-label">修改密码</span>
              <button class="save-btn" @click="openPwdModal">修改</button>
            </div>
          </div>
        </div>

        <!-- 更多空间 -->
        <div class="section">
          <div class="section-title">更多空间</div>
          <div class="menu-card">
            <button type="button" class="menu-row" @click="openTreehole">
              <span class="setting-icon">🌳</span>
              <span>树洞回声</span>
              <span class="arrow">›</span>
            </button>
            <button type="button" class="menu-row" @click="router.push('/trend')">
              <span class="setting-icon">📊</span>
              <span>情绪报告</span>
              <span class="arrow">›</span>
            </button>
          </div>
        </div>

        <!-- 管理员入口 -->
        <div class="section" v-if="userStore.isAdmin">
          <div class="section-title">系统</div>
          <div class="menu-card">
            <button type="button" class="menu-row" @click="router.push('/admin')">
              <span class="setting-icon">⚙️</span>
              <span>教师端</span>
              <span class="arrow">›</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 树洞回声 -->
    <div v-if="showTreehole" class="treehole-overlay" @click.self="closeTreehole">
      <div ref="treeholePanel" class="treehole-panel" role="dialog" aria-modal="true" aria-label="树洞回声" tabindex="-1">
        <button type="button" class="treehole-close" aria-label="关闭树洞" @click="closeTreehole">×</button>
        <div class="treehole-scroll">
          <TreeHoleView :inline="true" @close="closeTreehole" @open-chat="openChatFromTreehole" />
        </div>
      </div>
    </div>

    <!-- 修改密码弹窗 -->
    <div class="modal-overlay" v-if="showPwdModal" @click.self="closePwdModal">
      <div ref="pwdModalCard" class="modal-card" role="dialog" aria-modal="true" aria-labelledby="pwd-modal-title" tabindex="-1">
        <h4 id="pwd-modal-title">修改密码</h4>
        <input ref="oldPwdInput" class="modal-input" v-model="oldPwd" type="password" placeholder="请输入旧密码" aria-label="旧密码" />
        <input class="modal-input" v-model="newPwd1" type="password" placeholder="请输入新密码（至少10位）" aria-label="新密码" />
        <input class="modal-input" v-model="newPwd2" type="password" placeholder="请再次输入新密码" aria-label="再次输入新密码" />
        <div class="modal-btns">
          <button class="modal-cancel" @click="closePwdModal">取消</button>
          <button class="modal-confirm" @click="handleChangePwd">确认修改</button>
        </div>
        <p v-if="pwdMsg" :class="['pwd-msg', pwdOk ? 'success' : 'error']">{{ pwdMsg }}</p>
      </div>
    </div>

    <MoodRecordSheet v-if="showMoodSheet" @close="showMoodSheet = false" @saved="onMoodSaved" />

    <button class="logout-btn" @click="handleLogout">退出登录</button>
  </div>
</template>

<script setup>
import { ref, reactive, computed, defineAsyncComponent, nextTick, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { updateProfile } from '../api/user'
import { changePassword } from '../api/user'
import { getMoodStats, getTodayMood } from '../api/mood'
import { getChatSessionCount } from '../api/chat'
import { activateDialog } from '../utils/dialogFocus'
import { useTimeOfDay } from '../utils/timeOfDay'
import { petImageForStatus, readPetCompanion } from '../utils/petCompanion'
import MoodRecordSheet from '../components/student/MoodRecordSheet.vue'
import GameBackdrop from '../components/student/GameBackdrop.vue'
import homeDay from '../assets/island/home-day.png'
import homeDusk from '../assets/island/home-dusk.png'
import homeNight from '../assets/island/home-night.png'

const TreeHoleView = defineAsyncComponent(() => import('./TreeHoleView.vue'))

const router = useRouter()
const userStore = useUserStore()
const part = useTimeOfDay()
const heroScene = computed(() => part.value === 'evening' ? homeDusk : part.value === 'night' ? homeNight : homeDay)
const petState = computed(() => readPetCompanion(userStore.userId))
const petAvatar = computed(() => petImageForStatus(part.value === 'night' && petState.value.status !== 'happy' ? 'sleeping' : petState.value.status))
const todayMood = ref(null)
const showMoodSheet = ref(false)

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
  loadStats()
}
const nickname = ref(userStore.nickname || '')
const stats = reactive({ moodCount: 0, chatCount: 0, days: 0 })
const distribution = ref({})
const totalMoodCount = computed(() => Object.values(distribution.value).reduce((a, b) => a + b, 0))

const badges = computed(() => [
  { icon: '🌱', name: '初次倾诉', desc: '开始第一次倾诉', unlocked: stats.chatCount >= 1 },
  { icon: '📝', name: '记录者', desc: '记录5次情绪', unlocked: stats.moodCount >= 5 },
  { icon: '💪', name: '坚持一周', desc: '记录心情满7天', unlocked: stats.days >= 7 },
  { icon: '🌟', name: '倾诉达人', desc: '倾诉满20次', unlocked: stats.chatCount >= 20 },
  { icon: '🎯', name: '情绪大师', desc: '50次情绪记录', unlocked: stats.moodCount >= 50 },
  { icon: '💎', name: '忠实用户', desc: '记录心情满30天', unlocked: stats.days >= 30 },
])

function getEmoji(label) {
  const map = {
    '愤怒': '😠', '厌恶': '🤢', '恐惧': '😨', '开心': '😊', '中性': '😐', '悲伤': '😢', '惊讶': '😲',
    '平静': '😌', '焦虑': '😰', '难过': '😢',
  }
  return map[label] || '🙂'
}

function getPercent(count) {
  return totalMoodCount.value ? Math.round(count / totalMoodCount.value * 100) : 0
}

// ─── 今日状态（本地注脚，不做测评） ───
const statusOptions = ['很累', '有点烦', '还可以', '轻松', '开心']
const todayStatus = ref('')
function statusStorageKey() {
  return `shengyu_student_status_${userStore.userId || 'guest'}`
}
function localDateKey() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
function loadTodayStatus() {
  try {
    const saved = JSON.parse(localStorage.getItem(statusStorageKey()) || 'null')
    if (saved && saved.date === localDateKey()) todayStatus.value = saved.label
  } catch {}
}
function pickStatus(label) {
  todayStatus.value = todayStatus.value === label ? '' : label
  try {
    if (todayStatus.value) {
      localStorage.setItem(statusStorageKey(), JSON.stringify({ label: todayStatus.value, date: localDateKey() }))
    } else {
      localStorage.removeItem(statusStorageKey())
    }
  } catch {}
}

// ─── 近14天迷你日历 ───
const trendDays = ref([])
const miniCalendar = computed(() => {
  const byDate = {}
  for (const day of trendDays.value) {
    if (day.labels?.length) byDate[day.date] = day.labels[0]
  }
  const days = []
  const now = new Date()
  for (let i = 13; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(now.getDate() - i)
    const key = `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    days.push({ label: d.getDate(), date: key, mood: byDate[key] || '' })
  }
  return days
})

async function loadStats() {
  const uid = Number(userStore.userId)
  try {
    const moodRes = await getMoodStats(uid, 999)
    stats.moodCount = moodRes.data.count || 0
    distribution.value = moodRes.data.distribution || {}
    trendDays.value = moodRes.data.trend || []
    stats.days = trendDays.value.length
  } catch {}
  try {
    const chatRes = await getChatSessionCount()
    stats.chatCount = chatRes.data?.count || 0
  } catch {}
}

async function saveNickname() {
  if (!nickname.value.trim()) { alert('昵称不能为空'); return }
  try {
    await updateProfile(Number(userStore.userId), nickname.value, '')
    userStore.login(userStore.userId, nickname.value, userStore.isAdmin)
    alert('保存成功')
  } catch { alert('保存失败') }
}

async function handleLogout() {
  if (!confirm('确定要退出登录吗？')) return
  const wasTeacher = userStore.isAdmin
  await userStore.logout()
  if (wasTeacher) {
    router.push('/teacher-login')
    return
  }
  try {
    await userStore.ensureStudentSession()
  } catch {
    router.push('/teacher-login')
  }
}

// 树洞回声
const showTreehole = ref(false)
const treeholePanel = ref(null)
let releaseTreeholeDialog = null

watch(showTreehole, async open => {
  if (open) {
    await nextTick()
    releaseTreeholeDialog = activateDialog(treeholePanel.value, { onClose: closeTreehole })
  } else {
    releaseTreeholeDialog?.()
    releaseTreeholeDialog = null
  }
})

function openTreehole() {
  showTreehole.value = true
}
function closeTreehole() {
  showTreehole.value = false
}
function openChatFromTreehole() {
  closeTreehole()
  router.push('/chat')
}

// 修改密码
const showPwdModal = ref(false)
const pwdModalCard = ref(null)
const oldPwdInput = ref(null)
let releasePwdDialog = null
const oldPwd = ref('')
const newPwd1 = ref('')
const newPwd2 = ref('')
const pwdMsg = ref('')
const pwdOk = ref(false)

watch(showPwdModal, async open => {
  if (open) {
    await nextTick()
    releasePwdDialog = activateDialog(pwdModalCard.value, { onClose: closePwdModal, initialFocus: () => oldPwdInput.value })
  } else {
    releasePwdDialog?.()
    releasePwdDialog = null
  }
})

function openPwdModal() {
  pwdMsg.value = ''
  pwdOk.value = false
  oldPwd.value = ''
  newPwd1.value = ''
  newPwd2.value = ''
  showPwdModal.value = true
}
function closePwdModal() {
  showPwdModal.value = false
}

async function handleChangePwd() {
  pwdMsg.value = ''
  if (!oldPwd.value) { pwdMsg.value = '请输入旧密码'; return }
  if (!newPwd1.value.trim()) { pwdMsg.value = '请输入新密码'; return }
  if (newPwd1.value !== newPwd2.value) { pwdMsg.value = '两次输入的新密码不一致'; return }
  if (newPwd1.value.length < 10) { pwdMsg.value = '新密码至少10位'; return }
  try {
    await changePassword(Number(userStore.userId), oldPwd.value, newPwd1.value, newPwd2.value)
    pwdOk.value = true
    pwdMsg.value = '密码修改成功！'
    oldPwd.value = ''; newPwd1.value = ''; newPwd2.value = ''
    setTimeout(() => { closePwdModal(); pwdMsg.value = ''; pwdOk.value = false }, 1500)
  } catch (e) {
    pwdOk.value = false
    pwdMsg.value = e.response?.data?.detail || '修改失败'
  }
}

onMounted(() => { loadStats(); loadTodayStatus(); refreshTodayMood() })

onBeforeUnmount(() => {
  releaseTreeholeDialog?.()
  releasePwdDialog?.()
})
</script>

<style scoped>
.profile-page {
  background: transparent; min-height: 100vh; padding-bottom: 40px;
  position: relative;
  color: var(--game-ink);
  font-family: 'PingFang SC','Microsoft YaHei',sans-serif;
}
.profile-hero, .stats-row, .profile-body, .logout-btn { position: relative; z-index: 1; }

/* 顶部英雄区：直接使用房间的昼夜场景图 */
.profile-hero {
  position: relative; padding-bottom: 28px;
  animation: m-fadein 400ms var(--m-ease-soft) backwards;
}
.hero-bg {
  position: absolute; inset: 0; height: 186px;
  background: linear-gradient(160deg, #6b4e37 0%, #4f3a2a 52%, #33261c 100%);
  border-radius: 0 0 32px 32px;
  overflow: hidden;
}
.hero-art {
  width: 100%; height: 100%; object-fit: cover; object-position: center 62%;
  opacity: .62; filter: saturate(.92);
}
.hero-bg::after {
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(180deg, rgba(24, 17, 12, .12) 0%, rgba(24, 17, 12, .52) 100%);
}
.profile-room-link {
  position: absolute; top: 14px; left: 16px; z-index: 3;
  display: inline-flex; align-items: center;
  padding: 5px 12px; border-radius: 999px;
  background: rgba(24, 17, 12, .34);
  border: 1px solid rgba(240, 216, 170, .28);
  color: #f6ebd7; font-size: 12px; font-weight: 600;
  text-decoration: none;
  transition: background var(--m-dur-fast) var(--m-ease), transform var(--m-dur-fast) var(--m-ease);
}
.profile-room-link:hover { background: rgba(24, 17, 12, .5); }
.profile-room-link:active { transform: scale(.95); }
.hero-content {
  position: relative; z-index: 1;
  display: flex; flex-direction: column; align-items: center;
  padding-top: 28px;
}
.avatar {
  width: 72px; height: 72px; border-radius: 50%;
  background: #fdf6e8;
  border: 2px solid #e3c27d;
  box-shadow: 0 4px 16px rgba(0,0,0,0.24), inset 0 0 0 4px rgba(107, 78, 55, .09);
  display: flex; align-items: center; justify-content: center;
  font-size: 30px; font-weight: bold; color: #6b4e37;
  margin-bottom: 10px;
}
.hero-content h3 { color: white; font-size: 18px; margin: 0; text-shadow: 0 1px 4px rgba(0,0,0,0.15); }
.uid { color: #FFFFFF; font-size: 12px; margin: 4px 0 0; }
.admin-badge {
  margin-top: 6px; background: rgba(20, 40, 34, 0.35); color: white;
  font-size: 11px; padding: 2px 10px; border-radius: 10px;
}

/* 数据统计 */
.stats-row {
  background: var(--game-surface); margin: 0 16px 14px; border-radius: 16px;
  border: 1px solid var(--game-line);
  box-shadow: var(--game-shadow-soft);
  display: flex; align-items: center; padding: 16px 0;
  backdrop-filter: none;
}
.stat-item {
  flex: 1; text-align: center; cursor: pointer;
  padding: 0; border: 0; background: transparent;
  font-family: inherit;
  transition: transform var(--m-dur-fast) var(--m-ease);
}
.stat-item:hover { transform: scale(1.05); }
.stat-item:active { transform: scale(.97); }
.stat-val { font-size: 24px; font-weight: 700; color: var(--game-wood); }
.stat-lbl { font-size: 11px; color: var(--game-ink-3); margin-top: 3px; }
.stat-divider { width: 1px; height: 36px; background: var(--game-line); }

/* 通用 section */
.section { margin: 0 16px 14px; }
.section-title {
  font-size: 12px; color: var(--game-ink-3); font-weight: 500;
  letter-spacing: 1px; text-transform: uppercase;
  margin-bottom: 8px; padding-left: 4px;
}

/* 咕团羁绊卡：和房间共用同一只咕团状态 */
.pet-bond-card {
  display: flex; align-items: center; gap: 14px;
  padding: 14px 16px;
  color: var(--game-ink);
  text-decoration: none;
  transition: transform var(--m-dur-fast) var(--m-ease), box-shadow var(--m-dur) var(--m-ease);
}
.pet-bond-card:hover { transform: translateY(-1px); box-shadow: var(--game-shadow); }
.pet-bond-card:active { transform: scale(.985); }
.pet-bond-avatar {
  flex-shrink: 0; width: 58px; height: 58px; border-radius: 50%;
  display: grid; place-items: center;
  background: var(--game-gold-soft);
  border: 1.5px solid var(--game-line-strong);
  overflow: hidden;
}
.pet-bond-avatar img { width: 48px; height: 48px; object-fit: contain; }
.pet-bond-copy { flex: 1; min-width: 0; }
.pet-bond-head { display: flex; align-items: center; gap: 8px; margin-bottom: 3px; }
.pet-bond-head strong { font-size: 14px; color: var(--game-ink); }
.pet-bond-copy p { margin: 0 0 7px; font-size: 12px; color: var(--game-ink-2); }
.pet-bond-track {
  height: 6px; border-radius: 999px; overflow: hidden;
  background: var(--game-accent-soft);
}
.pet-bond-track > div {
  height: 100%; border-radius: 999px;
  background: linear-gradient(90deg, var(--game-wood-soft), var(--game-gold));
  transition: width .6s var(--m-ease-soft);
}
.pet-bond-copy small { display: block; margin-top: 6px; font-size: 11px; color: var(--game-ink-3); }
.pet-bond-arrow { color: var(--game-ink-3); font-size: 20px; }

/* 快速心情记录 */
.mood-entry-card {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 16px;
}
.mood-entry-copy { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
.mood-entry-emoji { font-size: 24px; flex-shrink: 0; }
.mood-entry-copy strong { display: block; font-size: 13px; color: var(--game-ink); }
.mood-entry-copy small { display: block; margin-top: 2px; font-size: 11px; color: var(--game-ink-3); }

/* v5.1.0-alpha.41 入场错峰（hero 只淡入：hero-bg 大圆角绝对定位，位移会露缝） */
.stats-row, .profile-col .section {
  animation: m-rise var(--m-enter-dur) var(--m-ease) backwards;
}
.stats-row { animation-delay: 40ms; }
.profile-col .section:nth-child(1) { animation-delay: 80ms; }
.profile-col .section:nth-child(2) { animation-delay: 140ms; }
.profile-col .section:nth-child(3) { animation-delay: 200ms; }
.profile-col .section:nth-child(4) { animation-delay: 260ms; }
.profile-col .section:nth-child(5) { animation-delay: 320ms; }
.profile-col .section:nth-child(6) { animation-delay: 380ms; }
.profile-col .section:nth-child(7) { animation-delay: 440ms; }

/* 今日状态 */
.status-card { padding: 14px 16px; }
.status-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.status-chips button {
  padding: 7px 14px; border-radius: 999px; font-size: 13px;
  background: var(--m-bg); color: var(--m-ink-2);
  border: 1.5px solid transparent; transition: all var(--m-dur-fast) var(--m-ease);
}
.status-chips button:not(.active):hover { border-color: var(--game-line-strong); }
.status-chips button:active { transform: scale(.94); }
.status-chips button.active {
  background: var(--m-accent-soft); color: var(--m-accent-strong);
  border-color: var(--m-accent); font-weight: 600;
}
.status-hint { margin: 10px 0 0; font-size: 11.5px; color: var(--m-ink-3); }

/* 迷你日历 */
.mini-calendar { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; padding: 14px; }
.mini-cell {
  display: flex; flex-direction: column; align-items: center; gap: 1px;
  padding: 6px 0; border-radius: var(--m-radius-sm);
  background: var(--m-bg); color: var(--m-ink-3); font-size: 11px;
}
.mini-cell.has-mood { background: var(--m-accent-soft); color: var(--m-ink-2); }
.mini-cell em { font-style: normal; font-size: 14px; line-height: 1.2; min-height: 17px; }

/* 情绪分布 */
.mood-dist {
  background: var(--game-surface); border-radius: 16px; padding: 14px;
  border: 1px solid var(--game-line);
  box-shadow: var(--game-shadow-soft);
  display: flex; flex-direction: column; gap: 10px;
}
.dist-row { display: flex; align-items: center; gap: 8px; }
.dist-emoji { font-size: 16px; width: 22px; text-align: center; }
.dist-label { width: 36px; font-size: 13px; color: var(--game-ink-2); flex-shrink: 0; }
.dist-track { flex: 1; height: 7px; background: var(--game-accent-soft); border-radius: 4px; overflow: hidden; }
.dist-fill { height: 100%; border-radius: 4px; background: linear-gradient(90deg, var(--game-accent), var(--game-gold)); transition: width 0.8s ease; }
.dist-pct { width: 34px; font-size: 11px; color: var(--game-ink-3); text-align: right; }

/* 成就徽章 */
.badges {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;
}
.badge {
  background: var(--game-surface); border-radius: 14px; padding: 14px 8px 12px;
  border: 1px solid var(--game-line);
  text-align: center; box-shadow: var(--game-shadow-soft);
  opacity: 0.35; filter: grayscale(.6);
  transition: all 0.3s; position: relative;
}
.badge.unlocked {
  opacity: 1; filter: none;
  border-color: var(--game-gold);
  box-shadow: 0 3px 14px var(--game-gold-soft);
}
.badge-icon { font-size: 26px; margin-bottom: 4px; }
.badge-name { font-size: 12px; font-weight: 600; color: var(--game-ink); }
.badge-desc { font-size: 10px; color: var(--game-ink-3); margin-top: 2px; }
.badge-check {
  position: absolute; top: 6px; right: 8px;
  font-size: 10px; color: var(--game-gold); font-weight: 700;
}

/* 设置/菜单卡片 */
.menu-card {
  background: var(--game-surface); border-radius: 16px;
  border: 1px solid var(--game-line);
  box-shadow: var(--game-shadow-soft); overflow: hidden;
}
.setting-row {
  display: flex; align-items: center; gap: 10px; padding: 14px 16px;
}
.setting-icon { font-size: 16px; }
.setting-label { font-size: 14px; color: var(--game-ink-2); flex-shrink: 0; }
.setting-input {
  flex: 1; padding: 6px 10px; border: 1.5px solid var(--game-line-strong);
  border-radius: 8px; font-size: 13px; outline: none;
  background: transparent; color: var(--game-ink);
  transition: border-color 0.2s;
}
.setting-input::placeholder { color: var(--game-ink-3); }
.setting-input:focus { border-color: var(--game-accent); }
.save-btn {
  padding: 6px 14px; background: var(--m-accent); color: white;
  border-radius: 8px; font-size: 12px; white-space: nowrap;
  transition: background var(--m-dur-fast) var(--m-ease),
              transform var(--m-dur-fast) var(--m-ease);
}
.save-btn:hover { background: var(--m-accent-strong); }
.save-btn:active { transform: scale(.96); }

.menu-row {
  display: flex; align-items: center; gap: 10px; padding: 14px 16px;
  width: 100%; border: 0; background: transparent; text-align: left;
  cursor: pointer; font-family: inherit; font-size: 14px; color: var(--game-ink-2);
  transition: background var(--m-dur-fast) var(--m-ease);
}
.menu-row:hover { background: var(--game-accent-soft); }
.menu-row:active { background: var(--game-gold-soft); }
.arrow { margin-left: auto; font-size: 18px; color: var(--game-ink-3); }

/* 退出按钮 */
.logout-btn {
  display: block; width: calc(100% - 32px); margin: 8px 16px 0;
  padding: 13px; border-radius: 14px; text-align: center;
  font-size: 14px; color: var(--game-danger);
  background: var(--game-surface); border: 1.5px solid var(--game-line);
  box-shadow: var(--game-shadow-soft);
  transition: all 0.2s;
}
.logout-btn:hover { background: var(--game-gold-soft); border-color: var(--game-danger); }
.logout-btn:active { transform: scale(.98); }

/* 树洞回声：inline 皮肤按深色底设计，这里整套沿用深色面板 */
.treehole-overlay {
  position: fixed; inset: 0; z-index: 230;
  background: rgba(20, 20, 25, .55);
  display: flex; align-items: stretch; justify-content: center;
}
.treehole-panel {
  position: relative;
  width: 100%; max-width: 980px; height: 100%;
  display: flex; flex-direction: column;
  background: #141419;
  overflow: hidden;
}
.treehole-scroll { flex: 1; min-height: 0; overflow: auto; }
.treehole-close {
  position: absolute; top: 10px; right: 12px; z-index: 3;
  width: 34px; height: 34px; border-radius: 50%;
  background: rgba(255,255,255,.9); color: #3A3530;
  font-size: 18px; line-height: 1;
}
@media (min-width: 768px) {
  .treehole-overlay { padding: 28px; }
  .treehole-panel { border-radius: var(--m-radius-lg); }
}

/* 修改密码弹窗 */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.45);
  display: flex; align-items: center; justify-content: center;
  z-index: 300;
}
.modal-card {
  background: var(--game-surface-solid); border-radius: 20px; padding: 28px 24px 20px;
  width: 300px; border: 1px solid var(--game-line);
  box-shadow: 0 18px 48px rgba(0,0,0,0.28);
}
.modal-card h4 { margin: 0 0 18px; font-size: 18px; color: var(--game-ink); text-align: center; }
.modal-input {
  width: 100%; padding: 10px 14px; border: 1.5px solid var(--game-line-strong);
  border-radius: 10px; font-size: 14px; outline: none; margin-bottom: 12px;
  box-sizing: border-box; transition: border-color 0.2s;
  background: transparent; color: var(--game-ink);
}
.modal-input::placeholder { color: var(--game-ink-3); }
.modal-input:focus { border-color: var(--game-accent); }
.modal-btns { display: flex; gap: 10px; margin-top: 4px; }
.modal-cancel {
  flex: 1; padding: 10px; border-radius: 10px; font-size: 14px;
  background: var(--game-gold-soft); color: var(--game-ink-2); text-align: center;
  transition: background var(--m-dur-fast) var(--m-ease),
              transform var(--m-dur-fast) var(--m-ease);
}
.modal-cancel:hover { background: var(--game-accent-soft); }
.modal-cancel:active { transform: scale(.97); }
.modal-confirm {
  flex: 1; padding: 10px; border-radius: 10px; font-size: 14px;
  background: var(--m-accent); color: white; text-align: center;
  transition: background var(--m-dur-fast) var(--m-ease),
              transform var(--m-dur-fast) var(--m-ease);
}
.modal-confirm:hover { background: var(--m-accent-strong); }
.modal-confirm:active { transform: scale(.97); }
.pwd-msg { text-align: center; margin: 12px 0 0; font-size: 13px; }
.pwd-msg.success { color: var(--m-accent-strong); }
.pwd-msg.error { color: var(--m-danger); }

/* 手机端：分栏容器退化为普通流，顺序不变 */
@media (max-width: 767px) {
  .profile-col { display: contents; }
}

/* ═══════════ 电脑端适配：1080 双栏 ═══════════ */
@media (min-width: 768px) {
  .profile-page { max-width: 1080px; margin: 0 auto; padding-bottom: 64px; }
  .profile-body {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0 20px;
    align-items: start;
  }
  .profile-hero { padding-bottom: 30px; }
  .stats-row { padding: 20px 0; }
  .stat-val { font-size: 28px; }
  .badges { grid-template-columns: repeat(3, 1fr); gap: 12px; }
  .badge { padding: 18px 10px 14px; }
  .badge-icon { font-size: 30px; }
  .badge-name { font-size: 13px; }
  .badge-desc { font-size: 11px; }
  .mini-calendar { gap: 8px; }
  .mini-cell { padding: 9px 0; font-size: 12px; }
  .mini-cell em { font-size: 16px; }
  .logout-btn { width: calc(100% - 32px); margin: 16px 16px 0; padding: 15px; }
}

/* 像素皮肤 3.0 · 我的 */
.hero-bg { border-radius: 0 0 6px 6px; border-bottom: 2px solid var(--px-line); }
.avatar {
  border-radius: 4px;
  border: 2px solid var(--px-gold);
  box-shadow: 4px 4px 0 rgba(0, 0, 0, .4);
}
.profile-room-link {
  border: 2px solid rgba(240, 216, 170, .36);
  border-radius: 4px;
  font-family: var(--px-font);
  font-size: 12px;
}
.stats-row {
  border: 2px solid var(--px-line);
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.stat-item:hover { transform: translate(-1px, -1px); }
.stat-item:active { transform: translate(2px, 2px); }
.stat-val { font-family: var(--px-font); }
.stat-divider { width: 2px; background: var(--px-line); }
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--px-font);
  font-size: 13px;
}
.section-title::before { content: ''; width: 5px; height: 5px; flex: none; background: var(--px-gold); }
.pet-bond-card {
  border: 2px solid var(--px-line);
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
  transition: transform 160ms steps(2, end), box-shadow 160ms steps(2, end);
}
.pet-bond-card:hover { transform: translate(-1px, -1px); box-shadow: 5px 5px 0 var(--px-shadow); }
.pet-bond-card:active { transform: translate(2px, 2px); box-shadow: 1px 1px 0 var(--px-shadow); }
.pet-bond-avatar { border-radius: 4px; border: 2px solid var(--px-line); }
.pet-bond-head strong { font-family: var(--px-font); font-size: 14px; }
.pet-bond-track,
.pet-bond-track > div { border-radius: 0; }
.menu-card {
  border: 2px solid var(--px-line);
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.menu-row { font-size: 14px; }
.setting-input { border-width: 2px; border-radius: 4px; }
.save-btn {
  border: 2px solid var(--px-gold);
  border-radius: 4px;
  background: var(--px-gold);
  color: var(--game-on-accent);
  font-family: var(--px-font);
  box-shadow: 3px 3px 0 var(--px-shadow);
}
.save-btn:hover { background: var(--px-gold); filter: brightness(1.05); }
.save-btn:active { transform: translate(2px, 2px); box-shadow: 1px 1px 0 var(--px-shadow); }
.logout-btn {
  border: 2px solid var(--game-line);
  border-radius: 4px;
  box-shadow: none;
}
.mood-dist {
  border: 2px solid var(--px-line);
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.mini-cell { border: 1px solid var(--px-line); border-radius: 3px; }
.dist-track,
.dist-fill { border-radius: 0; }
.badges .badge { border-width: 2px; border-radius: 4px; }
.badges .badge.unlocked { border-color: var(--px-gold); box-shadow: 3px 3px 0 var(--px-shadow); }
.modal-card {
  border: 2px solid var(--px-line);
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.modal-input { border-width: 2px; border-radius: 4px; }
.modal-cancel,
.modal-confirm {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: 3px 3px 0 var(--px-shadow);
}
.modal-cancel:active,
.modal-confirm:active { transform: translate(2px, 2px); box-shadow: 1px 1px 0 var(--px-shadow); }
.treehole-close { border-radius: 4px; }
.profile-room-link:focus-visible,
.stat-item:focus-visible,
.pet-bond-card:focus-visible,
.menu-row:focus-visible,
.save-btn:focus-visible,
.logout-btn:focus-visible,
.treehole-close:focus-visible,
.modal-cancel:focus-visible,
.modal-confirm:focus-visible {
  outline: 3px dashed var(--px-gold);
  outline-offset: 3px;
}
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
</style>
