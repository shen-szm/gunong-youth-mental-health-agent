<template>
  <div class="pet-home" :class="`phase-${currentPhase}`">
    <!-- 背景图 -->
    <div class="home-bg" :style="{ backgroundImage: `url(${bgImage})` }"></div>
    <div class="home-overlay"></div>

    <!-- 顶部 -->
    <div class="pet-header">
      <strong>咕团家园</strong>
      <small>{{ moodLabel }}的咕团</small>
    </div>

    <!-- 咕团舞台 -->
    <div class="pet-stage">
      <div class="pet-character" :class="[`pet-${petMood}`, { 'pet-eating': eating, 'pet-grooming': grooming }]">
        <img :src="petImage" class="pet-sprite" alt="咕团" />
        <div class="pet-shadow"></div>
        <div v-if="eating" class="food-item">🍎</div>
        <div v-if="grooming" class="groom-sparkle">✨</div>
      </div>

      <!-- 对话气泡 -->
      <transition name="bubble">
        <div v-if="petMessage" class="pet-bubble">
          <p>{{ petMessage }}</p>
        </div>
      </transition>
    </div>

    <!-- 互动按钮 -->
    <div class="pet-actions">
      <button type="button" class="action-btn" :disabled="busy" @click="feedPet">
        <span class="action-icon">🍎</span>
        <span>喂食</span>
      </button>
      <button type="button" class="action-btn" :disabled="busy" @click="groomPet">
        <span class="action-icon">🪮</span>
        <span>梳毛</span>
      </button>
      <button type="button" class="action-btn" :disabled="busy" @click="playWithPet">
        <span class="action-icon">🎾</span>
        <span>玩耍</span>
      </button>
      <button type="button" class="action-btn talk-btn" :disabled="busy" @click="toggleTalk">
        <span class="action-icon">💬</span>
        <span>{{ talking ? '结束' : '说话' }}</span>
      </button>
    </div>

    <!-- 对话面板 -->
    <transition name="slide">
      <div v-if="talking" class="talk-panel">
        <div class="talk-history">
          <div v-for="(msg, i) in talkHistory" :key="i" :class="['talk-msg', msg.role]">
            <span>{{ msg.text }}</span>
          </div>
        </div>
        <div class="talk-input">
          <input v-model="talkInput" type="text" placeholder="跟咕团说点什么..." maxlength="100" @keyup.enter="sendTalk" />
          <button type="button" @click="sendTalk" :disabled="!talkInput.trim()">说</button>
        </div>
      </div>
    </transition>

    <!-- 亲密度提示 -->
    <div class="intimacy-hint">
      <span>{{ intimacyLabel }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getPetState, interactWithPet, logIslandBehavior } from '../../api/island.js'
import homeDay from '../../assets/island/home-day.png'
import homeDusk from '../../assets/island/home-dusk.png'
import homeNight from '../../assets/island/home-night.png'

const props = defineProps({ timePhase: { type: String, default: 'day' } })
const emit = defineEmits(['played'])

const currentPhase = ref('day')
const petMood = ref('content')
const petMessage = ref('')
const eating = ref(false)
const grooming = ref(false)
const busy = ref(false)
const talking = ref(false)
const talkInput = ref('')
const talkHistory = ref([])
const intimacy = ref(0)
let messageTimer = null

const bgImage = computed(() => ({
  day: homeDay, dusk: homeDusk, night: homeNight,
}[currentPhase.value] || homeDay))

const petImage = computed(() => {
  if (eating.value) return '/images/guguan/guguan-eating.png'
  if (petMood.value === 'happy') return '/images/guguan/guguan-happy.png'
  if (petMood.value === 'sleepy') return '/images/guguan/guguan-sleeping.png'
  return '/images/guguan/guguan-idle.png'
})

const moodLabel = computed(() => ({
  content: '安静', happy: '开心', curious: '好奇',
  concerned: '关心', sleepy: '困倦',
})[petMood.value] || '安静')

