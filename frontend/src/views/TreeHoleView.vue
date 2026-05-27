<template>
  <div class="treehole-page" :class="{ 'inline-mode': inline }">
    <div class="treehole-header" v-if="!inline">
      <button class="back-btn" @click="router.back()">←</button>
      <h1>💌 虚拟树洞</h1>
    </div>
    <div class="inline-title" v-if="inline">
      <h2>💌 虚拟树洞</h2>
    </div>

    <div class="treehole-intro">
      <p>🌿 这里是安全的匿名空间</p>
      <p>没有人知道你是谁，但有人懂你的感受</p>
      <!-- 每日一句温暖 -->
      <div class="daily-warmth" v-if="dailyQuote">
        <span class="dw-icon">💡</span>
        <span class="dw-text">{{ dailyQuote }}</span>
      </div>
      <div class="stats" v-if="stats">
        已有 {{ stats.total_posts }} 位朋友倾诉 · {{ stats.total_resonance }} 次共鸣
      </div>
    </div>

    <!-- AI陪伴入口 + 漂流瓶 -->
    <div class="entry-row">
      <div class="companion-entry half" @click="showCompanions = true">
        <div class="ce-left">
          <span class="ce-emoji">🤗</span>
          <div>
            <div class="ce-title">AI 陪伴聊天</div>
            <div class="ce-desc">选一个角色陪你聊</div>
          </div>
        </div>
        <span class="ce-arrow">→</span>
      </div>
      <div class="companion-entry half bottle" @click="openDriftBottle">
        <div class="ce-left">
          <span class="ce-emoji">🫙</span>
          <div>
            <div class="ce-title">心情漂流瓶</div>
            <div class="ce-desc">捞一个陌生人的心情</div>
          </div>
        </div>
        <span class="ce-arrow">→</span>
      </div>
    </div>

    <!-- 漂流瓶弹窗 -->
    <Transition name="fade">
      <div v-if="showDriftBottle" class="companion-modal" @click.self="showDriftBottle = false">
        <div class="companion-panel drift-panel">
          <div class="cp-header">
            <h3>🫙 捞到一个漂流瓶</h3>
            <button class="cp-close" @click="showDriftBottle = false">✕</button>
          </div>
          <div class="drift-content">
            <div class="drift-mood">{{ getMoodEmoji(driftMood) }} {{ driftMood }}</div>
            <p class="drift-text">{{ driftContent }}</p>
            <div class="drift-hint">—— 来自一位陌生人的心情</div>
          </div>
          <button class="drift-again" @click="openDriftBottle">再捞一个</button>
        </div>
      </div>
    </Transition>

    <!-- AI陪伴选择弹窗 -->
    <Transition name="fade">
      <div v-if="showCompanions" class="companion-modal" @click.self="showCompanions = false">
        <div class="companion-panel">
          <div class="cp-header">
            <h3>选择陪伴角色</h3>
            <button class="cp-close" @click="showCompanions = false">✕</button>
          </div>
          <div class="cp-list">
            <div v-for="c in companions" :key="c.id" class="cp-item" @click="startCompanion(c)">
              <div class="cpi-avatar">{{ c.avatar }}</div>
              <div class="cpi-info">
                <div class="cpi-name">{{ c.name }}</div>
                <div class="cpi-desc">{{ c.desc }}</div>
              </div>
              <span class="cpi-go">→</span>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 陪伴对话界面 -->
    <Transition name="fade">
      <div v-if="companionActive" class="companion-chat">
        <div class="cc-header">
          <button @click="companionActive = false">← 返回树洞</button>
          <span>{{ companionName }}</span>
        </div>
        <div class="cc-messages" ref="chatMessages">
          <div v-for="(msg, i) in companionMsgs" :key="i" class="cc-msg" :class="msg.role">
            <div class="ccm-bubble">{{ msg.content }}</div>
          </div>
          <div v-if="companionTyping" class="cc-msg assistant">
            <div class="ccm-bubble typing">正在输入...</div>
          </div>
        </div>
        <div class="cc-input">
          <input v-model="companionInput" placeholder="说点什么..." @keyup.enter="sendCompanionMsg" />
          <button @click="sendCompanionMsg" :disabled="!companionInput.trim() || companionTyping">发送</button>
        </div>
      </div>
    </Transition>

    <!-- 发布区域 -->
    <div class="post-area" v-if="!companionActive">
      <div class="mood-selector">
        <button v-for="m in moodOptions" :key="m.label" class="mood-btn" :class="{ active: selectedMood === m.label }" @click="selectedMood = m.label">
          {{ m.emoji }} {{ m.label }}
        </button>
      </div>
      <div class="input-row">
        <input v-model="newContent" placeholder="说一说你现在的感受..." @keyup.enter="createPost" />
        <button class="post-btn" @click="createPost" :disabled="!newContent.trim()">发布</button>
      </div>
    </div>

    <!-- 信息流 -->
    <div class="feed" v-if="!companionActive">
      <div v-for="post in posts" :key="post.id" class="treehole-card">
        <div class="thc-mood">{{ getMoodEmoji(post.mood_card) }}</div>
        <div class="thc-body">
          <p class="thc-content">{{ post.content }}</p>
          <div class="thc-footer">
            <span class="thc-time">{{ formatTime(post.created_at) }}</span>
            <button class="thc-resonance" @click="addResonance(post.id)">
              🤝 我也一样 ({{ post.resonance_count }})
            </button>
          </div>
        </div>
      </div>
      <div v-if="!posts.length" class="empty-hint">还没有人发言，做第一个吧~</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { treeholeApi } from '../api/treehole'
