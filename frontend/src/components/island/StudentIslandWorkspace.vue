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
    <header class="island-header" :inert="Boolean(activeActivity || safetyLocked)" :aria-hidden="activeActivity || safetyLocked ? 'true' : undefined">
      <div class="island-brand">
        <small>咕哝心岛</small>
        <h2 id="island-title">今天想在岛上做什么？</h2>
      </div>

      <div class="island-phase-status" role="status" aria-live="polite" aria-label="心岛光景随本地时间自动变化">
        <span>随时间变化</span>
        <strong>{{ activePhase.label }}</strong>
        <small>{{ activePhase.period }}</small>
      </div>

      <div class="island-header-actions">
        <span class="island-version">v{{ version }}</span>
        <button ref="closeButton" type="button" class="island-close" aria-label="关闭心岛，返回首页" @click="$emit('close')">×</button>
      </div>
    </header>

    <main class="island-stage-shell">
      <div
        ref="gameSurface"
        class="island-game-surface"
        :inert="Boolean(activeActivity || safetyLocked)"
        :aria-hidden="activeActivity || safetyLocked ? 'true' : undefined"
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
          <button type="button" class="agent-rail-toggle" :aria-expanded="agentExpanded" aria-controls="island-agent-rail-body" @click.stop="agentExpanded = !agentExpanded">
            <span :class="['agent-state-dot', `is-${agentPhase}`]" aria-hidden="true"></span>
            <span class="agent-rail-copy"><strong>心岛陪伴 Agent</strong><span>{{ agentText }}</span></span>
            <small>{{ agentExpanded ? '收起' : '查看' }}</small>
          </button>
          <p class="sr-only" role="status" aria-live="polite">{{ agentText }}</p>
          <div id="island-agent-rail-body" class="agent-rail-body">
            <p>{{ agentText }}</p>
            <div class="agent-source-row" aria-label="当前 Agent 生成来源">
              <span>{{ agentSourceLabel }}</span>
              <small>{{ agentSourceDetail }}</small>
            </div>
            <p v-if="agentSafetyAction" class="agent-safety-action" role="status">{{ agentSafetyAction }}</p>
            <ol>
              <li v-for="(step, index) in agentSteps" :key="step.title" :class="agentStepClass(index)" :aria-current="index === agentStepIndex ? 'step' : undefined">
                <span aria-hidden="true">{{ index < agentStepIndex ? '✓' : index === agentStepIndex ? '•' : '·' }}</span>
                <div><strong>{{ step.title }}</strong><span class="sr-only">{{ agentStepStatusLabel(index) }}：</span><small>{{ step.detail }}</small></div>
              </li>
            </ol>
            <small class="agent-boundary">Agent 使用你主动选择的标签、主观回看、活动偏好与使用节律来安排功能；不会依据游戏成绩或使用行为判断情绪，也不进行心理诊断。</small>
          </div>
        </aside>

        <section v-if="arrivalCard" class="island-arrival-card" aria-live="polite">
          <button type="button" class="arrival-dismiss" aria-label="关闭到达提示" @click.stop="dismissArrival">×</button>
          <small>已经到达</small>
          <strong>{{ arrivalCard.label }}</strong>
          <p>{{ arrivalCard.hint }}</p>
          <button ref="arrivalPrimary" type="button" class="arrival-primary" @click.stop="openArrivalActivity">{{ arrivalActivityLabel }}</button>
        </section>

        <div v-if="loading" class="island-loading" role="status">
          <span aria-hidden="true"></span>
          <strong>正在铺开心岛 · {{ loadProgress }}%</strong>
          <small>{{ liveStatus }}</small>
        </div>
        <div v-else-if="loadError" class="island-error" role="alert">
          <strong>心岛暂时没有展开</strong>
          <p>聊天记录都还在，可以重新准备心岛或先返回首页。</p>
          <div>
            <button type="button" @click="startGame">重新尝试</button>
            <button type="button" @click="$emit('close')">返回首页</button>
          </div>
        </div>
      </div>

      <section v-if="activeActivity" ref="activityPanel" :class="['island-activity-panel', `is-${activeActivity}`]" :inert="safetyLocked" :aria-hidden="safetyLocked ? 'true' : undefined" :aria-label="`${activeActivityLabel}玩法`">
        <header class="activity-panel-header">
          <button ref="activityBack" type="button" :disabled="safetyLocked" @click="closeActivity">返回岛上</button>
          <nav aria-label="切换心岛玩法">
            <button v-for="activity in activityTabs" :key="activity.id" type="button" :disabled="safetyLocked" :class="{ active: activeActivity === activity.id }" :aria-current="activeActivity === activity.id ? 'page' : undefined" @click="selectActivity(activity.id)">{{ activity.label }}</button>
          </nav>
        </header>
        <div class="activity-panel-body">
          <IslandGardenGame v-if="activeActivity === 'garden'" :garden="activityState.garden" @update:garden="updateGarden" @played="handleActivityPlayed" />
          <IslandFishingGame v-else-if="activeActivity === 'fishing'" :fishing="activityState.fishing" @update:fishing="updateFishing" @played="handleActivityPlayed" />
          <IslandTidalBeach v-else-if="activeActivity === 'beach'" :time-phase="timePhase" @played="handleActivityPlayed" />
          <IslandBreathingRoom v-else-if="activeActivity === 'breathing'" :time-phase="timePhase" @played="handleActivityPlayed" />
          <IslandPetHome v-else-if="activeActivity === 'pet'" :time-phase="timePhase" @played="handleActivityPlayed" />
          <IslandHappinessExchange v-else :happiness="activityState.happiness" :storage-error="storageError" @update:happiness="updateHappiness" @played="handleActivityPlayed" @open-chat="$emit('open-chat')" />

          <fieldset v-if="activityPlayed && !safetyLocked" class="island-reflection">
            <legend>结束这一小轮后，此刻更接近</legend>
            <button v-for="option in reflectionOptions" :key="option.id" type="button" :class="{ active: activityState.reflection === option.id }" @click="finishReflection(option.id)">{{ option.label }}</button>
            <p v-if="reflectionCopy">{{ reflectionCopy }}</p>
          </fieldset>
        </div>
      </section>

      <section v-if="safetyLocked" ref="urgentSupport" class="island-urgent-support" role="alert" tabindex="-1" aria-labelledby="island-urgent-title">
        <small>安全优先 · 普通玩法已暂停</small>
        <strong id="island-urgent-title">现在先和可信任的人待在一起</strong>
        <p>不要独处，远离可能伤害自己的物品，马上联系可信老师或其他安全成年人。如果照顾你的成年人可能让你受伤，请联系其他可信成年人或报警。</p>
        <div>
          <a href="tel:12356">拨打 12356</a>
          <a href="tel:110">危险迫近拨打 110</a>
          <a href="tel:120">需要急救拨打 120</a>
          <button type="button" @click="$emit('open-chat')">打开安全支持</button>
        </div>
      </section>

      <nav v-if="!activeActivity" class="island-place-dock" :inert="safetyLocked" :aria-hidden="safetyLocked ? 'true' : undefined" aria-label="心岛地点快捷导航">
        <button
          v-for="place in places"
          :key="place.id"
          type="button"
          :class="{ 'is-current': currentPlaceLabel === place.label }"
          @click="visitPlace(place)"
        >
          <strong>{{ place.label }}</strong>
          <small>{{ place.id === 'home' ? '咕团' : place.id === 'garden' ? '耕种' : place.id === 'dock' ? '沙滩' : place.id === 'exchange' ? '交换' : '呼吸' }}</small>
        </button>
      </nav>

      <p id="island-instructions" class="island-instructions">
        方向键或 WASD 行走，点击地图或地点可自动前往，Enter 或空格互动；手机可双指捏合缩放地图，放大后单指拖动查看。
      </p>
      <p id="island-live-status" class="sr-only" role="status" aria-live="polite">{{ liveStatus }}</p>

      <div v-if="!loading && !loadError" class="island-zoom-controls" role="group" aria-label="地图缩放" :inert="Boolean(activeActivity || safetyLocked)" :aria-hidden="activeActivity || safetyLocked ? 'true' : undefined">
        <button type="button" aria-label="放大地图" :disabled="mapZoom >= zoomLimits.max - 0.001" @click.stop="zoomMap('in')">＋</button>
        <button type="button" aria-label="缩小地图" :disabled="mapZoom <= zoomLimits.min + 0.001" @click.stop="zoomMap('out')">－</button>
        <span class="island-zoom-level" aria-hidden="true">{{ zoomPercent }}%</span>
        <button type="button" class="is-zoom-reset" aria-label="复位地图缩放" :disabled="mapZoom <= zoomLimits.min + 0.001" @click.stop="zoomMap('reset')">复位</button>
      </div>

      <div class="island-mobile-controls" :inert="Boolean(activeActivity || safetyLocked)" :aria-hidden="activeActivity || safetyLocked ? 'true' : undefined" aria-label="心岛移动控制">
        <button type="button" aria-label="向左上移动" @pointerdown="startPointerMove($event, -1, -1)" @pointerup="stopMoving" @pointercancel="stopMoving" @lostpointercapture="stopMoving">↖</button>
        <button type="button" aria-label="向上移动" @pointerdown="startPointerMove($event, 0, -1)" @pointerup="stopMoving" @pointercancel="stopMoving" @lostpointercapture="stopMoving">↑</button>
        <button type="button" aria-label="向右上移动" @pointerdown="startPointerMove($event, 1, -1)" @pointerup="stopMoving" @pointercancel="stopMoving" @lostpointercapture="stopMoving">↗</button>
        <button type="button" aria-label="向左移动" @pointerdown="startPointerMove($event, -1, 0)" @pointerup="stopMoving" @pointercancel="stopMoving" @lostpointercapture="stopMoving">←</button>
        <button type="button" class="is-interact" @click="interact">互动</button>
        <button type="button" aria-label="向右移动" @pointerdown="startPointerMove($event, 1, 0)" @pointerup="stopMoving" @pointercancel="stopMoving" @lostpointercapture="stopMoving">→</button>
        <button type="button" aria-label="向左下移动" @pointerdown="startPointerMove($event, -1, 1)" @pointerup="stopMoving" @pointercancel="stopMoving" @lostpointercapture="stopMoving">↙</button>
        <button type="button" aria-label="向下移动" @pointerdown="startPointerMove($event, 0, 1)" @pointerup="stopMoving" @pointercancel="stopMoving" @lostpointercapture="stopMoving">↓</button>
        <button type="button" aria-label="向右下移动" @pointerdown="startPointerMove($event, 1, 1)" @pointerup="stopMoving" @pointercancel="stopMoving" @lostpointercapture="stopMoving">↘</button>
      </div>
    </main>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { recordActivityReflection } from '../../api/mood.js'
