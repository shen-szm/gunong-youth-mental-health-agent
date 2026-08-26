<template>
  <section class="garden-game" aria-labelledby="island-garden-title" @keydown="handleKeydown">
    <header class="activity-copy">
      <div>
        <small>云顶暖房 · 合并种植</small>
        <h3 id="island-garden-title">把相同作物推到一起</h3>
        <p>方向键移动整片田地，相同生长阶段会合成。培育出暖阳花后，可以随时收获。</p>
      </div>
      <dl>
        <div><dt>照料步数</dt><dd>{{ garden.moves }}</dd></div>
        <div><dt>已收获</dt><dd>{{ garden.harvests }}</dd></div>
      </dl>
    </header>

    <div class="garden-playfield">
      <div ref="grid" class="merge-grid" role="grid" aria-label="四乘四合并种植区" tabindex="0">
        <div
          v-for="(tier, index) in garden.board"
          :key="index"
          :class="['merge-cell', tier ? `is-tier-${tier}` : 'is-empty']"
          role="gridcell"
          :aria-label="cellLabel(tier, index)"
        >
          <span v-if="tier" class="crop-pixel" aria-hidden="true">{{ cropFor(tier).mark }}</span>
          <small v-if="tier">{{ cropFor(tier).label }}</small>
        </div>
      </div>

      <div class="garden-tools" aria-label="田园操作">
        <div class="direction-pad">
          <button type="button" aria-label="向上合并" @click="move('up')">↑</button>
          <button type="button" aria-label="向左合并" @click="move('left')">←</button>
          <button type="button" aria-label="向下合并" @click="move('down')">↓</button>
          <button type="button" aria-label="向右合并" @click="move('right')">→</button>
        </div>
        <button type="button" class="tool-button" :disabled="!garden.previous" @click="undo">撤销一步</button>
        <button type="button" class="harvest-button" :disabled="highestTier < 5" @click="harvest">收获成熟作物</button>
      </div>
    </div>

    <p class="activity-status" role="status" aria-live="polite">{{ message }}</p>
  </section>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import { canMoveGarden, GARDEN_CROPS, harvestGarden, moveGarden } from '../../game/island/gardenMergeEngine.js'

const props = defineProps({ garden: { type: Object, required: true } })
const emit = defineEmits(['update:garden', 'played'])
const grid = ref(null)
const message = ref('先用方向键试着合并两株嫩芽。没有倒计时，也没有失败惩罚。')
const highestTier = computed(() => Math.max(0, ...props.garden.board))

function cropFor(tier) { return GARDEN_CROPS[Math.max(0, tier - 1)] || GARDEN_CROPS[0] }
function cellLabel(tier, index) { return `第${index + 1}格，${tier ? cropFor(tier).label : '空地'}` }

function move(direction) {
  const result = moveGarden(props.garden.board, direction)
  if (!result.moved) {
    message.value = canMoveGarden(props.garden.board) ? '这个方向暂时没有变化，换一个方向试试。' : '田地已经铺满。可以收获成熟作物，或撤销上一步。'
    return
  }
  emit('update:garden', {
    ...props.garden,
    previous: props.garden.board.slice(),
    board: result.board,
    score: props.garden.score + result.gained,
    moves: props.garden.moves + 1,
  })
  message.value = result.merges ? `合成了 ${result.merges} 组作物，新的嫩芽也落进田里。` : '作物已经移动，新的嫩芽落进田里。'
  emit('played', { activity: 'garden', action: 'move' })
}

function undo() {
  if (!props.garden.previous) return
  emit('update:garden', { ...props.garden, board: props.garden.previous.slice(), previous: null })
  message.value = '已经回到上一步。'
  emit('played', { activity: 'garden', action: 'undo' })
  nextTick(() => grid.value?.focus({ preventScroll: true }))
}

function harvest() {
  const result = harvestGarden(props.garden.board)
  if (!result.harvested) return
  emit('update:garden', { ...props.garden, board: result.board, previous: null, harvests: props.garden.harvests + 1 })
  message.value = `收获了一株${cropFor(result.tier).label}，田地留出了新的空间。`
  emit('played', { activity: 'garden', action: 'harvest' })
}

function handleKeydown(event) {
  const direction = { ArrowUp: 'up', ArrowRight: 'right', ArrowDown: 'down', ArrowLeft: 'left' }[event.key]
  if (!direction) return
  event.preventDefault()
  move(direction)
}
</script>

