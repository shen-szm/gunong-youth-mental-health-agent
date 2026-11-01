<template>
  <div class="trend-page game-page" :data-part="part">
    <GameBackdrop :part="part" variant="page" />
    <div class="page-header">
      <button class="back-btn" @click="router.push('/')" aria-label="返回首页">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
      </button>
      <div class="header-title">
        <h2>情绪回顾</h2>
        <p>了解你的情绪变化</p>
      </div>
      <div style="width:36px"></div>
    </div>

    <div class="tab-bar">
      <button v-for="t in tabs" :key="t.key" :class="{active: activeTab===t.key}" @click="activeTab=t.key">
        {{ t.label }}
      </button>
    </div>

    <div class="trend-pet-note game-card">
      <img :src="petAvatar" alt="咕团" />
      <div>
        <strong>咕团陪你回看</strong>
        <p>{{ petLine }}</p>
      </div>
      <router-link to="/">回首页</router-link>
    </div>

    <StudentWellbeingAssessment />

    <div class="stats-row">
      <div class="stat-card main-stat">
        <div class="main-score">{{ topMoodEmoji }}</div>
        <div class="main-label">较常记录的情绪</div>
        <div class="main-hint">只描述主动留下的记录</div>
      </div>
      <div class="side-stats">
        <div class="stat-card side-card">
          <div class="side-val">{{ stats.count || 0 }}</div>
          <div class="side-label">记录次数</div>
        </div>
        <div class="stat-card side-card">
          <div class="side-val">{{ stats.recorded_days || 0 }}</div>
          <div class="side-label">有记录的天数</div>
        </div>
      </div>
    </div>

    <!-- 情绪日历 -->
    <div class="card calendar-card">
      <div class="card-title">情绪日历</div>
      <div class="calendar-hint">最近 {{ calendarSpan }} 天里留下的记录</div>
      <div class="calendar-grid">
        <div v-for="day in calendarDays" :key="day.date" class="cal-cell" :class="{ 'has-mood': !!day.mood }">
          <span class="cal-day">{{ day.label }}</span>
          <span class="cal-mood" aria-hidden="true">{{ day.mood ? getEmoji(day.mood) : '' }}</span>
        </div>
      </div>
    </div>

    <!-- 回顾报告：跟随筛选，切换时会重新生成 -->
    <div class="card report-card">
      <div class="card-title">{{ reportRangeLabel }}</div>
      <p v-if="activeTab === 999" class="report-window-hint">选择“全部”时，回顾仍固定取最近 30 天。</p>
      <div v-if="reportLoading" class="insight-loading">
        <span class="dot"></span><span class="dot"></span><span class="dot"></span>
      </div>
      <template v-else-if="report">
        <p class="report-sources">
          基于 {{ report.sources?.self_records || 0 }} 条主动记录 · {{ report.sources?.conversation_signals || 0 }} 条对话线索<template v-if="report.sources?.conversation_summary"> · 含最近 1 份倾诉小结</template>
        </p>
        <p class="insight-text">{{ report.overview }}</p>
        <p class="report-focus"><strong>可以试着关注</strong>{{ report.support_focus }}</p>
        <ol class="report-steps">
          <li v-for="step in report.next_steps" :key="step">{{ step }}</li>
        </ol>
        <p class="report-boundary">{{ report.boundary }}</p>
        <p class="report-boundary">以上是对已记录内容的描述性整理，不是心理测评。</p>
      </template>
      <button class="refresh-btn" @click="loadReport" :disabled="reportLoading">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="margin-right:4px"><path d="M17.65 6.35A7.96 7.96 0 0012 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0112 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
        重新整理
      </button>
    </div>

    <!-- 主动记录时间线 -->
    <div class="card chart-card" v-if="stats.trend?.length">
      <div class="card-title">近期主动记录</div>
      <div class="record-timeline">
        <article v-for="day in stats.trend" :key="day.date"><time>{{ day.date }}</time><div><span v-for="label in day.labels" :key="label">{{ label }}</span></div><small>{{ day.count }}条</small></article>
      </div>
    </div>

    <!-- 情绪分布 -->
    <div class="card" v-if="stats.distribution && Object.keys(stats.distribution).length">
      <div class="card-title">情绪分布</div>
      <div class="dist-list">
        <div v-for="(count, label) in sortedDist" :key="label" class="dist-row">
          <span class="dist-emoji">{{ getEmoji(label) }}</span>
          <span class="dist-label">{{ label }}</span>
          <div class="dist-track">
            <div class="dist-fill" :style="{width: getDistWidth(count)+'%', background: getMoodColor(label)}"></div>
          </div>
          <span class="dist-pct">{{ getDistWidth(count) }}%</span>
        </div>
      </div>
    </div>

    <!-- 情绪小结 -->
    <div class="card insight-card">
      <div class="card-title">近7天情绪小结</div>
      <div class="insight-content">
        <div v-if="insightLoading" class="insight-loading">
          <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </div>
        <p v-else class="insight-text">{{ insight }}</p>
      </div>
      <button class="refresh-btn" @click="loadInsight" :disabled="insightLoading">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="margin-right:4px"><path d="M17.65 6.35A7.96 7.96 0 0012 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0112 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
        重新生成
      </button>
    </div>

    <!-- 空状态 -->
    <div class="empty-state" v-if="!stats.trend?.length && !Object.keys(stats.distribution||{}).length">
      <div class="empty-icon">🌿</div>
      <p>{{ emptyTitle }}</p>
      <p class="empty-hint">记录心情后，这里会显示你的情绪变化；倾诉线索会进入回顾报告。</p>
      <button class="go-chat-btn" @click="router.push('/chat')">去倾诉 →</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { getMoodStats, getMoodInsight, getEmotionReport } from '../api/mood'
