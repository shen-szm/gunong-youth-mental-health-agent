<template>
  <section
    ref="dialog"
    :class="['island-workspace', `is-${timePhase}`]"
    data-workspace="leisure"
    role="dialog"
    aria-modal="true"
    aria-labelledby="island-title"
    @click.stop
    @pointerdown.stop
    @keydown="handleDialogKeydown"
  >
    <header class="island-header">
      <div class="island-brand">
        <small>咕哝 · 心岛漫游</small>
        <h2 id="island-title">和咕团沿着光，选一件今晚想做的小事</h2>
      </div>

      <div class="island-phase-switch" aria-label="预览心岛时间阶段">
        <span>岛屿光景</span>
        <div>
          <button
            v-for="phase in phases"
            :key="phase.id"
            type="button"
            :class="{ 'is-active': timePhase === phase.id }"
            :aria-pressed="timePhase === phase.id"
            :title="phase.period"
            @click="setTimePhase(phase.id)"
          >{{ phase.label }}</button>
        </div>
      </div>

      <div class="island-header-actions">
        <button type="button" class="island-classic-entry" @click="$emit('fallback')">经典休闲角</button>
        <button ref="closeButton" type="button" class="island-close" aria-label="关闭心岛，返回房间" @click="$emit('close')">×</button>
      </div>
    </header>

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

        <section class="island-mission-glass" aria-label="当前漫游提示">
          <small>{{ activePhase.shortLabel }}时刻</small>
          <strong>{{ currentPlaceLabel === '星灯小径' ? '和咕团散散步' : `靠近 · ${currentPlaceLabel}` }}</strong>
          <p>你的主动选择会决定下一步，不用解释原因。</p>
        </section>

        <aside :class="['island-agent-rail', { 'is-expanded': agentExpanded }]" aria-label="心岛陪伴 Agent 工作进度">
          <button type="button" class="agent-rail-toggle" :aria-expanded="agentExpanded" @click.stop="agentExpanded = !agentExpanded">
            <span :class="['agent-state-dot', `is-${agentPhase}`]" aria-hidden="true"></span>
            <strong>Agent</strong>
            <small>{{ agentExpanded ? '收起' : '进度' }}</small>
          </button>
          <div class="agent-rail-body">
            <p>{{ agentText }}</p>
            <ol>
              <li v-for="(step, index) in agentSteps" :key="step.title" :class="agentStepClass(index)">
                <span aria-hidden="true">{{ index < agentStepIndex ? '✓' : index === agentStepIndex ? '•' : '·' }}</span>
                <div><strong>{{ step.title }}</strong><small>{{ step.detail }}</small></div>
              </li>
            </ol>
            <small class="agent-boundary">不从游戏成绩推断情绪，不进行心理诊断。</small>
          </div>
        </aside>

        <section v-if="arrivalCard" class="island-arrival-card" aria-live="polite">
          <button type="button" class="arrival-dismiss" aria-label="关闭到达提示" @click.stop="arrivalCard = null">×</button>
          <small>已经到达</small>
          <strong>{{ arrivalCard.label }}</strong>
          <p>{{ arrivalCard.hint }}</p>
          <button type="button" class="arrival-primary" @click.stop="$emit('fallback')">打开对应休闲活动</button>
        </section>

        <div v-if="loading" class="island-loading" role="status">
          <span aria-hidden="true"></span>
          <strong>正在铺开心岛</strong>
          <small>地图、咕团与光景正在准备</small>
        </div>
        <div v-else-if="loadError" class="island-error" role="alert">
          <strong>心岛暂时没有展开</strong>
          <p>房间与原有休闲内容都还在，可以重试或进入经典休闲角。</p>
          <div>
            <button type="button" @click="startGame">重新尝试</button>
            <button type="button" @click="$emit('fallback')">打开经典休闲角</button>
          </div>
        </div>
      </div>

      <nav class="island-place-dock" aria-label="心岛地点快捷导航">
        <button
          v-for="place in places"
          :key="place.id"
          type="button"
          :class="{ 'is-current': currentPlaceLabel === place.label }"
          @click="visitPlace(place)"
        >
          <strong>{{ place.label }}</strong>
          <small>{{ place.id === 'home' ? '陪伴' : place.id === 'garden' ? '耕种' : place.id === 'dock' ? '钓鱼' : place.id === 'exchange' ? '交换' : '放松' }}</small>
        </button>
      </nav>

      <p id="island-instructions" class="island-instructions">
        方向键或 WASD 行走，点击地图或地点可自动前往，Enter 或空格互动。
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
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { createIslandBridge } from '../../game/island/islandBridge.js'
import { ISLAND_PHASES, ISLAND_PLACES, loadIslandState, saveIslandState } from '../../game/island/islandState.js'

