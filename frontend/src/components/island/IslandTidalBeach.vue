<template>
  <div class="tidal-beach" :class="`phase-${currentPhase}`" tabindex="0" @keydown="onKeyDown" @keyup="onKeyUp" ref="beachRef">
    <!-- 背景图 -->
    <div class="beach-bg" :style="{ backgroundImage: `url(${bgImage})` }"></div>
    <div class="beach-overlay"></div>

    <!-- 顶部标签 -->
    <div class="beach-header">
      <strong>潮汐沙滩</strong>
      <small>{{ phaseLabel }} · {{ tideLabel }}</small>
    </div>

    <!-- 收集进度 -->
    <div class="shell-count">
      <span>拾贝 {{ collectedCount }}</span>
    </div>

    <!-- 可收集贝壳 -->
    <div
      v-for="shell in shells"
      :key="shell.id"
      class="collectible-shell"
      :class="{ collected: shell.collected, near: isNearShell(shell) }"
      :style="{ left: shell.x + '%', top: shell.y + '%' }"
      @click="moveToShell(shell)"
    >
      <span>{{ shell.icon }}</span>
    </div>

    <!-- 可移动咕团（使用项目标准形象） -->
    <div
      class="movable-pet"
      :class="[`facing-${petFacing}`, { walking: isMoving }]"
      :style="{ left: petPos.x + '%', top: petPos.y + '%' }"
    >
      <img :src="petImage" class="pet-sprite" alt="咕团" />
      <div class="pet-shadow"></div>
    </div>

    <!-- 收集反馈 -->
    <transition name="pop">
      <div v-if="collectFeedback" class="collect-feedback">
        <span>{{ collectFeedback }}</span>
      </div>
    </transition>

    <!-- 静坐看海 -->
    <transition name="fade">
      <div v-if="sitting" class="sitting-overlay" @click.self="sitting = false">
        <div class="sitting-card">
          <p class="sitting-text">{{ sittingText }}</p>
          <small class="sitting-hint">海浪会带走一些东西，也会留下一些东西。</small>
          <button type="button" class="sitting-close" @click="sitting = false">
            回到沙滩
          </button>
        </div>
      </div>
    </transition>

    <!-- 底部按钮 -->
    <div class="beach-actions">
      <button type="button" class="beach-btn primary" @click="sitAndWatch">
        坐下来看海
      </button>
      <button type="button" class="beach-btn" @click="refreshShells">
        再看看沙滩
      </button>
    </div>

    <!-- 移动提示 -->
    <div class="move-hint">
      <span>方向键 / WASD 移动 · 点击沙滩走过去</span>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { logIslandBehavior } from '../../api/island.js'
import beachDay from '../../assets/island/beach-day.png'
import beachDusk from '../../assets/island/beach-dusk.png'
import beachNight from '../../assets/island/beach-night.png'

const props = defineProps({ timePhase: { type: String, default: '' } })
const emit = defineEmits(['played'])
const beachRef = ref(null)

const currentPhase = ref(props.timePhase || 'day')
watch(() => props.timePhase, (value) => { if (value) currentPhase.value = value })
const shells = ref([])
const collectedCount = ref(0)
const collectFeedback = ref('')
const sitting = ref(false)
const sittingText = ref('')

const bgImage = computed(() => ({
  day: beachDay, dusk: beachDusk, night: beachNight,
}[currentPhase.value] || beachDay))

// 咕团位置（百分比）
const petPos = reactive({ x: 25, y: 82 })
const petFacing = ref('right')
const isMoving = ref(false)
const petMood = ref('idle')
const pressedKeys = new Set()
let moveInterval = null
let feedbackTimer = null
let targetPos = null

const petImage = computed(() => {
  const map = {
    idle: '/images/guguan/guguan-idle.webp',
    happy: '/images/guguan/guguan-happy.webp',
    eating: '/images/guguan/guguan-eating.webp',
    sleeping: '/images/guguan/guguan-sleeping.webp',
  }
  return map[petMood.value] || map.idle
})

const phaseLabel = computed(() => ({ day: '白天', dusk: '傍晚', night: '夜晚' })[currentPhase.value])
const tideLabel = computed(() => ({ day: '涨潮时分', dusk: '日落时分', night: '退潮时分' })[currentPhase.value])

