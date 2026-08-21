<template>
  <div class="chat-page">
    <!-- 顶部导航 -->
    <div class="chat-header">
      <button class="back-btn" @click="router.back()">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
      </button>
      <div class="header-center">
        <div class="ai-avatar">🫧</div>
        <div>
          <div class="ai-name">咕哝</div>
          <div class="ai-status">
            <span class="status-dot" :class="{thinking: loading}"></span>
            {{ loading ? '正在思考...' : '在线，随时倾听' }}
          </div>
        </div>
      </div>
      <div class="header-right"></div>
    </div>

    <!-- 消息列表 -->
    <div class="chat-messages" ref="msgBox">
      <!-- 欢迎语 -->
      <div class="welcome-wrap" v-if="messages.length === 0">
        <div class="welcome-avatar">🫧</div>
        <div class="welcome-bubble">
          <p>嘿，你来了 👋</p>
          <p>今天怎么样？有什么想聊的，我都在这里。</p>
        </div>
      </div>

      <div v-for="(m, i) in messages" :key="i" :class="['msg-row', m.role]">
        <div class="msg-avatar" v-if="m.role === 'assistant'">🫧</div>
        <div class="bubble-wrap">
          <!-- 情绪标签 -->
          <div v-if="m.emotion" class="emotion-tag">
            <span>{{ getEmotionEmoji(m.emotion) }}</span>
            <span>{{ m.emotion }}</span>
          </div>
          <div class="bubble">
            <!-- AI 回复打字效果 -->
            <span>{{ m.content }}</span>
          </div>
          <!-- TTS 按钮 -->
          <button v-if="m.role === 'assistant' && !m.typing" class="tts-btn" @click="playTTS(m.content)" :class="{playing: ttsPlaying === i}">
            <svg v-if="ttsPlaying !== i" viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.8-1-3.3-2.5-4v8c1.5-.7 2.5-2.2 2.5-4z"/></svg>
            <svg v-else viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
          </button>
        </div>
      </div>

      <!-- 加载动画 -->
      <div v-if="loading" class="msg-row assistant">
        <div class="msg-avatar">🫧</div>
        <div class="bubble-wrap">
          <div class="bubble typing-bubble">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 快捷情绪按钮 -->
    <div class="quick-wrap">
      <div class="quick-scroll">
        <button v-for="e in emotions" :key="e.text" class="quick-btn" @click="sendMsg(e.text)">
          <span>{{ e.emoji }}</span> {{ e.text }}
        </button>
      </div>
    </div>

    <!-- 输入栏 -->
    <div class="input-bar">
      <button class="voice-btn" :class="{ recording }" @click="toggleVoice" :disabled="loading" :title="recording ? '停止录音' : '语音输入'">
        <svg v-if="!recording" viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 14c1.7 0 3-1.3 3-3V5c0-1.7-1.3-3-3-3S9 3.3 9 5v6c0 1.7 1.3 3 3 3zm5.3-3c0 3-2.5 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.4 2.7 6.2 6 6.7V21h2v-3.3c3.3-.5 6-3.3 6-6.7h-1.7z"/></svg>
        <span v-else class="rec-wave"></span>
      </button>
      <div class="input-wrap">
        <input
          v-model="input"
          placeholder="说说你的感受..."
          @keyup.enter="sendMsg()"
          :disabled="loading"
          ref="inputEl"
        />
      </div>
      <button class="send-btn" @click="sendMsg()" :disabled="loading || !input.trim()">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
      </button>
    </div>

    <!-- 录音提示 -->
    <transition name="hint-fade">
      <div v-if="recording" class="recording-hint">
        <span class="rec-dot"></span> 正在录音，再次点击停止
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { sendMessage, getChatHistory } from '../api/chat'

const router = useRouter()
const userStore = useUserStore()
const input = ref('')
const messages = ref([])
const loading = ref(false)
const recording = ref(false)
const msgBox = ref(null)
const inputEl = ref(null)
const ttsPlaying = ref(-1)

