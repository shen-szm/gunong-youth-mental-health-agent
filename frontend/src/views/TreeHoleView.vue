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
      <div class="stats" v-if="stats">
        已有 {{ stats.total_posts }} 位朋友倾诉 · {{ stats.total_resonance }} 次共鸣
      </div>
    </div>

    <!-- AI陪伴入口 -->
    <div class="companion-entry" @click="showCompanions = true">
      <div class="ce-left">
        <span class="ce-emoji">🤗</span>
        <div>
          <div class="ce-title">AI 陪伴聊天</div>
          <div class="ce-desc">选择一个角色，陪你聊聊天</div>
        </div>
      </div>
      <span class="ce-arrow">→</span>
    </div>

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
        <button class="post-btn" @click="createPost" :disabled="!newContent.trim() || !selectedMood">发布</button>
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
  { emoji: '😰', label: '焦虑' },
  { emoji: '😢', label: '难过' },
  { emoji: '😡', label: '愤怒' },
  { emoji: '😴', label: '疲惫' },
  { emoji: '🤔', label: '迷茫' },
  { emoji: '😌', label: '平静' },
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

async function createPost() {
  if (!newContent.value.trim() || !selectedMood.value) return
  try {
    const res = await treeholeApi.createPost(Number(userStore.userId), selectedMood.value, newContent.value)
    newContent.value = ''
    selectedMood.value = ''
    loadFeed()
    // 显示AI温暖回复
    if (res.data?.warm_reply) {
      alert('💌 来自树洞的温暖：\n\n' + res.data.warm_reply)
    }
  } catch (e) {
    console.error('发布失败', e)
  }
}

async function addResonance(postId) {
  try {
    const res = await treeholeApi.addResonance(postId, Number(userStore.userId))
    if (res.data.success) {
      const post = posts.value.find(p => p.id === postId)
      if (post) post.resonance_count = res.data.resonance_count
    }
  } catch (e) {
    console.error('共鸣失败', e)
  }
}

async function loadFeed() {
  try {
    const res = await treeholeApi.getFeed(Number(userStore.userId))
    posts.value = res.data?.posts || []
  } catch (e) {
    console.error('加载失败', e)
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
})
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

/* AI陪伴入口 */
.companion-entry {
  margin: 0 16px 16px; padding: 16px; background: white;
  border-radius: 14px; display: flex; align-items: center;
  justify-content: space-between; cursor: pointer;
  transition: all 0.2s; border: 1px solid #e8e0d8;
}
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
.mood-selector { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
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

/* inline 弹窗模式 */
.treehole-page.inline-mode { background: transparent; padding: 0; min-height: auto; }
.inline-title { text-align: center; margin-bottom: 16px; }
.inline-title h2 { margin: 0; font-size: 18px; color: #333; }
</style>
