<template>
  <div class="breathing-room" :class="`phase-${currentPhase}`">
    <!-- 背景图 -->
    <div class="room-bg" :style="{ backgroundImage: `url(${bgImage})` }"></div>
    <div class="room-overlay"></div>

    <!-- 顶部 -->
    <div class="breath-header">
      <strong>星灯呼吸小屋</strong>
      <small>跟着光，慢慢呼吸</small>
    </div>

    <!-- 模式选择 -->
    <div v-if="!breathing" class="mode-selector">
      <p class="mode-hint">选一种呼吸方式，不用勉强，随时可以停。</p>
      <div class="mode-cards">
        <button
          v-for="mode in modes"
          :key="mode.id"
          class="mode-card"
          :class="{ active: selectedMode === mode.id }"
          @click="selectedMode = mode.id"
        >
          <span class="mode-icon">{{ mode.icon }}</span>
          <strong>{{ mode.name }}</strong>
          <small>{{ mode.pattern }}</small>
          <em>{{ mode.desc }}</em>
        </button>
      </div>
      <p class="breath-safety-note">如果出现头晕、胸闷或呼吸不适，请立即停止并恢复自然呼吸；已有呼吸或心血管不适时，不选择含屏息的练习。</p>
      <button type="button" class="start-btn" @click="startBreathing">
        开始呼吸
      </button>
    </div>

    <!-- 呼吸进行中 -->
    <div v-else class="breathing-area">
      <div class="breath-circle-wrap">
        <div class="breath-glow" :class="breathState"></div>
        <div class="breath-circle" :class="breathState">
          <div class="breath-inner">
            <span class="breath-text">{{ breathText }}</span>
            <span class="breath-count" v-if="cycleCount > 0">{{ cycleCount }} / {{ targetCycles }}</span>
          </div>
        </div>
        <div class="breath-ring ring-1" :class="breathState"></div>
        <div class="breath-ring ring-2" :class="breathState"></div>
      </div>
      <div class="breath-guide">
        <p>{{ guideText }}</p>
      </div>
      <div class="breath-controls">
        <button type="button" class="stop-btn" @click="stopBreathing">
          {{ finished ? '完成' : '先停在这里' }}
        </button>
      </div>
    </div>

    <!-- 完成反馈 -->
    <transition name="fade">
      <div v-if="showComplete" class="complete-overlay">
        <div class="complete-card">
          <div class="complete-icon-wrap">
            <span class="complete-icon">✦</span>
          </div>
          <strong>做得很好</strong>
          <p>刚才的{{ completedCycles }}次呼吸，是你给自己的一小段安静时间。</p>
          <p class="complete-sub">不用记录什么，你刚刚为自己留出了一段暂停时间。</p>
          <button type="button" class="complete-btn" @click="reset">
            回到小屋
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { logIslandBehavior } from '../../api/island.js'
import breathingDay from '../../assets/island/breathing-day.png'
import breathingDusk from '../../assets/island/breathing-dusk.png'
import breathingNight from '../../assets/island/breathing-night.png'

const props = defineProps({ timePhase: { type: String, default: '' } })
const emit = defineEmits(['played'])

const modes = [
  { id: 'box', name: '星灯呼吸', icon: '✦', pattern: '吸4秒 · 屏4秒 · 呼4秒 · 屏4秒', desc: '日常放松，稳定心神' },
  { id: '478', name: '深海呼吸', icon: '🌊', pattern: '吸4秒 · 屏7秒 · 呼8秒', desc: '节奏较慢，可按舒适程度练习' },
  { id: 'coherent', name: '海浪呼吸', icon: '〜', pattern: '吸5秒 · 呼5秒', desc: '不含屏息，节奏简单' },
]

const currentPhase = ref(props.timePhase || 'day')
watch(() => props.timePhase, (value) => { if (value) currentPhase.value = value })
const selectedMode = ref('box')
const breathing = ref(false)
const breathState = ref('idle')
const breathText = ref('准备')
const guideText = ref('')
const cycleCount = ref(0)
const completedCycles = ref(0)
const finished = ref(false)
const showComplete = ref(false)
let breathTimer = null

const bgImage = computed(() => ({
  day: breathingDay, dusk: breathingDusk, night: breathingNight,
}[currentPhase.value] || breathingNight))

