<template>
  <section
    ref="dialog"
    class="island-workspace"
    data-workspace="leisure"
    role="dialog"
    aria-modal="true"
    aria-labelledby="island-title"
    @click.stop
    @pointerdown.stop
    @keydown="handleDialogKeydown"
  >
    <header class="island-header">
      <div>
        <p>咕哝 · 心岛探索</p>
        <h2 id="island-title">把心情放进一座能慢慢走的岛</h2>
      </div>
      <div class="island-header-actions">
        <button type="button" class="island-games-entry" @click="$emit('fallback')">去小田园和慢钓台</button>
        <button ref="closeButton" type="button" class="island-close" aria-label="关闭心岛，返回房间" @click="$emit('close')">×</button>
      </div>
    </header>

    <div class="island-layout">
      <main class="island-stage-shell">
        <div
          ref="gameSurface"
          class="island-game-surface"
          tabindex="0"
          aria-label="心岛地图控制区"
          aria-describedby="island-instructions island-live-status"
          @click="focusGameSurface"
          @keydown="handleGameKeydown"
          @keyup="handleGameKeyup"
          @blur="stopKeyboardMoving"
        >
          <div ref="gameHost" class="island-game-host" aria-hidden="true"></div>
          <div v-if="loading" class="island-loading" role="status">
            <span aria-hidden="true"></span>
            <strong>正在铺开岛屿地图</strong>
            <small>游戏引擎只在进入心岛后加载</small>
          </div>
          <div v-else-if="loadError" class="island-error" role="alert">
            <strong>心岛暂时没有展开</strong>
            <p>房间与原有休闲内容都还在，可以重试或切换到经典休闲角。</p>
            <div>
              <button type="button" @click="startGame">重新尝试</button>
              <button type="button" @click="$emit('fallback')">打开经典休闲角</button>
            </div>
          </div>
        </div>

        <p id="island-instructions" class="island-instructions">
          使用方向键或 WASD 行走，点击地图或地点按钮可自动前往，Enter 或空格互动。
        </p>
        <p id="island-live-status" class="sr-only" role="status" aria-live="polite">{{ liveStatus }}</p>

        <div class="island-mobile-controls" aria-label="心岛移动控制">
          <button type="button" aria-label="向上移动" @pointerdown="startPointerMove($event, 0, -1)" @pointerup="stopMoving" @pointercancel="stopMoving" @lostpointercapture="stopMoving">↑</button>
          <button type="button" aria-label="向左移动" @pointerdown="startPointerMove($event, -1, 0)" @pointerup="stopMoving" @pointercancel="stopMoving" @lostpointercapture="stopMoving">←</button>
          <button type="button" class="is-interact" @click="interact">互动</button>
          <button type="button" aria-label="向右移动" @pointerdown="startPointerMove($event, 1, 0)" @pointerup="stopMoving" @pointercancel="stopMoving" @lostpointercapture="stopMoving">→</button>
          <button type="button" aria-label="向下移动" @pointerdown="startPointerMove($event, 0, 1)" @pointerup="stopMoving" @pointercancel="stopMoving" @lostpointercapture="stopMoving">↓</button>
        </div>
      </main>

      <aside class="island-side-panel" aria-label="心岛任务与地点">
        <section class="island-agent-card">
          <div class="island-agent-heading">
            <span :class="['agent-state-dot', `is-${agentPhase}`]" aria-hidden="true"></span>
            <div>
              <small>心岛陪伴 Agent</small>
              <strong>{{ agentText }}</strong>
            </div>
          </div>
          <ol>
            <li class="is-complete"><span>✓</span><div><strong>理解探索选择</strong><small>以你的主动选择为准</small></div></li>
            <li class="is-complete"><span>✓</span><div><strong>确认安全边界</strong><small>不从走路与成绩推断情绪</small></div></li>
            <li :class="agentPhase === 'arrived' ? 'is-complete' : 'is-running'"><span>{{ agentPhase === 'arrived' ? '✓' : '•' }}</span><div><strong>陪伴行动</strong><small>{{ currentPlaceLabel }}</small></div></li>
            <li :class="agentPhase === 'arrived' ? 'is-running' : 'is-waiting'"><span>·</span><div><strong>自主回看</strong><small>由你决定是否记录感受</small></div></li>
          </ol>
          <p>展示的是可核验工作状态，不展示私有思维过程，也不进行心理诊断。</p>
        </section>

        <section class="island-place-card">
          <div class="island-section-title">
            <div><small>简化操作模式</small><h3>想先去哪里？</h3></div>
            <span>{{ currentPlaceLabel }}</span>
          </div>
          <div class="island-place-grid">
            <button v-for="place in places" :key="place.id" type="button" @click="visitPlace(place)">
              <strong>{{ place.label }}</strong>
              <small>{{ place.hint }}</small>
            </button>
          </div>
        </section>

        <section v-if="arrivalCard" class="island-arrival-card" aria-live="polite">
          <small>已到达 · {{ arrivalCard.label }}</small>
          <strong>{{ arrivalCard.hint }}</strong>
          <button type="button" @click="arrivalCard = null">我知道了</button>
        </section>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { createIslandBridge } from '../../game/island/islandBridge.js'