const props = defineProps({ storageScope: { type: [String, Number], required: true } })
const emit = defineEmits(['close', 'fallback'])
const dialog = ref(null)
const closeButton = ref(null)
const gameHost = ref(null)
const gameSurface = ref(null)
const loading = ref(true)
const loadError = ref(false)
const agentPhase = ref('ready')
const agentText = ref('正在听懂你想去的方向')
const compactViewport = typeof window !== 'undefined' && window.matchMedia('(max-width: 900px)').matches
const agentExpanded = ref(!compactViewport)
const liveStatus = ref('心岛地图正在准备')
const nearby = ref('星灯小径')
const targetPlaceLabel = ref('')
const arrivalCard = ref(null)
const places = ISLAND_PLACES
const phases = ISLAND_PHASES
let bridge = createIslandBridge()
const currentState = ref(loadIslandState(props.storageScope))
const timePhase = ref(currentState.value.timePhase)
const activePhase = computed(() => phases.find(phase => phase.id === timePhase.value) || phases[0])
const currentPlaceLabel = computed(() => nearby.value || '星灯小径')
const agentStepIndex = computed(() => agentPhase.value === 'arrived' ? 2 : agentPhase.value === 'moving' ? 1 : 0)
const agentSteps = computed(() => [
  { title: '听懂此刻', detail: '以你的主动选择为准' },
  { title: '安排活动', detail: agentPhase.value === 'moving' ? `正在前往${targetPlaceLabel.value || '地图上的位置'}` : '等待你选择目的地' },
  { title: '陪你回看', detail: agentPhase.value === 'arrived' ? '由你决定是否记录感受' : '到达后再轻轻回看' },
])
let game = null
let cancelled = false
let disposers = []
let gameGeneration = 0
let startingPromise = null
let movementSource = 'none'
const pressedDirections = new Set()
const keyboardDirections = {
  ArrowUp: [0, -1], KeyW: [0, -1], ArrowDown: [0, 1], KeyS: [0, 1],
  ArrowLeft: [-1, 0], KeyA: [-1, 0], ArrowRight: [1, 0], KeyD: [1, 0],
}

function normalizeScope(scope) { return String(scope || '') }
function isCurrentGeneration(generation, scope) {
  return !cancelled && generation === gameGeneration && normalizeScope(props.storageScope) === scope
}

function persistState(patch = {}) {
  currentState.value = { ...currentState.value, ...patch, timePhase: timePhase.value }
  saveIslandState(props.storageScope, currentState.value)
}