import { useTimeOfDay } from '../utils/timeOfDay'
import { petImageForStatus, readPetCompanion } from '../utils/petCompanion'
import StudentWellbeingAssessment from '../components/StudentWellbeingAssessment.vue'
import GameBackdrop from '../components/student/GameBackdrop.vue'

const router = useRouter()
const userStore = useUserStore()
const part = useTimeOfDay()
const petState = computed(() => readPetCompanion(userStore.userId))
const petAvatar = computed(() => petImageForStatus(part.value === 'night' && petState.value.status !== 'happy' ? 'sleeping' : petState.value.status))
const petLine = computed(() => {
  const count = stats.value.count || 0
  if (!count) return '今天还没有记录也没关系。想说话的时候，回首页找我。'
  const label = topMood.value && topMood.value !== '--' ? `出现最多的是「${topMood.value}」。` : ''
  return `这里记下了 ${count} 次心情。${label}看一看就好，不急着给自己下结论。`
})
const activeTab = ref(7)
const tabs = [{ key: 7, label: '近7天' }, { key: 30, label: '近30天' }, { key: 999, label: '全部' }]
const stats = ref({})
const insight = ref('正在分析你的情绪数据...')
const insightLoading = ref(false)
const report = ref(null)
const reportLoading = ref(false)
const reportDays = computed(() => activeTab.value === 7 ? 7 : 30)
const reportRangeLabel = computed(() => reportDays.value === 7 ? '近 7 天回顾' : '近 30 天回顾')
const emptyTitle = computed(() => (
  activeTab.value === 7 ? '近 7 天还没有情绪记录'
    : activeTab.value === 30 ? '近 30 天还没有情绪记录'
      : '还没有情绪记录'
))

const topMood = computed(() => {
  const dist = stats.value.distribution || {}
  if (!Object.keys(dist).length) return '--'
  return Object.entries(dist).sort((a, b) => b[1] - a[1])[0][0]
})

