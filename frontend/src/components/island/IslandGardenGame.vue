<script setup>
import { computed, ref } from 'vue'
import { GARDEN_CROPS as crops, GARDEN_TOOLS as tools, normalizeGardenLifeState, actOnGardenPlot, buyGardenSeeds, fulfillGardenOrder, usePetGardenHelp, gardenCrop } from '../../game/island/gardenLifeEngine.js'
const props = defineProps({ garden: { type: Object, required: true } })
const emit = defineEmits(['update:garden', 'played'])
const state = computed(() => normalizeGardenLifeState(props.garden))
const message = ref('先选锄地，再点一块草地。每次照料都会推进已浇水植物的生长。')
const selectedTool = computed({ get: () => state.value.selectedTool, set: value => emit('update:garden', { ...state.value, selectedTool: value }) })
const selectedSeed = computed({ get: () => state.value.selectedSeed, set: value => emit('update:garden', { ...state.value, selectedSeed: value }) })
const status = plot => !plot.crop ? plot.soil === 'tilled' ? '空田 · 可以播种' : '草地 · 可以锄地' : `${gardenCrop(plot.crop).label} · ${plot.stage >= gardenCrop(plot.crop).stages ? '可以收获' : plot.watered ? '水分充足' : '需要浇水'}`
function apply(result, action) {
  message.value = result.message
  if (!result.changed) return
  emit('update:garden', result.state)
  emit('played', { action, activity: 'garden' })
}
</script>

<template>
  <section class="island-garden-game" aria-labelledby="island-garden-title">
    <header><div><small>云顶暖房</small><h3 id="island-garden-title">把一颗种子，照料成一份收获</h3><p>锄地 → 播种 → 浇水 → 收获。生长随照料行动推进，不需要在线等待，也不会因离开枯萎。</p></div><span>第 {{ state.day }} 个照料日 · {{ state.coins }} 岛币</span></header>
    <div class="garden-layout">
      <div>
        <div class="garden-tools" role="toolbar" aria-label="花园操作"><button v-for="tool in tools" :key="tool.id" :aria-pressed="selectedTool === tool.id" :title="tool.hint" @click="selectedTool = tool.id">{{ tool.label }}</button></div>
        <label class="garden-seed">当前种子<select v-model="selectedSeed"><option v-for="crop in crops" :key="crop.id" :value="crop.id">{{ crop.label }} · {{ state.seeds[crop.id] }} 颗</option></select></label>
        <div class="garden-plots"><button v-for="(plot, index) in state.plots" :key="index" class="plot" :class="{ tilled: plot.soil === 'tilled', mature: plot.crop && plot.stage >= gardenCrop(plot.crop).stages }" :aria-label="`第${index + 1}块地：${status(plot)}`" @click="apply(actOnGardenPlot(state, index), selectedTool)">
          <span aria-hidden="true" class="plant">{{ !plot.crop ? plot.soil === 'tilled' ? '·' : '☘' : plot.stage >= gardenCrop(plot.crop).stages ? ({ sunflower: '🌻', carrot: '🥕', berry: '🫐', mint: '🌿' })[plot.crop] : '🌱' }}</span>
          <strong>{{ status(plot) }}</strong><small v-if="plot.crop">生长 {{ plot.stage }} / {{ gardenCrop(plot.crop).stages }}</small>
        </button></div>
        <p class="garden-message" role="status" aria-live="polite">{{ message }}</p>
        <button class="garden-help" :disabled="!state.petHelpReady" @click="apply(usePetGardenHelp(state), 'pet_help')">{{ state.petHelpReady ? '请咕团帮忙浇水' : '咕团已帮忙，下个照料日再来' }}</button>
      </div>
      <aside><h4>岛民委托</h4><p>交付 {{ state.order.amount }} 份{{ gardenCrop(state.order.crop).label }}，换取 {{ state.order.reward }} 岛币。</p><button @click="apply(fulfillGardenOrder(state), 'order')">交付收获</button><h4>收获篮与种子铺</h4><div v-for="crop in crops" :key="crop.id" class="garden-stock"><span>{{ crop.label }}<small>收获 {{ state.produce[crop.id] }} · 种子 {{ state.seeds[crop.id] }}</small></span><button :disabled="state.coins < Math.max(2, crop.value - 1)" @click="apply(buyGardenSeeds(state, crop.id), 'buy_seeds')">换 2 颗 · {{ Math.max(2, crop.value - 1) }} 币</button></div><p class="garden-boundary">进度保存在当前账号的本机浏览器中。玩法成绩不用于判断情绪。</p></aside>
    </div>
  </section>
</template>