import axios from 'axios'

const API = import.meta.env.VITE_API_BASE || ''
const router = useRouter()
const userStore = useUserStore()

const props = defineProps({ inline: { type: Boolean, default: false } })
const emit = defineEmits(['close'])

const posts = ref([])
const newContent = ref('')
const selectedMood = ref('')
const stats = ref(null)

// 每日温暖语录
const WARM_QUOTES = [
  '你今天的努力，是幸运的伏笔。',
  '不必着急赶路，偶尔停下来看看天空也很好。',
  '世界很大，你的心事有人愿意听。',
  '今天的你，已经比昨天更勇敢了。',
  '累了就休息，不是放弃，是为了走得更远。',
  '你值得被温柔以待，尤其是被自己。',
  '没有白走的路，每一步都算数。',
  '允许自己不开心，也是爱自己的一种方式。',
  '你比你想象的更强大。',
  '慢慢来，谁还没有一个努力的过程。',
  '星星发亮是为了让每个人找到自己的星星。',
  '今天的不开心就止于此吧，明天依旧光芒万丈。',
]
const dailyQuote = ref('')

// 漂流瓶
const showDriftBottle = ref(false)
const driftContent = ref('')
const driftMood = ref('')

// AI陪伴
const showCompanions = ref(false)
const companions = ref([])
const companionActive = ref(false)
const companionName = ref('')
const companionId = ref('')
const companionMsgs = ref([])
const companionInput = ref('')
const companionTyping = ref(false)
const chatMessages = ref(null)

const moodOptions = [
  { emoji: '😰', label: '蕉绿了' },
  { emoji: '😢', label: 'emo了' },
  { emoji: '😡', label: '蚌埠住了' },
  { emoji: '😴', label: '电量不足' },
  { emoji: '🤔', label: '整个人不好' },
  { emoji: '😌', label: '还好吧' },
  { emoji: '🥳', label: '开心到飞起' },
  { emoji: '✨', label: '被治愈了' },
  { emoji: '💪', label: '支棱起来了' },
]

function getMoodEmoji(label) {
  const m = moodOptions.find(o => o.label === label)
  return m ? m.emoji : '💚'
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
  return Math.floor(diff / 86400000) + '天前'
}

