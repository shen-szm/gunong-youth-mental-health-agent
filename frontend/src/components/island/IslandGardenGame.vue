<template>
  <section class="garden-simple" aria-labelledby="island-garden-title">
    <header class="garden-header">
      <div>
        <small>云顶暖房 · 一小片花园</small>
        <h3 id="island-garden-title">慢慢种，慢慢长</h3>
        <p>翻地、播种、浇水，再把收成交给岛民。不用赶时间，植物会按自己的节奏生长。</p>
      </div>
    </header>

    <div class="garden-body">
      <!-- 工具选择 -->
      <div class="garden-tools" role="toolbar" aria-label="花园操作">
        <button
          v-for="tool in tools"
          :key="tool.id"
          type="button"
          :class="{ active: selectedTool === tool.id }"
          @click="selectedTool = tool.id"
        >
          <span class="tool-icon">{{ tool.icon }}</span>
          <span>{{ tool.label }}</span>
        </button>
      </div>

      <!-- 种子选择（播种工具时显示） -->
      <div v-if="selectedTool === 'seed'" class="seed-selector">
        <span>选一种种子：</span>
        <button
          v-for="crop in crops"
          :key="crop.id"
          type="button"
          :class="{ active: selectedSeed === crop.id }"
          @click="selectedSeed = crop.id"
        >
          <i :style="{ background: crop.color }"></i>
          {{ crop.label }}
        </button>
      </div>

      <!-- 花园网格 -->
      <div class="garden-plots">
        <button
          v-for="(plot, index) in plots"
          :key="index"
          type="button"
          class="plot"
          :class="[`soil-${plot.soil}`, { watered: plot.watered, mature: isMature(plot) }]"
          @click="actOnPlot(index)"
        >
          <span v-if="plot.crop" class="plant" :style="plantStyle(plot)">
            <span class="stem"></span>
            <span class="leaves"></span>
            <span v-if="isMature(plot)" class="flower" :style="{ background: cropColor(plot.crop) }"></span>
          </span>
          <span v-if="plot.watered" class="water-drop">💧</span>
          <small>{{ plotStatus(plot) }}</small>
        </button>
      </div>

      <!-- 状态提示 -->
      <p class="garden-message" role="status" aria-live="polite">{{ message }}</p>

      <!-- 咕团帮忙 -->
      <button type="button" class="pet-help-btn" :disabled="!petHelpReady" @click="petHelp">
        {{ petHelpReady ? '请咕团帮忙浇水' : '咕团今天已经帮忙过了' }}
      </button>
      <p class="garden-message"><strong>岛民委托：</strong>照料任意一块田并完成一次收获。委托只记录玩法进度，不用于判断情绪。</p>
    </div>
  </section>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { logIslandBehavior } from '../../api/island.js'

const emit = defineEmits(['update:garden', 'played'])

// 作物定义
const crops = [
  { id: 'sunflower', label: '暖阳花', color: '#FFD700', stages: 3, growTime: 2 },
  { id: 'mint', label: '海风薄荷', color: '#98D8C8', stages: 2, growTime: 1 },
  { id: 'berry', label: '星莓', color: '#E74C3C', stages: 3, growTime: 2 },
  { id: 'carrot', label: '脆甜萝卜', color: '#FF8C00', stages: 2, growTime: 1 },
]

const tools = [
  { id: 'hoe', icon: '⛏️', label: '翻土' },
  { id: 'seed', icon: '🌱', label: '播种' },
  { id: 'water', icon: '💧', label: '浇水' },
  { id: 'harvest', icon: '🧺', label: '收获' },
]

// 6块地（简化，原来9块）
const plots = reactive(
  Array.from({ length: 6 }, () => ({
    soil: 'grass', // grass / tilled
    crop: null,
    stage: 0,
    watered: false,
    growProgress: 0,
  }))
)

const selectedTool = ref('hoe')
const selectedSeed = ref('sunflower')
const message = ref('先翻翻土，再选种子播种。不用急，植物会慢慢长。')
const petHelpReady = ref(true)