import { runIslandAgent, getPendingCommands, ackCommands, logIslandBehavior } from '../../api/island.js'
import IslandTidalBeach from './IslandTidalBeach.vue'
import IslandBreathingRoom from './IslandBreathingRoom.vue'
import IslandPetHome from './IslandPetHome.vue'
import IslandGardenGame from './IslandGardenGame.vue'
import IslandFishingGame from './IslandFishingGame.vue'
import IslandHappinessExchange from './IslandHappinessExchange.vue'
import { createIslandBridge } from '../../game/island/islandBridge.js'
import { loadActivityState, saveActivityState } from '../../game/island/islandActivityState.js'
import { ISLAND_PHASES, ISLAND_PLACES, loadIslandState, millisecondsUntilNextIslandPhase, resolveIslandPhase, saveIslandState } from '../../game/island/islandState.js'
import { ISLAND_ZOOM } from '../../game/island/islandZoom.js'

const props = defineProps({ storageScope: { type: [String, Number], required: true } })
const emit = defineEmits(['close', 'activity', 'open-chat', 'safety'])
const version = import.meta.env.VITE_APP_VERSION || __APP_PACKAGE_VERSION__ || 'local'
const dialog = ref(null)
const closeButton = ref(null)
const arrivalPrimary = ref(null)
const activityBack = ref(null)
const activityPanel = ref(null)
const gameHost = ref(null)
const gameSurface = ref(null)
const urgentSupport = ref(null)
const loading = ref(true)
const loadProgress = ref(5)
const loadError = ref(false)
const agentPhase = ref('ready')
const agentText = ref('正在听懂你想去的方向')
const agentSource = ref('deterministic')
const agentSafetyAction = ref('')
const viewportQuery = typeof window !== 'undefined' ? window.matchMedia('(max-width: 900px)') : null
const compactViewport = !!viewportQuery?.matches
const mapZoom = ref(1)
const zoomLimits = ISLAND_ZOOM
const zoomPercent = computed(() => Math.round(mapZoom.value * 100))
const agentExpanded = ref(false)
const liveStatus = ref('心岛地图正在准备')
const nearby = ref('星灯小径')
const targetPlaceLabel = ref('')
const arrivalCard = ref(null)
const activeActivity = ref('')
const activityPlayed = ref(false)
const safetyLocked = ref(false)
const storageError = ref(false)
const places = ISLAND_PLACES
const phases = ISLAND_PHASES
let bridge = createIslandBridge()
const currentState = ref(loadIslandState(props.storageScope))
const activityState = ref(loadActivityState(props.storageScope))
const timePhase = ref(currentState.value.timePhase)
const activePhase = computed(() => phases.find(phase => phase.id === timePhase.value) || phases[0])
const currentPlaceLabel = computed(() => nearby.value || '星灯小径')
const arrivalActivityLabel = computed(() => ({
  home: '去找咕团',
  garden: '开始照料田园',
  dock: '去潮汐沙滩走走',
  exchange: '交换幸福小事',
  rest: '打开星灯呼吸',
})[arrivalCard.value?.place] || '打开这里的活动')
const activityTabs = Object.freeze([
  { id: 'garden', label: '云顶暖房' },
  { id: 'fishing', label: '月光钓鱼湾' },
  { id: 'beach', label: '潮汐沙滩' },
  { id: 'breathing', label: '星灯呼吸' },
  { id: 'pet', label: '咕团家园' },
  { id: 'exchange', label: '幸福交换树' },
])
const reflectionOptions = Object.freeze([
  { id: 'lighter', label: '轻松一点' },
  { id: 'same', label: '差不多' },
  { id: 'energized', label: '更有精神' },
  { id: 'more_tense', label: '反而更紧绷' },
])
const activeActivityLabel = computed(() => activityTabs.find(item => item.id === activeActivity.value)?.label || '')
const agentSourceLabel = computed(() => ({
  xunfei_constrained: '讯飞受约束生成',
  safety_override: '安全规则强制覆盖',
  degraded: '规则安全降级',
  deterministic: '本地确定性规则',
})[agentSource.value] || '本地确定性规则')
const agentSourceDetail = computed(() => ({
  xunfei_constrained: '无需单独申请，受约束讯飞协作已执行；安全规则仍具有最终裁决权',
  safety_override: '风险行动由本地安全规则确定，模型不能覆盖',
  degraded: '外部协作不可用或输出未通过校验，已切回审核模板',
  deterministic: '模型未参与本次生成，全部在本地整理',
})[agentSource.value] || '当前来源尚未确认')
const agentStepIndex = computed(() => safetyLocked.value ? 1 : activityState.value.reflection ? 4 : activityPlayed.value ? 3 : activeActivity.value ? 2 : agentPhase.value === 'moving' ? 1 : 0)
const agentSteps = computed(() => [
  { title: '理解你的选择', detail: activeActivity.value ? `你选择了${activeActivityLabel.value}` : '等待你主动选择目的地' },
  { title: '确认安全边界', detail: safetyLocked.value ? '需要立即协助，正在保持真人安全支持' : '不诊断，不用成绩推断情绪' },
  { title: '组织合适玩法', detail: safetyLocked.value ? '普通玩法已暂停' : activeActivity.value ? `正在运行${activeActivityLabel.value}完整玩法` : agentPhase.value === 'moving' ? `正在前往${targetPlaceLabel.value || '地图上的位置'}` : '到达后再加载玩法' },
  { title: '观察过程反馈', detail: activityPlayed.value ? '仅记录操作进度，不分析输赢' : '等待一次真实互动' },
  { title: '整理下一步', detail: activityState.value.reflection ? '已根据你的主观反馈生成建议' : '由你决定是否回看感受' },
])
const reflectionCopy = computed(() => ({
  lighter: '把这点轻松留住就好。可以回到岛上走走，也可以直接结束。',
  same: '没有变化也很正常。可以换一种玩法，或回首页继续倾诉。',
  energized: '把这点精神留给一件你愿意做的小事，不需要马上安排很多任务。',
  more_tense: '先停下玩法，回首页坐一会或继续倾诉；这份主动反馈会出现在你的情绪回顾里。',
})[activityState.value.reflection] || '')
let game = null
let cancelled = false
let disposers = []
let gameGeneration = 0
let startingPromise = null
let phaseTimer = null
let commandPollTimer = null
let gameStartTimeout = null
let agentTriggered = false
let movementSource = 'none'
let arrivalCooldown = false
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
      if (gameStartTimeout) window.clearTimeout(gameStartTimeout)
      gameStartTimeout = null
      loadProgress.value = 100
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
    activeBridge.on('loading', event => {
      if (!isCurrentGeneration(generation, scope)) return
      loadProgress.value = Math.max(loadProgress.value, Number(event.progress) || 5)
      liveStatus.value = event.text || '正在准备心岛资源。'
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
    activeBridge.on('zoom', event => {
      if (!isCurrentGeneration(generation, scope)) return
      const zoom = Number(event?.zoom)
      if (Number.isFinite(zoom)) mapZoom.value = zoom
    }),
    activeBridge.on('arrive', event => {
      if (!isCurrentGeneration(generation, scope)) return
      nearby.value = event.label
      targetPlaceLabel.value = event.label
      persistState({ position: event.position, lastPlace: event.place })
      // 靠近即自动转场进入，无需点击确认
      if (!activeActivity.value && !safetyLocked.value && !arrivalCooldown) {
        arrivalCooldown = true
        setTimeout(() => { arrivalCooldown = false }, 3000)
        const placeToActivity = {
          garden: 'garden', dock: 'beach', exchange: 'exchange',
          rest: 'breathing', home: 'pet',
        }
        const activity = placeToActivity[event.place]
        if (activity) {
          selectActivity(activity)
        } else {
          emit('activity', event.place)
        }
      }
    }),
  ]
}