const intimacyLabel = computed(() => {
  if (intimacy.value >= 500) return '咕团跟你很熟了，会一直陪着你。'
  if (intimacy.value >= 200) return '咕团越来越喜欢你了。'
  if (intimacy.value >= 50) return '咕团开始认识你了。'
  return '咕团在慢慢熟悉你。'
})

function showMessage(msg, duration = 3000) {
  petMessage.value = msg
  if (messageTimer) clearTimeout(messageTimer)
  messageTimer = setTimeout(() => { petMessage.value = '' }, duration)
}

async function feedPet() {
  if (busy.value) return
  busy.value = true
  eating.value = true
  petMood.value = 'happy'
  showMessage('咕！好吃！')
  try {
    const res = await interactWithPet('feed')
    intimacy.value = res.data?.pet_state?.intimacy || intimacy.value + 3
    showMessage(res.data?.reply || '咕，好好吃！')
  } catch { showMessage('咕，好好吃！') }
  logIslandBehavior('pet_interaction', 'home', 'feed', {}).catch(() => {})
  emit('played', { action: 'feed' })
  setTimeout(() => { eating.value = false; busy.value = false; petMood.value = 'content' }, 2000)
}

async function groomPet() {
  if (busy.value) return
  busy.value = true
  grooming.value = true
  petMood.value = 'content'
  showMessage('咕～好舒服～')
  try {
    const res = await interactWithPet('groom')
    intimacy.value = res.data?.pet_state?.intimacy || intimacy.value + 3
    showMessage(res.data?.reply || '咕团的毛都顺了。')
  } catch { showMessage('咕团的毛都顺了。') }
  logIslandBehavior('pet_interaction', 'home', 'groom', {}).catch(() => {})
  emit('played', { action: 'groom' })
  setTimeout(() => { grooming.value = false; busy.value = false }, 2500)
}

async function playWithPet() {
  if (busy.value) return
  busy.value = true
  petMood.value = 'curious'
  showMessage('咕！来玩来玩！')
  try {
    const res = await interactWithPet('play')
    intimacy.value = res.data?.pet_state?.intimacy || intimacy.value + 3
    showMessage(res.data?.reply || '咕团玩得很开心！')
  } catch { showMessage('咕团玩得很开心！') }
  petMood.value = 'happy'
  logIslandBehavior('pet_interaction', 'home', 'play', {}).catch(() => {})
  emit('played', { action: 'play' })
  setTimeout(() => { busy.value = false; petMood.value = 'content' }, 2500)
}

function toggleTalk() {
  talking.value = !talking.value
  if (talking.value) {
    petMood.value = 'curious'
    showMessage('咕，你想说什么？')
    logIslandBehavior('pet_interaction', 'home', 'talk_start', {}).catch(() => {})
  } else {
    talkHistory.value = []
    petMood.value = 'content'
  }
}

async function sendTalk() {
  const text = talkInput.value.trim()
  if (!text || busy.value) return
  busy.value = true
  talkHistory.value.push({ role: 'user', text })
  talkInput.value = ''
  try {
    const res = await interactWithPet('talk', text)
    const reply = res.data?.reply || '咕，我在听。'
    talkHistory.value.push({ role: 'pet', text: reply })
    intimacy.value = res.data?.pet_state?.intimacy || intimacy.value + 2
    showMessage(reply, 4000)
    petMood.value = res.data?.pet_state?.mood || 'content'
  } catch {
    talkHistory.value.push({ role: 'pet', text: '咕，我在听。' })
  }
  logIslandBehavior('pet_interaction', 'home', 'talk', { message_length: text.length }).catch(() => {})
  emit('played', { action: 'talk' })
  busy.value = false
}

async function loadPetState() {
  try {
    const res = await getPetState()
    intimacy.value = res.data?.intimacy || 0
    petMood.value = res.data?.mood || 'content'
  } catch {}
}

