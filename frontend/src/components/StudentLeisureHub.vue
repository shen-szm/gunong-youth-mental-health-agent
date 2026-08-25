<template>
  <section ref="dialog" class="leisure-hub" role="dialog" aria-modal="true" aria-labelledby="leisure-title" @keydown="handleDialogKeydown">
    <header class="leisure-header">
      <div>
        <p>像素休闲角</p>
        <h2 id="leisure-title">小田园、慢钓台，都可以真正玩起来</h2>
        <span>先选一种节奏，再进入完整玩法；没有连续打卡，也不会根据输赢判断情绪。</span>
      </div>
      <div class="leisure-header-actions">
        <button class="island-entry" type="button" @click="$emit('open-island')">进入心岛漫游</button>
        <button class="panel-close leisure-close" type="button" aria-label="关闭休闲角" @click="$emit('close')">×</button>
      </div>
    </header>

    <div class="leisure-layout">
      <main class="leisure-main">
        <fieldset class="need-picker">
          <legend>此刻更想</legend>
          <button
            v-for="need in needs"
            :key="need.id"
            type="button"
            :class="{ active: selectedNeed === need.id }"
            :aria-pressed="selectedNeed === need.id"
            @click="chooseNeed(need.id)"
          >
            <span class="pixel-mark" aria-hidden="true">{{ need.mark }}</span>
            <strong>{{ need.label }}</strong>
            <small>{{ need.hint }}</small>
          </button>
        </fieldset>

        <section class="agent-recommendation" aria-live="polite">
          <span class="recommendation-mark" aria-hidden="true">A</span>
          <div>
            <small>陪伴 Agent 的安排</small>
            <strong>{{ recommendation.title }}</strong>
            <p>{{ recommendation.reason }}</p>
          </div>
          <button type="button" @click="selectGame(recommendation.game)">去试试</button>
        </section>

        <nav class="game-tabs" aria-label="休闲玩法">
          <button type="button" :class="{ active: activeGame === 'garden' }" :aria-current="activeGame === 'garden' ? 'page' : undefined" @click="selectGame('garden')">
            <span aria-hidden="true">田</span> 小田园
          </button>
          <button type="button" :class="{ active: activeGame === 'fishing' }" :aria-current="activeGame === 'fishing' ? 'page' : undefined" @click="selectGame('fishing')">
            <span aria-hidden="true">水</span> 慢钓台
          </button>
          <button type="button" @click="$emit('open-healing')">
            <span aria-hidden="true">息</span> 放松工具
          </button>
        </nav>

        <section v-if="activeGame === 'garden'" class="game-board garden-board" aria-labelledby="garden-title">
          <div class="game-copy">
            <div>
              <p>一步一格</p>
              <h3 id="garden-title">小田园</h3>
              <span>空地种下，幼苗浇水，成熟后收获。随时停下都可以。</span>
            </div>
            <strong>收获 {{ leisureState.harvests }} 次</strong>
          </div>
          <div class="seed-picker" role="group" aria-label="选择要种的作物">
            <span>种子袋</span>
            <button v-for="seed in seedTypes" :key="seed.id" type="button" :class="{ active: selectedSeed === seed.id }" :aria-pressed="selectedSeed === seed.id" @click="selectedSeed = seed.id">
              <i aria-hidden="true">{{ seed.mark }}</i>{{ seed.label }}
            </button>
          </div>
          <div class="garden-grid" role="group" aria-label="六块小田地">
            <button
              v-for="(plot, index) in leisureState.plots"
              :key="index"
              type="button"
              :class="['garden-plot', `stage-${plot.stage}`, `crop-${plot.crop || 'sunflower'}`, { watered: plot.watered }]"
              :aria-label="plotLabel(plot, index)"
              @click="tendPlot(index)"
            >
              <span class="soil-lines" aria-hidden="true"></span>
              <span class="crop" aria-hidden="true"><i></i><b></b></span>
              <small>{{ plotAction(plot) }}</small>
            </button>
          </div>
          <p class="game-status" role="status">{{ gardenMessage }}</p>
        </section>

        <section v-else class="game-board fishing-board" aria-labelledby="fishing-title">
          <div class="game-copy">
            <div>
              <p>等一等，再回应</p>
              <h3 id="fishing-title">慢钓台</h3>
              <span>抛竿后等水面出现方形涟漪，再收线。没有连胜和失败惩罚。</span>
            </div>
            <strong>遇见 {{ leisureState.catches }} 条鱼</strong>
          </div>
          <div class="pixel-pond" :class="`is-${fishingState}`" aria-hidden="true">
            <span class="pond-shore"></span>
            <span class="float-line"></span>
            <span class="float"></span>
            <span class="fish fish-one"></span>
            <span class="fish fish-two"></span>
          </div>
          <div class="fishing-action">
            <button v-if="fishingState === 'idle' || fishingState === 'result'" type="button" @click="castLine">抛竿</button>
            <button v-else-if="fishingState === 'waiting'" type="button" disabled>安静等一会</button>
            <button v-else type="button" class="is-biting" @click="reelLine">现在收线</button>
            <p class="game-status" role="status" aria-live="polite">{{ fishingMessage }}</p>
          </div>
          <div class="fish-book" aria-label="鱼类图鉴">
            <span>鱼类图鉴</span>
            <div v-for="fish in fishTypes" :key="fish.id"><i aria-hidden="true">{{ fish.mark }}</i><strong>{{ fish.label }}</strong><small>× {{ leisureState.fishBook[fish.id] || 0 }}</small></div>
          </div>
        </section>

        <fieldset v-if="hasPlayed" class="after-play">
          <legend>玩完后，此刻更接近</legend>
          <button v-for="option in afterOptions" :key="option.id" type="button" :class="{ active: afterFeeling === option.id }" @click="finishReflection(option.id)">
            {{ option.label }}
          </button>
          <p v-if="afterFeeling">{{ nextStep }}</p>
        </fieldset>
      </main>

      <aside class="leisure-agent" aria-labelledby="leisure-agent-title">
        <header>
          <span class="agent-lamp" :class="agentStatus" aria-hidden="true"></span>
          <div>
            <p>可核验工作进度</p>
            <h3 id="leisure-agent-title">休闲陪伴 Agent</h3>
          </div>
        </header>
        <ol>
          <li v-for="step in agentSteps" :key="step.id" :class="`is-${step.status}`">
            <span aria-hidden="true">{{ step.status === 'done' ? '✓' : step.status === 'active' ? '•' : '·' }}</span>
            <div><strong>{{ step.label }}</strong><small>{{ step.summary }}</small></div>
            <em>{{ step.status === 'done' ? '完成' : step.status === 'active' ? '进行中' : '等待' }}</em>
          </li>
        </ol>
        <p class="agent-boundary">只使用你主动选择的需要和结束后的自评来安排下一步；不会仅凭游戏成绩判断心理状态，也不会自动提供给教师端。</p>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, onDeactivated, onUnmounted, reactive, ref, watch } from 'vue'