const emotions = [
  { emoji: '😊', text: '今天有好事发生' },
  { emoji: '🌟', text: '我想分享快乐' },
  { emoji: '💪', text: '给自己打个气' },
  { emoji: '🌈', text: '来点正能量' },
  { emoji: '✨', text: '感恩小确幸' },
  { emoji: '🎯', text: '聊聊小目标' },
]

function getEmotionEmoji(emotion) {
  const map = { '开心': '😊', '平静': '😌', '焦虑': '😰', '难过': '😢', '愤怒': '😡', '疲惫': '😴' }
  return map[emotion] || '🙂'
}

async function sendMsg(text) {
  const msg = text || input.value.trim()
  if (!msg || loading.value) return
  input.value = ''
  messages.value.push({ role: 'user', content: msg })
  scrollBottom()
  loading.value = true
  try {
    const res = await sendMessage(Number(userStore.userId), msg)
    if (res.data.reply) {
      const aiMsg = { role: 'assistant', content: res.data.reply, emotion: res.data.emotion }
      messages.value.push(aiMsg)
      loading.value = false
      scrollBottom()
    } else {
      messages.value.push({ role: 'assistant', content: '抱歉，我暂时无法回复，请稍后再试...' })
    }
  } catch {
    messages.value.push({ role: 'assistant', content: '网络异常，请检查连接后重试...' })
  }
  loading.value = false
  scrollBottom()
}

// 语音输入
let mediaRecorder = null, audioContext = null, audioChunks = [], mediaStream = null

async function toggleVoice() {
  recording.value ? stopRecording() : await startRecording()
}

async function startRecording() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true } })
    audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 })
    const source = audioContext.createMediaStreamSource(mediaStream)
    const processor = audioContext.createScriptProcessor(4096, 1, 1)
    audioChunks = []
    processor.onaudioprocess = (e) => {
      const f = e.inputBuffer.getChannelData(0)
      const int16 = new Int16Array(f.length)
      for (let i = 0; i < f.length; i++) { const s = Math.max(-1, Math.min(1, f[i])); int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF }
      audioChunks.push(int16.buffer)
    }
    source.connect(processor); processor.connect(audioContext.destination)
    recording.value = true
  } catch { alert('无法启动录音，请确保浏览器有麦克风权限') }
}

function stopRecording() {
  recording.value = false
  if (audioContext) { audioContext.close().catch(() => {}); audioContext = null }
  if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null }
  if (!audioChunks.length) return
  const totalLength = audioChunks.reduce((a, b) => a + b.byteLength, 0)
  const merged = new Int16Array(totalLength)
  let offset = 0
  for (const chunk of audioChunks) { merged.set(new Int16Array(chunk), offset); offset += chunk.byteLength / 2 }
  loading.value = true
  fetch('/api/chat/asr', { method: 'POST', body: new Blob([merged.buffer], { type: 'audio/raw' }), headers: { 'Content-Type': 'audio/raw' } })
    .then(r => r.json())
    .then(data => { if (data.text) sendMsg(data.text); else messages.value.push({ role: 'assistant', content: '没有听清，请再说一次~' }) })
    .catch(() => messages.value.push({ role: 'assistant', content: '语音识别失败，请重试...' }))
    .finally(() => { loading.value = false })
  audioChunks = []
}