function bindBridge(activeBridge, generation, scope) {
  disposers.forEach(dispose => dispose())
  disposers = [
    activeBridge.on('ready', event => {
      if (!isCurrentGeneration(generation, scope)) return
      loading.value = false
      const restoredPlace = places.find(place => place.id === event.place)?.label || '星灯小径'
      timePhase.value = event.timePhase || timePhase.value
      liveStatus.value = `心岛已打开。当前是${activePhase.value.label}，你在${restoredPlace}附近。`
      nextTick(() => {
        if (document.activeElement === closeButton.value || document.activeElement === document.body) {
          gameSurface.value?.focus({ preventScroll: true })
        }
      })
    }),
    activeBridge.on('agent', event => {
      if (!isCurrentGeneration(generation, scope)) return
      agentPhase.value = event.phase
      agentText.value = event.text
      if (event.targetLabel) targetPlaceLabel.value = event.targetLabel
    }),
    activeBridge.on('phase', event => {
      if (!isCurrentGeneration(generation, scope)) return
      timePhase.value = event.phase
      persistState()
    }),
    activeBridge.on('position', event => {
      if (!isCurrentGeneration(generation, scope)) return
      nearby.value = event.nearby
      if (event.timePhase) timePhase.value = event.timePhase
      persistState({ position: event.position, lastPlace: event.place })
    }),
    activeBridge.on('status', event => {
      if (!isCurrentGeneration(generation, scope)) return
      liveStatus.value = event.text
    }),
    activeBridge.on('arrive', event => {
      if (!isCurrentGeneration(generation, scope)) return
      nearby.value = event.label
      targetPlaceLabel.value = event.label
      arrivalCard.value = event
      liveStatus.value = `已到达${event.label}。${event.hint}`
      persistState({ position: event.position, lastPlace: event.place })
    }),
  ]
}

async function startGame() {
  if (game || startingPromise || !gameHost.value) return startingPromise
  const generation = gameGeneration
  const scope = normalizeScope(props.storageScope)
  const activeBridge = bridge
  loading.value = true
  loadError.value = false
  bindBridge(activeBridge, generation, scope)
  const promise = (async () => {
    try {
      const { createIslandGame } = await import('../../game/island/createIslandGame.js')
      if (!isCurrentGeneration(generation, scope) || !gameHost.value) return
      const createdGame = await createIslandGame({
        parent: gameHost.value,
        bridge: activeBridge,
        initialState: currentState.value,
        reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
      })
      if (!isCurrentGeneration(generation, scope) || activeBridge !== bridge) {
        createdGame?.destroy(true)
        return
      }
      game = createdGame
    } catch (error) {
      if (!isCurrentGeneration(generation, scope)) return
      console.error('Heart Island failed to start', error)
      loading.value = false
      loadError.value = true
      liveStatus.value = '心岛加载失败，可以重试或进入经典休闲角。'
    }
  })()
  startingPromise = promise
  try {
    await promise
  } finally {
    if (startingPromise === promise) startingPromise = null
  }
}

function setTimePhase(phase) {
  if (timePhase.value === phase) return
  timePhase.value = phase
  persistState()
  bridge.emit('command', { type: 'phase', phase })
}

function agentStepClass(index) {
  if (index < agentStepIndex.value) return 'is-complete'
  if (index === agentStepIndex.value) return 'is-running'
  return 'is-waiting'
}