const props = defineProps({
  storageScope: { type: String, default: '' },
})

const emit = defineEmits(['close', 'open-healing', 'open-island'])
const dialog = ref(null)

const needs = [
  { id: 'quiet', mark: '静', label: '安静一下', hint: '把节奏慢下来' },
  { id: 'shift', mark: '换', label: '转移注意', hint: '暂时换个频道' },
  { id: 'control', mark: '稳', label: '找回掌控', hint: '做几步明确的小事' },
  { id: 'play', mark: '玩', label: '只是想玩', hint: '不用解释原因' },
]
const recommendationMap = {
  quiet: { game: 'fishing', title: '先去慢钓台坐一会', reason: '等待和收线只有两个动作，适合把节奏放慢；想停时直接关掉即可。' },
  shift: { game: 'fishing', title: '用一小轮钓鱼换个频道', reason: '短暂关注水面变化，不要求你继续解释刚才的感受。' },
  control: { game: 'garden', title: '从一块小田地开始', reason: '种下、浇水、收获都是明确的小步骤，完成一格就算结束。' },
  play: { game: 'garden', title: '小田园和慢钓台都开放', reason: '不做情绪推断，也没有任务压力；先从小田园随便点一块地。' },
}
const afterOptions = [
  { id: 'lighter', label: '轻松一点' },
  { id: 'same', label: '差不多' },
  { id: 'switch', label: '想换一种' },
]
const seedTypes = [
  { id: 'sunflower', label: '向日葵', mark: '☀' },
  { id: 'carrot', label: '胡萝卜', mark: '芽' },
  { id: 'berry', label: '莓果', mark: '果' },
]
const fishTypes = [
  { id: 'silver', label: '银尾小鱼', mark: '◇' },
  { id: 'square', label: '方鳍鱼', mark: '□' },
  { id: 'moon', label: '月光鱼', mark: '◐' },
]
const defaultPlots = () => Array.from({ length: 6 }, () => ({ stage: 0, watered: false, crop: 'sunflower' }))
const defaultFishBook = () => Object.fromEntries(fishTypes.map(fish => [fish.id, 0]))
const defaultState = () => ({ plots: defaultPlots(), harvests: 0, catches: 0, fishBook: defaultFishBook() })
const normalizedScope = computed(() => String(props.storageScope || '').replace(/[^a-zA-Z0-9_-]/g, ''))
const storageKey = computed(() => normalizedScope.value ? `shengyu_leisure_v5_${normalizedScope.value}` : '')