function playTTS(text) {
  if (!text) return
  fetch('/api/chat/tts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) })
    .then(r => { if (!r.ok) throw new Error(); return r.blob() })
    .then(blob => {
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audio.play().catch(() => alert('语音播放失败'))
      audio.onended = () => { URL.revokeObjectURL(url); ttsPlaying.value = -1 }
    })
    .catch(() => alert('语音合成失败'))
}

function scrollBottom() {
  nextTick(() => { if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight })
}

onMounted(async () => {
  try {
    const res = await getChatHistory(Number(userStore.userId))
    if (res.data?.length) messages.value = res.data
    scrollBottom()
  } catch {}
})

onUnmounted(() => { if (recording.value) stopRecording() })
</script>

<style scoped>
/* ═══════════ 页面结构 ═══════════ */
.chat-page {
  display: flex; flex-direction: column;
  height: 100vh;
  background: #F5F0EC;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* ═══════════ 顶部导航 ═══════════ */
.chat-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; padding-top: max(12px, env(safe-area-inset-top));
  background: rgba(248,244,240,0.95);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0,0,0,0.06);
  flex-shrink: 0;
}
.back-btn {
  width: 36px; height: 36px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: rgba(0,0,0,0.05); color: #666;
  transition: background 0.2s;
}
.back-btn:hover { background: rgba(0,0,0,0.1); }
.header-center { display: flex; align-items: center; gap: 10px; }
.ai-avatar { font-size: 28px; }
.ai-name { font-size: 15px; font-weight: 600; color: #3A3530; }
.ai-status {
  display: flex; align-items: center; gap: 4px;
  font-size: 11px; color: #9A948E; margin-top: 1px;
}
.status-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #82C4A0;
  transition: background 0.3s;
}
.status-dot.thinking {
  background: #E8C468;
  animation: pulse-dot 1s infinite;
}
@keyframes pulse-dot { 0%,100%{opacity:1} 50%{opacity:0.4} }
.header-right { width: 36px; }

/* ═══════════ 消息区域 ═══════════ */
.chat-messages {
  flex: 1; overflow-y: auto; padding: 20px 16px 12px;
  scroll-behavior: smooth;
}
.chat-messages::-webkit-scrollbar { width: 0; }