const sittingTexts = [
  '听，海浪一下一下地拍着沙滩，像在帮你把心里的事慢慢抚平。',
  '不用急着做什么，就这样坐着，海会陪你。',
  '那些说不出口的话，可以让海浪带走。',
  '你已经很努力了，现在允许自己休息一下。',
  '沙滩上的贝壳，每一个都曾是某个小生命的家。',
  '夕阳落下去，明天还会升起来，你也是。',
]
const shellIcons = ['🐚', '🐚', '🐚', '⭐', '🦀', '🐚', '🪨', '🐚']
const collectMessages = ['一枚漂亮的贝壳', '小螃蟹跑掉了', '这块石头暖暖的', '海星在晒太阳', '又一枚贝壳', '今天运气不错']

function generateShells() {
  const count = 5 + Math.floor(Math.random() * 3)
  const newShells = []
  for (let i = 0; i < count; i++) {
    newShells.push({
      id: Date.now() + i,
      icon: shellIcons[Math.floor(Math.random() * shellIcons.length)],
      x: 8 + Math.random() * 80,
      y: 58 + Math.random() * 28,
      collected: false,
    })
  }
  shells.value = newShells
}

function isNearShell(shell) {
  if (shell.collected) return false
  const dx = Math.abs(petPos.x - shell.x)
  const dy = Math.abs(petPos.y - shell.y)
  return dx < 6 && dy < 6
}

function checkShellCollection() {
  for (const shell of shells.value) {
    if (!shell.collected && isNearShell(shell)) {
      shell.collected = true
      collectedCount.value++
      collectFeedback.value = collectMessages[Math.floor(Math.random() * collectMessages.length)]
      if (feedbackTimer) clearTimeout(feedbackTimer)
      feedbackTimer = setTimeout(() => { collectFeedback.value = '' }, 1600)
      logIslandBehavior('activity_interact', 'beach', 'collect_shell', { count: collectedCount.value }).catch(() => {})
      emit('played', { action: 'collect_shell', count: collectedCount.value })
    }
  }
}

function clampPos() {
  petPos.x = Math.max(5, Math.min(92, petPos.x))
  petPos.y = Math.max(55, Math.min(88, petPos.y))
}

function movePet(dx, dy) {
  if (sitting.value) return
  petPos.x += dx
  petPos.y += dy
  clampPos()
  if (dx > 0) petFacing.value = 'right'
  else if (dx < 0) petFacing.value = 'left'
  checkShellCollection()
}

function onKeyDown(e) {
  const key = e.key.toLowerCase()
  if (['arrowup', 'arrowdown', 'arrowleft', 'arrowright', 'w', 'a', 's', 'd'].includes(key)) {
    e.preventDefault()
    pressedKeys.add(key)
    targetPos = null
    if (!moveInterval) {
      isMoving.value = true
      moveInterval = setInterval(() => {
        let dx = 0, dy = 0
        if (pressedKeys.has('arrowleft') || pressedKeys.has('a')) dx -= 0.8
        if (pressedKeys.has('arrowright') || pressedKeys.has('d')) dx += 0.8
        if (pressedKeys.has('arrowup') || pressedKeys.has('w')) dy -= 0.6
        if (pressedKeys.has('arrowdown') || pressedKeys.has('s')) dy += 0.6
        if (dx || dy) movePet(dx, dy)
      }, 30)
    }
  }
}

function onKeyUp(e) {
  const key = e.key.toLowerCase()
  pressedKeys.delete(key)
  if (pressedKeys.size === 0 && moveInterval) {
    clearInterval(moveInterval)
    moveInterval = null
    isMoving.value = false
  }
}

function moveToShell(shell) {
  if (shell.collected) return
  targetPos = { x: shell.x, y: shell.y }
  moveToTarget()
}