function loadState() {
  if (!storageKey.value) return defaultState()
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey.value) || '{}')
    return {
      plots: Array.isArray(saved.plots) && saved.plots.length === 6 ? saved.plots.map(plot => ({ stage: Math.max(0, Math.min(2, Number(plot.stage) || 0)), watered: !!plot.watered, crop: seedTypes.some(seed => seed.id === plot.crop) ? plot.crop : 'sunflower' })) : defaultPlots(),
      harvests: Math.max(0, Number(saved.harvests) || 0),
      catches: Math.max(0, Number(saved.catches) || 0),
      fishBook: Object.fromEntries(fishTypes.map(fish => [fish.id, Math.max(0, Number(saved.fishBook?.[fish.id]) || 0)])),
    }
  } catch {
    return defaultState()
  }
}

const leisureState = reactive(loadState())
const selectedNeed = ref('')
const selectedSeed = ref('sunflower')
const activeGame = ref('garden')
const gardenMessage = ref('选一块空地开始。这里没有倒计时。')
const fishingState = ref('idle')
const fishingMessage = ref('准备好时再抛竿。')
const hasPlayed = ref(false)
const afterFeeling = ref('')
let biteTimer = null
let escapeTimer = null

const recommendation = computed(() => recommendationMap[selectedNeed.value] || {
  game: 'garden',
  title: '先告诉我你想要的节奏',
  reason: 'Agent 会根据你的主动选择安排玩法，而不是猜测你的情绪。',
})
const nextStep = computed(() => ({
  lighter: '把这点轻松留住就好。可以回房间，也可以只再玩一小轮。',
  same: '没有变化也很正常。若心里还有话，可以回到倾诉；不想说也可以先休息。',
  switch: activeGame.value === 'garden' ? '可以换到慢钓台，或打开放松工具。' : '可以换到小田园，做一件步骤明确的小事。',
})[afterFeeling.value] || '')
const agentStatus = computed(() => afterFeeling.value ? 'ready' : (selectedNeed.value || hasPlayed.value) ? 'running' : 'standby')
const agentSteps = computed(() => [
  { id: 'intent', label: '理解主动选择', summary: selectedNeed.value ? `已记录“${needs.find(item => item.id === selectedNeed.value)?.label}”` : hasPlayed.value ? '你直接选择了玩法，按普通娱乐模式进行' : '等待你选择想要的节奏', status: (selectedNeed.value || hasPlayed.value) ? 'done' : 'active' },
  { id: 'boundary', label: '确认安全边界', summary: '不从成绩推断情绪，不做诊断，不设置失败惩罚', status: (selectedNeed.value || hasPlayed.value) ? 'done' : 'waiting' },
  { id: 'plan', label: '安排合适玩法', summary: selectedNeed.value ? recommendation.value.title : hasPlayed.value ? `已进入${activeGame.value === 'garden' ? '小田园' : '慢钓台'}` : '选择后生成低负担玩法建议', status: hasPlayed.value ? 'done' : selectedNeed.value ? 'active' : 'waiting' },
  { id: 'review', label: '完成后回看', summary: afterFeeling.value ? nextStep.value : '只采用你的主观反馈生成下一步', status: afterFeeling.value ? 'done' : hasPlayed.value ? 'active' : 'waiting' },
])