function syncPhase() {
  const hour = new Date().getHours()
  if (hour >= 6 && hour < 17) currentPhase.value = 'day'
  else if (hour >= 17 && hour < 20) currentPhase.value = 'dusk'
  else currentPhase.value = 'night'
}

onMounted(() => {
  syncPhase()
  loadPetState()
  logIslandBehavior('place_enter', 'home', null, {}).catch(() => {})
  setTimeout(() => {
    const hour = new Date().getHours()
    if (hour < 6) showMessage('咕，这么晚了，咕团陪你。')
    else if (hour < 12) showMessage('咕，早上好！')
    else if (hour < 18) showMessage('咕，下午好！')
    else showMessage('咕，晚上好，今天过得怎么样？')
  }, 800)
})

onBeforeUnmount(() => {
  if (messageTimer) clearTimeout(messageTimer)
  logIslandBehavior('activity_finish', 'home', 'leave', { talking: talking.value }).catch(() => {})
})
</script>

<style scoped>
.pet-home {
  position: relative;
  width: 100%; height: 100%;
  min-height: 100%;
  overflow: hidden;
  font-family: 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
  color: #fff;
  background: #2a1f1a;
}

.home-bg {
  position: absolute; inset: 0;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  image-rendering: pixelated;
}
.home-overlay {
  position: absolute; inset: 0;
  background: linear-gradient(180deg, rgba(0,0,0,.15) 0%, transparent 30%, transparent 55%, rgba(0,0,0,.25) 100%);
  pointer-events: none;
}

.pet-header {
  position: absolute; top: 16px; left: 20px; z-index: 5;
  text-shadow: 0 2px 6px rgba(0,0,0,.5);
}
.pet-header strong { display: block; font-size: 17px; font-weight: 700; }
.pet-header small { font-size: 11px; opacity: .85; }

/* 咕团舞台 */
.pet-stage {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  z-index: 3;
}
.pet-character { position: relative; transition: transform .3s; }
.pet-eating { transform: translateY(4px); }
.pet-grooming { transform: rotate(-3deg); }

.pet-sprite {
  width: 90px; height: 90px;
  object-fit: contain;
  image-rendering: pixelated;
  filter: drop-shadow(0 6px 12px rgba(0,0,0,.3));
  animation: petBob 3s ease-in-out infinite;
}
.pet-happy .pet-sprite { animation: petHappy 1.5s ease-in-out infinite; }
.pet-sleepy .pet-sprite { animation: petSleep 4s ease-in-out infinite; }
@keyframes petBob { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-7px); } }
@keyframes petHappy { 0%,100% { transform: translateY(0) rotate(-3deg); } 50% { transform: translateY(-10px) rotate(3deg); } }
@keyframes petSleep { 0%,100% { transform: translateY(0) scaleY(1); } 50% { transform: translateY(-2px) scaleY(.96); } }

.pet-shadow {
  width: 60px; height: 10px;
  background: rgba(0,0,0,.2);
  border-radius: 50%;
  margin: 4px auto 0;
}

.food-item {
  position: absolute; top: -10px; right: -8px;
  font-size: 28px;
  animation: eatBounce .5s ease infinite;
}
@keyframes eatBounce { 0%,100% { transform: translateY(0) rotate(0); } 50% { transform: translateY(-12px) rotate(15deg); } }
.groom-sparkle {
  position: absolute; top: -20px; left: 50%;
  transform: translateX(-50%);
  font-size: 24px;
  animation: sparkle 1s ease infinite;
}
@keyframes sparkle { 0%,100% { opacity: .3; transform: translateX(-50%) scale(.8); } 50% { opacity: 1; transform: translateX(-50%) scale(1.3); } }