async function startGame() {
  if (game || startingPromise || !gameHost.value) return startingPromise
  const generation = gameGeneration
  const scope = normalizeScope(props.storageScope)
  const activeBridge = bridge
  loading.value = true
  loadProgress.value = 5
  loadError.value = false
  liveStatus.value = '正在加载心岛运行组件。'
  if (gameStartTimeout) window.clearTimeout(gameStartTimeout)
  gameStartTimeout = window.setTimeout(() => {
    if (!isCurrentGeneration(generation, scope) || !loading.value) return
    loading.value = false
    loadError.value = true
    liveStatus.value = '网络加载时间过长，可以重试；已经下载的资源会继续保留在浏览器缓存中。'
    game?.destroy(true)
    game = null
  }, 15_000)
  bindBridge(activeBridge, generation, scope)
  const promise = (async () => {
    try {
      const { createIslandGame } = await import('../../game/island/createIslandGame.js')
      loadProgress.value = Math.max(loadProgress.value, 18)
      if (!isCurrentGeneration(generation, scope) || !gameHost.value || !loading.value) return
      const createdGame = await createIslandGame({
        parent: gameHost.value,
        bridge: activeBridge,
        initialState: currentState.value,
        reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
      })
      if (!isCurrentGeneration(generation, scope) || activeBridge !== bridge || !loading.value) {
        createdGame?.destroy(true)
        return
      }
      game = createdGame
    } catch (error) {
      if (!isCurrentGeneration(generation, scope)) return
      console.error('Heart Island failed to start', error)
      if (gameStartTimeout) window.clearTimeout(gameStartTimeout)
      gameStartTimeout = null
      loading.value = false
      loadError.value = true
      liveStatus.value = '心岛加载失败，可以重试或先返回首页。'
    }
  })()
  startingPromise = promise
  try {
    await promise
  } finally {
    if (startingPromise === promise) startingPromise = null
  }
}

function syncPhaseWithClock(announce = false) {
  const phase = resolveIslandPhase()
  if (timePhase.value === phase) return
  timePhase.value = phase
  currentState.value = { ...currentState.value, timePhase: phase }
  bridge.emit('command', { type: 'phase', phase })
  if (announce) liveStatus.value = `心岛已随本地时间进入${activePhase.value.label}，地图与进度保持不变。`
}

function schedulePhaseSync() {
  if (phaseTimer) window.clearTimeout(phaseTimer)
  phaseTimer = window.setTimeout(() => {
    syncPhaseWithClock(true)
    schedulePhaseSync()
  }, millisecondsUntilNextIslandPhase() + 1_000)
}

function handleVisibilityChange() {
  if (document.visibilityState !== 'visible') return
  syncPhaseWithClock(true)
  schedulePhaseSync()
}

function handleViewportChange(event) {
  if (event.matches) agentExpanded.value = false
}

// ── 心岛守护者 Agent ──
async function triggerIslandAgent(trigger = 'login') {
  if (agentTriggered) return
  agentTriggered = true
  try {
    const res = await runIslandAgent(trigger)
    const data = res.data
    if (data?.crisis) {
      safetyLocked.value = true
      agentPhase.value = 'urgent'
      agentText.value = data.message || '检测到需要立即关注的信号'
      agentSource.value = 'safety_override'
      emit('safety', { source: 'island_agent' })
      nextTick(() => urgentSupport.value?.focus({ preventScroll: true }))
      return
    }
    const supportAction = data?.plan?.data?.plan?.support_action || ''
    agentSafetyAction.value = supportAction
    if (data?.safety_status === 'professional') {
      agentPhase.value = 'perceived'
      agentText.value = supportAction || '今天请联系一位可信成年人，并请对方协助连接专业支持。'
      agentSource.value = 'safety_override'
      return
    }
    if (data?.safety_status === 'watch') {
      agentPhase.value = 'perceived'
      agentText.value = data?.pet_message || '可以继续低负担活动，同时留意最近的状态变化。'
      agentSource.value = 'safety_override'
      pollCommands()
      return
    }
    if (data?.pet_message) {
      agentText.value = data.pet_message
    }
    if (data?.perception?.summary) {
      agentPhase.value = 'perceived'
    }
    agentSource.value = data?.degraded ? 'degraded' : data?.model_used === 'xunfei-constrained' ? 'xunfei_constrained' : 'deterministic'
    // 立即处理一次指令
    pollCommands()
  } catch {
    agentSource.value = 'degraded'
    agentText.value = '协作服务暂时不可用，心岛玩法仍可继续；没有伪造分析结果。'
  }
}

async function pollCommands() {
  try {
    const res = await getPendingCommands()
    const commands = res.data?.commands || []
    if (commands.length === 0) return
    for (const cmd of commands) {
      applyIslandCommand(cmd)
    }
    // 确认已接收
    const ids = commands.map(c => c.id)
    if (ids.length) ackCommands(ids).catch(() => {})
  } catch {
    // 静默失败
  }
}

function applyIslandCommand(cmd) {
  if (!cmd?.type) return
  switch (cmd.type) {
    case 'set_phase':
      // 昼夜始终由本地时间决定；忽略历史 Agent 指令，避免心理状态改变环境时钟。
      break
    case 'pet_action':
      // 咕团行为通过桥接通知Phaser场景
      bridge.emit('command', { type: 'pet_action', action: cmd.payload?.action, message: cmd.payload?.message })
      if (cmd.payload?.message) {
        agentText.value = cmd.payload.message
      }
      break
    case 'toast':
      if (cmd.payload?.message) {
        liveStatus.value = cmd.payload.message
      }
      break
    case 'recommend':
      if (cmd.payload?.message) {
        agentText.value = cmd.payload.message
      }
      break
    default:
      break
  }
}

function startCommandPolling() {
  if (commandPollTimer) return
  commandPollTimer = setInterval(pollCommands, 8000)
}

function agentStepClass(index) {
  if (index < agentStepIndex.value) return 'is-complete'
  if (index === agentStepIndex.value) return 'is-running'
  return 'is-waiting'
}
function agentStepStatusLabel(index) {
  return index < agentStepIndex.value ? '已完成' : index === agentStepIndex.value ? '进行中' : '等待'
}