const targetCycles = computed(() => {
  const m = modes.find(m => m.id === selectedMode.value)
  return m?.id === 'coherent' ? 6 : 4
})

const BREATH_SEQUENCES = {
  box: [
    { state: 'inhale', text: '吸气', duration: 4000, guide: '慢慢吸气，感受空气充满胸腔' },
    { state: 'hold', text: '屏住', duration: 4000, guide: '轻轻屏住，不用用力' },
    { state: 'exhale', text: '呼气', duration: 4000, guide: '慢慢呼气，把紧张一起带走' },
    { state: 'hold2', text: '停顿', duration: 4000, guide: '停顿一下，准备下一次' },
  ],
  '478': [
    { state: 'inhale', text: '吸气', duration: 4000, guide: '用鼻子慢慢吸气，数4秒' },
    { state: 'hold', text: '屏住', duration: 7000, guide: '屏住呼吸，数7秒' },
    { state: 'exhale', text: '呼气', duration: 8000, guide: '用嘴慢慢呼气，数8秒' },
  ],
  coherent: [
    { state: 'inhale', text: '吸气', duration: 5000, guide: '像海浪涨潮一样，慢慢吸气' },
    { state: 'exhale', text: '呼气', duration: 5000, guide: '像海浪退潮一样，慢慢呼气' },
  ],
}

function startBreathing() {
  breathing.value = true
  breathState.value = 'idle'
  breathText.value = '准备'
  guideText.value = '找到一个舒服的姿势，准备好了就开始。'
  cycleCount.value = 0
  finished.value = false
  logIslandBehavior('activity_start', 'rest', 'breathing', { mode: selectedMode.value }).catch(() => {})
  setTimeout(() => runCycle(), 1500)
}

function runCycle() {
  if (!breathing.value) return
  const sequence = BREATH_SEQUENCES[selectedMode.value]
  let stepIndex = 0
  function nextStep() {
    if (!breathing.value) return
    if (stepIndex >= sequence.length) {
      cycleCount.value++
      if (cycleCount.value >= targetCycles.value) { finishBreathing(); return }
      stepIndex = 0
    }
    const step = sequence[stepIndex]
    breathState.value = step.state
    breathText.value = step.text
    guideText.value = step.guide
    stepIndex++
    breathTimer = setTimeout(nextStep, step.duration)
  }
  nextStep()
}

function stopBreathing() {
  if (breathTimer) clearTimeout(breathTimer)
  breathing.value = false
  completedCycles.value = cycleCount.value
  if (cycleCount.value > 0) showComplete.value = true
  logIslandBehavior('activity_finish', 'rest', 'breathing', {
    mode: selectedMode.value, cycles: cycleCount.value,
    completed: cycleCount.value >= targetCycles.value,
    stopped_early: cycleCount.value < targetCycles.value,
  }).catch(() => {})
  emit('played', { action: 'breathing', cycles: cycleCount.value, mode: selectedMode.value })
}

function finishBreathing() {
  if (breathTimer) clearTimeout(breathTimer)
  finished.value = true
  breathText.value = '完成'
  guideText.value = '做得很好，慢慢回到当下。'
  completedCycles.value = cycleCount.value
}

function reset() {
  showComplete.value = false
  breathing.value = false
  breathState.value = 'idle'
  cycleCount.value = 0
}

onBeforeUnmount(() => {
  if (breathTimer) clearTimeout(breathTimer)
})
</script>

<style scoped>
.breathing-room {
  position: relative;
  width: 100%; height: 100%;
  min-height: 100%;
  overflow: hidden;
  font-family: 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
  color: #fff;
  background: #1a1a2e;
}

.room-bg {
  position: absolute; inset: 0;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  image-rendering: pixelated;
}
.room-overlay {
  position: absolute; inset: 0;
  background: linear-gradient(180deg, rgba(0,0,0,.2) 0%, transparent 30%, transparent 50%, rgba(0,0,0,.3) 100%);
  pointer-events: none;
}

.breath-header {
  position: absolute; top: 16px; left: 20px; z-index: 5;
  text-shadow: 0 2px 6px rgba(0,0,0,.5);
}
.breath-header strong { display: block; font-size: 17px; font-weight: 700; }
.breath-header small { font-size: 11px; opacity: .85; }

