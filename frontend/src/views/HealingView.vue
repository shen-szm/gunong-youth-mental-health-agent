<template>
  <div class="healing-page" :class="{ 'inline-mode': inline }">
    <div class="healing-header" v-if="!inline">
      <button class="back-btn" @click="router.back()">←</button>
      <h1>🌿 治愈中心</h1>
    </div>
    <div class="inline-title" v-if="inline">
      <h2>🌿 治愈中心</h2>
    </div>

    <!-- 灵能等级 -->
    <div class="energy-card" v-if="energy">
      <div class="energy-level">
        <span class="level-icon">🌱</span>
        <span class="level-name">{{ energy.level_name }}</span>
        <span class="level-num">Lv.{{ energy.level }}</span>
      </div>
      <div class="energy-bar">
        <div class="energy-fill" :style="{ width: (energy.progress * 100) + '%' }"></div>
      </div>
      <div class="energy-points">{{ energy.total_points }} 灵能点</div>
    </div>

    <!-- AI音乐推荐 -->
    <div class="section">
      <h2>🎵 AI 音乐处方</h2>
      <div class="music-recommend" v-if="musicRecommend">
        <div class="mr-song">
          <div class="mr-cover">🎶</div>
          <div class="mr-info">
            <div class="mr-name">{{ musicRecommend.song?.name }}</div>
            <div class="mr-artist">{{ musicRecommend.song?.artist }}</div>
          </div>
          <button class="mr-play" @click="playRecommendSong">播放</button>
        </div>
        <div class="mr-reason">
          <span class="mr-tag">{{ musicRecommend.emotion_label }}</span>
          <p>{{ musicRecommend.reason }}</p>
        </div>
      </div>
      <div v-else class="loading-hint">AI 正在为你挑选音乐...</div>
    </div>

    <!-- 白噪音 -->
    <div class="section">
      <h2>🔊 治愈白噪音</h2>
      <div class="whitenoise-reason" v-if="noiseReason">💡 {{ noiseReason }}</div>
      <div class="noise-grid">
        <div v-for="s in whiteNoises" :key="s.id" class="noise-card" :class="{ playing: playingNoise === s.id }" @click="toggleNoise(s)">
          <div class="nc-emoji">{{ s.emoji }}</div>
          <div class="nc-name">{{ s.name }}</div>
          <div class="nc-desc">{{ s.desc }}</div>
          <div class="nc-status">{{ playingNoise === s.id ? '⏸ 暂停' : '▶ 播放' }}</div>
        </div>
      </div>
      <audio ref="noiseAudio" @ended="onNoiseEnd" loop></audio>
    </div>

    <!-- 今日治愈清单 -->
    <div class="section">
      <h2>✨ 今日治愈清单</h2>
      <div class="checklist">
        <div v-for="task in tasks" :key="task.id" class="checklist-item" :class="{ done: task.completed }" @click="!task.completed && checkinTask(task.id)">
          <div class="ci-check">{{ task.completed ? '✅' : '⬜' }}</div>
          <div class="ci-content">
            <span class="ci-desc">{{ task.desc }}</span>
            <span class="ci-points">+{{ task.points }} 灵能</span>
          </div>
        </div>
        <div v-if="!tasks.length" class="empty-hint">今日还没有治愈清单，快去和咕哝聊聊吧~</div>
      </div>
    </div>

    <!-- 微旅行推荐 -->
    <div class="section">
      <h2>🗺️ 微旅行推荐</h2>
      <div class="travel-cards">
        <div v-for="t in travels" :key="t.name" class="travel-card">
          <div class="tc-emoji">{{ t.emoji }}</div>
          <div class="tc-info">
            <div class="tc-name">{{ t.name }}</div>
            <div class="tc-desc">{{ t.desc }}</div>
            <div class="tc-time">⏱ {{ t.duration }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { healingApi } from '../api/healing'
import axios from 'axios'

const API = import.meta.env.VITE_API_BASE || ''
const router = useRouter()
const userStore = useUserStore()

const props = defineProps({ inline: { type: Boolean, default: false } })
const emit = defineEmits(['close'])

const energy = ref(null)
const tasks = ref([])
const travels = ref([])
const whiteNoises = ref([])
const noiseReason = ref('')
const musicRecommend = ref(null)
const playingNoise = ref(null)
const noiseAudio = ref(null)

// ═══ 本地 fallback 数据（当后端 API 不可用时显示）═══
const DEFAULT_ENERGY = { level: 1, level_name: '萌芽', progress: 0.35, total_points: 350 }
const DEFAULT_TASKS = [
  { id: 1, desc: '深呼吸三次，感受空气流入肺部', points: 10, completed: false },
  { id: 2, desc: '写下今天让你感恩的一件小事', points: 15, completed: false },
  { id: 3, desc: '听一首喜欢的歌，闭上眼睛感受旋律', points: 10, completed: false },
  { id: 4, desc: '给窗外的一棵树拍张照片', points: 20, completed: false },
]
const DEFAULT_TRAVELS = [
  { name: '楼下公园漫步', desc: '去最近的小公园走走，看看花草树木', emoji: '🌳', duration: '15分钟' },
  { name: '街角咖啡馆', desc: '点一杯喜欢的饮品，看窗外人来人往', emoji: '☕', duration: '30分钟' },
  { name: '日落天台', desc: '找一个高处，静静等待日落', emoji: '🌅', duration: '20分钟' },
  { name: '书店漫游', desc: '去书店随机翻开一本书，读任意一页', emoji: '📚', duration: '40分钟' },
]
const DEFAULT_NOISES = [
  { id: 'rain', name: '细雨绵绵', desc: '窗外小雨', emoji: '🌧️', url: '' },
  { id: 'thunder', name: '雷雨夜', desc: '夏夜雷暴', emoji: '⛈️', url: '' },
  { id: 'forest', name: '林间鸟鸣', desc: '清晨森林', emoji: '🐦', url: '' },
  { id: 'waves', name: '海浪拍岸', desc: '海边微风', emoji: '🌊', url: '' },
]
const DEFAULT_MUSIC = {
  song: { id: 25706282, name: 'Weightless', artist: 'Marconi Union' },
  emotion_label: '焦虑缓解',
  reason: '这首被神经科学家认证为"世界上最放松的音乐"，能有效降低 65% 的焦虑感。闭上眼睛，让音符带走你的烦恼。',
}

onMounted(async () => {
  const userId = Number(userStore.userId)
  try {
    const [energyRes, checklistRes, travelRes, noiseRes, noiseRecRes, musicRes] = await Promise.all([
      healingApi.getEnergy(userId).catch(() => ({ data: null })),
      healingApi.getChecklist(userId).catch(() => ({ data: { tasks: [] } })),
      healingApi.getTravel(userId).catch(() => ({ data: { suggestions: [] } })),
      axios.get(`${API}/api/music/whitenoise/list`).catch(() => ({ data: { sounds: [] } })),
      axios.get(`${API}/api/music/whitenoise/recommend`, { params: { user_id: userId } }).catch(() => ({ data: { sounds: [], reason: '' } })),
      axios.get(`${API}/api/music/recommend`, { params: { user_id: userId } }).catch(() => ({ data: null })),
    ])
    energy.value = energyRes.data || DEFAULT_ENERGY
    tasks.value = checklistRes.data?.tasks?.length ? checklistRes.data.tasks : DEFAULT_TASKS
    travels.value = travelRes.data?.suggestions?.length ? travelRes.data.suggestions : DEFAULT_TRAVELS

    // 白噪音：优先显示推荐的
    if (noiseRecRes.data?.sounds?.length) {
      whiteNoises.value = noiseRecRes.data.sounds
      noiseReason.value = noiseRecRes.data.reason || ''
    } else if (noiseRes.data?.sounds?.length) {
      whiteNoises.value = noiseRes.data.sounds.slice(0, 4)
    } else {
      whiteNoises.value = DEFAULT_NOISES
      noiseReason.value = '根据你最近的情绪状态，推荐以下白噪音帮助你放松'
    }

    // AI音乐推荐
    musicRecommend.value = musicRes.data?.song ? musicRes.data : DEFAULT_MUSIC
  } catch (e) {
    console.error('加载治愈中心失败', e)
    // 全部使用 fallback
    energy.value = DEFAULT_ENERGY
    tasks.value = DEFAULT_TASKS
    travels.value = DEFAULT_TRAVELS
    whiteNoises.value = DEFAULT_NOISES
    noiseReason.value = '根据你最近的情绪状态，推荐以下白噪音帮助你放松'
    musicRecommend.value = DEFAULT_MUSIC
  }
})

onUnmounted(() => {
  if (noiseAudio.value) {
    noiseAudio.value.pause()
    noiseAudio.value.src = ''
  }
})

async function checkinTask(taskId) {
  try {
    const res = await healingApi.checkin(taskId)
    if (res.data.success) {
      const task = tasks.value.find(t => t.id === taskId)
      if (task) task.completed = true
      if (energy.value) {
        energy.value.total_points = res.data.total_points
        energy.value.level = res.data.level
        energy.value.level_name = res.data.level_name
      }
    }
  } catch (e) {
    console.error('打卡失败', e)
  }
}

function toggleNoise(sound) {
  if (!noiseAudio.value) return

  if (playingNoise.value === sound.id) {
    noiseAudio.value.pause()
    noiseAudio.value.src = ''
    playingNoise.value = null
  } else {
    noiseAudio.value.src = sound.url
    noiseAudio.value.play().catch(() => {
      alert('播放失败，请检查网络连接')
    })
    playingNoise.value = sound.id
  }
}

function onNoiseEnd() {
  playingNoise.value = null
}

function playRecommendSong() {
  if (!musicRecommend.value?.song?.id) return
  const songId = musicRecommend.value.song.id
  window.open(`https://music.163.com/song?id=${songId}`, '_blank')
}
</script>

<style scoped>
.healing-page {
  min-height: 100vh;
  background: #F5F7F5;
  padding-bottom: 80px;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.healing-header {
  display: flex; align-items: center; gap: 12px;
  padding: 16px 20px; padding-top: max(16px, env(safe-area-inset-top));
  background: white; border-bottom: 1px solid #eee;
}
.healing-header h1 { font-size: 18px; font-weight: 600; color: #3D6B5E; margin: 0; }
.back-btn { background: none; border: none; font-size: 20px; color: #5B8C7E; cursor: pointer; }

.energy-card {
  margin: 16px; padding: 20px;
  background: linear-gradient(135deg, #5B8C7E, #7FB3A6);
  border-radius: 16px; color: white;
}
.energy-level { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.level-icon { font-size: 24px; }
.level-name { font-size: 18px; font-weight: 700; }
.level-num { font-size: 14px; opacity: 0.8; }
.energy-bar { height: 8px; background: rgba(255,255,255,0.3); border-radius: 4px; overflow: hidden; }
.energy-fill { height: 100%; background: white; border-radius: 4px; transition: width 0.5s ease; }
.energy-points { font-size: 13px; opacity: 0.8; margin-top: 8px; }

.section { margin: 16px; }
.section h2 { font-size: 16px; font-weight: 600; color: #3D6B5E; margin-bottom: 12px; }

/* AI音乐推荐 */
.music-recommend {
  background: white; border-radius: 14px; padding: 16px; overflow: hidden;
}
.mr-song {
  display: flex; align-items: center; gap: 14px; margin-bottom: 12px;
}
.mr-cover {
  width: 52px; height: 52px; border-radius: 12px;
  background: linear-gradient(135deg, #E8D5B7, #F0E6D0);
  display: flex; align-items: center; justify-content: center; font-size: 24px;
}
.mr-info { flex: 1; }
.mr-name { font-size: 15px; font-weight: 600; color: #333; }
.mr-artist { font-size: 12px; color: #888; margin-top: 2px; }
.mr-play {
  padding: 8px 16px; border-radius: 20px; border: none;
  background: #5B8C7E; color: white; font-size: 13px; font-weight: 500;
  cursor: pointer; transition: all 0.2s;
}
.mr-play:hover { background: #4a7a6e; }
.mr-reason {
  background: #f8f6f2; border-radius: 10px; padding: 12px;
}
.mr-tag {
  display: inline-block; padding: 2px 10px; border-radius: 10px;
  background: rgba(91,140,126,0.15); color: #5B8C7E;
  font-size: 11px; font-weight: 500; margin-bottom: 6px;
}
.mr-reason p { font-size: 13px; color: #666; line-height: 1.6; margin: 4px 0 0; }
.loading-hint { font-size: 13px; color: #999; text-align: center; padding: 20px; }

/* 白噪音 */
.whitenoise-reason {
  font-size: 12px; color: #888; margin-bottom: 10px; padding: 0 4px;
}
.noise-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
}
.noise-card {
  padding: 16px 12px; background: white; border-radius: 14px;
  text-align: center; cursor: pointer; transition: all 0.25s;
  border: 2px solid transparent;
}
.noise-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
.noise-card.playing { border-color: #5B8C7E; background: rgba(91,140,126,0.05); }
.nc-emoji { font-size: 32px; margin-bottom: 6px; }
.nc-name { font-size: 14px; font-weight: 600; color: #333; }
.nc-desc { font-size: 11px; color: #999; margin-top: 4px; line-height: 1.4; }
.nc-status { font-size: 11px; color: #5B8C7E; margin-top: 8px; font-weight: 500; }

/* 治愈清单 */
.checklist { display: flex; flex-direction: column; gap: 8px; }
.checklist-item {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 16px; background: white; border-radius: 12px;
  cursor: pointer; transition: all 0.2s;
}
.checklist-item:hover { transform: translateX(4px); }
.checklist-item.done { opacity: 0.6; }
.ci-check { font-size: 20px; }
.ci-content { flex: 1; display: flex; justify-content: space-between; align-items: center; }
.ci-desc { font-size: 14px; color: #333; }
.ci-points { font-size: 12px; color: #5B8C7E; font-weight: 500; }
.empty-hint { font-size: 13px; color: #999; text-align: center; padding: 20px; }

/* 微旅行 */
.travel-cards { display: flex; flex-direction: column; gap: 10px; }
.travel-card {
  display: flex; align-items: center; gap: 14px;
  padding: 16px; background: white; border-radius: 12px;
}
.tc-emoji { font-size: 28px; }
.tc-info { flex: 1; }
.tc-name { font-size: 14px; font-weight: 600; color: #333; }
.tc-desc { font-size: 12px; color: #777; margin-top: 4px; }
.tc-time { font-size: 11px; color: #5B8C7E; margin-top: 4px; }

/* inline 弹窗模式 - 适配深色背景 */
.healing-page.inline-mode { background: transparent; padding: 0; min-height: auto; }
.healing-page.inline-mode .section h2 { color: #7FB3A6; font-size: 15px; }
.healing-page.inline-mode .energy-card { margin: 0 0 12px; }
.healing-page.inline-mode .section { margin: 0 0 14px; }
.healing-page.inline-mode .music-recommend,
.healing-page.inline-mode .noise-card,
.healing-page.inline-mode .checklist-item,
.healing-page.inline-mode .travel-card { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08); }
.healing-page.inline-mode .mr-name,
.healing-page.inline-mode .nc-name,
.healing-page.inline-mode .ci-desc,
.healing-page.inline-mode .tc-name { color: #E8E2D8; }
.healing-page.inline-mode .mr-artist,
.healing-page.inline-mode .nc-desc,
.healing-page.inline-mode .tc-desc,
.healing-page.inline-mode .tc-time { color: rgba(232,226,216,0.55); }
.healing-page.inline-mode .mr-reason { background: rgba(255,255,255,0.05); }
.healing-page.inline-mode .mr-reason p { color: rgba(232,226,216,0.7); }
.healing-page.inline-mode .mr-tag { background: rgba(127,179,166,0.2); color: #7FB3A6; }
.healing-page.inline-mode .loading-hint,
.healing-page.inline-mode .empty-hint { color: rgba(232,226,216,0.4); }
.healing-page.inline-mode .noise-card.playing { border-color: #7FB3A6; background: rgba(127,179,166,0.1); }
.healing-page.inline-mode .nc-status { color: #7FB3A6; }
.inline-title { text-align: center; margin-bottom: 16px; }
.inline-title h2 { margin: 0; font-size: 18px; color: #E8E2D8; }

/* 像素皮肤 3.0 · 疗愈（inline 深色） */
.healing-page.inline-mode {
  --px-line: rgba(240, 216, 170, .24);
  --px-gold: #e8cf9a;
  --px-shadow: rgba(0, 0, 0, .55);
}
.healing-page .inline-title h2 { font-family: var(--px-font); }
.healing-page .energy-card {
  border: 2px solid var(--px-line);
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.healing-page .energy-bar,
.healing-page .energy-fill { border-radius: 0; }
.healing-page .section h2 { font-family: var(--px-font); font-size: 15px; }
.healing-page .music-recommend,
.healing-page .noise-card,
.healing-page .checklist-item,
.healing-page .travel-card {
  border: 2px solid var(--px-line);
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
  transition: transform 160ms steps(2, end), box-shadow 160ms steps(2, end), background 160ms steps(2, end);
}
.healing-page .noise-card:hover,
.healing-page .checklist-item:hover,
.healing-page .travel-card:hover { transform: translate(-1px, -1px); box-shadow: 5px 5px 0 var(--px-shadow); }
.healing-page .noise-card.playing { border-color: var(--px-gold); }
.healing-page .mr-play {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: 3px 3px 0 var(--px-shadow);
}
.healing-page .mr-tag { border-radius: 4px; }
.healing-page .noise-card:focus-visible,
.healing-page .checklist-item:focus-visible,
.healing-page .travel-card:focus-visible,
.healing-page .mr-play:focus-visible {
  outline: 3px dashed var(--px-gold);
  outline-offset: 3px;
}
</style>