import { ISLAND_PLACES, loadIslandState, saveIslandState } from '../../game/island/islandState.js'

const props = defineProps({ storageScope: { type: [String, Number], required: true } })
const emit = defineEmits(['close', 'fallback'])
const dialog = ref(null)
const closeButton = ref(null)
const gameHost = ref(null)
const gameSurface = ref(null)
const loading = ref(true)
const loadError = ref(false)
const agentPhase = ref('ready')
const agentText = ref('已准备好，等你选择方向')
const liveStatus = ref('心岛地图正在准备')
const nearby = ref('潮汐小屋')
const arrivalCard = ref(null)
const places = ISLAND_PLACES
const bridge = createIslandBridge()
const currentState = ref(loadIslandState(props.storageScope))
const currentPlaceLabel = computed(() => nearby.value || '岛屿小径')
let game = null
let cancelled = false
let disposers = []
let movementSource = 'none'
const pressedDirections = new Set()
const keyboardDirections = {
  ArrowUp: [0, -1], KeyW: [0, -1], ArrowDown: [0, 1], KeyS: [0, 1],
  ArrowLeft: [-1, 0], KeyA: [-1, 0], ArrowRight: [1, 0], KeyD: [1, 0],
}

function bindBridge() {
  disposers.forEach(dispose => dispose())
  disposers = [
    bridge.on('ready', event => {
      loading.value = false
      const restoredPlace = places.find(place => place.id === event.place)?.label || '岛屿小径'
      liveStatus.value = `心岛已打开。你现在位于${restoredPlace}附近。`
      nextTick(() => {
        if (document.activeElement === closeButton.value || document.activeElement === document.body) {
          gameSurface.value?.focus({ preventScroll: true })
        }
      })
    }),
    bridge.on('agent', event => {
      agentPhase.value = event.phase
      agentText.value = event.text
    }),
    bridge.on('position', event => {
      nearby.value = event.nearby
      currentState.value = { position: event.position, lastPlace: event.place }
      saveIslandState(props.storageScope, currentState.value)
    }),
    bridge.on('status', event => {
      liveStatus.value = event.text
    }),
    bridge.on('arrive', event => {
      nearby.value = event.label
      arrivalCard.value = event
      liveStatus.value = `已到达${event.label}。${event.hint}`
      currentState.value = { position: event.position, lastPlace: event.place }
      saveIslandState(props.storageScope, currentState.value)
    }),
  ]
}