/* 模式选择 */
.mode-selector {
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 60px 24px 24px; z-index: 4;
}
.mode-hint {
  font-size: 13px; opacity: .9; margin: 0 0 24px;
  text-align: center; text-shadow: 0 1px 3px rgba(0,0,0,.5);
}
.mode-cards { display: flex; gap: 14px; flex-wrap: wrap; justify-content: center; max-width: 580px; margin-bottom: 28px; }
.mode-card {
  width: 165px; min-height: 150px;
  padding: 18px 16px;
  border: 0; border-radius: 18px;
  background: rgba(255,255,255,.15);
  backdrop-filter: blur(14px);
  color: #fff; font: inherit; text-align: center;
  cursor: pointer; transition: all .3s;
  display: flex; flex-direction: column; align-items: center; gap: 5px;
  text-shadow: 0 1px 3px rgba(0,0,0,.4);
}
.mode-card:hover { background: rgba(255,255,255,.25); transform: translateY(-3px); }
.mode-card.active {
  background: rgba(255,215,0,.2);
  box-shadow: 0 0 0 2px rgba(255,215,0,.5), 0 8px 30px rgba(255,215,0,.2);
}
.mode-icon { font-size: 30px; margin-bottom: 6px; }
.mode-card strong { font-size: 14px; font-weight: 700; }
.mode-card small { font-size: 10px; opacity: .8; line-height: 1.4; }
.mode-card em { font-size: 10px; opacity: .7; font-style: normal; margin-top: 4px; }

.start-btn {
  min-height: 46px; padding: 0 36px;
  border: 0; border-radius: 24px;
  background: linear-gradient(135deg, #FFD700, #FFA500);
  color: #2D2D1A;
  font: inherit; font-size: 14px; font-weight: 700;
  cursor: pointer; transition: all .2s;
  box-shadow: 0 6px 20px rgba(255,215,0,.35);
}
.start-btn:hover { transform: scale(1.04); }

/* 呼吸进行中 */
.breathing-area {
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  z-index: 4;
}
.breath-circle-wrap {
  position: relative;
  width: 220px; height: 220px;
  display: grid; place-items: center;
  margin-bottom: 28px;
}
.breath-glow {
  position: absolute; inset: -40px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255,215,0,.25), transparent 70%);
  transition: all 1s ease; opacity: .5;
}
.breath-glow.inhale { transform: scale(1.3); opacity: .85; }
.breath-glow.exhale { transform: scale(.8); opacity: .3; }
.breath-circle {
  width: 160px; height: 160px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, rgba(255,255,255,.25), rgba(255,215,0,.2));
  border: 2px solid rgba(255,215,0,.5);
  display: grid; place-items: center;
  transition: transform 1s ease, background 1s ease;
  position: relative; z-index: 2;
  backdrop-filter: blur(4px);
}
.breath-circle.inhale { transform: scale(1.45); background: radial-gradient(circle at 35% 30%, rgba(255,255,255,.35), rgba(255,215,0,.3)); border-color: rgba(255,215,0,.7); }
.breath-circle.exhale { transform: scale(.8); background: radial-gradient(circle at 35% 30%, rgba(150,200,255,.25), rgba(100,150,255,.2)); border-color: rgba(150,200,255,.5); }
.breath-circle.hold, .breath-circle.hold2 { transform: scale(1.15); }
.breath-inner { text-align: center; }
.breath-text { display: block; font-size: 24px; font-weight: 700; letter-spacing: 2px; text-shadow: 0 2px 6px rgba(0,0,0,.4); }
.breath-count { display: block; font-size: 12px; opacity: .8; margin-top: 6px; text-shadow: 0 1px 3px rgba(0,0,0,.4); }
.breath-ring {
  position: absolute; border-radius: 50%;
  border: 1px solid rgba(255,215,0,.25);
  transition: all 1s ease;
}
.ring-1 { width: 190px; height: 190px; }
.ring-2 { width: 220px; height: 220px; opacity: .5; }
.ring-1.inhale, .ring-2.inhale { transform: scale(1.3); border-color: rgba(255,215,0,.4); }
.ring-1.exhale, .ring-2.exhale { transform: scale(.75); }

.breath-guide { text-align: center; margin-bottom: 24px; max-width: 340px; }
.breath-guide p { margin: 0; font-size: 14px; opacity: .9; line-height: 1.6; text-shadow: 0 1px 3px rgba(0,0,0,.5); }

