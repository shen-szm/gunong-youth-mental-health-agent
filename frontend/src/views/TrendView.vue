<template>
  <div class="trend-page">
    <!-- 顶部导航 -->
    <div class="page-header">
      <button class="back-btn" @click="router.back()">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
      </button>
      <div class="header-title">
        <h2>情绪回顾</h2>
        <p>了解你的情绪变化</p>
      </div>
      <div style="width:36px"></div>
    </div>

    <!-- 时间选择标签 -->
    <div class="tab-bar">
      <button v-for="t in tabs" :key="t.key" :class="{active: activeTab===t.key}" @click="activeTab=t.key">
        {{ t.label }}
      </button>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card main-stat">
        <div class="main-score" :style="{color: scoreColor}">{{ stats.avg_score || '--' }}</div>
        <div class="main-label">平均情绪分</div>
        <div class="main-hint" :style="{color: scoreColor}">{{ scoreHint }}</div>
        <!-- 情绪分圆形进度 -->
        <svg class="score-ring" viewBox="0 0 80 80">
          <circle cx="40" cy="40" r="34" fill="none" stroke="#F0ECE8" stroke-width="6"/>
          <circle cx="40" cy="40" r="34" fill="none" :stroke="scoreColor" stroke-width="6"
            stroke-linecap="round" stroke-dasharray="213.6"
            :stroke-dashoffset="213.6 - 213.6 * ((stats.avg_score || 0) / 10)"
            transform="rotate(-90 40 40)" style="transition:stroke-dashoffset 1s ease"/>
        </svg>
      </div>
      <div class="side-stats">
        <div class="stat-card side-card">
          <div class="side-val">{{ stats.count || 0 }}</div>
          <div class="side-label">记录次数</div>
        </div>
        <div class="stat-card side-card">
          <div class="side-val">{{ topMoodEmoji }}</div>
          <div class="side-label">主要情绪</div>
        </div>
      </div>
    </div>

    <!-- 折线图 / 情绪趋势 -->
    <div class="card chart-card" v-if="stats.trend?.length">
      <div class="card-title">📈 情绪走势</div>
      <div class="line-chart-wrap">
        <svg class="line-chart" viewBox="0 0 300 100" preserveAspectRatio="none">
          <!-- 网格线 -->
          <line v-for="y in [20,50,80]" :key="y" x1="0" :y1="y" x2="300" :y2="y" stroke="#F0ECE8" stroke-width="1"/>
          <!-- 渐变填充 -->
          <defs>
            <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" :stop-color="scoreColor" stop-opacity="0.25"/>
              <stop offset="100%" :stop-color="scoreColor" stop-opacity="0"/>
            </linearGradient>
          </defs>
          <polygon v-if="polyPoints" :points="polyPoints + ` ${lastX},95 ${firstX},95`" :fill="'url(#lineGrad)'"/>
          <!-- 折线 -->
          <polyline v-if="linePoints" :points="linePoints" fill="none" :stroke="scoreColor" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
          <!-- 数据点 -->
          <circle v-for="(p, i) in chartPoints" :key="i" :cx="p.x" :cy="p.y" r="3.5" fill="white" :stroke="scoreColor" stroke-width="2"/>
        </svg>
        <!-- X轴日期 -->
        <div class="x-labels">
          <span v-for="(d, i) in xLabels" :key="i">{{ d }}</span>
        </div>
      </div>
    </div>

    <!-- 情绪分布 -->
    <div class="card" v-if="stats.distribution && Object.keys(stats.distribution).length">
      <div class="card-title">🎯 情绪分布</div>
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

    <!-- AI 洞察 -->
    <div class="card insight-card">
      <div class="card-title">🤖 AI情绪洞察</div>
      <div class="insight-content">
        <div v-if="insightLoading" class="insight-loading">
          <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </div>
        <p v-else class="insight-text">{{ insight }}</p>
      </div>
      <button class="refresh-btn" @click="loadInsight" :disabled="insightLoading">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="margin-right:4px"><path d="M17.65 6.35A7.96 7.96 0 0012 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0112 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
        重新分析
      </button>
    </div>

    <!-- 空状态 -->
    <div class="empty-state" v-if="!stats.trend?.length && !Object.keys(stats.distribution||{}).length">
      <div class="empty-icon">🌿</div>
      <p>还没有情绪记录</p>
      <p class="empty-hint">去倾诉一下，这里会自动记录你的情绪变化</p>
      <button class="go-chat-btn" @click="router.push('/chat')">去倾诉 →</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { getMoodStats, getMoodInsight } from '../api/mood'