function focusGameSurface() { gameSurface.value?.focus({ preventScroll: true }) }
function startMoving(x, y, source = 'keyboard') {
  if (safetyLocked.value || activeActivity.value) return
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
function interact() {
  if (safetyLocked.value || activeActivity.value) return
  bridge.emit('command', { type: 'interact' })
}
function zoomMap(action) {
  if (safetyLocked.value || activeActivity.value) return
  bridge.emit('command', { type: 'zoom', action })
}
function openArrivalActivity() {
  if (!arrivalCard.value?.place) return
  const place = arrivalCard.value.place
  const placeToActivity = {
    garden: 'garden', dock: 'beach', exchange: 'exchange',
    rest: 'breathing', home: 'pet',
  }
  if (placeToActivity[place]) {
    selectActivity(placeToActivity[place])
    arrivalCard.value = null
    return
  }
  emit('activity', place)
}
function persistActivityState() {
  storageError.value = !saveActivityState(props.storageScope, activityState.value)
}
function selectActivity(activity) {
  if (safetyLocked.value) return
  if (!activityTabs.some(item => item.id === activity)) return
  stopMoving()
  activeActivity.value = activity
  activityPlayed.value = false
  activityState.value = { ...activityState.value, reflection: '' }
  persistActivityState()
  agentPhase.value = 'arrived'
  agentText.value = `已完成安全边界检查，正在运行${activityTabs.find(item => item.id === activity)?.label}`
  liveStatus.value = `已打开${activityTabs.find(item => item.id === activity)?.label}。`
  nextTick(() => activityBack.value?.focus({ preventScroll: true }))
}
function closeActivity() {
  if (safetyLocked.value) {
    nextTick(() => activityPanel.value?.querySelector('.happiness-safety')?.focus({ preventScroll: true }))
    return
  }
  activeActivity.value = ''
  activityPlayed.value = false
  arrivalCard.value = null
  arrivalCooldown = true
  setTimeout(() => { arrivalCooldown = false }, 3000)
  liveStatus.value = '已回到心岛地图。'
  nextTick(focusGameSurface)
}
function updateGarden(garden) {
  activityState.value = { ...activityState.value, garden }
  persistActivityState()
}
function updateFishing(fishing) {
  activityState.value = { ...activityState.value, fishing }
  persistActivityState()
}
function updateHappiness(happiness) {
  activityState.value = { ...activityState.value, happiness }
  persistActivityState()
}
function handleActivityPlayed(event) {
  if (event?.action === 'safety') {
    safetyLocked.value = true
    activityPlayed.value = false
    agentPhase.value = 'urgent'
    agentText.value = '普通玩法已暂停，当前优先连接真人安全支持'
    liveStatus.value = '检测到需要立即协助的安全信号，普通玩法和回看已经暂停。'
    emit('safety', { source: event?.source || 'happiness_exchange' })
    nextTick(() => urgentSupport.value?.focus({ preventScroll: true }))
    return
  }
  activityPlayed.value = true
  agentText.value = '正在记录本轮操作进度，等待你主动回看'
}
async function finishReflection(id) {
  if (!reflectionOptions.some(option => option.id === id)) return
  activityState.value = { ...activityState.value, reflection: id }
  persistActivityState()
  agentText.value = '已根据你的主观反馈整理下一步'
  liveStatus.value = reflectionCopy.value
  try {
    await recordActivityReflection(activeActivity.value === 'exchange' ? 'happiness' : activeActivity.value, id)
    liveStatus.value = `${reflectionCopy.value} 已加入你的情绪回顾。`
  } catch {
    liveStatus.value = `${reflectionCopy.value} 本次反馈暂未同步，玩法存档不受影响。`
  }
}
function dismissArrival() {
  arrivalCard.value = null
  nextTick(focusGameSurface)
}
function visitPlace(place) {
  if (safetyLocked.value || activeActivity.value) return
  // Explicit navigation should not be swallowed by the automatic re-entry cooldown.
  arrivalCooldown = false
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
    if (activeActivity.value) {
      if (safetyLocked.value) {
        nextTick(() => activityPanel.value?.querySelector('.happiness-safety')?.focus({ preventScroll: true }))
        return
      }
      closeActivity()
      return
    }
    emit('close')
    return
  }
  if (event.key !== 'Tab') return
  const focusable = [...dialog.value.querySelectorAll('button:not([disabled]), a[href], textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex="0"], [tabindex="-1"]')]
    .filter(element => !element.closest('[inert]') && element.getClientRects().length > 0 && getComputedStyle(element).visibility !== 'hidden')
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
  if (gameStartTimeout) window.clearTimeout(gameStartTimeout)
  gameStartTimeout = null
  stopMoving()
  disposers.forEach(dispose => dispose())
  disposers = []
  game?.destroy(true)
  game = null
  bridge.clear()
  bridge = createIslandBridge()
  arrivalCard.value = null
  activeActivity.value = ''
  activityPlayed.value = false
  safetyLocked.value = false
  nearby.value = '星灯小径'
  targetPlaceLabel.value = ''
  mapZoom.value = 1
  agentPhase.value = 'ready'
  agentText.value = '正在听懂你想去的方向'
  agentSource.value = 'deterministic'
  agentTriggered = false
  currentState.value = loadIslandState(nextScope)
  activityState.value = loadActivityState(nextScope)
  storageError.value = false
  timePhase.value = currentState.value.timePhase
  loading.value = true
  loadProgress.value = 5
  loadError.value = false
  liveStatus.value = '学生身份已切换，正在重新铺开心岛。'
  await nextTick()
  if (!cancelled) startGame()
})

onMounted(async () => {
  window.addEventListener('pointerup', stopPointerMoving)
  window.addEventListener('pointercancel', stopPointerMoving)
  window.addEventListener('blur', stopMoving)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  viewportQuery?.addEventListener?.('change', handleViewportChange)
  await nextTick()
  closeButton.value?.focus({ preventScroll: true })
  startGame()
  schedulePhaseSync()
  // 触发心岛守护者Agent
  triggerIslandAgent('login')
  startCommandPolling()
  // 记录登录行为
  logIslandBehavior('login', null, null, {}).catch(() => {})
})