.stop-btn {
  min-height: 40px; padding: 0 26px;
  border: 0; border-radius: 22px;
  background: rgba(255,255,255,.2);
  backdrop-filter: blur(10px);
  color: #fff; font: inherit; font-size: 13px; font-weight: 600;
  cursor: pointer; transition: background .2s;
  text-shadow: 0 1px 3px rgba(0,0,0,.4);
}
.stop-btn:hover { background: rgba(255,255,255,.3); }

/* 完成 */
.complete-overlay {
  position: absolute; inset: 0;
  background: rgba(0,0,0,.4);
  backdrop-filter: blur(6px);
  display: grid; place-items: center;
  z-index: 10; padding: 24px;
}
.complete-card {
  width: min(340px, 90%);
  padding: 32px 28px;
  background: rgba(255,255,255,.96);
  color: #3D3D2D;
  border-radius: 22px;
  text-align: center;
  box-shadow: 0 24px 60px rgba(0,0,0,.3);
}
.complete-icon-wrap { position: relative; width: 60px; height: 60px; margin: 0 auto 12px; display: grid; place-items: center; }
.complete-icon { font-size: 40px; color: #FFD700; animation: iconFloat 2s ease-in-out infinite; }
@keyframes iconFloat { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
.complete-card strong { display: block; font-size: 18px; margin-bottom: 10px; }
.complete-card p { margin: 6px 0; font-size: 13px; line-height: 1.6; color: #5A5A4A; }
.complete-sub { font-size: 11px !important; opacity: .65; }
.breath-safety-note { max-width: 720px; margin: 0; color: rgba(255,255,255,.72); font-size: 11px; line-height: 1.55; text-align: center; }
.complete-btn {
  margin-top: 18px;
  min-height: 40px; padding: 0 28px;
  border: 0; border-radius: 20px;
  background: linear-gradient(135deg, #FFD700, #FFA500);
  color: #2D2D1A;
  font: inherit; font-size: 13px; font-weight: 700;
  cursor: pointer;
}

.fade-enter-active, .fade-leave-active { transition: opacity .4s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@media (min-width: 901px) {
  .breathing-room button:focus-visible { outline: 3px solid #ffdca8; outline-offset: 3px; }
  .room-overlay { background: linear-gradient(180deg, rgba(16,22,22,.34), rgba(16,22,22,.04) 34%, rgba(16,22,22,.16) 64%, rgba(16,22,22,.58)); }
  .breath-header { top: 78px; left: 28px; padding: 10px 13px; border-radius: 11px; background: rgba(24,31,30,.7); backdrop-filter: blur(14px); text-shadow: none; }
  .breath-header strong { font-size: 15px; }
  .breath-header small { color: var(--island-muted, #d9c9b5); font-size: 10px; }
  .mode-selector { align-items: flex-start; justify-content: flex-end; padding: 128px 32px 34px; }
  .mode-hint { max-width: 440px; margin: 0 0 14px; color: rgba(255,248,234,.78); text-align: left; text-shadow: 0 1px 2px rgba(0,0,0,.45); }
  .mode-cards { justify-content: flex-start; max-width: 660px; margin-bottom: 16px; }
  .mode-card { width: 190px; min-height: 116px; align-items: flex-start; gap: 3px; padding: 15px; border-radius: 12px; color: var(--island-ink, #fff8ea); background: rgba(24,31,30,.72); backdrop-filter: blur(14px); text-align: left; text-shadow: none; transition: background .18s ease, transform .18s ease; }
  .mode-card:hover { background: rgba(39,49,47,.86); transform: translateY(-2px); }
  .mode-card.active { background: rgba(239,185,111,.92); color: #2d241c; box-shadow: none; }
  .mode-icon { display: grid; width: 28px; height: 28px; margin-bottom: 5px; place-items: center; border-radius: 8px; background: rgba(255,255,255,.1); font-size: 17px; }
  .mode-card.active .mode-icon { background: rgba(45,36,28,.1); }
  .mode-card em { margin-top: 3px; }
  .start-btn { min-height: 44px; padding: 0 24px; border-radius: 9px; color: #2d241c; background: var(--island-accent, #efb96f); box-shadow: none; transition: background .18s ease, transform .18s ease; }
  .start-btn:hover { background: #f3c789; transform: translateY(-1px); }
  .start-btn:active { transform: scale(.98); }
  .breathing-area { padding-top: 36px; }
  .breath-circle-wrap { width: 250px; height: 250px; margin-bottom: 24px; }
  .breath-circle { border-color: rgba(239,185,111,.56); background: radial-gradient(circle at 35% 30%, rgba(255,255,255,.24), rgba(239,185,111,.2)); backdrop-filter: blur(8px); }
  .breath-glow { background: radial-gradient(circle, rgba(239,185,111,.24), transparent 70%); }
  .breath-ring { border-color: rgba(239,185,111,.24); }
  .stop-btn { min-height: 40px; padding: 0 18px; border-radius: 9px; background: rgba(24,31,30,.72); text-shadow: none; }
  .stop-btn:hover { background: rgba(39,49,47,.88); }
  .complete-card { border-radius: 14px; color: #30251e; background: #f4eadb; box-shadow: 0 6px 8px rgba(0,0,0,.24); }
  .complete-btn { border-radius: 9px; color: #2d241c; background: var(--island-accent, #efb96f); }
}

/* 像素皮肤 3.0 · 星灯呼吸小屋 */
.breathing-room {
  --px-line: rgba(255, 248, 234, .24);
  --px-gold: var(--island-accent, #efb96f);
  --px-shadow: rgba(0, 0, 0, .5);
}
.breath-header strong { font-family: var(--px-font); }
.mode-card {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: 3px 3px 0 var(--px-shadow);
  transition: background 160ms steps(2, end), transform 160ms steps(2, end), box-shadow 160ms steps(2, end);
}
.mode-card:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.mode-card:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--px-shadow);
}
.mode-card.active { border-color: var(--px-gold); }
.mode-icon { border-radius: 4px; }
.mode-card strong { font-family: var(--px-font); }
.start-btn {
  border: 2px solid var(--px-gold);
  border-radius: 4px;
  background: var(--px-gold);
  color: #2d241c;
  box-shadow: 3px 3px 0 var(--px-shadow);
  font-family: var(--px-font);
  transition: background 160ms steps(2, end), transform 160ms steps(2, end), box-shadow 160ms steps(2, end);
}
.start-btn:hover {
  background: #f3c789;
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.start-btn:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--px-shadow);
}
.breath-text { font-family: var(--px-font); }
.stop-btn {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: 3px 3px 0 var(--px-shadow);
  font-family: var(--px-font);
  transition: background 160ms steps(2, end), transform 160ms steps(2, end), box-shadow 160ms steps(2, end);
}
.stop-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.stop-btn:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--px-shadow);
}
.complete-card {
  --px-line: rgba(74, 58, 42, .3);
  --px-gold: #b07a45;
  --px-shadow: rgba(74, 58, 42, .26);
  border: 2px solid var(--px-line);
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.complete-card strong { font-family: var(--px-font); }
.complete-btn {
  border: 2px solid var(--px-gold);
  border-radius: 4px;
  background: var(--px-gold);
  color: #fff8ea;
  box-shadow: 3px 3px 0 var(--px-shadow);
  font-family: var(--px-font);
}
.breathing-room button:focus-visible { outline: 3px dashed var(--px-gold); outline-offset: 3px; }

/* 窄屏：白天亮天空下白色半透明卡片几乎不可读，改用深色玻璃底 */
@media (max-width: 900px) {
  .breath-header {
    padding: 6px 10px;
    border-radius: 4px;
    background: rgba(24,31,30,.6);
    text-shadow: none;
  }
  .mode-hint {
    margin-bottom: 18px;
    padding: 6px 12px;
    border-radius: 4px;
    background: rgba(24,31,30,.58);
    color: rgba(255,248,234,.9);
    text-shadow: none;
  }
  .mode-card {
    color: var(--island-ink, #fff8ea);
    background: rgba(24,31,30,.64);
    backdrop-filter: blur(10px);
    text-shadow: none;
  }
  .mode-card:hover { background: rgba(39,49,47,.78); }
  .mode-card.active { background: rgba(47,50,36,.84); }
  .mode-card small { opacity: .85; }
  .mode-card em { opacity: .75; }
  .breath-safety-note {
    padding: 8px 12px;
    border-radius: 4px;
    color: rgba(255,248,234,.86);
    background: rgba(24,31,30,.58);
    backdrop-filter: blur(8px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .breathing-room *, .complete-icon { animation: none !important; transition-duration: .01ms !important; }
}
</style>