const MOOD_EMOJI = {
  '愤怒': '😠', '厌恶': '🤢', '恐惧': '😨', '开心': '😊', '中性': '😐', '悲伤': '😢', '惊讶': '😲',
  '平静': '😌', '焦虑': '😰', '难过': '😢',
}
const MOOD_COLOR = {
  '愤怒': '#D4776A', '厌恶': '#A98A5C', '恐惧': '#8B7BA6', '开心': '#6DB58B',
  '中性': '#A8A29A', '悲伤': '#8EAFC4', '惊讶': '#E8C468',
  '平静': '#7FB3A6', '焦虑': '#E8C468', '难过': '#8EAFC4',
}

const topMoodEmoji = computed(() => MOOD_EMOJI[topMood.value] || '--')

const sortedDist = computed(() => {
  const dist = stats.value.distribution || {}
  return Object.fromEntries(Object.entries(dist).sort((a, b) => b[1] - a[1]))
})

function getEmoji(label) {
  return MOOD_EMOJI[label] || '🙂'
}

function getMoodColor(label) {
  return MOOD_COLOR[label] || '#C8BEB4'
}

function getDistWidth(count) {
  const total = Object.values(stats.value.distribution || {}).reduce((a, b) => a + b, 0)
  return total ? Math.round(count / total * 100) : 0
}