watch(leisureState, value => {
  if (!storageKey.value) return
  localStorage.setItem(storageKey.value, JSON.stringify({ plots: value.plots, harvests: value.harvests, catches: value.catches, fishBook: value.fishBook }))
}, { deep: true })

watch(storageKey, (nextKey, previousKey) => {
  if (nextKey === previousKey) return
  clearFishingTimers()
  Object.assign(leisureState, loadState())
  selectedNeed.value = ''
  afterFeeling.value = ''
  hasPlayed.value = false
  fishingState.value = 'idle'
  fishingMessage.value = '准备好时再抛竿。'
  gardenMessage.value = '选一块空地开始。这里没有倒计时。'
}, { flush: 'sync' })

function chooseNeed(id) {
  selectedNeed.value = id
  afterFeeling.value = ''
}

function selectGame(game) {
  activeGame.value = game
  afterFeeling.value = ''
}

function plotAction(plot) {
  if (plot.stage === 0) return '种下'
  if (plot.stage === 1 && !plot.watered) return '浇水'
  if (plot.stage === 1) return '长大'
  return '收获'
}

function plotLabel(plot, index) {
  const crop = seedTypes.find(seed => seed.id === plot.crop)?.label || '作物'
  return `第${index + 1}块田，${crop}，${plotAction(plot)}`
}

function tendPlot(index) {
  const plot = leisureState.plots[index]
  if (plot.stage === 0) {
    plot.crop = selectedSeed.value
    plot.stage = 1
    gardenMessage.value = '种子已经放好。下一次点击给它一点水。'
  } else if (plot.stage === 1 && !plot.watered) {
    plot.watered = true
    gardenMessage.value = '水刚刚好。再点一次，看它慢慢长大。'
  } else if (plot.stage === 1) {
    plot.stage = 2
    gardenMessage.value = '它长好了。现在收获，或者先留在这里。'
  } else {
    plot.stage = 0
    plot.watered = false
    leisureState.harvests += 1
    gardenMessage.value = '收好这一份小成果。到这里停下也算完整。'
  }
  hasPlayed.value = true
}

function clearFishingTimers() {
  clearTimeout(biteTimer)
  clearTimeout(escapeTimer)
  biteTimer = null
  escapeTimer = null
}

function castLine() {
  clearFishingTimers()
  fishingState.value = 'waiting'
  fishingMessage.value = '水面很安静，先等一小会。'
  hasPlayed.value = true
  biteTimer = setTimeout(() => {
    fishingState.value = 'bite'
    fishingMessage.value = '方形涟漪出现了，现在可以收线。'
    escapeTimer = setTimeout(() => {
      fishingState.value = 'result'
      fishingMessage.value = '它游走了。这里没有损失，想再等一次也可以。'
    }, 2600)
  }, 1800)
}

function reelLine() {
  if (fishingState.value !== 'bite') return
  clearFishingTimers()
  leisureState.catches += 1
  fishingState.value = 'result'
  const fish = fishTypes[(leisureState.catches - 1) % fishTypes.length]
  leisureState.fishBook[fish.id] = (leisureState.fishBook[fish.id] || 0) + 1
  fishingMessage.value = `遇见了${fish.label}，已经收进图鉴。不需要继续，先看看现在的感觉。`
}

function finishReflection(id) {
  afterFeeling.value = id
}

function handleDialogKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    emit('close')
    return
  }
  if (event.key !== 'Tab' || !dialog.value) return
  const focusable = [...dialog.value.querySelectorAll('button:not([disabled]), a[href], input:not([disabled]), [tabindex]:not([tabindex="-1"])')]
    .filter(element => element.getClientRects().length > 0)
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

onDeactivated(clearFishingTimers)
onUnmounted(clearFishingTimers)
</script>

