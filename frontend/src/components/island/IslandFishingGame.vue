<template>
  <section class="fishing-game" aria-labelledby="island-fishing-title" @keydown="handleKeydown" @keyup="handleKeyup">
    <header class="activity-copy">
      <div>
        <small>月光钓鱼湾 · 技巧垂钓</small>
        <h3 id="island-fishing-title">控落点、抢提竿、稳住鱼线</h3>
        <p>先锁定远投落点，看到咬钩涟漪后及时提竿；收线时按住让浮标跟住金色鱼影，线太紧就松开。</p>
      </div>
      <dl>
        <div><dt>遇见鱼类</dt><dd>{{ discoveredCount }}/6</dd></div>
        <div><dt>本岛相遇</dt><dd>{{ fishing.catches }}</dd></div>
        <div><dt>最佳落点</dt><dd>{{ fishing.bestPrecision || 0 }}%</dd></div>
      </dl>
    </header>

    <div class="fishing-stage-shell">
      <div ref="gameHost" class="fishing-stage" aria-hidden="true"></div>
      <div v-if="loading" class="fishing-loading" role="status">正在准备水面与鱼线</div>
    </div>

    <div class="fishing-tools">
      <button
        ref="actionButton"
        type="button"
        :class="state === 'hooked' ? 'reel-button' : 'cast-button'"
        :aria-disabled="state === 'waiting' ? 'true' : undefined"
        @click="handleAction"
        @pointerdown="startReeling"
        @pointerup="stopReeling"
        @pointercancel="stopReeling"
        @lostpointercapture="stopReeling"
      >{{ actionLabel }}</button>
      <div v-if="state === 'hooked'" class="meter-copy" aria-label="钓鱼进度">
        <span>收线 {{ Math.round(progress * 100) }}%</span>
        <span :class="{ danger: tension > .84 }">张力 {{ Math.round(tension * 100) }}%</span>
      </div>
      <p role="status" aria-live="polite">{{ message }}</p>
    </div>

    <div class="fish-book" aria-label="鱼类图鉴">
      <article v-for="fish in FISH_TYPES" :key="fish.id" :class="{ discovered: fishing.fishBook[fish.id] }">
        <span aria-hidden="true">{{ fishing.fishBook[fish.id] ? '鱼' : '？' }}</span>
        <div><strong>{{ fishing.fishBook[fish.id] ? fish.label : '尚未遇见' }}</strong><small>{{ fish.rarity }} · {{ fishing.fishBook[fish.id] || 0 }} 次</small></div>
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { FISH_TYPES } from '../../game/island/islandActivityState.js'

const props = defineProps({ fishing: { type: Object, required: true } })
const emit = defineEmits(['update:fishing', 'played'])
const gameHost = ref(null)
const actionButton = ref(null)
const loading = ref(true)
const state = ref('idle')
const message = ref('准备好时再抛竿。这里没有连胜和失败惩罚。')
const progress = ref(0)
const tension = ref(0.3)
const discoveredCount = computed(() => FISH_TYPES.filter(fish => props.fishing.fishBook[fish.id]).length)
const actionLabel = computed(() => ({ idle: '开始抛竿', casting: '锁定落点', waiting: '等待咬钩', bite: '现在提竿', hooked: '按住收线', result: '再抛一竿' }[state.value] || '开始抛竿'))
let controller = null
let cancelled = false

async function startGame() {
  try {
    const { createFishingGame } = await import('../../game/island/createFishingGame.js')
    if (cancelled || !gameHost.value) return
    const created = await createFishingGame({
      parent: gameHost.value,
      reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
      onEvent: handleGameEvent,
    })
    if (cancelled || !gameHost.value) {
      created?.destroy()
      return
    }
    controller = created
  } catch {
    loading.value = false
    message.value = '钓鱼场景暂时没有准备好，请关闭后重试。'
  }
}

function handleGameEvent(event) {
  if (cancelled) return
  if (event.type === 'ready') loading.value = false
  if (event.type === 'state') {
    state.value = event.state
    message.value = event.message
    if (event.state === 'bite' || event.state === 'hooked') nextTick(() => actionButton.value?.focus({ preventScroll: true }))
    if (event.state === 'result') emit('played', { activity: 'fishing', action: 'round-complete' })
  }
  if (event.type === 'meter') {
    progress.value = event.progress
    tension.value = event.tension
  }
  if (event.type === 'caught') {
    state.value = 'result'
    const fish = FISH_TYPES[event.fishIndex] || FISH_TYPES[0]
    const nextBook = { ...props.fishing.fishBook, [fish.id]: (props.fishing.fishBook[fish.id] || 0) + 1 }
    emit('update:fishing', {
      ...props.fishing,
      catches: props.fishing.catches + 1,
      coins: (props.fishing.coins || 0) + (fish.rarity === '稀有' ? 8 : fish.rarity === '少见' ? 5 : 3),
      bestPrecision: Math.max(props.fishing.bestPrecision || 0, event.precision || 0),
      fishBook: nextBook,
    })
    emit('played', { activity: 'fishing', action: 'catch' })
    message.value = `遇见了${fish.label}，已经收进图鉴。可以继续，也可以到这里结束。`
  }
}