function focusGameSurface() { gameSurface.value?.focus({ preventScroll: true }) }
function startMoving(x, y, source = 'keyboard') {
  movementSource = source
  targetPlaceLabel.value = ''
  bridge.emit('command', { type: 'move', direction: { x, y } })
}
function startPointerMove(event, x, y) {
  try { event.currentTarget?.setPointerCapture?.(event.pointerId) } catch { /* window listeners still stop movement */ }
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
function stopPointerMoving() { if (movementSource === 'pointer') stopMoving() }
function interact() { bridge.emit('command', { type: 'interact' }) }
function visitPlace(place) {
  arrivalCard.value = null
  targetPlaceLabel.value = place.label
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

watch(() => props.storageScope, async (nextScope, previousScope) => {
  if (String(nextScope || '') === String(previousScope || '')) return
  gameGeneration += 1
  startingPromise = null
  stopMoving()
  disposers.forEach(dispose => dispose())
  disposers = []
  game?.destroy(true)
  game = null
  bridge.clear()
  bridge = createIslandBridge()
  arrivalCard.value = null
  nearby.value = '星灯小径'
  targetPlaceLabel.value = ''
  agentPhase.value = 'ready'
  agentText.value = '正在听懂你想去的方向'
  currentState.value = loadIslandState(nextScope)
  timePhase.value = currentState.value.timePhase
  loading.value = true
  loadError.value = false
  liveStatus.value = '学生身份已切换，正在重新铺开心岛。'
  await nextTick()
  if (!cancelled) startGame()
})

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
  gameGeneration += 1
  startingPromise = null
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
  --island-ink: #fff8ea;
  --island-muted: rgba(255, 248, 234, .72);
  --island-glass: rgba(25, 26, 45, .76);
  position: fixed;
  inset: 0;
  z-index: 410;
  display: grid;
  grid-template-rows: 72px minmax(0, 1fr);
  overflow: hidden;
  color: var(--island-ink);
  background: #172447;
  font-family: 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
}
.island-header {
  z-index: 8;
  display: grid;
  grid-template-columns: minmax(240px, 1fr) auto minmax(180px, 1fr);
  align-items: center;
  gap: 16px;
  padding: 10px 14px 10px 20px;
  background: rgba(22, 24, 42, .9);
  box-shadow: 0 5px 8px rgba(6, 9, 22, .28);
  backdrop-filter: blur(18px) saturate(1.08);
}
.island-brand { min-width: 0; }
.island-brand small, .island-brand h2 { display: block; margin: 0; }
.island-brand small { color: #f1cf86; font-size: 10px; font-weight: 800; }
.island-brand h2 { margin-top: 3px; overflow: hidden; font-size: 15px; line-height: 1.35; text-overflow: ellipsis; white-space: nowrap; }
.island-phase-switch { display: flex; align-items: center; gap: 9px; }
.island-phase-switch > span { color: var(--island-muted); font-size: 10px; }
.island-phase-switch > div { display: flex; padding: 3px; border-radius: 12px; background: rgba(255,255,255,.07); }
.island-phase-switch button { min-width: 58px; min-height: 36px; border: 0; border-radius: 9px; color: rgba(255,248,234,.72); background: transparent; font: inherit; font-size: 11px; font-weight: 700; cursor: pointer; }
.island-phase-switch button:hover { background: rgba(255,255,255,.08); }
.island-phase-switch button.is-active { color: #292034; background: #f1cf86; }
.island-header-actions { display: flex; justify-content: flex-end; gap: 8px; }
.island-classic-entry, .island-close { min-height: 44px; border: 0; border-radius: 11px; color: var(--island-ink); background: rgba(255,255,255,.08); font: inherit; cursor: pointer; }
.island-classic-entry { padding: 0 13px; font-size: 11px; font-weight: 700; }
.island-close { width: 48px; font-size: 23px; }

.island-stage-shell { position: relative; display: grid; align-content: start; align-items: start; justify-items: center; min-width: 0; min-height: 0; padding: 12px 16px 86px; overflow: hidden; }
.island-game-surface { position: relative; width: min(100%, 1420px); aspect-ratio: 16 / 9; overflow: hidden; border-radius: 14px; background: #1a3157; box-shadow: 0 7px 8px rgba(5, 8, 20, .34); touch-action: none; }
.island-game-host, .island-game-host :deep(canvas) { width: 100%; height: 100%; image-rendering: pixelated; }
.island-game-host :deep(canvas) { display: block; }
.island-mission-glass {
  position: absolute;
  top: 16px;
  left: 16px;
  z-index: 4;
  width: min(310px, calc(100% - 100px));
  padding: 12px 14px;
  border-radius: 12px;
  color: var(--island-ink);
  background: var(--island-glass);
  box-shadow: 0 5px 8px rgba(6, 9, 20, .22);
  backdrop-filter: blur(16px) saturate(1.08);
  pointer-events: none;
}
.island-mission-glass small, .island-mission-glass strong { display: block; }
.island-mission-glass small { color: #f1cf86; font-size: 10px; font-weight: 800; }
.island-mission-glass strong { margin-top: 3px; font-size: 15px; }
.island-mission-glass p { margin: 4px 0 0; color: var(--island-muted); font-size: 10px; line-height: 1.45; }

.island-agent-rail { position: absolute; top: 16px; right: 16px; z-index: 5; width: 214px; border-radius: 13px; color: var(--island-ink); background: rgba(25, 26, 45, .82); box-shadow: 0 5px 8px rgba(6,9,22,.25); backdrop-filter: blur(18px) saturate(1.08); }
.agent-rail-toggle { display: grid; grid-template-columns: 9px 1fr auto; align-items: center; gap: 8px; width: 100%; min-height: 46px; padding: 8px 11px; border: 0; border-radius: inherit; color: inherit; background: transparent; text-align: left; cursor: pointer; }
.agent-rail-toggle small { color: var(--island-muted); font-size: 9px; }
.agent-state-dot { width: 8px; height: 8px; border-radius: 3px; background: #f1cf86; }
.agent-state-dot.is-arrived { background: #a8d4c1; }
.agent-rail-body { display: none; padding: 0 12px 12px; }
.island-agent-rail.is-expanded .agent-rail-body { display: block; }
.agent-rail-body > p { margin: 0 0 8px; color: var(--island-muted); font-size: 10px; line-height: 1.45; }
.agent-rail-body ol { display: grid; gap: 2px; margin: 0; padding: 0; list-style: none; }
.agent-rail-body li { display: grid; grid-template-columns: 22px 1fr; gap: 7px; align-items: start; padding: 8px 0; border-top: 1px solid rgba(255,255,255,.08); }
.agent-rail-body li > span { display: grid; width: 21px; height: 21px; place-items: center; border-radius: 7px; color: rgba(255,248,234,.65); background: rgba(255,255,255,.07); font-size: 11px; }
.agent-rail-body li.is-complete > span { color: #17231f; background: #a8d4c1; }
.agent-rail-body li.is-running > span { color: #2d2532; background: #f1cf86; }
.agent-rail-body strong, .agent-rail-body small { display: block; }
.agent-rail-body strong { font-size: 10px; }
.agent-rail-body li small { margin-top: 2px; color: var(--island-muted); font-size: 9px; line-height: 1.35; }
.agent-boundary { margin-top: 8px; color: rgba(255,248,234,.58); font-size: 9px; line-height: 1.45; }

.island-arrival-card { position: absolute; right: 16px; bottom: 16px; z-index: 6; width: min(300px, calc(100% - 32px)); padding: 14px; border-radius: 13px; color: #2b2230; background: rgba(255, 239, 198, .94); box-shadow: 0 7px 8px rgba(6,9,22,.28); backdrop-filter: blur(16px); }
.island-arrival-card small, .island-arrival-card strong { display: block; }
.island-arrival-card small { color: #765337; font-size: 9px; font-weight: 800; }
.island-arrival-card strong { margin-top: 3px; font-size: 16px; }
.island-arrival-card p { margin: 5px 26px 10px 0; color: #594759; font-size: 11px; line-height: 1.5; }
.arrival-dismiss { position: absolute; top: 8px; right: 8px; width: 36px; height: 36px; border: 0; border-radius: 9px; color: #594759; background: rgba(89,71,89,.08); font-size: 18px; cursor: pointer; }
.arrival-primary { min-height: 40px; padding: 0 12px; border: 0; border-radius: 9px; color: #fff8ea; background: #60465e; font: inherit; font-size: 10px; font-weight: 800; cursor: pointer; }

.island-place-dock { position: static; z-index: 8; display: flex; width: min(900px, calc(100% - 32px)); margin-top: 12px; padding: 5px; border-radius: 14px; background: rgba(30, 29, 48, .84); box-shadow: 0 5px 8px rgba(6,9,22,.3); backdrop-filter: blur(18px) saturate(1.08); }
.island-place-dock button { flex: 1 1 0; min-width: 0; min-height: 52px; padding: 6px 10px; border: 0; border-radius: 10px; color: rgba(255,248,234,.72); background: transparent; font: inherit; cursor: pointer; }
.island-place-dock button:hover, .island-place-dock button.is-current { color: #2a2130; background: #f1cf86; }
.island-place-dock strong, .island-place-dock small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.island-place-dock strong { font-size: 11px; }
.island-place-dock small { margin-top: 2px; font-size: 9px; opacity: .76; }
.island-instructions { position: absolute; left: 18px; bottom: 7px; margin: 0; color: rgba(255,248,234,.62); font-size: 9px; }
.island-mobile-controls { display: none; }
.island-loading, .island-error { position: absolute; inset: 0; z-index: 10; display: grid; place-content: center; justify-items: center; gap: 8px; padding: 24px; color: var(--island-ink); text-align: center; background: rgba(25,31,54,.94); }
.island-loading span { width: 27px; height: 27px; border: 4px solid rgba(255,255,255,.17); border-top-color: #f1cf86; border-radius: 50%; animation: island-spin .9s linear infinite; }
.island-loading small, .island-error p { color: var(--island-muted); font-size: 11px; }
.island-error p { max-width: 420px; margin: 0; line-height: 1.6; }
.island-error div { display: flex; gap: 8px; }
.island-error button { min-height: 44px; padding: 0 13px; border: 0; border-radius: 10px; color: #2a2130; background: #f1cf86; font-weight: 800; cursor: pointer; }
.island-workspace button:focus-visible, .island-game-surface:focus-visible { outline: 3px solid #fff0a8; outline-offset: 3px; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
@keyframes island-spin { to { transform: rotate(360deg); } }

@media (max-width: 900px) {
  .island-workspace { grid-template-rows: auto minmax(0, 1fr); }
  .island-header { grid-template-columns: 1fr auto; gap: 8px; padding: 8px 10px; }
  .island-brand h2 { max-width: 56vw; font-size: 12px; }
  .island-phase-switch { grid-column: 1 / -1; grid-row: 2; justify-content: center; }
  .island-header-actions { grid-column: 2; grid-row: 1; }
  .island-classic-entry { display: none; }
  .island-stage-shell { align-content: start; padding: 8px 8px calc(150px + env(safe-area-inset-bottom)); overflow-y: auto; }
  .island-game-surface { width: 100%; min-height: 54vw; border-radius: 12px; }
  .island-mission-glass { top: 8px; left: 8px; width: min(230px, calc(100% - 64px)); padding: 9px 10px; }
  .island-mission-glass p { display: none; }
  .island-agent-rail { top: 8px; right: 8px; width: 54px; }
  .island-agent-rail.is-expanded { width: min(220px, calc(100% - 16px)); }
  .agent-rail-toggle { grid-template-columns: 8px 1fr; padding: 6px 8px; }
  .agent-rail-toggle small { display: none; }
  .island-agent-rail:not(.is-expanded) .agent-rail-toggle strong { font-size: 0; }
  .island-agent-rail:not(.is-expanded) .agent-rail-toggle strong::after { content: 'AI'; font-size: 10px; }
  .island-arrival-card { right: 8px; bottom: 8px; }
  .island-place-dock { position: absolute; right: auto; bottom: calc(78px + env(safe-area-inset-bottom)); left: 8px; width: calc(100% - 16px); margin-top: 0; overflow-x: auto; transform: none; }
  .island-place-dock button { flex: 0 0 118px; }
  .island-instructions { display: none; }
  .island-mobile-controls { position: absolute; right: 8px; bottom: calc(12px + env(safe-area-inset-bottom)); z-index: 8; display: grid; grid-template-columns: repeat(5, minmax(48px, 1fr)); width: calc(100% - 16px); gap: 6px; }
  .island-mobile-controls button { min-height: 52px; border: 0; border-radius: 11px; color: var(--island-ink); background: rgba(30,29,48,.88); font-size: 17px; font-weight: 800; backdrop-filter: blur(16px); touch-action: none; }
  .island-mobile-controls .is-interact { color: #2a2130; background: #f1cf86; font-size: 11px; }
}
@media (max-width: 520px) {
  .island-phase-switch > span { display: none; }
  .island-phase-switch button { min-width: 72px; }
  .island-game-surface { min-height: 62vw; }
  .island-mission-glass strong { font-size: 12px; }
}
@media (prefers-reduced-motion: reduce) {
  .island-loading span { animation: none; }
  .island-workspace * { scroll-behavior: auto !important; transition: none !important; }
}
</style>