onBeforeUnmount(() => {
  cancelled = true
  gameGeneration += 1
  startingPromise = null
  stopMoving()
  window.removeEventListener('pointerup', stopPointerMoving)
  window.removeEventListener('pointercancel', stopPointerMoving)
  window.removeEventListener('blur', stopMoving)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  viewportQuery?.removeEventListener?.('change', handleViewportChange)
  if (phaseTimer) window.clearTimeout(phaseTimer)
  phaseTimer = null
  if (commandPollTimer) clearInterval(commandPollTimer)
  commandPollTimer = null
  if (gameStartTimeout) window.clearTimeout(gameStartTimeout)
  gameStartTimeout = null
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
  --island-muted: #d9c9b5;
  --island-accent: #efb96f;
  --island-accent-strong: #d9914f;
  --island-surface: rgba(24, 31, 30, .88);
  --island-surface-soft: rgba(24, 31, 30, .72);
  --island-line: rgba(255, 248, 234, .14);
  position: fixed;
  inset: 0;
  z-index: 410;
  overflow: hidden;
  color: var(--island-ink);
  background: #000;
  font-family: 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
}
.island-header {
  position: absolute;
  top: 0; left: 0; right: 0;
  z-index: 8;
  display: grid;
  grid-template-columns: minmax(240px, 1fr) auto minmax(180px, 1fr);
  align-items: center;
  gap: 16px;
  padding: 10px 14px 10px 20px;
  border-bottom: 0;
  background: linear-gradient(180deg, rgba(0,0,0,.5) 0%, transparent 100%);
  backdrop-filter: blur(6px);
}
.island-brand { min-width: 0; }
.island-brand small, .island-brand h2 { display: block; margin: 0; text-shadow: 0 1px 3px rgba(0,0,0,.6); }
.island-brand small { color: #ffd083; font-size: 10px; font-weight: 800; }
.island-brand h2 { margin-top: 3px; overflow: hidden; font-size: 15px; line-height: 1.35; text-overflow: ellipsis; white-space: nowrap; }
.island-phase-status { display: grid; grid-template-columns: auto auto; align-items: center; gap: 2px 9px; min-width: 144px; padding: 7px 11px; border-radius: 12px; background: rgba(0,0,0,.35); backdrop-filter: blur(10px); }
.island-phase-status > span { grid-row: 1 / 3; color: rgba(255,255,255,.7); font-size: 9px; }
.island-phase-status strong { color: #ffd083; font-size: 12px; }
.island-phase-status small { color: rgba(255,255,255,.6); font-size: 8px; }
.island-header-actions { display: flex; justify-content: flex-end; gap: 8px; }
.island-version { align-self: center; color: rgba(255,255,255,.75); font-size: 10px; font-variant-numeric: tabular-nums; text-shadow: 0 1px 2px rgba(0,0,0,.5); }
.island-close { min-height: 44px; border: 0; border-radius: 11px; color: #fff; background: rgba(0,0,0,.4); backdrop-filter: blur(10px); font: inherit; cursor: pointer; text-shadow: 0 1px 2px rgba(0,0,0,.4); }
.island-close { width: 48px; font-size: 23px; }

.island-stage-shell { position: absolute; inset: 0; min-width: 0; min-height: 0; padding: 0; overflow: hidden; }
.island-game-surface { position: relative; z-index: 1; width: 100%; height: 100%; overflow: hidden; border: 0; border-radius: 0; background: transparent; touch-action: none; }
.island-game-host, .island-game-host :deep(canvas) { width: 100%; height: 100%; image-rendering: pixelated; }
.island-game-host :deep(canvas) { display: block; }
.island-mission-glass {
  position: absolute;
  bottom: 16px;
  left: 16px;
  z-index: 4;
  width: min(310px, calc(100% - 100px));
  padding: 12px 14px;
  border-radius: 14px;
  color: #fff;
  background: rgba(0,0,0,.35);
  border: 0;
  box-shadow: 0 8px 24px rgba(0,0,0,.2);
  backdrop-filter: blur(14px);
  pointer-events: none;
}
.island-mission-glass small, .island-mission-glass strong { display: block; }
.island-mission-glass small { color: #ffd083; font-size: 10px; font-weight: 800; }
.island-mission-glass strong { margin-top: 3px; font-size: 15px; text-shadow: 0 1px 2px rgba(0,0,0,.4); }
.island-mission-glass p { margin: 4px 0 0; color: rgba(255,255,255,.75); font-size: 10px; line-height: 1.45; }

.island-agent-rail { position: absolute; top: 16px; right: 16px; z-index: 15; width: 232px; border: 0; border-radius: 16px; color: #fff; background: rgba(0,0,0,.4); box-shadow: 0 8px 24px rgba(0,0,0,.2); backdrop-filter: blur(14px); }
.agent-rail-toggle { display: grid; grid-template-columns: 9px 1fr auto; align-items: center; gap: 8px; width: 100%; min-height: 46px; padding: 8px 11px; border: 0; border-radius: inherit; color: inherit; background: transparent; text-align: left; cursor: pointer; }
.agent-rail-toggle small { color: var(--island-muted); font-size: 9px; }
.agent-rail-copy { display: grid; min-width: 0; gap: 2px; }
.agent-rail-copy strong, .agent-rail-copy > span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.agent-rail-copy > span { color: var(--island-muted); font-size: 9px; line-height: 1.35; }
.agent-state-dot { width: 8px; height: 8px; border-radius: 3px; background: #ffd083; }
.agent-state-dot.is-arrived { background: #a8c38b; }
.agent-rail-body { display: none; padding: 0 12px 12px; }
.island-agent-rail.is-expanded .agent-rail-body { display: block; }
.agent-rail-body > p { margin: 0 0 8px; color: var(--island-muted); font-size: 10px; line-height: 1.45; }
.agent-source-row { display: none; }
.agent-rail-body ol { display: grid; gap: 2px; margin: 0; padding: 0; list-style: none; }
.agent-rail-body li { display: grid; grid-template-columns: 22px 1fr; gap: 7px; align-items: start; padding: 8px 0; border-top: 1px solid rgba(255,255,255,.08); }
.agent-rail-body li > span { display: grid; width: 21px; height: 21px; place-items: center; border-radius: 7px; color: rgba(255,248,234,.65); background: rgba(255,255,255,.07); font-size: 11px; }
.agent-rail-body li.is-complete > span { color: #3c2b24; background: #a8c38b; }
.agent-rail-body li.is-running > span { color: #4a2b22; background: #ffd083; }
.agent-rail-body strong, .agent-rail-body small { display: block; }
.agent-rail-body strong { font-size: 10px; }
.agent-rail-body li small { margin-top: 2px; color: var(--island-muted); font-size: 9px; line-height: 1.35; }
.agent-boundary { margin-top: 8px; color: rgba(255,248,234,.58); font-size: 9px; line-height: 1.45; }

@media (min-width: 1024px) {
  .agent-source-row { display: grid; gap: 2px; margin: 0 0 10px; padding: 8px 9px; border: 1px solid rgba(255,208,131,.2); border-radius: 10px; background: rgba(255,208,131,.08); }
  .agent-source-row span { color: #ffd998; font-size: 13px; font-weight: 800; }
  .agent-source-row small { color: rgba(255,248,234,.72); font-size: 12px; line-height: 1.5; }
  .agent-safety-action { display: block; margin: 0 0 10px !important; padding: 9px; border-left: 3px solid #ffd083; border-radius: 8px; color: #fff4df !important; background: rgba(130,68,48,.42); font-size: 12px !important; line-height: 1.55 !important; }
}

.island-arrival-card { position: absolute; right: 16px; bottom: 16px; z-index: 12; width: min(300px, calc(100% - 32px)); padding: 14px; border: 1px solid #fff0bd; border-radius: 15px; color: #4a2b22; background: rgba(255, 224, 169, .95); box-shadow: 0 16px 34px rgba(67,30,27,.28); backdrop-filter: blur(18px); }
.island-urgent-support { position: absolute; z-index: 60; top: 50%; left: 50%; display: grid; width: min(620px, calc(100% - 40px)); gap: 10px; padding: 22px; border: 2px solid rgba(255,199,154,.72); border-radius: 14px; color: #fff6e8; background: rgba(70,29,27,.96); box-shadow: 0 12px 20px rgba(0,0,0,.36); transform: translate(-50%, -50%); }
.island-urgent-support small { color: #ffc9b7; font-weight: 800; letter-spacing: .06em; }
.island-urgent-support strong { font-size: 20px; }
.island-urgent-support p { margin: 0; color: rgba(255,246,232,.86); font-size: 13px; line-height: 1.7; }
.island-urgent-support div { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
.island-urgent-support a, .island-urgent-support button { display: grid; min-height: 44px; place-items: center; padding: 8px 10px; border: 0; border-radius: 9px; color: #321914; background: #ffd0c0; font: inherit; font-size: 11px; font-weight: 800; text-align: center; text-decoration: none; cursor: pointer; }
.island-urgent-support button { color: #fff4ef; background: rgba(255,255,255,.14); }
.island-urgent-support a:focus-visible, .island-urgent-support button:focus-visible { outline: 3px solid #fff3c8; outline-offset: 3px; }
.island-arrival-card small, .island-arrival-card strong { display: block; }
.island-arrival-card small { color: #765337; font-size: 9px; font-weight: 800; }
.island-arrival-card strong { margin-top: 3px; font-size: 16px; }
.island-arrival-card p { margin: 5px 26px 10px 0; color: #594759; font-size: 11px; line-height: 1.5; }
.arrival-dismiss { position: absolute; top: 8px; right: 8px; width: 36px; height: 36px; border: 0; border-radius: 9px; color: #594759; background: rgba(89,71,89,.08); font-size: 18px; cursor: pointer; }
.arrival-primary { min-height: 40px; padding: 0 12px; border: 0; border-radius: 9px; color: #fff4df; background: #744336; font: inherit; font-size: 10px; font-weight: 800; cursor: pointer; }

.island-place-dock { position: absolute; bottom: 16px; left: 50%; z-index: 8; display: flex; width: min(680px, calc(100% - 360px)); margin: 0; padding: 5px; border: 0; border-radius: 16px; background: rgba(0,0,0,.35); box-shadow: 0 8px 24px rgba(0,0,0,.2); backdrop-filter: blur(14px); transform: translateX(-50%); }
.island-place-dock button { flex: 1 1 0; min-width: 0; min-height: 48px; padding: 6px 10px; border: 0; border-radius: 12px; color: rgba(255,255,255,.75); background: transparent; font: inherit; cursor: pointer; transition: all .2s; }
.island-place-dock button:hover, .island-place-dock button.is-current { color: #4a2b22; background: #ffd083; }
.island-place-dock strong, .island-place-dock small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.island-place-dock strong { font-size: 11px; }
.island-place-dock small { margin-top: 2px; font-size: 9px; opacity: .76; }
.island-instructions { position: absolute; right: 180px; bottom: 24px; margin: 0; color: rgba(255,255,255,.6); font-size: 9px; text-shadow: 0 1px 2px rgba(0,0,0,.5); z-index: 5; }
.island-zoom-controls { position: absolute; top: 82px; left: 16px; z-index: 8; display: flex; align-items: center; gap: 4px; padding: 4px 6px; border-radius: 12px; background: rgba(0,0,0,.32); backdrop-filter: blur(12px); }
.island-zoom-controls button { width: 36px; min-height: 36px; border: 0; border-radius: 9px; color: #fff; background: rgba(0,0,0,.28); font: inherit; font-size: 17px; font-weight: 800; cursor: pointer; touch-action: manipulation; }
.island-zoom-controls button:hover { background: rgba(0,0,0,.46); }
.island-zoom-controls button:disabled { opacity: .36; cursor: not-allowed; }
.island-zoom-controls .is-zoom-reset { width: auto; padding: 0 8px; font-size: 10px; font-weight: 700; }
.island-zoom-level { min-width: 34px; color: rgba(255,255,255,.8); font-size: 10px; font-variant-numeric: tabular-nums; text-align: center; text-shadow: 0 1px 2px rgba(0,0,0,.5); }
.island-mobile-controls { position: absolute; right: 16px; bottom: 16px; z-index: 8; display: grid; grid-template-columns: repeat(3, 46px); width: 146px; gap: 4px; }
.island-mobile-controls button { min-height: 44px; border: 0; border-radius: 10px; color: #fff; background: rgba(0,0,0,.35); font-size: 16px; font-weight: 800; backdrop-filter: blur(10px); touch-action: none; cursor: pointer; transition: background .2s; }
.island-mobile-controls button:hover { background: rgba(0,0,0,.5); }
.island-mobile-controls .is-interact { color: #2a2130; background: #f1cf86; font-size: 11px; }
.island-mobile-controls .is-interact:hover { background: #ffd083; }
.island-loading, .island-error { position: absolute; inset: 0; z-index: 10; display: grid; place-content: center; justify-items: center; gap: 8px; padding: 24px; color: var(--island-ink); text-align: center; background: rgba(25,31,54,.94); }
.island-loading span { width: 27px; height: 27px; border: 4px solid rgba(255,255,255,.17); border-top-color: #f1cf86; border-radius: 50%; animation: island-spin .9s linear infinite; }
.island-loading small, .island-error p { color: var(--island-muted); font-size: 11px; }
.island-error p { max-width: 420px; margin: 0; line-height: 1.6; }
.island-error div { display: flex; gap: 8px; }
.island-error button { min-height: 44px; padding: 0 13px; border: 0; border-radius: 10px; color: #2a2130; background: #f1cf86; font-weight: 800; cursor: pointer; }
.island-activity-panel {
  position: absolute;
  inset: 0;
  z-index: 30;
  display: grid;
  grid-template-rows: 1fr;
  overflow: hidden;
  border: 0;
  border-radius: 0;
  color: #fff4df;
  background: #1a1a2e;
}
.activity-panel-header {
  position: absolute;
  top: 12px;
  left: 16px;
  right: 16px;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0;
  border-bottom: 0;
  background: transparent;
}
.activity-panel-header > button {
  min-height: 34px;
  padding: 0 16px;
  border: 0;
  border-radius: 18px;
  color: #fff;
  background: rgba(0,0,0,.28);
  backdrop-filter: blur(10px);
  font: inherit; font-size: 12px; font-weight: 600;
  cursor: pointer;
  transition: background .2s;
  text-shadow: 0 1px 2px rgba(0,0,0,.3);
}
.activity-panel-header > button:hover { background: rgba(0,0,0,.45); }
.activity-panel-header > button:disabled { opacity: .5; cursor: not-allowed; }
.activity-panel-header nav {
  display: flex; gap: 4px;
  padding: 3px;
  border-radius: 20px;
  background: rgba(0,0,0,.25);
  backdrop-filter: blur(10px);
}
.activity-panel-header nav button {
  min-height: 30px;
  padding: 0 14px;
  border: 0;
  border-radius: 16px;
  color: rgba(255,255,255,.75);
  background: transparent;
  font: inherit; font-size: 11px; font-weight: 600;
  cursor: pointer;
  transition: all .2s;
  text-shadow: 0 1px 2px rgba(0,0,0,.3);
}
.activity-panel-header nav button:hover { color: #fff; }
.activity-panel-header nav button.active {
  color: #4a2b22;
  background: #ffd083;
  text-shadow: none;
  box-shadow: 0 2px 8px rgba(255,208,131,.3);
}
.activity-panel-body {
  position: relative;
  z-index: 1;
  overflow: hidden;
  padding: 0;
}
.island-reflection { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 18px 0 0; padding: 14px 0 0; border: 0; border-top: 1px solid rgba(255, 226, 185, .16); }
.island-reflection legend { width: 100%; margin-bottom: 2px; color: #f3cdb2; font-size: 12px; font-weight: 800; }
.island-reflection button { min-height: 42px; padding: 0 13px; border: 1px solid #b96e52; border-radius: 11px; color: #fff4df; background: #75463b; font: inherit; font-weight: 800; cursor: pointer; }
.island-reflection button.active { color: #4a2b22; background: #ffd083; }
.island-reflection p { flex: 1 1 300px; margin: 0 0 0 8px; color: #f3cdb2; font-size: 12px; line-height: 1.5; }
.island-workspace button:focus-visible, .island-game-surface:focus-visible { outline: 3px solid #fff0a8; outline-offset: 3px; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
@keyframes island-spin { to { transform: rotate(360deg); } }

@media (min-width: 901px) {
  .island-workspace {
    color: var(--island-ink);
    background: #18201f;
  }
  .island-header {
    top: 16px;
    right: 16px;
    left: 16px;
    grid-template-columns: minmax(260px, 1fr) auto auto;
    gap: 10px;
    padding: 0;
    background: transparent;
    backdrop-filter: none;
  }
  .island-brand {
    width: fit-content;
    max-width: 460px;
    padding: 10px 14px;
    border-radius: 12px;
    background: var(--island-surface-soft);
    box-shadow: 0 4px 8px rgba(8, 13, 12, .2);
    backdrop-filter: blur(16px) saturate(115%);
  }
  .island-brand small { color: var(--island-accent); font-size: 10px; letter-spacing: .02em; }
  .island-brand h2 { margin-top: 2px; font-size: 16px; letter-spacing: -.015em; }
  .island-phase-status {
    min-width: 154px;
    padding: 9px 12px;
    border-radius: 12px;
    background: var(--island-surface-soft);
    box-shadow: 0 4px 8px rgba(8, 13, 12, .18);
    backdrop-filter: blur(16px) saturate(115%);
  }
  .island-phase-status > span { color: var(--island-muted); }
  .island-phase-status strong { color: var(--island-accent); }
  .island-header-actions { align-items: center; }
  .island-version { padding: 5px 8px; border-radius: 7px; color: rgba(255,248,234,.72); background: rgba(19,25,24,.42); }
  .island-close {
    width: 44px;
    min-height: 44px;
    border-radius: 12px;
    background: var(--island-surface);
    box-shadow: 0 4px 8px rgba(8, 13, 12, .2);
    backdrop-filter: blur(16px);
    transition: background .18s ease, transform .18s ease;
  }
  .island-close:hover { background: rgba(64, 56, 48, .94); }
  .island-close:active { transform: scale(.97); }

  .island-mission-glass {
    bottom: 18px;
    left: 18px;
    width: 246px;
    padding: 11px 13px;
    border-radius: 12px;
    background: var(--island-surface-soft);
    box-shadow: 0 4px 8px rgba(8,13,12,.2);
    backdrop-filter: blur(16px) saturate(115%);
  }
  .island-mission-glass small { color: var(--island-accent); }
  .island-mission-glass p { color: var(--island-muted); }

  .island-agent-rail {
    top: 82px;
    right: 16px;
    width: 308px;
    border-radius: 12px;
    background: var(--island-surface);
    box-shadow: 0 6px 8px rgba(8,13,12,.24);
    backdrop-filter: blur(18px) saturate(115%);
    transition: width .18s ease, background .18s ease;
  }
  .island-agent-rail:not(.is-expanded) { background: rgba(24,31,30,.78); }
  .agent-rail-toggle { min-height: 58px; padding: 9px 12px; border-radius: 12px; }
  .agent-rail-toggle:hover { background: rgba(255,255,255,.055); }
  .agent-state-dot { border-radius: 50%; background: var(--island-accent); }
  .agent-rail-copy { gap: 3px; }
  .agent-rail-copy strong { font-size: 12px; }
  .agent-rail-copy > span { color: rgba(255,248,234,.68); font-size: 10px; }
  .agent-rail-toggle small { color: var(--island-accent); font-size: 10px; font-weight: 700; }
  .agent-rail-body { padding: 2px 13px 13px; }
  .agent-rail-body > p { color: rgba(255,248,234,.78); font-size: 11px; }
  .agent-source-row { border: 0; border-radius: 9px; background: rgba(239,185,111,.1); }
  .agent-source-row span { color: #f5c98f; font-size: 11px; }
  .agent-source-row small { font-size: 10px; }
  .agent-rail-body li { grid-template-columns: 24px 1fr; padding: 8px 0; border-top-color: var(--island-line); }
  .agent-rail-body li > span { border-radius: 7px; }
  .agent-rail-body li.is-complete > span { background: #a9cbb1; }
  .agent-rail-body li.is-running > span { background: var(--island-accent); }
  .agent-rail-body strong { font-size: 11px; }
  .agent-rail-body li small, .agent-boundary { color: rgba(255,248,234,.62); font-size: 9px; }
  .agent-safety-action { border-left: 0 !important; border-radius: 9px !important; background: rgba(154,70,53,.45) !important; }

  .island-place-dock {
    bottom: 18px;
    width: min(650px, calc(100% - 600px));
    padding: 5px;
    border-radius: 14px;
    background: var(--island-surface-soft);
    box-shadow: 0 4px 8px rgba(8,13,12,.22);
    backdrop-filter: blur(16px) saturate(115%);
  }
  .island-place-dock button {
    min-height: 50px;
    border-radius: 10px;
    color: rgba(255,248,234,.72);
    transition: color .18s ease, background .18s ease, transform .18s ease;
  }
  .island-place-dock button:hover { color: var(--island-ink); background: rgba(255,255,255,.07); }
  .island-place-dock button:active { transform: scale(.98); }
  .island-place-dock button.is-current { color: #2d241c; background: var(--island-accent); }
  .island-place-dock strong { font-size: 11px; }
  .island-place-dock small { color: inherit; font-size: 9px; opacity: .72; }
  .island-instructions { display: none; }
  .island-mobile-controls { right: 18px; bottom: 18px; grid-template-columns: repeat(3, 42px); width: 134px; gap: 4px; }
  .island-mobile-controls button {
    min-height: 42px;
    border-radius: 9px;
    color: rgba(255,248,234,.84);
    background: var(--island-surface-soft);
    backdrop-filter: blur(14px);
  }
  .island-mobile-controls button:hover { background: rgba(52,61,57,.9); }
  .island-mobile-controls .is-interact { color: #2d241c; background: var(--island-accent); }

  .island-arrival-card {
    right: 18px;
    bottom: 170px;
    width: 286px;
    border: 0;
    border-radius: 12px;
    color: #30251e;
    background: #f4d09c;
    box-shadow: 0 6px 8px rgba(39,26,20,.24);
  }
  .arrival-primary { border-radius: 9px; background: #4c4835; }

  .island-activity-panel { color: var(--island-ink); background: #18201f; }
  .activity-panel-header {
    top: 0;
    right: 0;
    left: 0;
    min-height: 60px;
    padding: 8px 16px;
    background: rgba(20,27,26,.92);
    box-shadow: 0 1px 0 rgba(255,255,255,.08);
    backdrop-filter: blur(18px) saturate(115%);
  }
  .activity-panel-header > button {
    min-height: 40px;
    padding: 0 14px;
    border-radius: 10px;
    color: var(--island-ink);
    background: rgba(255,255,255,.07);
    text-shadow: none;
  }
  .activity-panel-header > button:hover { background: rgba(255,255,255,.12); }
  .activity-panel-header nav { gap: 2px; padding: 3px; border-radius: 11px; background: rgba(255,255,255,.055); backdrop-filter: none; }
  .activity-panel-header nav button { min-height: 34px; padding: 0 12px; border-radius: 8px; color: rgba(255,248,234,.7); text-shadow: none; }
  .activity-panel-header nav button:hover { color: var(--island-ink); background: rgba(255,255,255,.055); }
  .activity-panel-header nav button.active { color: #2d241c; background: var(--island-accent); box-shadow: none; }
  .activity-panel-body { height: 100%; }
  .island-activity-panel.is-fishing .activity-panel-body,
  .island-activity-panel.is-garden .activity-panel-body,
      .island-activity-panel.is-exchange .activity-panel-body {
    box-sizing: border-box;
    overflow-y: auto;
        padding: 86px 42px 150px;
    background:
      radial-gradient(circle at 12% 0%, rgba(217,145,79,.13), transparent 32%),
      linear-gradient(145deg, #22322e, #171f1f 60%);
  }
  .island-reflection {
    position: absolute;
    right: 18px;
    bottom: 18px;
    left: 18px;
    z-index: 8;
    margin: 0;
    padding: 12px;
    border: 0;
    border-radius: 12px;
    background: rgba(24,31,30,.92);
    box-shadow: 0 4px 8px rgba(8,13,12,.22);
    backdrop-filter: blur(16px);
  }
  .island-reflection button { min-height: 38px; border: 0; border-radius: 8px; color: var(--island-ink); background: rgba(255,255,255,.08); }
  .island-reflection button.active { color: #2d241c; background: var(--island-accent); }
}

@media (max-width: 900px) {
  .island-header { grid-template-columns: 1fr auto; gap: 8px; padding: 8px 10px; }
  .island-brand h2 { max-width: 56vw; font-size: 12px; }
  .island-phase-status { grid-column: 1 / -1; grid-row: 2; justify-self: center; }
  .island-header-actions { grid-column: 2; grid-row: 1; }
  .island-mission-glass { top: auto; bottom: 80px; left: 8px; width: min(230px, calc(100% - 64px)); padding: 9px 10px; }
  .island-mission-glass p { display: none; }
  .island-agent-rail { top: 8px; right: 8px; width: 54px; }
  .island-agent-rail.is-expanded { width: min(220px, calc(100% - 16px)); }
  .agent-rail-toggle { grid-template-columns: 8px 1fr; padding: 6px 8px; }
  .agent-rail-toggle small { display: none; }
  .island-agent-rail:not(.is-expanded) .agent-rail-copy > span { display: none; }
  .island-agent-rail:not(.is-expanded) .agent-rail-toggle strong { font-size: 0; }
  .island-agent-rail:not(.is-expanded) .agent-rail-toggle strong::after { content: 'AI'; font-size: 10px; }
  .island-arrival-card { right: 8px; bottom: 80px; }
  .island-urgent-support { width: calc(100% - 24px); padding: 16px; }
  .island-urgent-support div { grid-template-columns: 1fr; }
  .island-place-dock { bottom: 8px; width: calc(100% - 180px); }
  .island-place-dock button { min-height: 42px; }
  .island-instructions { display: none; }
  .island-zoom-controls { top: 86px; left: 8px; }
}
@media (max-width: 520px) {
  .island-phase-status { min-width: 132px; }
  .island-mission-glass strong { font-size: 12px; }
}
@media (prefers-reduced-motion: reduce) {
  .island-loading span { animation: none; }
  .island-workspace * { scroll-behavior: auto !important; transition: none !important; }
}

/* 像素皮肤 3.0 · 心岛工作台 */
.island-workspace {
  --px-line: rgba(255, 248, 234, .24);
  --px-gold: var(--island-accent);
  --px-shadow: rgba(0, 0, 0, .5);
}
.island-header {
  border-bottom: 2px solid var(--px-line);
}
.island-brand small { font-family: var(--px-font); }
.island-brand h2 { font-family: var(--px-font); }
.island-phase-status {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: 3px 3px 0 var(--px-shadow);
}
.island-phase-status strong { font-family: var(--px-font); }
.island-version {
  border: 1px solid var(--px-line);
  border-radius: 3px;
}
.island-close {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: 3px 3px 0 var(--px-shadow);
  transition: transform 160ms steps(2, end), box-shadow 160ms steps(2, end), background 160ms steps(2, end);
}
.island-close:hover {
  border-color: var(--px-gold);
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.island-close:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--px-shadow);
}
.island-mission-glass {
  border: 2px solid var(--px-line);
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.island-mission-glass small { font-family: var(--px-font); }
.island-mission-glass strong { font-family: var(--px-font); }
.island-agent-rail {
  border: 2px solid var(--px-line);
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.agent-state-dot { border-radius: 0; }
.agent-rail-body li > span { border-radius: 4px; }
.island-arrival-card {
  --px-line: rgba(118, 83, 55, .4);
  --px-gold: #744336;
  --px-shadow: rgba(67, 30, 27, .32);
  border: 2px solid #fff0bd;
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.island-arrival-card small { font-family: var(--px-font); }
.island-arrival-card strong { font-family: var(--px-font); }
.arrival-dismiss {
  border: 2px solid var(--px-line);
  border-radius: 4px;
}
.arrival-primary {
  border: 2px solid var(--px-gold);
  border-radius: 4px;
  box-shadow: 3px 3px 0 var(--px-shadow);
  font-family: var(--px-font);
  transition: transform 160ms steps(2, end), box-shadow 160ms steps(2, end);
}
.arrival-primary:hover { transform: translate(-1px, -1px); box-shadow: 4px 4px 0 var(--px-shadow); }
.arrival-primary:active { transform: translate(2px, 2px); box-shadow: 1px 1px 0 var(--px-shadow); }
.island-urgent-support {
  border-width: 2px;
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.island-urgent-support strong { font-family: var(--px-font); }
.island-urgent-support a,
.island-urgent-support button {
  border: 2px solid rgba(255, 243, 200, .3);
  border-radius: 4px;
  box-shadow: 3px 3px 0 rgba(0, 0, 0, .38);
}
.island-place-dock {
  border: 2px solid var(--px-line);
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.island-place-dock button {
  border: 2px solid transparent;
  border-radius: 4px;
}
.island-place-dock button.is-current {
  border-color: var(--px-gold);
  box-shadow: 2px 2px 0 var(--px-shadow);
}
.island-place-dock strong { font-family: var(--px-font); }
.island-zoom-controls {
  border: 2px solid var(--px-line);
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.island-zoom-controls button {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: 2px 2px 0 var(--px-shadow);
  font-family: var(--px-font);
}
.island-zoom-controls .is-zoom-reset { border-color: var(--px-gold); }
.island-zoom-controls button:active:not(:disabled) { transform: translate(1px, 1px); box-shadow: 1px 1px 0 var(--px-shadow); }
.island-mobile-controls button {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: 2px 2px 0 var(--px-shadow);
}
.island-mobile-controls .is-interact { border-color: var(--px-gold); }
.island-activity-panel {
  border: 2px solid var(--px-line);
  border-radius: 6px;
}
.activity-panel-header > button {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: 3px 3px 0 var(--px-shadow);
  font-family: var(--px-font);
}
.activity-panel-header nav {
  border: 2px solid var(--px-line);
  border-radius: 6px;
}
.activity-panel-header nav button {
  border: 2px solid transparent;
  border-radius: 4px;
  font-family: var(--px-font);
}
.activity-panel-header nav button.active {
  border-color: var(--px-gold);
  box-shadow: 2px 2px 0 var(--px-shadow);
}
.activity-panel-body { scrollbar-color: var(--px-gold) rgba(255, 248, 234, .12); }
.island-reflection {
  border: 2px solid var(--px-line);
  border-top-width: 2px;
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.island-reflection legend { font-family: var(--px-font); }
.island-reflection button {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: 2px 2px 0 var(--px-shadow);
  font-family: var(--px-font);
}
.island-reflection button.active {
  border-color: var(--px-gold);
  box-shadow: 2px 2px 0 var(--px-shadow);
}
.island-workspace button:focus-visible,
.island-workspace a:focus-visible,
.island-game-surface:focus-visible {
  outline: 3px dashed var(--px-gold);
  outline-offset: 3px;
}

@media (min-width: 901px) {
  .island-header { border-bottom: 0; }
  .island-brand {
    border: 2px solid var(--px-line);
    border-radius: 6px;
    box-shadow: 4px 4px 0 var(--px-shadow);
  }
  .island-phase-status { border-radius: 4px; }
  .island-close { border-radius: 4px; }
  .island-mission-glass { border-radius: 6px; }
  .island-agent-rail { border-radius: 6px; }
  .island-place-dock { border-radius: 6px; }
  .island-place-dock button { border-radius: 4px; }
  .island-arrival-card { border-radius: 6px; }
  .activity-panel-header { border-bottom: 2px solid var(--px-line); }
  .activity-panel-header > button { border-radius: 4px; }
  .activity-panel-header nav { border-radius: 6px; }
  .activity-panel-header nav button { border-radius: 4px; }
  .island-reflection { border-radius: 6px; }
}

/* 像素皮肤 3.0 · 海面留白：16:9 画布以外的区域也是同一片海 */
.island-workspace {
  background-color: #2c7c9a;
  background-image:
    repeating-linear-gradient(0deg, rgba(255, 255, 255, .04) 0 2px, transparent 2px 9px),
    linear-gradient(180deg, #3f90a6 0%, #2c7c9a 46%, #1d5c76 100%);
}
.island-workspace.is-dusk {
  background-color: #355567;
  background-image:
    repeating-linear-gradient(0deg, rgba(255, 236, 210, .035) 0 2px, transparent 2px 9px),
    linear-gradient(180deg, #4b7180 0%, #355567 46%, #243b4c 100%);
}
.island-workspace.is-night {
  background-color: #101f31;
  background-image:
    radial-gradient(circle at 22px 28px, rgba(255, 236, 170, .8) 0 1px, transparent 2px),
    radial-gradient(circle at 88px 64px, rgba(255, 236, 170, .5) 0 1px, transparent 2px),
    repeating-linear-gradient(0deg, rgba(150, 200, 230, .03) 0 2px, transparent 2px 9px),
    linear-gradient(180deg, #1b3346 0%, #101f31 52%, #081320 100%);
  background-size: 128px 96px, 96px 80px, auto, auto;
}

/* 窄屏：地点导航独占一行，摇杆上移，避免与底栏互相遮挡 */
@media (max-width: 520px) {
  .island-place-dock {
    right: 8px;
    left: 8px;
    bottom: 8px;
    width: auto;
    transform: none;
  }
  .island-place-dock button { padding: 6px 4px; }
  .island-place-dock strong { font-size: 10.5px; }
  .island-mobile-controls { right: 8px; bottom: 70px; }
  .island-mission-glass {
    left: 8px;
    bottom: 70px;
    width: min(212px, calc(100% - 168px));
  }
  .island-arrival-card { right: 8px; bottom: 220px; width: calc(100% - 16px); }
}

/* 窄屏玩法页：标签排成三列两行，内容给顶栏让位 */
@media (max-width: 700px) {
  .activity-panel-header {
    align-items: flex-start;
    gap: 8px;
  }
  .activity-panel-header > button {
    flex: 0 0 auto;
    min-height: 36px;
    padding: 0 10px;
    font-size: 11px;
  }
  .activity-panel-header nav {
    display: grid;
    flex: 1 1 auto;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 2px;
    min-width: 0;
    padding: 3px;
  }
  .activity-panel-header nav button {
    min-height: 32px;
    padding: 0 4px;
    overflow: hidden;
    font-size: 10.5px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .island-activity-panel.is-garden .activity-panel-body,
  .island-activity-panel.is-fishing .activity-panel-body,
  .island-activity-panel.is-exchange .activity-panel-body {
    box-sizing: border-box;
    overflow-y: auto;
    padding: 92px 0 24px;
  }
  .island-activity-panel.is-fishing .activity-panel-body,
  .island-activity-panel.is-exchange .activity-panel-body {
    padding-right: 16px;
    padding-left: 16px;
  }
}
</style>