function cast() {
  controller?.command({ type: 'cast' })
}
function handleAction() { if (['idle', 'result', 'casting', 'bite'].includes(state.value)) cast() }
function setReeling(active) { controller?.command({ type: 'reel', active }) }
function startReeling(event) {
  if (state.value !== 'hooked') return
  try { event.currentTarget?.setPointerCapture?.(event.pointerId) } catch { /* window listeners still release */ }
  setReeling(true)
}
function stopReeling() { setReeling(false) }
function handleKeydown(event) {
  if (event.code !== 'Space' || state.value !== 'hooked') return
  event.preventDefault()
  setReeling(true)
}
function handleKeyup(event) {
  if (event.code !== 'Space') return
  event.preventDefault()
  setReeling(false)
}

onMounted(async () => {
  window.addEventListener('pointerup', stopReeling)
  window.addEventListener('pointercancel', stopReeling)
  await nextTick()
  startGame()
})
onBeforeUnmount(() => {
  cancelled = true
  window.removeEventListener('pointerup', stopReeling)
  window.removeEventListener('pointercancel', stopReeling)
  setReeling(false)
  controller?.destroy()
  controller = null
})
</script>

<style scoped>
.fishing-game { display: grid; gap: 14px; color: #fff4df; }
.activity-copy { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; }
.activity-copy small { color: #ffd083; font-size: 12px; font-weight: 800; letter-spacing: .06em; }
.activity-copy h3 { margin: 4px 0 0; font-size: 24px; line-height: 1.2; }
.activity-copy p { max-width: 62ch; margin: 7px 0 0; color: #f5d9bd; font-size: 14px; line-height: 1.55; }
.activity-copy dl { display: flex; gap: 8px; margin: 0; }
.activity-copy dl div { min-width: 88px; padding: 9px 12px; border: 1px solid rgba(255,224,187,.2); border-radius: 12px; background: #743f31; }
.activity-copy dt { color: #f0c7a6; font-size: 11px; }
.activity-copy dd { margin: 3px 0 0; font-size: 18px; font-weight: 800; font-variant-numeric: tabular-nums; }
.fishing-stage-shell { position: relative; overflow: hidden; min-height: 250px; border: 1px solid #c17a59; border-radius: 18px; background: #356f78; }
.fishing-stage { width: 100%; height: min(30vw, 300px); min-height: 250px; }
.fishing-stage :deep(canvas) { display: block; width: 100% !important; height: 100% !important; object-fit: contain; }
.fishing-loading { position: absolute; inset: 0; display: grid; place-items: center; color: #fff4df; background: #4b6d70; }
.fishing-tools { display: grid; grid-template-columns: 150px minmax(0, 220px) 1fr; align-items: center; gap: 12px; }
.fishing-tools button { min-height: 48px; border: 1px solid #e7a570; border-radius: 12px; color: #4a2b22; background: #ffd083; font: inherit; font-weight: 900; cursor: pointer; }
.fishing-tools button:disabled { color: #f5d9bd; background: #70463a; opacity: .7; cursor: wait; }
.fishing-tools button[aria-disabled="true"] { color: #f5d9bd; background: #70463a; opacity: .74; cursor: wait; }
.reel-button { touch-action: none; user-select: none; }
.meter-copy { display: flex; gap: 12px; color: #f5d9bd; font-size: 12px; }
.meter-copy .danger { color: #ffb09d; font-weight: 900; }
.fishing-tools p { margin: 0; color: #f5d9bd; font-size: 13px; line-height: 1.5; }
.fish-book { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.fish-book article { display: flex; align-items: center; gap: 9px; min-height: 54px; padding: 8px 10px; border: 1px solid rgba(255,224,187,.14); border-radius: 12px; color: #e4c3ad; background: #623c35; }
.fish-book article.discovered { color: #fff4df; background: #704a3a; }
.fish-book article > span { display: grid; width: 34px; height: 34px; flex: 0 0 auto; place-items: center; border-radius: 9px; background: rgba(255,255,255,.08); font-weight: 900; }
.fish-book strong, .fish-book small { display: block; }
.fish-book strong { font-size: 12px; }.fish-book small { margin-top: 2px; font-size: 10px; opacity: .75; }
button:focus-visible { outline: 3px solid #fff0a8; outline-offset: 3px; }
@media (max-width: 900px) { .activity-copy dl { display: none; } .fishing-tools { grid-template-columns: 1fr; } }
</style>