const cropFor = id => crops.find(c => c.id === id)
const cropColor = id => cropFor(id)?.color || '#888'
const isMature = plot => !!plot.crop && plot.stage >= cropFor(plot.crop).stages

function plantStyle(plot) {
  const crop = cropFor(plot.crop)
  if (!crop) return {}
  const growth = Math.max(20, ((plot.stage + 1) / (crop.stages + 1)) * 100)
  return {
    '--growth': `${growth}%`,
    '--crop-color': crop.color,
    height: `${Math.min(60, 20 + growth * 0.5)}px`,
  }
}

function plotStatus(plot) {
  if (!plot.crop) {
    return plot.soil === 'tilled' ? '空田 · 可播种' : '草地 · 可翻土'
  }
  if (isMature(plot)) return `${cropFor(plot.crop).label} · 成熟啦`
  return `${cropFor(plot.crop).label} · ${plot.watered ? '浇过水了' : `生长中 ${plot.stage}/${cropFor(plot.crop).stages}`}`
}

function actOnPlot(index) {
  const plot = plots[index]
  const tool = selectedTool.value

  if (tool === 'hoe') {
    if (plot.soil === 'grass' && !plot.crop) {
      plot.soil = 'tilled'
      message.value = '土翻好了，松松软软的。'
      logAction('hoe')
    } else if (plot.crop) {
      message.value = '这里已经种了东西，不要翻掉哦。'
    } else {
      message.value = '已经翻过了，可以播种了。'
    }
  }

  else if (tool === 'seed') {
    if (plot.soil === 'tilled' && !plot.crop) {
      plot.crop = selectedSeed.value
      plot.stage = 0
      plot.watered = false
      message.value = `种下了${cropFor(selectedSeed.value).label}，浇点水它就会开始长。`
      logAction('seed', selectedSeed.value)
    } else if (plot.crop) {
      message.value = '这里已经种了东西了。'
    } else {
      message.value = '先翻翻土再播种。'
    }
  }

  else if (tool === 'water') {
    if (plot.crop && !plot.watered) {
      plot.watered = true
      // 浇水后生长
      const crop = cropFor(plot.crop)
      if (plot.stage < crop.stages) {
        plot.stage += 1
      }
      message.value = isMature(plot)
        ? `${crop.label}成熟了！可以收获了。`
        : `浇了水，${crop.label}又长大了一点。`
      logAction('water')
    } else if (plot.watered) {
      message.value = '已经浇过水了，等它吸收一下。'
    } else {
      message.value = '这里还没种东西呢。'
    }
  }

  else if (tool === 'harvest') {
    if (isMature(plot)) {
      const cropName = cropFor(plot.crop).label
      plot.crop = null
      plot.stage = 0
      plot.watered = false
      plot.soil = 'grass'
      message.value = `收获了${cropName}！可以再翻土种新的。`
      logAction('harvest', cropName)
      emit('played', { action: 'harvest', crop: cropName })
    } else if (plot.crop) {
      message.value = '还没成熟，再等等，浇浇水。'
    } else {
      message.value = '这里还没种东西。'
    }
  }
}

function petHelp() {
  if (!petHelpReady.value) return
  // 咕团帮所有种了的地浇水
  let watered = 0
  plots.forEach(plot => {
    if (plot.crop && !plot.watered) {
      plot.watered = true
      const crop = cropFor(plot.crop)
      if (plot.stage < crop.stages) plot.stage += 1
      watered++
    }
  })
  petHelpReady.value = false
  message.value = watered > 0
    ? `咕团帮你浇了${watered}块地，开心地摇了摇尾巴。`
    : '咕团看了看，没有需要浇水的植物，就坐下来陪你了。'
  logAction('pet_help')
  emit('played', { action: 'pet_help' })
}

function logAction(action, detail = '') {
  logIslandBehavior('activity_finish', 'garden', action, { detail }).catch(() => {})
}
</script>