/* 欢迎消息 */
.welcome-wrap { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 20px; }
.welcome-avatar { font-size: 26px; margin-top: 2px; }
.welcome-bubble {
  background: white;
  border-radius: 4px 16px 16px 16px;
  padding: 12px 16px; max-width: 75%;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.welcome-bubble p { margin: 0; font-size: 14px; line-height: 1.6; color: #3A3530; }
.welcome-bubble p + p { margin-top: 6px; }

/* 消息行 */
.msg-row { display: flex; align-items: flex-end; gap: 8px; margin-bottom: 16px; }
.msg-row.user { flex-direction: row-reverse; }
.msg-avatar { font-size: 24px; flex-shrink: 0; margin-bottom: 4px; }

.bubble-wrap { display: flex; flex-direction: column; max-width: 72%; }
.msg-row.user .bubble-wrap { align-items: flex-end; }
.msg-row.assistant .bubble-wrap { align-items: flex-start; }

/* 情绪标签 */
.emotion-tag {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 11px; padding: 3px 10px; border-radius: 10px;
  background: #EEE8E0; color: #7A6E64;
  margin-bottom: 4px;
}

/* 气泡 */
.bubble {
  padding: 11px 15px; border-radius: 16px;
  font-size: 14px; line-height: 1.65; word-break: break-all;
  position: relative;
}
.msg-row.user .bubble {
  background: #8EA89A; color: white;
  border-bottom-right-radius: 4px;
}
.msg-row.assistant .bubble {
  background: white; color: #3A3530;
  border-bottom-left-radius: 4px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.06);
}
.cursor {
  display: inline-block; width: 2px; height: 14px;
  background: #8EA89A; margin-left: 1px; vertical-align: middle;
  animation: blink-cursor 0.8s infinite;
}
@keyframes blink-cursor { 0%,50%{opacity:1} 51%,100%{opacity:0} }

/* TTS 按钮 */
.tts-btn {
  margin-top: 4px; align-self: flex-start;
  padding: 3px 8px; border-radius: 8px;
  background: rgba(0,0,0,0.04); color: #9A948E;
  font-size: 12px; display: flex; align-items: center; gap: 3px;
  transition: all 0.2s;
}
.tts-btn:hover, .tts-btn.playing { background: #E8DDD4; color: #7A6E64; }

/* 加载气泡 */
.typing-bubble {
  display: flex; gap: 5px; padding: 14px 18px;
}
.dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #C8BEB4; animation: bounce 1.2s infinite both;
}
.dot:nth-child(2) { animation-delay: 0.15s; }
.dot:nth-child(3) { animation-delay: 0.3s; }
@keyframes bounce { 0%,80%,100%{transform:translateY(0)} 40%{transform:translateY(-6px)} }

/* ═══════════ 快捷按钮 ═══════════ */
.quick-wrap {
  flex-shrink: 0; padding: 8px 0 6px;
  border-top: 1px solid rgba(0,0,0,0.04);
  background: rgba(248,244,240,0.9);
}
.quick-scroll {
  display: flex; gap: 6px; padding: 0 16px; overflow-x: auto;
}
.quick-scroll::-webkit-scrollbar { display: none; }
.quick-btn {
  white-space: nowrap; flex-shrink: 0;
  padding: 6px 12px; border-radius: 14px;
  background: white; color: #7A6E64; font-size: 12px;
  border: 1px solid rgba(0,0,0,0.06);
  transition: all 0.2s; display: flex; align-items: center; gap: 4px;
}
.quick-btn:hover { background: #E8DDD4; border-color: #C8BEB4; }

/* ═══════════ 输入栏 ═══════════ */
.input-bar {
  flex-shrink: 0; display: flex; align-items: center; gap: 8px;
  padding: 10px 16px; padding-bottom: max(10px, env(safe-area-inset-bottom));
  background: rgba(248,244,240,0.98);
  border-top: 1px solid rgba(0,0,0,0.05);
  backdrop-filter: blur(12px);
}
.input-wrap {
  flex: 1; background: white; border-radius: 22px;
  border: 1.5px solid rgba(0,0,0,0.08);
  transition: border-color 0.2s;
  overflow: hidden;
}
.input-wrap:focus-within { border-color: #A0B8AE; }
.input-wrap input {
  width: 100%; padding: 10px 16px;
  font-size: 14px; background: transparent; color: #3A3530;
  outline: none;
}
.input-wrap input::placeholder { color: #C0B8B0; }

.voice-btn {
  width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: white; color: #8EA89A;
  border: 1.5px solid rgba(0,0,0,0.08); transition: all 0.2s;
}
.voice-btn:hover { background: #E8F0EC; }
.voice-btn.recording {
  background: #FFE8E6; color: #D4776A; border-color: #D4776A;
  animation: pulse-rec 1s infinite;
}
.rec-wave {
  display: block; width: 18px; height: 18px;
  border: 2.5px solid #D4776A; border-radius: 50%;
  animation: wave 1s infinite;
}
@keyframes wave { 0%{transform:scale(0.8);opacity:1} 100%{transform:scale(1.4);opacity:0} }
@keyframes pulse-rec { 0%,100%{transform:scale(1)} 50%{transform:scale(1.05)} }

.send-btn {
  width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: #8EA89A; color: white; transition: all 0.2s;
}
.send-btn:hover:not(:disabled) { background: #7A9A8C; transform: scale(1.05); }
.send-btn:disabled { background: #C8D4CE; }

/* ═══════════ 电脑端适配 ═══════════ */
@media (min-width: 768px) {
  .chat-page { height: calc(100vh - 60px); }
  .chat-messages { padding: 24px 24px 16px; }
  .bubble-wrap { max-width: 60%; }
  .welcome-bubble { max-width: 60%; }
  .quick-scroll { padding: 0 24px; }
  .input-bar { padding: 12px 24px; padding-bottom: max(12px, env(safe-area-inset-bottom)); }
}

/* ═══════════ 录音提示 ═══════════ */
.recording-hint {
  position: fixed; bottom: 90px; left: 50%; transform: translateX(-50%);
  background: rgba(50,45,42,0.8); color: white; padding: 8px 20px;
  border-radius: 20px; font-size: 13px; display: flex; align-items: center; gap: 8px;
  backdrop-filter: blur(8px); z-index: 10;
  pointer-events: none;
}
.rec-dot {
  width: 8px; height: 8px; border-radius: 50%; background: #D4776A;
  animation: blink-dot 1s infinite;
}
@keyframes blink-dot { 0%,100%{opacity:1} 50%{opacity:0.3} }
.hint-fade-enter-active, .hint-fade-leave-active { transition: opacity 0.3s; }
.hint-fade-enter-from, .hint-fade-leave-to { opacity: 0; }
</style>