<style scoped>
.island-garden-game{color:#293f34;padding:24px;background:#f3f7f3;min-height:100%}.island-garden-game header{display:flex;justify-content:space-between;gap:20px}.island-garden-game h3{font-size:24px;margin:8px 0}.island-garden-game p{line-height:1.7;max-width:65ch;color:#4a6254}.island-garden-game header>span{white-space:nowrap;font-size:13px}.garden-layout{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(220px,1fr);gap:28px;margin-top:18px}.garden-tools{display:flex;gap:8px;flex-wrap:wrap}.island-garden-game button,.garden-seed select{min-height:40px;border:1px solid #9aad9f;border-radius:8px;background:#fff;color:#293f34;padding:8px 12px;font:inherit;cursor:pointer}.garden-tools button[aria-pressed=true]{background:#315e47;color:white;border-color:#315e47}.garden-seed{display:flex;align-items:center;gap:12px;margin:14px 0;font-size:13px}.garden-plots{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.garden-plots .plot{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:7px;min-height:116px;background:#dce9da}.garden-plots .tilled{background:#e8ddca;border-color:#bbaa8c}.garden-plots .mature{background:#f0e8b8;border-color:#ad9754}.plant{font-size:28px}.plot strong,.plot small{font-size:12px}.garden-message{min-height:48px;margin:14px 0}.garden-layout aside{border-left:1px solid #cbd9ce;padding-left:24px}.garden-layout h4{margin:8px 0 12px}.garden-stock{display:flex;align-items:center;justify-content:space-between;gap:10px;border-bottom:1px solid #cbd9ce;padding:12px 0;font-size:13px}.garden-stock small{display:block;margin-top:5px;color:#4a6254}.garden-stock button{font-size:12px}.garden-boundary{font-size:12px}.island-garden-game button:disabled{opacity:.55;cursor:default}.island-garden-game button:hover:not(:disabled){filter:brightness(.96)}.island-garden-game :focus-visible{outline:3px solid #315e47;outline-offset:3px}@media(max-width:700px){.garden-layout{grid-template-columns:1fr}.garden-layout aside{border-left:0;border-top:1px solid #cbd9ce;padding:18px 0}.island-garden-game{padding:16px}.island-garden-game header{display:block}.island-garden-game h3{font-size:20px}.garden-plots .plot{padding:8px;min-height:110px}}

/* 像素皮肤 3.0 · 云顶暖房 */
.island-garden-game{
  --px-line: rgba(41, 63, 52, .28);
  --px-gold: #315e47;
  --px-shadow: rgba(41, 63, 52, .22);
}
.island-garden-game header small,
.island-garden-game h3,
.island-garden-game h4{font-family:var(--px-font)}
.garden-tools button,
.garden-seed select,
.island-garden-game .garden-help,
.garden-layout aside button{
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: 2px 2px 0 var(--px-shadow);
  font-family: var(--px-font);
  transition: transform 160ms steps(2, end), box-shadow 160ms steps(2, end), background 160ms steps(2, end);
}
.garden-tools button:hover:not(:disabled),
.island-garden-game .garden-help:hover:not(:disabled),
.garden-layout aside button:hover:not(:disabled){
  filter: none;
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 var(--px-shadow);
}
.garden-tools button:active:not(:disabled),
.island-garden-game .garden-help:active:not(:disabled),
.garden-layout aside button:active:not(:disabled){
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--px-shadow);
}
.garden-tools button[aria-pressed=true]{border-color:var(--px-gold)}
.garden-plots .plot{border-radius:4px}
.garden-layout aside{border-left-color:var(--px-line)}
.garden-stock{border-bottom-color:var(--px-line)}
.island-garden-game :focus-visible{outline:3px dashed var(--px-gold);outline-offset:3px}

/* 像素皮肤 3.0 · 暖房羊皮纸 */
.island-garden-game{
  --px-line: rgba(120, 88, 52, .38);
  --px-gold: #b07a45;
  --px-shadow: rgba(74, 52, 32, .22);
  color: #3d2e1f;
  background:
    repeating-linear-gradient(0deg, rgba(120, 92, 55, .035) 0 2px, transparent 2px 8px),
    #f4ead5;
}
.island-garden-game h3{font-size:22px;color:#3d2e1f}
.island-garden-game p,
.island-garden-game header>span,
.island-garden-game .garden-stock small,
.island-garden-game .garden-boundary{color:#6b5743}
.island-garden-game button,
.garden-seed select{
  border-color:#b99a6e;
  color:#3d2e1f;
  background:#fff8ea;
}
.garden-tools button[aria-pressed=true]{background:#b07a45;border-color:#7d5a33;color:#fff8ea}
.garden-plots .plot{border:2px solid #b99a6e;background:#e5d7bd}
.garden-plots .tilled{background:#c9a878;border-color:#a4814f}
.garden-plots .mature{background:#e9d391;border-color:#ab8a3e}
.garden-layout aside{border-left:2px dashed #c3a87c}
.garden-layout h4{color:#3d2e1f}
.garden-stock{border-bottom:1px solid #d8c6a5}
.island-garden-game :focus-visible{outline:3px dashed #b07a45;outline-offset:3px}
</style>