function moveToTarget() {
  if (!targetPos) return
  isMoving.value = true
  const step = () => {
    if (!targetPos) { isMoving.value = false; return }
    const dx = targetPos.x - petPos.x
    const dy = targetPos.y - petPos.y
    const dist = Math.sqrt(dx * dx + dy * dy)
    if (dist < 1.5) {
      targetPos = null
      isMoving.value = false
      checkShellCollection()
      return
    }
    const speed = 1.2
    movePet((dx / dist) * speed, (dy / dist) * speed)
    requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

function sitAndWatch() {
  sitting.value = true
  isMoving.value = false
  targetPos = null
  pressedKeys.clear()
  if (moveInterval) { clearInterval(moveInterval); moveInterval = null }
  sittingText.value = sittingTexts[Math.floor(Math.random() * sittingTexts.length)]
  logIslandBehavior('activity_interact', 'beach', 'sit_watch', {}).catch(() => {})
  emit('played', { action: 'sit_watch' })
}

function refreshShells() {
  generateShells()
  collectFeedback.value = '潮水带来了新的东西'
  if (feedbackTimer) clearTimeout(feedbackTimer)
  feedbackTimer = setTimeout(() => { collectFeedback.value = '' }, 1800)
  logIslandBehavior('activity_interact', 'beach', 'refresh', {}).catch(() => {})
}

onMounted(() => {
  generateShells()
  beachRef.value?.focus()
  logIslandBehavior('activity_start', 'beach', 'enter', { phase: currentPhase.value }).catch(() => {})
})

onBeforeUnmount(() => {
  if (feedbackTimer) clearTimeout(feedbackTimer)
  if (moveInterval) clearInterval(moveInterval)
  logIslandBehavior('activity_finish', 'beach', 'leave', { shells_collected: collectedCount.value }).catch(() => {})
})
</script>

<style scoped>
.tidal-beach {
  position: relative;
  width: 100%; height: 100%;
  min-height: 100%;
  overflow: hidden;
  outline: none;
  font-family: 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
  cursor: default;
  background: #1a1a2e;
}

.beach-bg {
  position: absolute; inset: 0;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  transition: opacity 1.2s ease;
  image-rendering: pixelated;
}

.beach-overlay {
  position: absolute; inset: 0;
  background: linear-gradient(180deg, rgba(0,0,0,.12) 0%, transparent 25%, transparent 55%, rgba(0,0,0,.18) 100%);
  pointer-events: none;
}

.beach-header {
  position: absolute; top: 14px; left: 18px; z-index: 5;
  color: #fff;
  text-shadow: 0 2px 6px rgba(0,0,0,.5);
}
.beach-header strong { display: block; font-size: 17px; font-weight: 700; }
.beach-header small { font-size: 11px; opacity: .85; }

.shell-count {
  position: absolute; top: 14px; right: 18px; z-index: 5;
  padding: 5px 12px;
  background: rgba(0,0,0,.3);
  backdrop-filter: blur(8px);
  border-radius: 12px;
  color: #fff;
  font-size: 11px; font-weight: 600;
  text-shadow: 0 1px 2px rgba(0,0,0,.4);
}

/* 贝壳 */
.collectible-shell {
  position: absolute; z-index: 3;
  font-size: 20px;
  cursor: pointer;
  transition: transform .2s, opacity .3s;
  filter: drop-shadow(0 2px 3px rgba(0,0,0,.3));
  animation: shellBob 2.5s ease-in-out infinite;
}
.collectible-shell:hover { transform: scale(1.3); }
.collectible-shell.near { animation: shellPulse .6s ease-in-out infinite; }
.collectible-shell.collected {
  opacity: 0; transform: scale(0) translateY(-20px);
  pointer-events: none;
}
@keyframes shellBob { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-3px); } }
@keyframes shellPulse { 0%,100% { transform: scale(1); } 50% { transform: scale(1.25); } }

/* 可移动咕团（项目标准形象） */
.movable-pet {
  position: absolute; z-index: 6;
  width: 56px; height: 56px;
  transform: translate(-50%, -100%);
  pointer-events: none;
}
.movable-pet.walking .pet-sprite { animation: petWalk .35s ease-in-out infinite; }
.movable-pet.facing-left .pet-sprite { transform: scaleX(-1); }