const TH_STORAGE_KEY = 'shengyu_treehole_posts'
const TH_RESONATED_KEY = 'shengyu_treehole_resonated'

function loadLocalPosts() {
  try {
    const saved = localStorage.getItem(TH_STORAGE_KEY)
    if (saved) return JSON.parse(saved)
  } catch {}
  return []
}
function saveLocalPosts(list) {
  localStorage.setItem(TH_STORAGE_KEY, JSON.stringify(list))
}
function getResonatedSet() {
  try {
    return new Set(JSON.parse(localStorage.getItem(TH_RESONATED_KEY) || '[]'))
  } catch { return new Set() }
}
function addResonatedId(id) {
  const set = getResonatedSet()
  set.add(id)
  localStorage.setItem(TH_RESONATED_KEY, JSON.stringify([...set]))
}

async function createPost() {
  const content = newContent.value.trim()
  if (!content) return
  const mood = selectedMood.value || '还好吧'

  const post = {
    id: Date.now(),
    content,
    mood_card: mood,
    created_at: new Date().toISOString(),
    resonance_count: 0,
  }

  // 优先走 API
  try {
    const res = await treeholeApi.createPost(Number(userStore.userId), mood, content)
    newContent.value = ''
    selectedMood.value = ''
    loadFeed()
    if (res.data?.warm_reply) {
      alert('💌 来自树洞的温暖：\n\n' + res.data.warm_reply)
    }
  } catch (e) {
    // API 失败则保存到本地
    const local = loadLocalPosts()
    local.unshift(post)
    saveLocalPosts(local)
    posts.value = local
    newContent.value = ''
    selectedMood.value = ''
  }
}

async function addResonance(postId) {
  const resonated = getResonatedSet()
  if (resonated.has(postId)) {
    alert('你已经共鸣过这条啦 💚')
    return
  }

  try {
    const res = await treeholeApi.addResonance(postId, Number(userStore.userId))
    if (res.data?.success) {
      const post = posts.value.find(p => p.id === postId)
      if (post) post.resonance_count = res.data.resonance_count
      addResonatedId(postId)
    }
  } catch (e) {
    // 本地模式：直接+1
    const post = posts.value.find(p => p.id === postId)
    if (post) {
      post.resonance_count = (post.resonance_count || 0) + 1
      addResonatedId(postId)
      // 同步保存到 localStorage
      const local = loadLocalPosts()
      const lp = local.find(p => p.id === postId)
      if (lp) lp.resonance_count = post.resonance_count
      saveLocalPosts(local)
    }
  }
}

async function loadFeed() {
  try {
    const res = await treeholeApi.getFeed(Number(userStore.userId))
    const apiPosts = res.data?.posts || []
    // 合并本地和 API 数据（本地优先，因为可能包含离线发布的内容）
    const local = loadLocalPosts()
    const merged = [...local]
    for (const p of apiPosts) {
      if (!merged.find(m => m.id === p.id)) merged.push(p)
    }
    merged.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    posts.value = merged
    saveLocalPosts(merged)
  } catch (e) {
    console.error('加载失败', e)
    posts.value = loadLocalPosts()
  }
}

async function loadStats() {
  try {
    const res = await axios.get(`${API}/api/treehole/stats`)
    stats.value = res.data
  } catch (e) { /* ignore */ }
}

async function loadCompanions() {
  try {
    const res = await axios.get(`${API}/api/companion/list`)
    companions.value = res.data?.companions || []
  } catch (e) { /* ignore */ }
}

async function startCompanion(c) {
  showCompanions.value = false
  companionId.value = c.id
  companionName.value = c.name
  companionMsgs.value = []
  companionActive.value = true

  try {
    const res = await axios.post(`${API}/api/companion/start`, null, {
      params: { user_id: Number(userStore.userId), character_id: c.id }
    })
    if (res.data?.greeting) {
      companionMsgs.value.push({ role: 'assistant', content: res.data.greeting })
    }
  } catch (e) {
    companionMsgs.value.push({ role: 'assistant', content: `你好呀！我是${c.name}，有什么想和我聊的吗？` })
  }
}