<style scoped>
.garden-simple {
  color: #fff4df;
  font-family: 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
}
.garden-header { margin-bottom: 16px; }
.garden-header small { color: #ffd083; font-size: 11px; font-weight: 800; }
.garden-header h3 { margin: 4px 0 0; font-size: 20px; }
.garden-header p { margin: 6px 0 0; color: #f5d9bd; font-size: 12px; line-height: 1.6; max-width: 50ch; }

.garden-body { display: grid; gap: 12px; }

.garden-tools {
  display: flex; gap: 8px; flex-wrap: wrap;
}
.garden-tools button {
  display: flex; align-items: center; gap: 6px;
  min-height: 40px; padding: 0 14px;
  border: 1px solid rgba(255,224,187,.2);
  border-radius: 10px;
  color: #f8dfc4; background: #643d34;
  font: inherit; font-size: 12px; font-weight: 600;
  cursor: pointer; transition: all .15s;
}
.garden-tools button:hover { background: #754a3f; }
.garden-tools button.active { border-color: #ffd083; background: #85543f; }
.tool-icon { font-size: 16px; }

.seed-selector {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding: 10px; border-radius: 10px;
  background: rgba(92,57,50,.6);
}
.seed-selector > span { font-size: 11px; color: #efc5a8; }
.seed-selector button {
  display: flex; align-items: center; gap: 5px;
  min-height: 32px; padding: 0 10px;
  border: 1px solid transparent; border-radius: 8px;
  color: #f8dfc4; background: #765044;
  font: inherit; font-size: 11px; cursor: pointer;
}
.seed-selector button.active { border-color: #ffd083; }
.seed-selector i { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }

.garden-plots {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;
}
.plot {
  position: relative;
  min-height: 100px;
  border: 2px solid #5a3829;
  border-radius: 10px;
  background: #806044;
  cursor: pointer;
  overflow: hidden;
  transition: all .2s;
  padding: 0;
}
.plot:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,.2); }
.plot.soil-grass { background: linear-gradient(#718d54 0 35%, #77563d 35%); }
.plot.soil-tilled { background: linear-gradient(#6B4423 0 35%, #5a3829 35%); }
.plot.watered { box-shadow: inset 0 0 0 3px #77a8b1; }
.plot.mature { border-color: #e9bc64; }

.plant {
  position: absolute; left: 50%; bottom: 28px;
  transform: translateX(-50%);
  display: flex; flex-direction: column; align-items: center;
}
.stem {
  width: 4px; background: #6f9c63;
  height: var(--growth);
  min-height: 10px;
}
.leaves {
  width: 20px; height: 14px;
  background: var(--crop-color);
  border-radius: 50% 50% 0 0;
  margin-top: -2px;
  box-shadow: -8px 4px 0 #6f9c63, 8px 4px 0 #6f9c63;
}
.flower {
  width: 14px; height: 14px;
  border-radius: 50%;
  margin-top: -8px;
  box-shadow: 0 0 8px currentColor;
}
.water-drop {
  position: absolute; top: 6px; right: 6px;
  font-size: 14px;
}
.plot > small {
  position: absolute; bottom: 0; left: 0; right: 0;
  padding: 5px;
  background: rgba(45,28,20,.76);
  font-size: 9px; font-weight: 700;
  color: #fff1db;
}

.garden-message {
  margin: 0; padding: 10px 14px;
  border-radius: 10px;
  background: rgba(255,255,255,.08);
  color: #f5d9bd; font-size: 12px; line-height: 1.5;
}

.pet-help-btn {
  justify-self: start;
  min-height: 38px; padding: 0 18px;
  border: 0; border-radius: 10px;
  background: #acd2ad; color: #2d4a2d;
  font: inherit; font-size: 12px; font-weight: 700;
  cursor: pointer; transition: all .15s;
}
.pet-help-btn:hover:not(:disabled) { background: #b8ddb9; }
.pet-help-btn:disabled { opacity: .5; cursor: not-allowed; }

@media (max-width: 600px) {
  .garden-plots { grid-template-columns: repeat(2, 1fr); }
}
</style>