<style scoped>
.garden-game { display: grid; gap: 16px; color: #fff4df; }
.activity-copy { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; }
.activity-copy small { color: #ffd083; font-size: 12px; font-weight: 800; letter-spacing: .06em; }
.activity-copy h3 { margin: 4px 0 0; font-size: 24px; line-height: 1.2; }
.activity-copy p { max-width: 58ch; margin: 7px 0 0; color: #f5d9bd; font-size: 14px; line-height: 1.55; }
.activity-copy dl { display: flex; gap: 8px; margin: 0; }
.activity-copy dl div { min-width: 88px; padding: 9px 12px; border: 1px solid rgba(255,224,187,.2); border-radius: 12px; background: #743f31; }
.activity-copy dt { color: #f0c7a6; font-size: 11px; }
.activity-copy dd { margin: 3px 0 0; font-size: 18px; font-weight: 800; font-variant-numeric: tabular-nums; }
.garden-playfield { display: grid; grid-template-columns: minmax(340px, 520px) 180px; gap: 18px; align-items: center; }
.merge-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; padding: 10px; border: 1px solid #b66f4e; border-radius: 18px; background: #683c2f; box-shadow: inset 0 0 0 1px rgba(255,224,187,.08), 0 18px 42px rgba(55,25,25,.25); }
.merge-cell { aspect-ratio: 1; display: grid; align-content: center; justify-items: center; gap: 3px; min-width: 0; border: 1px solid rgba(255,233,198,.16); border-radius: 13px; color: #3b2b24; background: #91583f; transition: transform 180ms cubic-bezier(.25,1,.5,1), background 180ms ease; }
.merge-cell.is-empty { background: #764735; box-shadow: inset 0 4px 0 rgba(57,31,26,.2); }
.merge-cell:not(.is-empty) { box-shadow: inset 0 0 0 1px rgba(255,255,255,.18), 0 7px 12px rgba(42,23,18,.2); }
.merge-cell.is-tier-1 { background: #c6c47a; }
.merge-cell.is-tier-2 { background: #94ad67; }
.merge-cell.is-tier-3 { background: #f0c276; }
.merge-cell.is-tier-4 { background: #ef9b58; }
.merge-cell.is-tier-5 { background: #ffd36d; }
.merge-cell.is-tier-6 { background: #ffe6a4; }
.crop-pixel { display: grid; width: 38px; height: 38px; place-items: center; border: 2px solid currentColor; border-radius: 10px 4px 10px 4px; font-size: 17px; font-weight: 900; image-rendering: pixelated; }
.merge-cell small { font-size: 10px; font-weight: 800; }
.garden-tools { display: grid; gap: 10px; }
.direction-pad { display: grid; grid-template-columns: repeat(3, 48px); justify-content: center; gap: 6px; }
.direction-pad button { width: 48px; height: 48px; border: 1px solid #d58f67; border-radius: 12px; color: #fff4df; background: #7e4938; font: inherit; font-size: 19px; cursor: pointer; }
.direction-pad button:first-child { grid-column: 2; }
.direction-pad button:nth-child(2) { grid-column: 1; grid-row: 2; }
.direction-pad button:nth-child(3) { grid-column: 2; grid-row: 2; }
.direction-pad button:nth-child(4) { grid-column: 3; grid-row: 2; }
.tool-button, .harvest-button { min-height: 44px; padding: 0 12px; border: 1px solid #d58f67; border-radius: 12px; color: #fff4df; background: #7e4938; font: inherit; font-weight: 800; cursor: pointer; }
.harvest-button { color: #4a2b22; background: #ffd083; }
button:disabled { opacity: .48; cursor: not-allowed; }
.activity-status { min-height: 24px; margin: 0; color: #f5d9bd; font-size: 13px; line-height: 1.5; }
button:focus-visible, .merge-grid:focus-visible { outline: 3px solid #fff0a8; outline-offset: 3px; }
@media (max-width: 900px) { .garden-playfield { grid-template-columns: 1fr; } .garden-tools { grid-template-columns: auto 1fr 1fr; } .activity-copy dl { display: none; } }
@media (prefers-reduced-motion: reduce) { .merge-cell { transition: none; } }
</style>