<style scoped>
.leisure-hub {
  --ink: #f7f4ed;
  --muted: rgba(247, 244, 237, .72);
  --mint: #b8d7c7;
  --sand: #e8d49b;
  width: min(1040px, calc(100vw - 36px));
  max-height: min(88vh, 820px);
  overflow: auto;
  padding: 22px;
  border: 1px solid rgba(255, 255, 255, .14);
  border-radius: 18px;
  color: var(--ink);
  background: rgba(16, 22, 28, .94);
  box-shadow: 0 14px 32px rgba(5, 8, 12, .38);
  backdrop-filter: blur(24px) saturate(1.16);
  font-family: 'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', system-ui, sans-serif;
}
.leisure-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
.leisure-header-actions { display: flex; align-items: center; gap: 8px; }
.island-entry { min-height: 42px; padding: 0 13px; border: 0; border-radius: 10px; color: #17231e; background: var(--mint); font-weight: 800; cursor: pointer; }
.leisure-header p, .leisure-header h2, .leisure-header span { margin: 0; }
.leisure-header p { color: var(--mint); font-size: 11px; font-weight: 800; letter-spacing: .06em; }
.leisure-header h2 { margin-top: 4px; font-size: 22px; line-height: 1.35; }
.leisure-header > div > span { display: block; margin-top: 5px; color: var(--muted); font-size: 12px; line-height: 1.55; }
.panel-close { width: 44px; height: 44px; flex: 0 0 auto; border: 0; border-radius: 10px; color: var(--ink); background: rgba(255, 255, 255, .08); font-size: 22px; cursor: pointer; }
.leisure-layout { display: grid; grid-template-columns: minmax(0, 1fr) 286px; gap: 18px; margin-top: 20px; }
.leisure-main { min-width: 0; }
.need-picker { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 0; padding: 0; border: 0; }
.need-picker legend, .after-play legend { margin-bottom: 8px; color: var(--muted); font-size: 11px; font-weight: 700; }
.need-picker button { display: grid; grid-template-columns: 30px minmax(0, 1fr); column-gap: 8px; min-height: 64px; padding: 9px; border: 1px solid rgba(255, 255, 255, .09); border-radius: 12px; color: var(--ink); background: rgba(255, 255, 255, .055); text-align: left; cursor: pointer; }
.need-picker button.active { border-color: var(--mint); background: rgba(184, 215, 199, .14); }
.pixel-mark { grid-row: 1 / 3; display: grid; place-items: center; width: 30px; height: 30px; border-radius: 7px; color: #18231f; background: var(--mint); font: 800 11px/1 ui-monospace, monospace; }
.need-picker strong { align-self: end; font-size: 12px; }
.need-picker small { color: var(--muted); font-size: 10px; }
.agent-recommendation { display: grid; grid-template-columns: 36px minmax(0, 1fr) auto; align-items: center; gap: 11px; margin-top: 12px; padding: 11px; border-radius: 12px; background: rgba(232, 212, 155, .1); }
.recommendation-mark { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 8px; color: #2d2514; background: var(--sand); font: 900 13px/1 ui-monospace, monospace; }
.agent-recommendation small, .agent-recommendation strong, .agent-recommendation p { display: block; margin: 0; }
.agent-recommendation small { color: var(--sand); font-size: 9px; font-weight: 800; }
.agent-recommendation strong { margin-top: 2px; font-size: 12px; }
.agent-recommendation p { margin-top: 2px; color: var(--muted); font-size: 11px; line-height: 1.45; }
.agent-recommendation button, .fishing-action button { min-height: 40px; padding: 0 14px; border: 0; border-radius: 10px; color: #18231f; background: var(--sand); font-weight: 800; cursor: pointer; }
.game-tabs { display: flex; gap: 6px; margin-top: 14px; padding: 5px; border-radius: 12px; background: rgba(255, 255, 255, .05); }
.game-tabs button { min-height: 40px; padding: 0 13px; border: 0; border-radius: 9px; color: var(--muted); background: transparent; font-weight: 700; cursor: pointer; }
.game-tabs button.active { color: #18231f; background: var(--mint); }
.game-tabs button span { display: inline-grid; place-items: center; width: 21px; height: 21px; margin-right: 4px; border: 1px solid currentColor; font: 800 9px/1 ui-monospace, monospace; }
.game-board { margin-top: 10px; padding: 15px; border-radius: 14px; background: rgba(255, 255, 255, .055); }
.game-copy { display: flex; align-items: flex-start; justify-content: space-between; gap: 15px; }
.game-copy p, .game-copy h3, .game-copy span { margin: 0; }
.game-copy p { color: var(--mint); font-size: 9px; font-weight: 800; }
.game-copy h3 { margin-top: 2px; font-size: 16px; }
.game-copy span { display: block; margin-top: 3px; color: var(--muted); font-size: 11px; line-height: 1.5; }
.game-copy > strong { color: var(--sand); font-size: 11px; white-space: nowrap; }
.seed-picker { display: flex; flex-wrap: wrap; align-items: center; gap: 7px; margin-top: 12px; }
.seed-picker > span, .fish-book > span { color: var(--muted); font-size: 10px; font-weight: 800; }
.seed-picker button { min-height: 34px; padding: 0 10px; border: 0; border-radius: 8px; color: var(--muted); background: rgba(255,255,255,.08); cursor: pointer; }
.seed-picker button.active { color: #17231e; background: var(--mint); }
.seed-picker i { display: inline-grid; place-items: center; width: 19px; height: 19px; margin-right: 5px; border-radius: 5px; background: rgba(255,255,255,.28); font-size: 10px; font-style: normal; }
.garden-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 13px; }
.garden-plot { position: relative; min-height: 100px; overflow: hidden; border: 2px solid #4f3928; border-radius: 9px; color: #f6ead4; background: #76543a; cursor: pointer; image-rendering: pixelated; }
.soil-lines { position: absolute; inset: 18px 8px 28px; border-block: 5px solid rgba(46, 28, 19, .4); }
.crop { position: absolute; left: 50%; bottom: 29px; width: 24px; height: 34px; transform: translateX(-50%); }
.crop i { position: absolute; left: 10px; bottom: 0; width: 5px; height: 0; background: #7bad73; }
.crop b { position: absolute; left: 2px; bottom: 12px; width: 20px; height: 0; background: #b8d477; box-shadow: -6px 5px 0 #7bad73, 6px 5px 0 #7bad73; }
.stage-1 .crop i { height: 14px; }
.stage-1.watered .crop b { height: 7px; }
.stage-2 .crop i { height: 23px; }
.stage-2 .crop b { height: 12px; box-shadow: -7px 7px 0 #7bad73, 7px 7px 0 #7bad73, 0 -7px 0 #e8d49b; }
.stage-2.crop-carrot .crop b { background: #e99655; box-shadow: -6px 6px 0 #7bad73, 6px 6px 0 #7bad73, 0 -6px 0 #e99655; }
.stage-2.crop-berry .crop b { background: #bd718c; box-shadow: -7px 7px 0 #7bad73, 7px 7px 0 #7bad73, 0 -7px 0 #bd718c; }
.garden-plot small { position: absolute; left: 0; right: 0; bottom: 0; min-height: 24px; padding: 5px; background: rgba(30, 20, 14, .76); font-size: 10px; font-weight: 800; }
.game-status { margin: 10px 0 0; color: var(--muted); font-size: 11px; line-height: 1.5; }
.pixel-pond { position: relative; height: 218px; margin-top: 13px; overflow: hidden; border: 2px solid #314e55; border-radius: 10px; background: #5e98a0; image-rendering: pixelated; }
.pond-shore { position: absolute; inset: 0 0 auto; height: 36px; border-bottom: 7px solid #b68d55; background: #d8bd76; }
.float-line { position: absolute; top: 30px; left: 50%; width: 2px; height: 94px; background: rgba(242, 235, 209, .7); transform: rotate(18deg); transform-origin: top; }
.float { position: absolute; top: 112px; left: 62%; width: 10px; height: 14px; border: 3px solid #f0d58e; background: #c96f5e; }
.fish { position: absolute; width: 24px; height: 10px; background: rgba(235, 231, 184, .72); }
.fish::after { content: ''; position: absolute; right: -8px; top: -4px; border-block: 9px solid transparent; border-left: 9px solid rgba(235, 231, 184, .72); }
.fish-one { left: 18%; top: 62%; }
.fish-two { right: 15%; top: 78%; transform: scaleX(-1); }
.pixel-pond.is-bite .float { outline: 5px solid rgba(240, 213, 142, .45); outline-offset: 8px; transform: translateY(7px); }
.fishing-action { display: flex; align-items: center; gap: 12px; margin-top: 10px; }
.fishing-action button:disabled { color: rgba(24, 35, 31, .65); background: #aaa687; cursor: wait; }
.fishing-action button.is-biting { background: var(--mint); }
.fishing-action .game-status { margin: 0; }
.fish-book { display: flex; flex-wrap: wrap; align-items: center; gap: 7px; margin-top: 12px; }
.fish-book div { display: grid; grid-template-columns: 22px auto auto; align-items: center; gap: 5px; min-height: 34px; padding: 5px 8px; border-radius: 8px; background: rgba(255,255,255,.07); }
.fish-book i { display: grid; place-items: center; width: 22px; height: 22px; color: #19333a; background: #9bc8c9; font-style: normal; }
.fish-book strong { font-size: 10px; }
.fish-book small { color: var(--sand); font-size: 9px; }
.after-play { display: flex; flex-wrap: wrap; align-items: center; gap: 7px; margin: 12px 0 0; padding: 11px; border: 1px solid rgba(255, 255, 255, .09); border-radius: 12px; }
.after-play legend { float: left; margin: 0 5px 0 0; }
.after-play button { min-height: 36px; padding: 0 11px; border: 0; border-radius: 9px; color: var(--muted); background: rgba(255, 255, 255, .08); cursor: pointer; }
.after-play button.active { color: #18231f; background: var(--mint); }
.after-play p { flex: 1 0 100%; margin: 3px 0 0; color: var(--mint); font-size: 11px; line-height: 1.55; }
.leisure-agent { align-self: start; padding: 14px; border-radius: 14px; background: rgba(255, 255, 255, .055); }
.leisure-agent header { display: grid; grid-template-columns: 12px minmax(0, 1fr); align-items: center; gap: 9px; }
.agent-lamp { width: 10px; height: 10px; border-radius: 2px; background: #86918c; }
.agent-lamp.running { background: var(--sand); }
.agent-lamp.ready { background: #91c8aa; }
.leisure-agent header p, .leisure-agent header h3 { margin: 0; }
.leisure-agent header p { color: var(--mint); font-size: 9px; font-weight: 800; }
.leisure-agent header h3 { margin-top: 2px; font-size: 14px; }
.leisure-agent ol { display: grid; gap: 2px; margin: 12px 0 0; padding: 0; list-style: none; }
.leisure-agent li { display: grid; grid-template-columns: 24px minmax(0, 1fr) auto; gap: 8px; padding: 10px 0; border-bottom: 1px solid rgba(255, 255, 255, .07); }
.leisure-agent li > span { display: grid; place-items: center; width: 22px; height: 22px; border-radius: 6px; color: var(--muted); background: rgba(255, 255, 255, .07); font-weight: 800; }
.leisure-agent li.is-done > span { color: #17231e; background: var(--mint); }
.leisure-agent li.is-active > span { color: #2f2412; background: var(--sand); }
.leisure-agent strong, .leisure-agent small { display: block; }
.leisure-agent strong { font-size: 11px; line-height: 1.4; }
.leisure-agent small { margin-top: 2px; color: var(--muted); font-size: 10px; line-height: 1.45; }
.leisure-agent em { color: var(--muted); font-size: 9px; font-style: normal; }
.agent-boundary { margin: 12px 0 0; color: var(--muted); font-size: 10px; line-height: 1.6; }
button:focus-visible { outline: 3px solid #f0d58e; outline-offset: 3px; }

@media (max-width: 820px) {
  .leisure-hub { width: calc(100vw - 20px); max-height: calc(100dvh - 28px); padding: 16px; border-radius: 16px; }
  .leisure-layout { grid-template-columns: 1fr; }
  .leisure-agent ol { grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 5px; }
  .leisure-agent li { grid-template-columns: 22px minmax(0, 1fr); padding: 7px; border: 0; border-radius: 9px; background: rgba(255, 255, 255, .04); }
  .leisure-agent li em { grid-column: 2; }
  .leisure-agent small { display: none; }
  .need-picker { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 520px) {
  .leisure-header { align-items: stretch; }
  .leisure-header-actions { flex-direction: column-reverse; align-items: flex-end; }
  .island-entry { min-height: 38px; font-size: 11px; }
  .leisure-header h2 { font-size: 18px; }
  .leisure-layout { margin-top: 14px; }
  .leisure-agent ol { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .agent-recommendation { grid-template-columns: 32px minmax(0, 1fr); }
  .agent-recommendation button { grid-column: 2; justify-self: start; }
  .game-tabs { overflow-x: auto; }
  .game-tabs button { flex: 0 0 auto; }
  .garden-grid { grid-template-columns: repeat(2, 1fr); }
  .pixel-pond { height: 180px; }
  .fishing-action { align-items: flex-start; flex-direction: column; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
}
</style>