async function sendCompanionMsg() {
  if (!companionInput.value.trim() || companionTyping.value) return

  const content = companionInput.value
  companionMsgs.value.push({ role: 'user', content })
  companionInput.value = ''
  companionTyping.value = true

  await nextTick()
  if (chatMessages.value) {
    chatMessages.value.scrollTop = chatMessages.value.scrollHeight
  }

  try {
    const res = await axios.post(`${API}/api/companion/chat`, {
      user_id: Number(userStore.userId),
      character_id: companionId.value,
      content: content,
    })
    if (res.data?.reply) {
      companionMsgs.value.push({ role: 'assistant', content: res.data.reply })
    }
  } catch (e) {
    companionMsgs.value.push({ role: 'assistant', content: '抱歉，我现在有点忙，稍后再聊~' })
  }

  companionTyping.value = false
  await nextTick()
  if (chatMessages.value) {
    chatMessages.value.scrollTop = chatMessages.value.scrollHeight
  }
}

onMounted(() => {
  loadFeed()
  loadStats()
  loadCompanions()
  // 根据日期选择每日语录（每天一样）
  const dayIndex = new Date().getDate() % WARM_QUOTES.length
  dailyQuote.value = WARM_QUOTES[dayIndex]
})

// 漂流瓶：随机捞一条别人的心情
function openDriftBottle() {
  if (!posts.value.length) {
    alert('树洞还是空的，来做第一个倾诉的人吧~')
    return
  }
  const randomPost = posts.value[Math.floor(Math.random() * posts.value.length)]
  driftContent.value = randomPost.content
  driftMood.value = randomPost.mood_card
  showDriftBottle.value = true
}
</script>

