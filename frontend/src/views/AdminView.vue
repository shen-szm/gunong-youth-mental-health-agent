<template>
  <div class="admin-page">
    <header class="admin-header">
      <button class="back-btn" @click="handleBack">← 返回</button>
      <h2>教师端</h2>
      <button class="logout-btn" @click="handleLogout">退出</button>
    </header>

    <!-- 权限检查 -->
    <div v-if="error" class="error-screen">
      <p>{{ error }}</p>
    </div>

    <template v-else>
      <!-- 统计概览 -->
      <div class="stats-grid">
        <div class="stat-card" v-for="s in statCards" :key="s.label">
          <p class="stat-value">{{ s.value }}</p>
          <p class="stat-label">{{ s.label }}</p>
        </div>
      </div>

      <!-- Tab 切换 -->
      <div class="tab-bar">
        <button :class="{active: tab==='users'}" @click="tab='users'; loadUsers()">用户管理</button>
        <button :class="{active: tab==='chats'}" @click="tab='chats'; loadChats()">对话监控</button>
      </div>

      <!-- ==================== 用户管理 ==================== -->
      <div v-if="tab==='users'" class="users-section">
        <!-- 用户列表 -->
        <div class="user-list" v-if="selectedUser">
          <div class="panel-header">
            <button class="btn-back-list" @click="selectedUser=null">← 返回列表</button>
            <h3>用户列表</h3>
          </div>
          <div
            v-for="u in users" :key="u.id"
            :class="['user-item', { selected: selectedUser.id === u.id }]"
            @click="selectUser(u)"
          >
            <div class="user-avatar">{{ (u.nickname || u.username)[0] }}</div>
            <div class="user-info">
              <span class="user-name">{{ u.nickname || u.username }}</span>
              <span class="user-meta">
                ID: {{ u.id }} · {{ u.is_admin ? '教师' : '普通用户' }}
                <span v-if="u.plain_password" class="user-pwd"> · 密码: {{ u.plain_password }}</span>
              </span>
            </div>
            <div class="user-actions">
              <button class="btn-sm warn" @click.stop="resetUserPwd(u)">重置密码</button>
              <button class="btn-sm" @click.stop="toggleAdmin(u)">{{ u.is_admin ? '取消教师' : '设为教师' }}</button>
              <button class="btn-sm danger" @click.stop="deleteUser(u)">删除</button>
            </div>
          </div>
          <div class="pagination" v-if="totalPages > 1">
            <button :disabled="page<=1" @click="page--; loadUsers()">上一页</button>
            <span>{{ page }} / {{ totalPages }}</span>
            <button :disabled="page>=totalPages" @click="page++; loadUsers()">下一页</button>
          </div>
        </div>
        <div v-else>
          <div
            v-for="u in users" :key="u.id"
            class="user-item"
            @click="selectUser(u)"
          >
            <div class="user-avatar">{{ (u.nickname || u.username)[0] }}</div>
            <div class="user-info">
              <span class="user-name">{{ u.nickname || u.username }}</span>
              <span class="user-meta">
                ID: {{ u.id }} · {{ u.is_admin ? '教师' : '普通用户' }} · {{ u.created_at?.slice(0, 10) }}
                <span v-if="u.plain_password" class="user-pwd"> · 密码: {{ u.plain_password }}</span>
              </span>
            </div>
            <div class="user-actions">
              <button class="btn-sm warn" @click.stop="resetUserPwd(u)">重置密码</button>
              <span class="arrow">→</span>
            </div>
          </div>
          <p v-if="users.length === 0" class="empty">暂无用户</p>
          <div class="pagination" v-if="totalPages > 1">
            <button :disabled="page<=1" @click="page--; loadUsers()">上一页</button>
            <span>{{ page }} / {{ totalPages }}</span>
            <button :disabled="page>=totalPages" @click="page++; loadUsers()">下一页</button>
          </div>
        </div>

        <!-- ====== 用户详情面板 ====== -->
        <transition name="slide">
          <div class="detail-panel" v-if="selectedUser">
            <div class="detail-header">
              <div class="detail-avatar">{{ (selectedUser.nickname || selectedUser.username)[0] }}</div>
              <div>
                <h3>{{ selectedUser.nickname || selectedUser.username }}</h3>
                <p class="detail-meta">ID: {{ selectedUser.id }} · 注册于 {{ selectedUser.created_at?.slice(0, 10) }}</p>
              </div>
            </div>

            <!-- 用户数据卡片 -->
            <div class="detail-stats">
              <div class="detail-stat">
                <p class="ds-value">{{ detail.stats.total_moods }}</p>
                <p class="ds-label">情绪记录</p>
              </div>
              <div class="detail-stat">
                <p class="ds-value">{{ detail.stats.total_chats }}</p>
                <p class="ds-label">对话次数</p>
              </div>
              <div class="detail-stat">
                <p class="ds-value">{{ detail.stats.use_days }}</p>
                <p class="ds-label">使用天数</p>
              </div>
              <div class="detail-stat">
                <p class="ds-value" :style="{color: getScoreColor(detail.stats.avg_score)}">{{ detail.stats.avg_score || '--' }}</p>
                <p class="ds-label">平均情绪分</p>
              </div>
            </div>

            <!-- 心情趋势图 -->
            <div class="chart-section">
              <h4>📈 心情趋势（近30天）</h4>
              <div class="trend-chart" v-if="detail.trend?.length">
                <div class="trend-area">
                  <div class="trend-grid" style="top:25%"></div>
                  <div class="trend-grid" style="top:50%"></div>
                  <div class="trend-grid" style="top:75%"></div>
                  <div v-for="d in detail.trend" :key="d.date" class="trend-col">
                    <span class="trend-val">{{ d.avg }}</span>
                    <div class="trend-track">
                      <div class="trend-bar" :style="{height: d.avg * 10 + '%', background: getScoreColor(d.avg)}"></div>
                    </div>
                    <span class="trend-date">{{ d.date }}</span>
                  </div>
                </div>
              </div>
              <p v-else class="empty-small">暂无趋势数据</p>
            </div>

            <!-- 情绪分布 -->
            <div class="chart-section">
              <h4>🎯 情绪分布</h4>
              <div class="dist-bars" v-if="detail.distribution && Object.keys(detail.distribution).length">
                <div v-for="(count, label) in sortedDist" :key="label" class="dist-row">
                  <span class="dist-emoji">{{ getEmoji(label) }}</span>
                  <span class="dist-label">{{ label }}</span>
                  <div class="dist-track">
                    <div class="dist-fill" :style="{width: getDistPct(count) + '%', background: getMoodColor(label)}"></div>
                  </div>
                  <span class="dist-count">{{ count }}次</span>
                </div>
              </div>
              <p v-else class="empty-small">暂无分布数据</p>
            </div>

            <!-- 词云 -->
            <div class="chart-section">
              <h4>💬 高频词汇</h4>
              <div class="word-cloud-wrap" v-if="detail.word_cloud?.length">
                <canvas ref="wordCloudCanvas" class="word-cloud-canvas"></canvas>
              </div>
              <p v-else class="empty-small">暂无词云数据</p>
            </div>

            <!-- AI 心理分析 -->
            <div class="chart-section">
              <h4>🤖 AI 心理分析</h4>
              <div class="analysis-card">
                <div v-if="analysisLoading" class="analysis-loading">
                  <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                </div>
                <p v-else class="analysis-text">{{ analysis }}</p>
              </div>
              <button class="btn-refresh" @click="loadAnalysis" :disabled="analysisLoading">
                🔄 重新分析
              </button>
            </div>
          </div>
        </transition>
      </div>

      <!-- ==================== 对话监控 ==================== -->
      <div v-if="tab==='chats'" class="chat-monitor">
        <!-- 用户筛选栏 -->
        <div class="chat-user-bar">
          <button
            :class="['chat-user-btn', { active: chatFilterUser === null }]"
            @click="chatFilterUser = null"
          >全部</button>
          <button
            v-for="u in chatUsers" :key="u.id"
            :class="['chat-user-btn', { active: chatFilterUser === u.id }]"
            @click="chatFilterUser = u.id"
          >
            {{ u.nickname || u.username }}
            <span class="chat-user-count">{{ u.msgCount }}</span>
          </button>
        </div>

        <!-- 聊天对话区域 -->
        <div class="chat-dialog" ref="chatDialogRef">
          <div
            v-for="(group, gi) in chatGroups" :key="gi"
            class="chat-session"
          >
            <!-- 用户标识头（按用户分组时显示） -->
            <div v-if="chatFilterUser === null" class="chat-session-header">
              <div class="chat-session-avatar">{{ group.userName[0] }}</div>
              <span class="chat-session-name">{{ group.userName }}</span>
              <span class="chat-session-time">{{ group.timeRange }}</span>
            </div>

            <!-- 消息列表 -->
            <div class="chat-bubbles">
              <div
                v-for="msg in group.messages" :key="msg.id"
                :class="['chat-bubble-row', msg.role === 'user' ? 'user' : 'ai']"
              >
                <div class="chat-bubble-avatar">
                  {{ msg.role === 'user' ? group.userName[0] : 'AI' }}
                </div>
                <div class="chat-bubble-body">
                  <div class="chat-bubble-meta">
                    <span class="chat-bubble-role">{{ msg.role === 'user' ? group.userName : '咕哝AI' }}</span>
                    <span class="chat-bubble-time">{{ formatChatTime(msg.created_at) }}</span>
                  </div>
                  <div :class="['chat-bubble-content', msg.role]">
                    {{ msg.content }}
                    <span v-if="msg.emotion" class="chat-bubble-emotion">{{ getEmoji(msg.emotion) }} {{ msg.emotion }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <p v-if="filteredChats.length === 0" class="empty">暂无对话</p>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from "vue"
import { useRouter } from "vue-router"
import { useUserStore } from "../stores/user"
import { resetPassword } from "../api/user"
import axios from "axios"

const router = useRouter()
const userStore = useUserStore()

const tab = ref("users")
const users = ref([])
const chats = ref([])
const page = ref(1)
const totalPages = ref(1)
const error = ref("")
const statCards = ref([])

// 对话监控
const chatFilterUser = ref(null)
const chatDialogRef = ref(null)

// 参与对话的用户列表（去重 + 计数）
const chatUsers = computed(() => {
  const map = new Map()
  for (const c of chats.value) {
    if (!map.has(c.user_id)) {
      map.set(c.user_id, { id: c.user_id, msgCount: 0 })
    }
    map.get(c.user_id).msgCount++
  }
  // 补充用户信息
  const result = []
  for (const [uid, info] of map) {
    const user = users.value.find(u => u.id === uid)
    result.push({
      id: uid,
      username: user?.username || `用户${uid}`,
      nickname: user?.nickname || '',
      msgCount: info.msgCount,
    })
  }
  return result.sort((a, b) => b.msgCount - a.msgCount)
})

// 过滤后的消息
const filteredChats = computed(() => {
  if (!chatFilterUser.value) return chats.value
  return chats.value.filter(c => c.user_id === chatFilterUser.value)
})

// 按会话分组（按用户 + 时间接近的消息聚合成一组）
const chatGroups = computed(() => {
  const msgs = filteredChats.value.filter(m => m.created_at)
  if (!msgs.length) return []
  // 按时间升序排列（最早的在前）
  const sorted = [...msgs].sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
  // 按用户分组
  const groups = []
  let current = { userId: sorted[0].user_id, messages: [] }
  for (const msg of sorted) {
    if (msg.user_id !== current.userId) {
      groups.push(current)
      current = { userId: msg.user_id, messages: [] }
    }
    current.messages.push(msg)
  }
  groups.push(current)
  // 组装展示数据
  return groups.map(g => {
    const user = users.value.find(u => u.id === g.userId)
    const userName = user?.nickname || user?.username || `用户${g.userId}`
    const times = g.messages.map(m => new Date(m.created_at)).filter(d => !isNaN(d.getTime()))
    if (!times.length) {
      return { userId: g.userId, userName, messages: g.messages, timeRange: '' }
    }
    const minT = new Date(Math.min(...times))
    const maxT = new Date(Math.max(...times))
    return {
      userId: g.userId,
      userName,
      messages: g.messages,
      timeRange: formatTimeRange(minT, maxT),
    }
  })
})

function formatChatTime(ts) {
  if (!ts) return '--'
  const d = new Date(ts)
  if (isNaN(d.getTime())) return String(ts).slice(0, 19)
  const MM = String(d.getMonth() + 1).padStart(2, '0')
  const DD = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${MM}-${DD} ${hh}:${mm}:${ss}`
}

function formatTimeRange(t1, t2) {
  if (!t1 || !t2 || isNaN(t1.getTime()) || isNaN(t2.getTime())) return ''
  const sameDay = t1.toDateString() === t2.toDateString()
  const h1 = String(t1.getHours()).padStart(2, '0')
  const m1 = String(t1.getMinutes()).padStart(2, '0')
  const h2 = String(t2.getHours()).padStart(2, '0')
  const m2 = String(t2.getMinutes()).padStart(2, '0')
  if (sameDay) return `${h1}:${m1} ~ ${h2}:${m2}`
  const MM1 = String(t1.getMonth() + 1).padStart(2, '0')
  const DD1 = String(t1.getDate()).padStart(2, '0')
  const MM2 = String(t2.getMonth() + 1).padStart(2, '0')
  const DD2 = String(t2.getDate()).padStart(2, '0')
  return `${MM1}-${DD1} ${h1}:${m1} ~ ${MM2}-${DD2} ${h2}:${m2}`
}

// 用户详情
const selectedUser = ref(null)
const detail = ref({ stats: {}, trend: [], distribution: {}, word_cloud: [] })
const analysis = ref("")
const analysisLoading = ref(false)
const wordCloudCanvas = ref(null)

// ─── 统计 ───
async function loadStats() {
  try {
    const r = await axios.get("/api/admin/stats", { params: { user_id: userStore.userId } })
    const d = r.data
    statCards.value = [
      { label: "总用户数", value: d.user_count },
      { label: "情绪记录", value: d.mood_count },
      { label: "对话消息", value: d.chat_count },
      { label: "今日记录", value: d.today_mood_count },
    ]
  } catch { error.value = "加载统计失败" }
}

// ─── 用户列表 ───
async function loadUsers() {
  try {
    const r = await axios.get("/api/admin/users", {
      params: { user_id: userStore.userId, page: page.value, size: 20 },
    })
    users.value = r.data.users
    totalPages.value = Math.ceil(r.data.total / 20)
  } catch { error.value = "加载用户失败" }
}

// ─── 选择用户 ───
async function selectUser(u) {
  selectedUser.value = u
  analysis.value = ""
  try {
    const r = await axios.get(`/api/admin/user-detail/${u.id}`, {
      params: { user_id: userStore.userId, days: 30 },
    })
    detail.value = r.data
  } catch { error.value = "加载用户详情失败" }
  // 自动加载 AI 分析
  loadAnalysis()
}

// ─── AI 心理分析 ───
async function loadAnalysis() {
  if (!selectedUser.value) return
  analysisLoading.value = true
  analysis.value = ""
  try {
    const r = await axios.get(`/api/admin/user-analysis/${selectedUser.value.id}`, {
      params: { user_id: userStore.userId },
    })
    analysis.value = r.data.analysis
  } catch {
    analysis.value = "AI 分析暂时不可用，请稍后重试。"
  }
  analysisLoading.value = false
}

// ─── 对话监控 ───
async function loadChats() {
  try {
    const r = await axios.get("/api/admin/chats", {
      params: { user_id: userStore.userId },
    })
    chats.value = r.data
    // 加载完成后滚动到底部
    nextTick(() => {
      if (chatDialogRef.value) {
        chatDialogRef.value.scrollTop = chatDialogRef.value.scrollHeight
      }
    })
  } catch { error.value = "加载对话失败" }
}

// ─── 管理员操作 ───
async function toggleAdmin(u) {
  if (!confirm(`确认${u.is_admin ? '取消' : '设置'}教师【${u.username}】？`)) return
  try {
    await axios.post(`/api/admin/set-admin/${u.id}`, null, {
      params: { user_id: userStore.userId },
    })
    loadUsers()
    if (selectedUser.value?.id === u.id) selectUser({ ...u, is_admin: !u.is_admin })
  } catch { error.value = "操作失败" }
}

async function deleteUser(u) {
  if (!confirm(`确认删除用户【${u.username}】？此操作不可恢复！`)) return
  try {
    await axios.delete(`/api/admin/users/${u.id}`, {
      params: { user_id: userStore.userId },
    })
    if (selectedUser.value?.id === u.id) selectedUser.value = null
    loadUsers()
    loadStats()
  } catch { error.value = "删除失败" }
}

async function resetUserPwd(u) {
  if (!confirm(`确认将用户【${u.username}】的密码重置为初始密码 123456 吗？`)) return
  try {
    await resetPassword(u.id, userStore.userId, "123456")
    alert(`已将 ${u.username} 的密码重置为 123456`)
    loadUsers()
  } catch (e) {
    error.value = e.response?.data?.detail || "重置密码失败"
  }
}

function handleBack() {
  if (selectedUser.value) {
    selectedUser.value = null
  } else {
    router.push("/")
  }
}

function handleLogout() {
  userStore.logout()
  router.push("/login")
}

// ─── 工具函数 ───
const sortedDist = computed(() => {
  const d = detail.value.distribution || {}
  return Object.fromEntries(Object.entries(d).sort((a, b) => b[1] - a[1]))
})

function getDistPct(count) {
  const total = Object.values(detail.value.distribution || {}).reduce((a, b) => a + b, 0)
  return total ? (count / total * 100) : 0
}

function getEmoji(label) {
  return { "开心": "😊", "平静": "😌", "焦虑": "😰", "难过": "😢", "愤怒": "😡" }[label] || "🙂"
}

function getMoodColor(label) {
  return { "开心": "#6DB58B", "平静": "#7FB3A6", "焦虑": "#E8C468", "难过": "#8EAFC4", "愤怒": "#D4766A" }[label] || "#ccc"
}

function getScoreColor(score) {
  if (score >= 7) return "#6DB58B"
  if (score >= 5) return "#7FB3A6"
  if (score >= 3) return "#E8C468"
  return "#D4766A"
}

// ─── 爆炸式词云渲染（横竖交错、无重叠）───
const morandiColors = [
  "#5A7A6E", "#6B9182", "#8BB5A4",
  "#7BA3C0", "#95B0C8", "#6B8095",
  "#A8B87A", "#C4D095",
  "#D4C88F", "#E0D8A8",
  "#9580A0", "#B5A5BF",
  "#A08878", "#BCA89A",
  "#8FA095", "#B0C0B5",
]

function renderWordCloud() {
  const canvas = wordCloudCanvas.value
  if (!canvas || !detail.value.word_cloud?.length) return

  const dpr = window.devicePixelRatio || 1
  const rect = canvas.parentElement.getBoundingClientRect()
  const W = rect.width - 32
  const H = 340
  canvas.width = W * dpr
  canvas.height = H * dpr
  canvas.style.width = W + 'px'
  canvas.style.height = H + 'px'

  const ctx = canvas.getContext('2d')
  ctx.scale(dpr, dpr)
  ctx.clearRect(0, 0, W, H)

  const words = detail.value.word_cloud.slice(0, 35)
  const maxCount = words[0].count
  const minCount = words[words.length - 1].count

  // 为每个词计算属性
  const items = words.map((w, i) => {
    const ratio = maxCount === minCount ? 0.5 : (w.count - minCount) / (maxCount - minCount)
    return {
      text: w.word,
      fontSize: 15 + ratio * 34,
      color: morandiColors[i % morandiColors.length],
      weight: ratio >= 0.75 ? 700 : ratio >= 0.45 ? 600 : 400,
    }
  })

  // 大词先放，保证高频词占据中心好位置
  items.sort((a, b) => b.fontSize - a.fontSize)

  const placed = []
  const cx = W / 2
  const cy = H / 2

  for (const item of items) {
    // 前3个高频词横排，之后交错竖排
    const idx = items.indexOf(item)
    const isVertical = idx >= 3 && idx % 2 === 0

    ctx.font = `${item.weight} ${item.fontSize}px "PingFang SC", "Microsoft YaHei", sans-serif`
    const tm = ctx.measureText(item.text)
    // 实际占据的宽高（考虑旋转后）
    const charH = item.fontSize * 1.15
    let tw, th
    if (isVertical) {
      // 竖排：宽度=字高，高度=文字宽度
      tw = charH + 4
      th = tm.width + 4
    } else {
      tw = tm.width + 6
      th = charH + 4
    }

    // 螺旋搜索不重叠位置
    let found = false
    let angle = Math.random() * Math.PI * 2
    let r = 0
    const gap = 5

    while (!found && r < Math.max(W, H) * 0.6) {
      const px = cx + Math.cos(angle) * r
      const py = cy + Math.sin(angle) * r

      // 边界检查
      if (px - tw/2 >= 2 && px + tw/2 <= W - 2 && py - th/2 >= 2 && py + th/2 <= H - 2) {
        let overlap = false
        for (const p of placed) {
          if (Math.abs(px - p.x) < (tw + p.w)/2 + gap && Math.abs(py - p.y) < (th + p.h)/2 + gap) {
            overlap = true
            break
          }
        }
        if (!overlap) {
          item.x = px
          item.y = py
          item.isVertical = isVertical
          placed.push({ x: px, y: py, w: tw, h: th })
          found = true
        }
      }
      angle += 0.5
      r += 1.2
    }

    // 如果还找不到，跳过这个词
    if (!found) {
      item.x = null
      item.y = null
    }
  }

  // 绘制词汇
  for (const item of items) {
    if (item.x == null || item.y == null) continue
    ctx.save()
    ctx.font = `${item.weight} ${item.fontSize}px "PingFang SC", "Microsoft YaHei", sans-serif`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillStyle = item.color

    if (item.isVertical) {
      // 竖排：逐字从上往下画
      const chars = item.text.split('')
      const totalH = chars.length * item.fontSize * 1.15
      const startY = item.y - totalH / 2 + item.fontSize * 0.575
      for (let ci = 0; ci < chars.length; ci++) {
        ctx.fillText(chars[ci], item.x, startY + ci * item.fontSize * 1.15)
      }
    } else {
      // 横排
      ctx.fillText(item.text, item.x, item.y)
    }
    ctx.restore()
  }
}

watch(() => detail.value.word_cloud, () => {
  nextTick(renderWordCloud)
}, { flush: 'post' })

onMounted(() => {
  if (!userStore.isAdmin) {
    error.value = "请用教师账号登录"
    return
  }
  loadStats()
  loadUsers()
})
</script>

<style scoped>
.admin-page { padding: 16px; padding-bottom: 40px; }
.admin-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.admin-header h2 { font-size: 20px; }
.back-btn, .logout-btn { padding: 6px 14px; background: var(--hover); border-radius: 8px; font-size: 13px; transition: background 0.2s; }
.back-btn:hover, .logout-btn:hover { background: #D8E4DB; }

.error-screen { text-align: center; padding: 60px 20px; color: var(--danger); font-size: 16px; }

/* 统计卡片 */
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px; }
.stat-card { background: var(--card); border-radius: 14px; padding: 14px 10px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
.stat-value { font-size: 24px; font-weight: bold; color: var(--primary); }
.stat-label { font-size: 11px; color: var(--text-secondary); margin-top: 4px; }

/* Tab */
.tab-bar { display: flex; gap: 8px; margin-bottom: 16px; }
.tab-bar button { padding: 8px 20px; border-radius: 8px; background: var(--hover); font-size: 14px; transition: background 0.2s; }
.tab-bar button.active { background: var(--primary); color: white; }

/* 用户列表 */
.users-section { display: flex; gap: 16px; position: relative; }
.user-list { flex: 0 0 320px; min-width: 280px; }
.user-item {
  display: flex; align-items: center; gap: 12px;
  padding: 12px; background: var(--card); border-radius: 12px;
  margin-bottom: 8px; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  transition: all 0.2s; border: 2px solid transparent;
}
.user-item:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.user-item.selected { border-color: var(--primary); background: #EDF5F0; }
.user-avatar {
  width: 40px; height: 40px; border-radius: 50%;
  background: linear-gradient(135deg, #7FB3A6, #3D6B5E);
  color: white; font-size: 16px; font-weight: bold;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.user-info { flex: 1; min-width: 0; }
.user-name { display: block; font-size: 14px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.user-meta { display: block; font-size: 11px; color: #aaa; margin-top: 2px; }
.user-actions { display: flex; gap: 4px; flex-shrink: 0; }
.arrow { color: #ccc; font-size: 18px; }
.panel-header { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.panel-header h3 { font-size: 15px; }
.btn-back-list { padding: 4px 10px; background: var(--hover); border-radius: 6px; font-size: 12px; }
.btn-sm { padding: 4px 8px; border-radius: 6px; font-size: 11px; background: var(--hover); white-space: nowrap; transition: background 0.2s; }
.btn-sm:hover { background: #D8E4DB; }
.btn-sm.danger { background: #F5E8E5; color: #D4766A; }
.btn-sm.danger:hover { background: #EDDCD8; }
.btn-sm.warn { background: #FFF8E5; color: #C49B3A; }
.btn-sm.warn:hover { background: #F5EDD0; }
.user-pwd { color: #D4766A; font-weight: 500; }
.pagination { display: flex; gap: 12px; align-items: center; justify-content: center; margin-top: 12px; font-size: 13px; }
.empty, .empty-small { color: #bbb; font-size: 13px; text-align: center; padding: 16px 0; }

/* ====== 详情面板 ====== */
.detail-panel {
  flex: 1; min-width: 0;
  background: var(--card); border-radius: 16px;
  padding: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  max-height: calc(100vh - 200px); overflow-y: auto;
}

.detail-header { display: flex; align-items: center; gap: 14px; margin-bottom: 20px; }
.detail-avatar {
  width: 52px; height: 52px; border-radius: 50%;
  background: linear-gradient(135deg, #7FB3A6, #3D6B5E);
  color: white; font-size: 22px; font-weight: bold;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 3px 10px rgba(91,140,126,0.3);
}
.detail-header h3 { font-size: 18px; margin: 0; }
.detail-meta { font-size: 12px; color: #aaa; margin-top: 2px; }

.detail-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px; }
.detail-stat { background: var(--bg); border-radius: 10px; padding: 12px 8px; text-align: center; }
.ds-value { font-size: 22px; font-weight: bold; color: var(--primary); }
.ds-label { font-size: 11px; color: var(--text-secondary); margin-top: 4px; }

.chart-section { margin-bottom: 20px; }
.chart-section h4 { font-size: 15px; margin-bottom: 10px; }

/* 趋势图 */
.trend-chart { background: var(--bg); border-radius: 12px; padding: 14px 10px; }
.trend-area { display: flex; align-items: flex-end; gap: 4px; position: relative; height: 120px; }
.trend-grid { position: absolute; left: 0; right: 0; height: 1px; background: var(--border); }
.trend-col { flex: 1; display: flex; flex-direction: column; align-items: center; position: relative; z-index: 1; min-width: 0; }
.trend-track { flex: 1; width: 100%; display: flex; align-items: flex-end; }
.trend-bar {
  width: 60%; max-width: 28px; border-radius: 4px 4px 0 0;
  min-height: 3px; transition: height 0.5s ease;
}
.trend-val { font-size: 9px; color: var(--text-secondary); margin-bottom: 1px; white-space: nowrap; }
.trend-date { font-size: 9px; color: #bbb; margin-top: 2px; white-space: nowrap; }

/* 情绪分布 */
.dist-bars { background: var(--bg); border-radius: 12px; padding: 14px; }
.dist-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.dist-row:last-child { margin-bottom: 0; }
.dist-emoji { font-size: 16px; width: 24px; text-align: center; }
.dist-label { width: 36px; font-size: 13px; flex-shrink: 0; }
.dist-track { flex: 1; height: 8px; background: var(--border); border-radius: 4px; overflow: hidden; }
.dist-fill { height: 100%; border-radius: 4px; transition: width 0.5s ease; }
.dist-count { width: 36px; font-size: 11px; color: #999; text-align: right; }

/* 词云 */
.word-cloud-wrap {
  background: var(--bg); border-radius: 12px; padding: 16px;
  min-height: 320px; display: flex; align-items: center; justify-content: center;
  position: relative;
}
.word-cloud-canvas {
  width: 100%;
  display: block;
}

/* AI 分析 */
.analysis-card {
  background: var(--bg); border-radius: 12px; padding: 16px;
  font-size: 14px; line-height: 1.8; color: var(--text-secondary);
  border-left: 3px solid var(--primary-light);
  min-height: 80px;
}
.analysis-text { white-space: pre-wrap; }
.analysis-loading { display: flex; gap: 6px; padding: 12px 0; }
.analysis-loading .dot {
  width: 10px; height: 10px; border-radius: 50%; background: var(--primary);
  animation: bounce 1.2s infinite both;
}
.analysis-loading .dot:nth-child(2) { animation-delay: 0.2s; }
.analysis-loading .dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%,100%{opacity:0.3;transform:translateY(0)} 50%{opacity:1;transform:translateY(-4px)} }

.btn-refresh {
  margin-top: 8px; padding: 6px 14px; background: var(--hover);
  border-radius: 8px; font-size: 13px; transition: all 0.2s;
}
.btn-refresh:hover { background: #D8E4DB; }
.btn-refresh:disabled { opacity: 0.5; }

/* 过渡动画 */
.slide-enter-active { transition: all 0.3s ease; }
.slide-leave-active { transition: all 0.2s ease; }
.slide-enter-from { opacity: 0; transform: translateX(20px); }
.slide-leave-to { opacity: 0; transform: translateX(-10px); }

/* ═══════════ 对话监控 — 聊天界面 ═══════════ */
.chat-monitor { display: flex; flex-direction: column; height: calc(100vh - 200px); min-height: 400px; }

/* 用户筛选栏 */
.chat-user-bar {
  display: flex; gap: 8px; flex-wrap: wrap;
  padding: 10px 12px; background: var(--card); border-radius: 14px 14px 0 0;
  border-bottom: 1px solid var(--border); overflow-x: auto;
}
.chat-user-btn {
  padding: 6px 14px; border-radius: 18px; font-size: 13px; white-space: nowrap;
  background: var(--hover); transition: all 0.2s; border: 2px solid transparent;
}
.chat-user-btn:hover { background: #D8E4DB; }
.chat-user-btn.active { background: var(--primary); color: white; }
.chat-user-count {
  display: inline-block; margin-left: 4px; padding: 1px 6px;
  background: rgba(255,255,255,0.25); border-radius: 8px; font-size: 11px;
}

/* 聊天对话区 */
.chat-dialog {
  flex: 1; overflow-y: auto; padding: 16px; background: var(--bg);
  border-radius: 0 0 14px 14px; scroll-behavior: smooth;
}

/* 会话分组 */
.chat-session { margin-bottom: 24px; }
.chat-session:last-child { margin-bottom: 0; }
.chat-session-header {
  display: flex; align-items: center; gap: 8px; margin-bottom: 12px;
  padding: 8px 12px; background: var(--card); border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.chat-session-avatar {
  width: 28px; height: 28px; border-radius: 50%;
  background: linear-gradient(135deg, #7FB3A6, #3D6B5E);
  color: white; font-size: 12px; font-weight: bold;
  display: flex; align-items: center; justify-content: center;
}
.chat-session-name { font-size: 14px; font-weight: 600; }
.chat-session-time { font-size: 11px; color: #aaa; margin-left: auto; }

/* 消息气泡 */
.chat-bubbles { display: flex; flex-direction: column; gap: 14px; }
.chat-bubble-row {
  display: flex; gap: 10px; max-width: 85%;
}
.chat-bubble-row.user { align-self: flex-end; flex-direction: row-reverse; }
.chat-bubble-row.ai { align-self: flex-start; }

.chat-bubble-avatar {
  width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0;
  font-size: 11px; font-weight: bold; color: white;
  display: flex; align-items: center; justify-content: center;
}
.chat-bubble-row.user .chat-bubble-avatar {
  background: linear-gradient(135deg, #7FB3A6, #5B8C7E);
}
.chat-bubble-row.ai .chat-bubble-avatar {
  background: linear-gradient(135deg, #E8C468, #D4A843);
  color: #4A3B15;
}

.chat-bubble-body { display: flex; flex-direction: column; gap: 2px; }
.chat-bubble-meta { display: flex; align-items: center; gap: 6px; font-size: 11px; }
.chat-bubble-row.user .chat-bubble-meta { justify-content: flex-end; }
.chat-bubble-role { font-weight: 600; color: var(--text-secondary); }
.chat-bubble-time { color: #bbb; }

.chat-bubble-content {
  padding: 10px 14px; border-radius: 14px; font-size: 14px; line-height: 1.6;
  word-break: break-word; position: relative; max-width: 100%;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.chat-bubble-content.user {
  background: #6DB58B; color: white;
  border-bottom-right-radius: 4px;
}
.chat-bubble-content.ai {
  background: white; color: var(--text);
  border: 1px solid var(--border);
  border-bottom-left-radius: 4px;
}
.chat-bubble-emotion {
  display: inline-block; margin-left: 6px; padding: 1px 6px;
  background: rgba(255,255,255,0.25); border-radius: 8px;
  font-size: 11px; vertical-align: middle;
}
.chat-bubble-content.ai .chat-bubble-emotion {
  background: rgba(109,181,139,0.12); color: #3D6B5E;
}

/* 旧表格样式（保留备用） */
.data-table { width: 100%; border-collapse: collapse; font-size: 12px; background: var(--card); border-radius: 14px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
.data-table th { background: #F0F4F1; padding: 10px 6px; text-align: left; font-weight: 600; }
.data-table td { padding: 8px 6px; border-bottom: 1px solid var(--border); }
.content-cell { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.role { font-size: 11px; padding: 2px 8px; border-radius: 4px; }
.role.user { background: #E8F0EB; color: #5B8C7E; }
.role.assistant { background: #E0EDE5; color: #3D6B5E; }

/* 响应式：小屏幕时上下排列 */
@media (max-width: 768px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .users-section { flex-direction: column; }
  .user-list { flex: none; width: 100%; }
  .detail-stats { grid-template-columns: repeat(2, 1fr); }
  .data-table { font-size: 11px; }
  .content-cell { max-width: 120px; }
  .chat-monitor { height: calc(100vh - 180px); }
  .chat-bubble-row { max-width: 92%; }
  .chat-bubble-content { font-size: 13px; padding: 8px 12px; }
  .chat-user-btn { padding: 5px 10px; font-size: 12px; }
}

/* 超小屏幕 */
@media (max-width: 400px) {
  .admin-page { padding: 12px; }
  .stats-grid { gap: 6px; }
  .stat-card { padding: 10px 6px; }
  .stat-value { font-size: 18px; }
  .tab-bar button { padding: 6px 12px; font-size: 13px; }
  .user-actions { flex-direction: column; gap: 2px; }
}

/* 大屏幕优化 */
@media (min-width: 1200px) {
  .admin-page { max-width: 1400px; margin: 0 auto; }
  .user-list { flex: 0 0 360px; }
  .detail-panel { padding: 28px; }
  .data-table { font-size: 13px; }
  .content-cell { max-width: 300px; }
}
</style>