.pet-sprite {
  width: 100%; height: 100%;
  object-fit: contain;
  image-rendering: pixelated;
  animation: petIdle 3s ease-in-out infinite;
  filter: drop-shadow(0 3px 6px rgba(0,0,0,.25));
}
@keyframes petIdle { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-3px); } }
@keyframes petWalk { 0%,100% { transform: translateY(0) rotate(-2deg); } 50% { transform: translateY(-5px) rotate(2deg); } }

.pet-shadow {
  width: 36px; height: 7px;
  background: rgba(0,0,0,.2);
  border-radius: 50%;
  margin: -4px auto 0;
}

/* 收集反馈 */
.collect-feedback {
  position: absolute; top: 45%; left: 50%;
  transform: translate(-50%, -50%);
  z-index: 10;
  padding: 10px 20px;
  background: rgba(255,255,255,.92);
  color: #4A3A2A;
  border-radius: 18px;
  font-size: 13px; font-weight: 600;
  box-shadow: 0 6px 18px rgba(0,0,0,.2);
  pointer-events: none;
}

/* 静坐看海 */
.sitting-overlay {
  position: absolute; inset: 0; z-index: 20;
  background: rgba(0,0,0,.35);
  backdrop-filter: blur(4px);
  display: grid; place-items: center;
  padding: 24px;
}
.sitting-card {
  width: min(360px, 90%);
  padding: 28px 24px;
  background: rgba(255,255,255,.95);
  border-radius: 20px;
  text-align: center;
  box-shadow: 0 16px 40px rgba(0,0,0,.3);
}
.sitting-text { margin: 0 0 14px; font-size: 15px; line-height: 1.8; color: #3D3D2D; }
.sitting-hint { display: block; font-size: 11px; color: #8A7A6A; margin-bottom: 18px; }
.sitting-close {
  min-height: 38px; padding: 0 24px;
  border: 0; border-radius: 19px;
  background: linear-gradient(135deg, #FFD700, #FFA500);
  color: #2D2D1A;
  font: inherit; font-size: 12px; font-weight: 700;
  cursor: pointer;
}

/* 底部按钮 */
.beach-actions {
  position: absolute; bottom: 16px; left: 50%;
  transform: translateX(-50%);
  display: flex; gap: 10px; z-index: 5;
}
.beach-btn {
  min-height: 38px; padding: 0 20px;
  border: 0; border-radius: 19px;
  background: rgba(255,255,255,.22);
  backdrop-filter: blur(10px);
  color: #fff;
  font: inherit; font-size: 12px; font-weight: 600;
  cursor: pointer;
  transition: all .2s;
  text-shadow: 0 1px 3px rgba(0,0,0,.4);
}
.beach-btn:hover { background: rgba(255,255,255,.34); transform: translateY(-2px); }
.beach-btn.primary {
  background: linear-gradient(135deg, rgba(255,215,0,.92), rgba(255,165,0,.92));
  color: #2D2D1A; text-shadow: none;
  box-shadow: 0 4px 12px rgba(255,180,0,.35);
}

.move-hint {
  position: absolute; bottom: 56px; left: 50%;
  transform: translateX(-50%);
  font-size: 10px; color: rgba(255,255,255,.7);
  text-shadow: 0 1px 2px rgba(0,0,0,.5);
  z-index: 5;
  pointer-events: none;
}

.pop-enter-active { transition: all .3s cubic-bezier(.34,1.56,.64,1); }
.pop-leave-active { transition: all .2s; }
.pop-enter-from { opacity: 0; transform: translate(-50%, -50%) scale(.5); }
.pop-leave-to { opacity: 0; transform: translate(-50%, -50%) scale(.8); }
.fade-enter-active, .fade-leave-active { transition: opacity .4s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@media (min-width: 901px) {
  .tidal-beach:focus-visible, .tidal-beach button:focus-visible { outline: 3px solid #ffdca8; outline-offset: 3px; }
  .beach-overlay { background: linear-gradient(180deg, rgba(17,25,26,.3), transparent 35%, rgba(17,25,26,.08) 58%, rgba(17,25,26,.52)); }
  .beach-header { top: 78px; left: 28px; padding: 10px 13px; border-radius: 11px; background: rgba(24,31,30,.72); backdrop-filter: blur(14px); text-shadow: none; }
  .beach-header strong { font-size: 15px; }
  .beach-header small { color: var(--island-muted, #d9c9b5); font-size: 10px; }
  .shell-count { top: 78px; right: 28px; padding: 8px 11px; border-radius: 9px; color: var(--island-ink, #fff8ea); background: rgba(24,31,30,.72); text-shadow: none; backdrop-filter: blur(14px); }
  .collect-feedback { padding: 9px 15px; border-radius: 9px; color: #30251e; background: #f4eadb; box-shadow: 0 5px 8px rgba(0,0,0,.2); }
  .sitting-overlay { background: rgba(11,17,17,.48); backdrop-filter: blur(8px); }
  .sitting-card { width: min(390px, 90%); padding: 28px; border-radius: 14px; color: #30251e; background: #f4eadb; box-shadow: 0 6px 8px rgba(0,0,0,.24); }
  .sitting-close { min-height: 40px; border-radius: 9px; color: #2d241c; background: var(--island-accent, #efb96f); }
  .beach-actions { bottom: 24px; gap: 5px; padding: 5px; border-radius: 12px; background: rgba(24,31,30,.72); backdrop-filter: blur(14px); }
  .beach-btn { min-height: 42px; padding: 0 15px; border-radius: 9px; color: rgba(255,248,234,.82); background: transparent; text-shadow: none; transition: color .18s ease, background .18s ease, transform .18s ease; }
  .beach-btn:hover { color: var(--island-ink, #fff8ea); background: rgba(255,255,255,.08); transform: translateY(-1px); }
  .beach-btn:active { transform: scale(.98); }
  .beach-btn.primary { color: #2d241c; background: var(--island-accent, #efb96f); box-shadow: none; }
  .move-hint { bottom: 80px; padding: 5px 8px; border-radius: 7px; color: rgba(255,248,234,.72); background: rgba(24,31,30,.54); text-shadow: none; }
}

/* 像素皮肤 3.0 · 潮汐沙滩 */
.tidal-beach {
  --px-line: rgba(255, 248, 234, .24);
  --px-gold: var(--island-accent, #efb96f);
  --px-shadow: rgba(0, 0, 0, .5);
}
.beach-header strong { font-family: var(--px-font); }
.shell-count {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  font-family: var(--px-font);
}
.collect-feedback {
  --px-line: rgba(74, 58, 42, .3);
  --px-gold: #b07a45;
  border: 2px solid var(--px-line);
  border-radius: 4px;
}
.sitting-card {
  --px-line: rgba(61, 61, 45, .3);
  --px-gold: #b07a45;
  --px-shadow: rgba(61, 61, 45, .26);
  border: 2px solid var(--px-line);
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.sitting-close {
  border: 2px solid var(--px-gold);
  border-radius: 4px;
  background: var(--px-gold);
  color: #fff8ea;
  box-shadow: 2px 2px 0 var(--px-shadow);
  font-family: var(--px-font);
}
.beach-btn {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: 3px 3px 0 var(--px-shadow);
  font-family: var(--px-font);
  transition: background 160ms steps(2, end), transform 160ms steps(2, end), box-shadow 160ms steps(2, end);
}
.beach-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.beach-btn:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--px-shadow);
}
.beach-btn.primary {
  border-color: var(--px-gold);
  background: var(--px-gold);
  color: #2d241c;
  text-shadow: none;
}
.move-hint { border-radius: 4px; }
.tidal-beach:focus-visible,
.tidal-beach button:focus-visible { outline: 3px dashed var(--px-gold); outline-offset: 3px; }

@media (min-width: 901px) {
  .beach-header {
    border: 2px solid var(--px-line);
    border-radius: 6px;
    box-shadow: 4px 4px 0 var(--px-shadow);
  }
  .beach-actions {
    border: 2px solid var(--px-line);
    border-radius: 6px;
    box-shadow: 4px 4px 0 var(--px-shadow);
  }
}

@media (prefers-reduced-motion: reduce) {
  .tidal-beach *, .collectible-shell, .pet-sprite { animation: none !important; transition-duration: .01ms !important; }
}
</style>