<style scoped>
.treehole-page {
  min-height: 100vh;
  background: #F5F0EC;
  padding-bottom: 80px;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.treehole-header {
  display: flex; align-items: center; gap: 12px;
  padding: 16px 20px; padding-top: max(16px, env(safe-area-inset-top));
  background: white; border-bottom: 1px solid #eee;
}
.treehole-header h1 { font-size: 18px; font-weight: 600; color: #3D6B5E; margin: 0; }
.back-btn { background: none; border: none; font-size: 20px; color: #5B8C7E; cursor: pointer; }

.treehole-intro { padding: 20px; text-align: center; }
.treehole-intro p { margin: 4px 0; font-size: 13px; color: #7A8B7E; }
.stats { font-size: 11px; color: #aaa; margin-top: 8px; }

/* 每日温暖 */
.daily-warmth {
  display: flex; align-items: center; justify-content: center;
  gap: 6px; margin-top: 10px; padding: 8px 14px;
  background: rgba(91,140,126,0.08); border-radius: 20px;
  max-width: 90%; margin-left: auto; margin-right: auto;
}
.dw-icon { font-size: 14px; }
.dw-text { font-size: 12px; color: #5B8C7E; font-style: italic; }

/* 入口行 */
.entry-row { display: flex; gap: 10px; margin: 0 16px 16px; }
.companion-entry {
  padding: 16px; background: white;
  border-radius: 14px; display: flex; align-items: center;
  justify-content: space-between; cursor: pointer;
  transition: all 0.2s; border: 1px solid #e8e0d8;
}
.companion-entry.half { flex: 1; margin: 0; }
.companion-entry.bottle { background: linear-gradient(135deg, #fff, #f8f4f0); }
.companion-entry:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
.ce-left { display: flex; align-items: center; gap: 12px; }
.ce-emoji { font-size: 28px; }
.ce-title { font-size: 14px; font-weight: 600; color: #3D6B5E; }
.ce-desc { font-size: 12px; color: #888; margin-top: 2px; }
.ce-arrow { font-size: 18px; color: #5B8C7E; }

/* 陪伴选择弹窗 */
.companion-modal {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: flex-end; justify-content: center; z-index: 100;
}
.companion-panel {
  background: white; border-radius: 20px 20px 0 0; width: 100%; max-width: 480px;
  padding: 20px; max-height: 70vh;
}
.cp-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.cp-header h3 { font-size: 16px; color: #3D6B5E; margin: 0; }
.cp-close { background: none; border: none; font-size: 18px; color: #999; cursor: pointer; }
.cp-item {
  display: flex; align-items: center; gap: 14px; padding: 14px;
  border-radius: 12px; cursor: pointer; transition: all 0.2s;
}
.cp-item:hover { background: #f5f0ec; }
.cpi-avatar { width: 48px; height: 48px; border-radius: 50%; background: #E8D5B7; display: flex; align-items: center; justify-content: center; font-size: 24px; }
.cpi-info { flex: 1; }
.cpi-name { font-size: 15px; font-weight: 600; color: #333; }
.cpi-desc { font-size: 12px; color: #888; margin-top: 4px; }
.cpi-go { color: #5B8C7E; font-size: 16px; }

/* 漂流瓶弹窗 */
.drift-panel { text-align: center; }
.drift-content { padding: 20px 10px; }
.drift-mood { font-size: 13px; color: #5B8C7E; margin-bottom: 12px; }
.drift-text { font-size: 16px; color: #333; line-height: 1.8; font-style: italic; margin: 0 0 16px; }
.drift-hint { font-size: 11px; color: #bbb; }
.drift-again {
  width: 100%; padding: 12px; border-radius: 12px; border: none;
  background: #5B8C7E; color: white; font-size: 14px; cursor: pointer;
  margin-top: 8px;
}

/* 陪伴对话界面 */
.companion-chat {
  position: fixed; inset: 0; background: #F5F0EC; z-index: 90;
  display: flex; flex-direction: column;
}
.cc-header {
  padding: 16px 20px; padding-top: max(16px, env(safe-area-inset-top));
  background: white; border-bottom: 1px solid #eee;
  display: flex; align-items: center; gap: 16px;
}
.cc-header button { background: none; border: none; font-size: 14px; color: #5B8C7E; cursor: pointer; }
.cc-header span { font-size: 16px; font-weight: 600; color: #3D6B5E; }

.cc-messages { flex: 1; overflow-y: auto; padding: 16px; }
.cc-msg { margin-bottom: 12px; display: flex; }
.cc-msg.user { justify-content: flex-end; }
.cc-msg.assistant { justify-content: flex-start; }
.ccm-bubble {
  max-width: 75%; padding: 12px 16px; border-radius: 16px;
  font-size: 14px; line-height: 1.6;
}
.cc-msg.user .ccm-bubble { background: #5B8C7E; color: white; border-bottom-right-radius: 4px; }
.cc-msg.assistant .ccm-bubble { background: white; color: #333; border-bottom-left-radius: 4px; }
.ccm-bubble.typing { color: #999; font-style: italic; }

.cc-input {
  padding: 12px 16px; background: white; border-top: 1px solid #eee;
  display: flex; gap: 8px;
}
.cc-input input {
  flex: 1; padding: 10px 14px; border-radius: 20px;
  border: 1px solid #e0e0e0; font-size: 14px; outline: none;
}
.cc-input input:focus { border-color: #5B8C7E; }
.cc-input button {
  padding: 10px 18px; border-radius: 20px; border: none;
  background: #5B8C7E; color: white; font-size: 14px; cursor: pointer;
}
.cc-input button:disabled { background: #ccc; }

/* 发布区域 */
.post-area { margin: 0 16px 16px; padding: 16px; background: white; border-radius: 14px; }
.mood-selector { display: flex; gap: 8px; margin-bottom: 12px; overflow-x: auto; padding-bottom: 4px; }
.mood-selector::-webkit-scrollbar { display: none; }
.mood-btn {
  padding: 6px 12px; border-radius: 20px; border: 1px solid #e0e0e0;
  background: #f8f8f8; font-size: 13px; cursor: pointer; transition: all 0.2s;
}
.mood-btn.active { background: #5B8C7E; color: white; border-color: #5B8C7E; }

.input-row { display: flex; gap: 8px; }
.input-row input {
  flex: 1; padding: 10px 14px; border-radius: 20px;
  border: 1px solid #e0e0e0; font-size: 14px; outline: none;
}
.input-row input:focus { border-color: #5B8C7E; }
.post-btn {
  padding: 10px 18px; border-radius: 20px; border: none;
  background: #5B8C7E; color: white; font-size: 14px; font-weight: 500;
  cursor: pointer; transition: all 0.2s;
}
.post-btn:disabled { background: #ccc; }
.post-btn:hover:not(:disabled) { background: #4a7a6e; }

.feed { padding: 0 16px; }
.treehole-card {
  display: flex; gap: 12px; padding: 16px;
  background: white; border-radius: 14px; margin-bottom: 10px;
}
.thc-mood { font-size: 28px; flex-shrink: 0; }
.thc-body { flex: 1; }
.thc-content { font-size: 14px; color: #333; line-height: 1.6; margin: 0 0 10px; }
.thc-footer { display: flex; justify-content: space-between; align-items: center; }
.thc-time { font-size: 11px; color: #bbb; }
.thc-resonance {
  background: none; border: none; font-size: 12px; color: #5B8C7E;
  cursor: pointer; padding: 4px 10px; border-radius: 12px; transition: all 0.2s;
}
.thc-resonance:hover { background: rgba(91,140,126,0.1); }
.empty-hint { text-align: center; padding: 40px; font-size: 13px; color: #999; }

/* 过渡动画 */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* inline 弹窗模式 - 适配深色背景 */
.treehole-page.inline-mode { background: transparent; padding: 0; min-height: auto; }
.treehole-page.inline-mode .treehole-intro p { color: rgba(232,226,216,0.6); }
.treehole-page.inline-mode .daily-warmth { background: rgba(127,179,166,0.1); }
.treehole-page.inline-mode .dw-text { color: #7FB3A6; }
.treehole-page.inline-mode .stats { color: rgba(232,226,216,0.4); }
.treehole-page.inline-mode .companion-entry { background: rgba(255,255,255,0.06); border-color: rgba(255,255,255,0.08); }
.treehole-page.inline-mode .companion-entry.bottle { background: linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03)); }
.treehole-page.inline-mode .ce-title { color: #7FB3A6; }
.treehole-page.inline-mode .ce-desc { color: rgba(232,226,216,0.5); }
.treehole-page.inline-mode .post-area { background: rgba(255,255,255,0.06); }
.treehole-page.inline-mode .mood-btn { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.1); color: rgba(232,226,216,0.7); }
.treehole-page.inline-mode .mood-btn.active { background: #5B8C7E; color: white; border-color: #5B8C7E; }
.treehole-page.inline-mode .input-row input { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.1); color: #E8E2D8; }
.treehole-page.inline-mode .input-row input::placeholder { color: rgba(232,226,216,0.35); }
.treehole-page.inline-mode .treehole-card { background: rgba(255,255,255,0.06); }
.treehole-page.inline-mode .thc-content { color: rgba(232,226,216,0.85); }
.treehole-page.inline-mode .thc-time { color: rgba(232,226,216,0.35); }
.treehole-page.inline-mode .thc-resonance { color: #7FB3A6; }
.treehole-page.inline-mode .empty-hint { color: rgba(232,226,216,0.35); }
.inline-title { text-align: center; margin-bottom: 16px; }
.inline-title h2 { margin: 0; font-size: 18px; color: #E8E2D8; }
</style>