/* 对话气泡 */
.pet-bubble {
  position: absolute;
  top: -80px; left: 50%;
  transform: translateX(-50%);
  min-width: 130px; max-width: 240px;
  padding: 12px 16px;
  background: rgba(255,255,255,.95);
  color: #4A3A2A;
  border-radius: 18px;
  font-size: 13px; line-height: 1.5;
  text-align: center;
  box-shadow: 0 6px 16px rgba(0,0,0,.2);
}
.pet-bubble::after {
  content: ''; position: absolute;
  bottom: -8px; left: 50%;
  transform: translateX(-50%);
  border: 8px solid transparent;
  border-top-color: rgba(255,255,255,.95);
}
.pet-bubble p { margin: 0; }

/* 互动按钮 */
.pet-actions {
  position: absolute; bottom: 20px; left: 50%;
  transform: translateX(-50%);
  display: flex; gap: 12px; z-index: 5;
}
.action-btn {
  display: flex; flex-direction: column;
  align-items: center; gap: 3px;
  min-width: 60px; min-height: 60px;
  padding: 8px 10px;
  border: 0; border-radius: 16px;
  background: rgba(255,255,255,.2);
  backdrop-filter: blur(12px);
  color: #fff;
  font: inherit; font-size: 11px; font-weight: 600;
  cursor: pointer;
  transition: all .2s;
  text-shadow: 0 1px 3px rgba(0,0,0,.4);
}
.action-btn:hover:not(:disabled) {
  transform: translateY(-3px);
  background: rgba(255,255,255,.3);
}
.action-btn:disabled { opacity: .45; cursor: not-allowed; }
.action-icon { font-size: 22px; }
.talk-btn {
  background: linear-gradient(135deg, rgba(255,215,0,.9), rgba(255,193,7,.9));
  color: #3D3D1A;
  text-shadow: none;
}

/* 对话面板 */
.talk-panel {
  position: absolute;
  bottom: 90px; left: 50%;
  transform: translateX(-50%);
  width: min(360px, 88%);
  background: rgba(255,255,255,.95);
  border-radius: 18px;
  padding: 14px;
  box-shadow: 0 10px 30px rgba(0,0,0,.2);
  z-index: 6;
}
.talk-history {
  max-height: 130px; overflow-y: auto;
  margin-bottom: 10px;
  display: flex; flex-direction: column; gap: 6px;
}
.talk-msg { display: flex; }
.talk-msg.user { justify-content: flex-end; }
.talk-msg span {
  max-width: 75%;
  padding: 7px 11px;
  border-radius: 12px;
  font-size: 12px; line-height: 1.5;
}
.talk-msg.user span { background: #A8D8A0; color: #2D4A2D; }
.talk-msg.pet span { background: #F0F0F0; color: #4A3A2A; }
.talk-input { display: flex; gap: 8px; }
.talk-input input {
  flex: 1; min-height: 36px;
  padding: 0 12px;
  border: 1px solid #e0e0e0; border-radius: 10px;
  font: inherit; font-size: 12px;
  outline: none;
}
.talk-input input:focus { border-color: #A8D8A0; }
.talk-input button {
  min-height: 36px; padding: 0 16px;
  border: 0; border-radius: 10px;
  background: #A8D8A0; color: #2D4A2D;
  font: inherit; font-size: 12px; font-weight: 600;
  cursor: pointer;
}
.talk-input button:disabled { opacity: .4; cursor: not-allowed; }

/* 亲密度提示 */
.intimacy-hint {
  position: absolute; bottom: 90px; left: 50%;
  transform: translateX(-50%);
  font-size: 10px; color: rgba(255,255,255,.8);
  text-shadow: 0 1px 3px rgba(0,0,0,.5);
  z-index: 5;
  pointer-events: none;
}

.bubble-enter-active, .bubble-leave-active { transition: all .3s; }
.bubble-enter-from, .bubble-leave-to { opacity: 0; transform: translateX(-50%) translateY(10px); }
.slide-enter-active, .slide-leave-active { transition: all .3s; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateX(-50%) translateY(20px); }
</style>