async function startGame() {
  if (game || !gameHost.value) return
  loading.value = true
  loadError.value = false
  bindBridge()
  try {
    const { createIslandGame } = await import('../../game/island/createIslandGame.js')
    if (cancelled || !gameHost.value) return
    game = await createIslandGame({
      parent: gameHost.value,
      bridge,
      initialState: currentState.value,
      reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    })
  } catch (error) {
    console.error('Heart Island failed to start', error)
    loading.value = false
    loadError.value = true
    liveStatus.value = '心岛加载失败，可以重试或进入经典休闲角。'
  }
}

function focusGameSurface() {
  gameSurface.value?.focus({ preventScroll: true })
}

function startMoving(x, y, source = 'keyboard') {
  movementSource = source
  bridge.emit('command', { type: 'move', direction: { x, y } })
}

function startPointerMove(event, x, y) {
  try {
    event.currentTarget?.setPointerCapture?.(event.pointerId)
  } catch {
    // Synthetic or already-cancelled pointers may not be capturable; window listeners still stop movement.
  }
  startMoving(x, y, 'pointer')
}

function stopMoving() {
  movementSource = 'none'
  pressedDirections.clear()
  bridge.emit('command', { type: 'stop' })
}

function stopKeyboardMoving() {
  pressedDirections.clear()
  if (movementSource === 'keyboard') stopMoving()
}

function stopPointerMoving() {
  if (movementSource === 'pointer') stopMoving()
}

function interact() {
  bridge.emit('command', { type: 'interact' })
}

function visitPlace(place) {
  bridge.emit('command', { type: 'visit', placeId: place.id })
  liveStatus.value = `正在前往${place.label}。`
  focusGameSurface()
}

function handleGameKeydown(event) {
  if (keyboardDirections[event.code]) {
    event.preventDefault()
    pressedDirections.add(event.code)
    updateKeyboardMovement()
  } else if (event.code === 'Enter' || event.code === 'Space') {
    event.preventDefault()
    interact()
  }
}

function handleGameKeyup(event) {
  if (!keyboardDirections[event.code]) return
  event.preventDefault()
  pressedDirections.delete(event.code)
  updateKeyboardMovement()
}

function updateKeyboardMovement() {
  const vector = [...pressedDirections].reduce((sum, code) => {
    const [x, y] = keyboardDirections[code]
    return { x: sum.x + x, y: sum.y + y }
  }, { x: 0, y: 0 })
  if (vector.x || vector.y) startMoving(vector.x, vector.y, 'keyboard')
  else if (movementSource === 'keyboard') stopMoving()
}

function handleDialogKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    stopMoving()
    emit('close')
    return
  }
  if (event.key !== 'Tab') return
  const focusable = [...dialog.value.querySelectorAll('button:not([disabled]), [tabindex="0"]')]
  if (!focusable.length) return
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

onMounted(async () => {
  window.addEventListener('pointerup', stopPointerMoving)
  window.addEventListener('pointercancel', stopPointerMoving)
  window.addEventListener('blur', stopMoving)
  await nextTick()
  closeButton.value?.focus({ preventScroll: true })
  startGame()
})

onBeforeUnmount(() => {
  cancelled = true
  stopMoving()
  window.removeEventListener('pointerup', stopPointerMoving)
  window.removeEventListener('pointercancel', stopPointerMoving)
  window.removeEventListener('blur', stopMoving)
  disposers.forEach(dispose => dispose())
  disposers = []
  game?.destroy(true)
  game = null
  bridge.clear()
})
</script>