const router = useRouter()
const userStore = useUserStore()
const activeTab = ref(7)
const tabs = [{ key: 7, label: '近7天' }, { key: 30, label: '近30天' }, { key: 999, label: '全部' }]
const stats = ref({})
const insight = ref('正在分析你的情绪数据...')
const insightLoading = ref(false)

const scoreColor = computed(() => {
  const s = stats.value.avg_score || 5
  if (s >= 7) return '#6DB58B'
  if (s >= 5) return '#7FB3A6'
  if (s >= 3) return '#E8C468'
  return '#D4776A'
})

const scoreHint = computed(() => {
  const s = stats.value.avg_score || 0
  if (s >= 8) return '状态很好 ☺'
  if (s >= 6) return '整体不错'
  if (s >= 4) return '需要关注'
  if (s > 0) return '建议多倾诉'
  return '--'
})

const topMood = computed(() => {
  const dist = stats.value.distribution || {}
  if (!Object.keys(dist).length) return '--'
  return Object.entries(dist).sort((a, b) => b[1] - a[1])[0][0]
})

const topMoodEmoji = computed(() => {
  const map = { '开心': '😊', '平静': '😌', '焦虑': '😰', '难过': '😢', '愤怒': '😡' }
  return map[topMood.value] || '--'
})

const sortedDist = computed(() => {
  const dist = stats.value.distribution || {}
  return Object.fromEntries(Object.entries(dist).sort((a, b) => b[1] - a[1]))
})

// 折线图计算
const chartPoints = computed(() => {
  const trend = stats.value.trend || []
  if (!trend.length) return []
  const n = trend.length
  return trend.map((d, i) => ({
    x: n === 1 ? 150 : 15 + (i / (n - 1)) * 270,
    y: 95 - (d.avg / 10) * 80
  }))
})

const linePoints = computed(() => chartPoints.value.map(p => `${p.x},${p.y}`).join(' '))
const polyPoints = computed(() => linePoints.value)
const firstX = computed(() => chartPoints.value[0]?.x)
const lastX = computed(() => chartPoints.value[chartPoints.value.length - 1]?.x)

const xLabels = computed(() => {
  const trend = stats.value.trend || []
  if (!trend.length) return []
  if (trend.length <= 5) return trend.map(d => d.date.slice(5))
  const step = Math.ceil(trend.length / 5)
  return trend.filter((_, i) => i % step === 0 || i === trend.length - 1).map(d => d.date.slice(5))
})

function getEmoji(label) {
  const map = { '开心': '😊', '平静': '😌', '焦虑': '😰', '难过': '😢', '愤怒': '😡' }
  return map[label] || '🙂'
}

function getMoodColor(label) {
  const c = { '开心': '#6DB58B', '平静': '#7FB3A6', '焦虑': '#E8C468', '难过': '#8EAFC4', '愤怒': '#D4776A' }
  return c[label] || '#C8BEB4'
}

function getDistWidth(count) {
  const total = Object.values(stats.value.distribution || {}).reduce((a, b) => a + b, 0)
  return total ? Math.round(count / total * 100) : 0
}