// ─── 情绪日历 ───
const calendarSpan = computed(() => activeTab.value === 7 ? 7 : 30)
const calendarDays = computed(() => {
  const byDate = {}
  for (const day of stats.value.trend || []) {
    if (day.labels?.length) byDate[day.date] = day.labels[0]
  }
  const days = []
  const now = new Date()
  for (let i = calendarSpan.value - 1; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(now.getDate() - i)
    const key = `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    days.push({ label: d.getDate(), date: key, mood: byDate[key] || '' })
  }
  return days
})

let dataRequestId = 0
async function loadData() {
  const requestId = ++dataRequestId
  try {
    const r = await getMoodStats(Number(userStore.userId), activeTab.value)
    if (requestId === dataRequestId) stats.value = r.data
  } catch {}
}

async function loadInsight() {
  insightLoading.value = true; insight.value = ''
  try {
    const r = await getMoodInsight(Number(userStore.userId))
    insight.value = r.data.insight
  } catch { insight.value = '分析失败，请稍后重试~' }
  insightLoading.value = false
}

let reportRequestId = 0
async function loadReport() {
  const requestId = ++reportRequestId
  reportLoading.value = true
  try {
    const res = await getEmotionReport(reportDays.value)
    if (requestId === reportRequestId) report.value = res.data
  } catch {
    if (requestId === reportRequestId) {
      report.value = {
        overview: '报告暂时没有生成成功，现有记录没有丢失。',
        sources: {}, next_steps: ['稍后重试，或先继续倾诉和主动记录'],
        support_focus: '先保留你的原始感受，不根据本次失败做任何判断。',
        boundary: '这不是心理测评或医学结论。',
      }
    }
  } finally {
    if (requestId === reportRequestId) reportLoading.value = false
  }
}

onMounted(() => { loadData(); loadInsight(); loadReport() })
watch(activeTab, () => { loadData(); loadReport() })
</script>

<style scoped>
.trend-page {
  padding: 0 0 40px;
  background: transparent;
  color: var(--m-ink);
  min-height: 100vh;
  position: relative;
  font-family: 'PingFang SC','Microsoft YaHei',sans-serif;
}
.trend-page > :not(.game-backdrop) { position: relative; z-index: 1; }

/* 咕团陪看 */
.trend-pet-note {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 10px 16px;
  padding: 12px 14px;
}
.trend-pet-note img { width: 44px; height: 44px; object-fit: contain; flex: none; }
.trend-pet-note div { flex: 1; min-width: 0; }
.trend-pet-note strong { display: block; font-size: 12.5px; color: var(--game-wood); }
.trend-pet-note p { margin: 2px 0 0; font-size: 12.5px; line-height: 1.65; color: var(--game-ink-2); }
.trend-pet-note a {
  flex: none;
  padding: 6px 11px;
  border-radius: 999px;
  border: 1px solid var(--game-line);
  background: var(--game-gold-soft);
  color: var(--game-wood);
  font-size: 11.5px;
  font-weight: 600;
  text-decoration: none;
  transition: transform var(--m-dur-fast) var(--m-ease), background var(--m-dur-fast) var(--m-ease);
}
.trend-pet-note a:hover { transform: translateY(-1px); background: var(--game-surface); }
.trend-pet-note a:active { transform: scale(.95); }

/* 顶部 */
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px; background: var(--m-surface);
  border-bottom: 1px solid var(--m-line);
  position: sticky; top: 0; z-index: 10;
}
.back-btn {
  width: 36px; height: 36px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: var(--m-bg); color: var(--m-ink-2);
  transition: background var(--m-dur-fast) var(--m-ease),
              transform var(--m-dur-fast) var(--m-ease);
}
.back-btn:hover { background: var(--m-accent-soft); }
.back-btn:active { transform: scale(.92); }
.header-title h2 { margin: 0; font-size: 17px; color: var(--m-ink); text-align: center; }
.header-title p { margin: 0; font-size: 11px; color: var(--m-ink-3); text-align: center; }

/* 标签 */
.tab-bar { display: flex; gap: 8px; padding: 14px 16px 6px; }
.tab-bar button {
  padding: 6px 18px; border-radius: 14px;
  background: var(--m-surface); color: var(--m-ink-2); font-size: 13px;
  border: 1px solid var(--m-line); transition: all var(--m-dur-fast) var(--m-ease);
}
.tab-bar button.active { background: var(--m-accent); color: var(--game-on-accent); border-color: var(--m-accent); }
.tab-bar button:not(.active):hover { border-color: var(--m-accent); color: var(--m-accent-strong); }
.tab-bar button:active { transform: scale(.96); }

/* 统计卡片 */
.stats-row { display: flex; gap: 10px; padding: 10px 16px; }

/* v5.1.0-alpha.41 入场错峰（backwards：终帧不残留 transform，不干扰 hover） */
.tab-bar, .stats-row, .trend-page > .card, .empty-state {
  animation: m-rise var(--m-enter-dur) var(--m-ease) backwards;
}
.tab-bar { animation-delay: 40ms; }
.stats-row { animation-delay: 80ms; }
.trend-page > .card, .empty-state { animation-delay: 140ms; }
.stat-card {
  background: var(--m-surface);
  border-radius: var(--m-radius-lg);
  border: 1px solid var(--m-line);
  box-shadow: var(--m-shadow);
}

.main-stat {
  flex: 1; padding: 16px;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-height: 110px;
}
.main-score { font-size: 32px; font-weight: 700; }
.main-label { font-size: 11px; color: var(--m-ink-2); margin-top: 2px; }
.main-hint { color: var(--m-ink-3); font-size: 12px; margin-top: 4px; font-weight: 500; }

.side-stats { display: flex; flex-direction: column; gap: 10px; flex: 0 0 90px; }
.side-card { padding: 12px; text-align: center; flex: 1; display: flex; flex-direction: column; justify-content: center; }
.side-val { font-size: 22px; font-weight: 700; color: var(--m-accent-strong); }
.side-label { font-size: 11px; color: var(--m-ink-2); margin-top: 3px; }

/* 通用卡片 */
.card {
  background: var(--m-surface);
  border-radius: var(--m-radius-lg);
  border: 1px solid var(--m-line);
  box-shadow: var(--m-shadow);
  margin: 10px 16px;
  padding: 16px;
}
.card-title { font-size: 14px; font-weight: 600; color: var(--m-ink); margin-bottom: 14px; }

/* 情绪日历 */
.calendar-hint { font-size: 12px; color: var(--m-ink-3); margin: -8px 0 10px; }
.calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; }
.cal-cell {
  display: flex; flex-direction: column; align-items: center; gap: 1px;
  padding: 7px 0; border-radius: var(--m-radius-sm);
  background: var(--m-bg); color: var(--m-ink-3); font-size: 11px;
}
.cal-cell.has-mood { background: var(--m-accent-soft); color: var(--m-ink-2); }
.cal-mood { font-size: 14px; line-height: 1.2; min-height: 17px; }

/* 时间线 */
.record-timeline { display: grid; gap: 9px; }
.record-timeline article { display: grid; grid-template-columns: 64px 1fr auto; align-items: center; gap: 10px; padding: 10px 0; border-top: 1px solid var(--m-line); }
.record-timeline time, .record-timeline small { color: var(--m-ink-3); font-size: 12px; }
.record-timeline article div { display: flex; flex-wrap: wrap; gap: 6px; }
.record-timeline article div span { padding: 5px 9px; border-radius: 999px; background: var(--m-accent-soft); color: var(--m-accent-strong); font-size: 12px; font-weight: 700; }

/* 情绪分布 */
.dist-list { display: flex; flex-direction: column; gap: 10px; }
.dist-row { display: flex; align-items: center; gap: 8px; }
.dist-emoji { font-size: 17px; width: 24px; text-align: center; }
.dist-label { width: 36px; font-size: 13px; color: var(--m-ink-2); flex-shrink: 0; }
.dist-track { flex: 1; height: 8px; background: var(--m-bg); border-radius: 4px; overflow: hidden; }
.dist-fill { height: 100%; border-radius: 4px; transition: width 0.8s ease; }
.dist-pct { width: 36px; font-size: 11px; color: var(--m-ink-3); text-align: right; }

/* 报告 / 洞察 */
.insight-content { min-height: 50px; }
.insight-loading { display: flex; gap: 6px; padding: 8px 0; }
.insight-loading .dot {
  width: 9px; height: 9px; border-radius: 50%; background: var(--m-accent);
  animation: bounce 1.2s infinite both;
}
.insight-loading .dot:nth-child(2) { animation-delay: 0.2s; }
.insight-loading .dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%,80%,100%{transform:translateY(0);opacity:0.4} 40%{transform:translateY(-5px);opacity:1} }
.insight-text { font-size: 14px; line-height: 1.7; color: var(--m-ink-2); }
.report-window-hint { font-size: 12px; color: var(--m-ink-3); margin: -8px 0 10px; }
.report-sources { font-size: 12px; color: var(--m-ink-3); margin-bottom: 8px; }
.report-focus { margin-top: 10px; font-size: 13.5px; line-height: 1.7; color: var(--m-ink-2); }
.report-focus strong { display: block; font-size: 12px; color: var(--m-accent-strong); margin-bottom: 2px; }
.report-steps { margin: 10px 0 0; padding-left: 18px; display: grid; gap: 6px; }
.report-steps li { font-size: 13px; line-height: 1.7; color: var(--m-ink-2); }
.report-boundary { margin: 10px 0 0; font-size: 11.5px; line-height: 1.7; color: var(--m-ink-3); }
.refresh-btn {
  margin-top: 12px; padding: 6px 14px; border-radius: 10px;
  background: var(--m-bg); color: var(--m-ink-2); font-size: 12px;
  display: inline-flex; align-items: center;
  transition: background var(--m-dur-fast) var(--m-ease),
              transform var(--m-dur-fast) var(--m-ease);
}
.refresh-btn:hover:not(:disabled) { background: var(--m-accent-soft); color: var(--m-accent-strong); }
.refresh-btn:active:not(:disabled) { transform: scale(.96); }
.refresh-btn:disabled { opacity: 0.4; }

/* 空状态 */
.empty-state { text-align: center; padding: 48px 24px; }
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-state p { font-size: 15px; color: var(--m-ink-2); margin: 0; }
.empty-hint { font-size: 13px; color: var(--m-ink-3); margin-top: 8px !important; }
.go-chat-btn {
  margin-top: 20px; padding: 10px 28px;
  background: var(--m-accent); color: var(--game-on-accent); border-radius: 20px; font-size: 14px;
  transition: background var(--m-dur-fast) var(--m-ease),
              transform var(--m-dur-fast) var(--m-ease);
}
.go-chat-btn:hover { background: var(--m-accent-strong); }
.go-chat-btn:active { transform: scale(.96); }

/* ═══════════ 电脑端适配：1080 双栏 ═══════════ */
@media (min-width: 768px) {
  .trend-page {
    width: min(1080px, calc(100% - 48px));
    margin: 0 auto;
    padding-bottom: 100px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px 20px;
    align-items: start;
  }
  .page-header, .tab-bar, .trend-pet-note, .wellbeing-card, .stats-row, .empty-state {
    grid-column: 1 / -1;
  }
  .trend-pet-note { margin: 0; }
  .stats-row { padding: 10px 0; }
  .card { margin: 0; }
  .side-stats { flex: 0 0 260px; flex-direction: row; }
  .side-card { min-width: 0; }
  .calendar-grid { grid-template-columns: repeat(10, 1fr); }
}

/* 像素皮肤 3.0 · 回顾页 */
.page-header { border-bottom: 2px solid var(--px-line); }
.back-btn {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  background: var(--game-surface-soft);
  box-shadow: 3px 3px 0 var(--px-shadow);
  transition: transform 160ms steps(2, end), box-shadow 160ms steps(2, end), background 160ms steps(2, end);
}
.back-btn:hover { transform: translate(-1px, -1px); box-shadow: 4px 4px 0 var(--px-shadow); }
.back-btn:active { transform: translate(2px, 2px); box-shadow: 1px 1px 0 var(--px-shadow); }
.header-title h2 { font-family: var(--px-font); font-size: 18px; letter-spacing: .02em; }
.tab-bar button {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  font-family: var(--px-font);
  font-size: 13px;
  box-shadow: 3px 3px 0 var(--px-shadow);
  transition: transform 160ms steps(2, end), box-shadow 160ms steps(2, end), background 160ms steps(2, end);
}
.tab-bar button.active { border-color: var(--px-gold); box-shadow: 1px 1px 0 var(--px-shadow); transform: translate(2px, 2px); }
.tab-bar button:not(.active):hover { transform: translate(-1px, -1px); box-shadow: 4px 4px 0 var(--px-shadow); }
.stat-card,
.card {
  border: 2px solid var(--px-line);
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.main-score,
.side-val { font-family: var(--px-font); }
.card-title { display: flex; align-items: center; gap: 8px; font-family: var(--px-font); font-size: 15px; }
.card-title::before { content: ''; width: 5px; height: 5px; flex: none; background: var(--px-gold); }
.cal-cell { border: 1px solid var(--px-line); border-radius: 3px; }
.record-timeline article div span { border: 2px solid var(--px-line); border-radius: 4px; }
.dist-track,
.dist-fill { border-radius: 0; }
.refresh-btn {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: 3px 3px 0 var(--px-shadow);
  transition: transform 160ms steps(2, end), box-shadow 160ms steps(2, end), background 160ms steps(2, end);
}
.refresh-btn:hover:not(:disabled) { transform: translate(-1px, -1px); box-shadow: 4px 4px 0 var(--px-shadow); }
.refresh-btn:active:not(:disabled) { transform: translate(2px, 2px); box-shadow: 1px 1px 0 var(--px-shadow); }
.go-chat-btn {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: 3px 3px 0 var(--px-shadow);
}
.back-btn:focus-visible,
.tab-bar button:focus-visible,
.refresh-btn:focus-visible,
.go-chat-btn:focus-visible {
  outline: 3px dashed var(--px-gold);
  outline-offset: 3px;
}
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
</style>