<style scoped>
.island-workspace {
  --island-ink: #fbf7ed;
  --island-muted: rgba(251, 247, 237, .7);
  position: fixed;
  inset: max(12px, env(safe-area-inset-top)) max(12px, env(safe-area-inset-right)) max(12px, env(safe-area-inset-bottom)) max(12px, env(safe-area-inset-left));
  z-index: 410;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
  color: var(--island-ink);
  border: 1px solid rgba(255,255,255,.18);
  border-radius: 22px;
  background: rgba(12, 18, 28, .94);
  box-shadow: 0 24px 80px rgba(4, 8, 18, .46), inset 0 1px 0 rgba(255,255,255,.12);
  backdrop-filter: blur(26px) saturate(1.18);
  font-family: 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
}
.island-header { display: flex; align-items: center; justify-content: space-between; gap: 18px; min-height: 74px; padding: 12px 18px 12px 22px; border-bottom: 1px solid rgba(255,255,255,.1); }
.island-header p, .island-header h2 { margin: 0; }
.island-header p { color: #b9dec9; font-size: 11px; font-weight: 800; letter-spacing: .05em; }
.island-header h2 { margin-top: 3px; font-size: clamp(16px, 2vw, 21px); line-height: 1.35; }
.island-header-actions { display: flex; align-items: center; gap: 8px; }
.island-games-entry { min-height: 44px; padding: 0 13px; border: 0; border-radius: 11px; color: #17261f; background: #b9dec9; font-weight: 800; cursor: pointer; }
.island-close { width: 48px; height: 48px; flex: 0 0 auto; border: 1px solid rgba(255,255,255,.12); border-radius: 13px; color: #fff; background: rgba(255,255,255,.08); font-size: 24px; cursor: pointer; }
.island-layout { display: grid; grid-template-columns: minmax(0, 1fr) 326px; min-height: 0; }
.island-stage-shell { display: grid; place-items: center; align-content: center; min-width: 0; min-height: 0; padding: 18px; background: radial-gradient(circle at 48% 44%, rgba(82,123,132,.2), transparent 62%); }
.island-game-surface { position: relative; width: min(100%, 1120px); aspect-ratio: 16 / 9; overflow: hidden; border: 1px solid rgba(255,255,255,.14); border-radius: 17px; background: #213b58; box-shadow: 0 16px 38px rgba(2,7,16,.35); touch-action: none; }
.island-game-host, .island-game-host :deep(canvas) { width: 100%; height: 100%; image-rendering: pixelated; }
.island-game-host :deep(canvas) { display: block; }
.island-loading, .island-error { position: absolute; inset: 0; z-index: 2; display: grid; place-content: center; justify-items: center; gap: 8px; padding: 24px; text-align: center; background: linear-gradient(145deg, #203b55, #182c44); }
.island-loading span { width: 28px; height: 28px; border: 4px solid rgba(255,255,255,.18); border-top-color: #b9dec9; border-radius: 50%; animation: island-spin .9s linear infinite; }
.island-loading small, .island-error p { color: var(--island-muted); font-size: 12px; }
.island-error p { max-width: 420px; margin: 0; line-height: 1.65; }
.island-error div { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; }
.island-error button, .island-arrival-card button { min-height: 44px; padding: 0 14px; border: 0; border-radius: 11px; color: #17261f; background: #b9dec9; font-weight: 800; cursor: pointer; }
.island-instructions { width: min(100%, 1120px); margin: 10px 0 0; color: var(--island-muted); font-size: 12px; text-align: center; }
.island-side-panel { display: grid; align-content: start; gap: 12px; min-height: 0; overflow-y: auto; padding: 16px; border-left: 1px solid rgba(255,255,255,.1); background: rgba(255,255,255,.025); }
.island-agent-card, .island-place-card, .island-arrival-card { padding: 15px; border: 1px solid rgba(255,255,255,.1); border-radius: 15px; background: rgba(255,255,255,.055); }
.island-agent-heading { display: flex; align-items: center; gap: 10px; }
.agent-state-dot { width: 11px; height: 11px; flex: 0 0 auto; border-radius: 3px; background: #d9bd79; }
.agent-state-dot.is-arrived { background: #9ed1b3; }
.island-agent-heading small, .island-agent-heading strong { display: block; }
.island-agent-heading small, .island-section-title small { color: #b9dec9; font-size: 10px; font-weight: 800; }
.island-agent-heading strong { margin-top: 2px; font-size: 12px; line-height: 1.45; }
.island-agent-card ol { display: grid; gap: 4px; margin: 14px 0 0; padding: 0; list-style: none; }
.island-agent-card li { display: grid; grid-template-columns: 24px minmax(0,1fr); gap: 8px; padding: 8px 0; border-top: 1px solid rgba(255,255,255,.07); }
.island-agent-card li > span { display: grid; place-items: center; width: 22px; height: 22px; border-radius: 6px; background: rgba(255,255,255,.08); font-weight: 900; }
.island-agent-card li.is-complete > span { color: #16251e; background: #a9d6bd; }
.island-agent-card li.is-running > span { color: #302510; background: #e8cd8b; }
.island-agent-card li strong, .island-agent-card li small { display: block; }
.island-agent-card li strong { font-size: 12px; }
.island-agent-card li small, .island-agent-card > p { color: var(--island-muted); font-size: 10px; line-height: 1.5; }
.island-agent-card > p { margin: 10px 0 0; }
.island-section-title { display: flex; align-items: end; justify-content: space-between; gap: 10px; }
.island-section-title h3 { margin: 2px 0 0; font-size: 15px; }
.island-section-title > span { color: #ecd493; font-size: 11px; }
.island-place-grid { display: grid; gap: 7px; margin-top: 11px; }
.island-place-grid button { min-height: 52px; padding: 10px 11px; border: 1px solid rgba(255,255,255,.09); border-radius: 11px; color: #fff; background: rgba(255,255,255,.055); cursor: pointer; text-align: left; }
.island-place-grid button:hover { background: rgba(185,222,201,.12); }
.island-place-grid strong, .island-place-grid small { display: block; }
.island-place-grid strong { font-size: 12px; }
.island-place-grid small { margin-top: 2px; color: var(--island-muted); font-size: 10px; line-height: 1.4; }
.island-arrival-card { display: grid; gap: 7px; border-color: rgba(185,222,201,.24); }
.island-arrival-card small { color: #b9dec9; }
.island-arrival-card strong { font-size: 13px; line-height: 1.6; }
.island-mobile-controls { display: none; grid-template-columns: repeat(5, 52px); justify-content: center; gap: 7px; margin-top: 10px; }
.island-mobile-controls button { min-width: 52px; min-height: 48px; border: 1px solid rgba(255,255,255,.12); border-radius: 12px; color: #fff; background: rgba(255,255,255,.08); font-size: 18px; font-weight: 800; touch-action: none; }
.island-mobile-controls .is-interact { color: #18241e; background: #b9dec9; font-size: 12px; }
.island-workspace button:focus-visible, .island-game-surface:focus-visible { outline: 3px solid #f1d48c; outline-offset: 3px; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
@keyframes island-spin { to { transform: rotate(360deg); } }

@media (max-width: 900px) {
  .island-workspace { inset: 0; border: 0; border-radius: 0; }
  .island-layout { grid-template-columns: 1fr; overflow-y: auto; }
  .island-stage-shell { min-height: auto; padding: 10px 10px 4px; }
  .island-side-panel { overflow: visible; padding: 10px 10px calc(18px + env(safe-area-inset-bottom)); border-left: 0; }
  .island-agent-card { order: 2; }
  .island-place-card { order: 1; }
  .island-arrival-card { order: 0; }
  .island-mobile-controls { display: grid; }
  .island-instructions { font-size: 11px; }
}
@media (max-width: 560px) {
  .island-header { min-height: 64px; padding: 8px 10px 8px 14px; }
  .island-header h2 { max-width: 245px; font-size: 15px; }
  .island-header p { font-size: 9px; }
  .island-header-actions { align-items: flex-end; }
  .island-games-entry { max-width: 110px; min-height: 38px; padding: 5px 8px; font-size: 10px; line-height: 1.3; }
  .island-close { width: 48px; height: 48px; }
  .island-mobile-controls { grid-template-columns: repeat(5, minmax(48px, 1fr)); width: 100%; }
}
@media (prefers-reduced-motion: reduce) {
  .island-loading span { animation: none; }
  .island-workspace * { scroll-behavior: auto !important; }
}
</style>