async function loadData() {
  try {
    const r = await getMoodStats(Number(userStore.userId), activeTab.value)
    stats.value = r.data
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

onMounted(() => { loadData(); loadInsight() })
watch(activeTab, loadData)
</script>

<style scoped>
.trend-page {
  padding: 0 0 40px;
  background: rgba(15,15,20,0.55); min-height: 100vh;
  font-family: 'PingFang SC','Microsoft YaHei',sans-serif;
}

/* 顶部 */
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px; background: rgba(30,30,35,0.6);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255,255,255,0.06);
  position: sticky; top: 0; z-index: 10;
}
.back-btn {
  width: 36px; height: 36px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.08); color: #B5ADA6;
  transition: background 0.2s;
}
.back-btn:hover { background: rgba(255,255,255,0.14); }
.header-title h2 { margin: 0; font-size: 17px; color: #E8E2D8; text-align: center; }
.header-title p { margin: 0; font-size: 11px; color: #8A847E; text-align: center; }

/* 标签 */
.tab-bar {
  display: flex; gap: 8px; padding: 14px 16px 6px;
}
.tab-bar button {
  padding: 6px 18px; border-radius: 14px;
  background: rgba(255,255,255,0.08); color: #9A948E; font-size: 13px;
  border: 1px solid rgba(255,255,255,0.08); transition: all 0.2s;
}
.tab-bar button.active { background: #8EA89A; color: white; border-color: #8EA89A; }

/* 统计卡片 */
.stats-row { display: flex; gap: 10px; padding: 10px 16px; }
.stat-card { background: rgba(40,40,48,0.7); border-radius: 16px; backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.06); }

.main-stat {
  flex: 1; padding: 16px; position: relative;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-height: 110px;
}
.score-ring {
  position: absolute; width: 80px; height: 80px; opacity: 0.5;
}
.main-score { font-size: 32px; font-weight: 700; position: relative; z-index: 1; }
.main-label { font-size: 11px; color: #8A847E; margin-top: 2px; position: relative; z-index: 1; }
.main-hint { font-size: 12px; margin-top: 4px; font-weight: 500; position: relative; z-index: 1; }

.side-stats { display: flex; flex-direction: column; gap: 10px; flex: 0 0 90px; }
.side-card { padding: 12px; text-align: center; flex: 1; display: flex; flex-direction: column; justify-content: center; }
.side-val { font-size: 22px; font-weight: 700; color: #8EA89A; }
.side-label { font-size: 11px; color: #8A847E; margin-top: 3px; }

/* 通用卡片 */
.card { background: rgba(40,40,48,0.7); border-radius: 16px; backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.06); margin: 10px 16px; padding: 16px; }
.card-title { font-size: 14px; font-weight: 600; color: #E8E2D8; margin-bottom: 14px; }

/* 折线图 */
.chart-card {}
.line-chart-wrap { position: relative; }
.line-chart { width: 100%; height: 100px; }
.x-labels {
  display: flex; justify-content: space-between;
  font-size: 10px; color: #8A847E; margin-top: 4px; padding: 0 10px;
}

/* 情绪分布 */
.dist-list { display: flex; flex-direction: column; gap: 10px; }
.dist-row { display: flex; align-items: center; gap: 8px; }
.dist-emoji { font-size: 17px; width: 24px; text-align: center; }
.dist-label { width: 36px; font-size: 13px; color: #C8C0B6; flex-shrink: 0; }
.dist-track { flex: 1; height: 8px; background: rgba(255,255,255,0.08); border-radius: 4px; overflow: hidden; }
.dist-fill { height: 100%; border-radius: 4px; transition: width 0.8s ease; }
.dist-pct { width: 36px; font-size: 11px; color: #8A847E; text-align: right; }

/* AI 洞察 */
.insight-card {}
.insight-content { min-height: 50px; }
.insight-loading { display: flex; gap: 6px; padding: 8px 0; }
.insight-loading .dot {
  width: 9px; height: 9px; border-radius: 50%; background: #8EA89A;
  animation: bounce 1.2s infinite both;
}
.insight-loading .dot:nth-child(2) { animation-delay: 0.2s; }
.insight-loading .dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%,80%,100%{transform:translateY(0);opacity:0.4} 40%{transform:translateY(-5px);opacity:1} }
.insight-text { font-size: 14px; line-height: 1.7; color: #B8B0A6; }
.refresh-btn {
  margin-top: 10px; padding: 6px 14px; border-radius: 10px;
  background: rgba(255,255,255,0.08); color: #8A847E; font-size: 12px;
  display: inline-flex; align-items: center;
  transition: background 0.2s;
}
.refresh-btn:hover:not(:disabled) { background: rgba(255,255,255,0.14); }
.refresh-btn:disabled { opacity: 0.4; }

/* 空状态 */
.empty-state { text-align: center; padding: 48px 24px; }
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-state p { font-size: 15px; color: #B8B0A6; margin: 0; }
.empty-hint { font-size: 13px; color: #8A847E; margin-top: 8px !important; }
.go-chat-btn {
  margin-top: 20px; padding: 10px 28px;
  background: #8EA89A; color: white; border-radius: 20px; font-size: 14px;
  transition: background 0.2s;
}
.go-chat-btn:hover { background: #7A9A8C; }

/* ═══════════ 电脑端适配 ═══════════ */
@media (min-width: 768px) {
  .trend-page {
    display: flex; flex-direction: column; align-items: center;
  }
  .page-header, .tab-bar, .stats-row, .card, .empty-state {
    width: 560px;
    margin-left: auto; margin-right: auto;
  }
  .stats-row { padding: 10px 0; }
  .card { margin: 10px auto; }
  .side-stats { flex: 0 0 110px; }
}
</style>
