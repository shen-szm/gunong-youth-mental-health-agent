// Stateful farm loop inspired by proven resource-management games, implemented
// as original MIT-compatible project code on top of the existing Vue/Phaser stack.

export const GARDEN_CROPS = Object.freeze([
  { id: 'sunflower', label: '暖阳花', seedLabel: '花种', stages: 3, value: 4, color: '#f2bf62' },
  { id: 'carrot', label: '脆甜萝卜', seedLabel: '萝卜籽', stages: 3, value: 5, color: '#e8874f' },
  { id: 'berry', label: '星莓', seedLabel: '莓果籽', stages: 4, value: 8, color: '#b86d83' },
  { id: 'mint', label: '海风薄荷', seedLabel: '薄荷籽', stages: 2, value: 3, color: '#78b594' },
])

export const GARDEN_TOOLS = Object.freeze([
  { id: 'hoe', label: '锄地', hint: '把草地翻成可播种的土壤' },
  { id: 'seed', label: '播种', hint: '种下当前选择的种子' },
  { id: 'water', label: '浇水', hint: '浇水后会随照料行动成长' },
  { id: 'harvest', label: '收获', hint: '把成熟作物放进篮子' },
])

const blankPlot = () => ({ soil: 'grass', crop: '', stage: 0, growth: 0, watered: false })

export function createGardenLifeState() {
  return {
    plots: Array.from({ length: 9 }, blankPlot),
    selectedTool: 'hoe',
    selectedSeed: 'sunflower',
    seeds: { sunflower: 5, carrot: 4, berry: 3, mint: 5 },
    produce: { sunflower: 0, carrot: 0, berry: 0, mint: 0 },
    harvests: 0,
    coins: 12,
    actions: 0,
    day: 1,
    petHelpReady: true,
    order: { crop: 'sunflower', amount: 2, reward: 12 },
  }
}

const cropById = id => GARDEN_CROPS.find(crop => crop.id === id) || GARDEN_CROPS[0]
const clampInt = (value, min, max) => Math.min(max, Math.max(min, Math.floor(Number(value) || 0)))

export function normalizeGardenLifeState(saved = {}) {
  const base = createGardenLifeState()
  const plots = Array.isArray(saved.plots) && saved.plots.length === 9
    ? saved.plots.map(plot => {
      const crop = GARDEN_CROPS.some(item => item.id === plot?.crop) ? plot.crop : ''
      const maxStage = crop ? cropById(crop).stages : 0
      return {
        soil: ['grass', 'tilled'].includes(plot?.soil) ? plot.soil : 'grass',
        crop,
        stage: clampInt(plot?.stage, 0, maxStage),
        growth: clampInt(plot?.growth, 0, 2),
        watered: !!plot?.watered,
      }
    })
    : base.plots
  return {
    plots,
    selectedTool: GARDEN_TOOLS.some(tool => tool.id === saved.selectedTool) ? saved.selectedTool : 'hoe',
    selectedSeed: GARDEN_CROPS.some(crop => crop.id === saved.selectedSeed) ? saved.selectedSeed : 'sunflower',
    seeds: Object.fromEntries(GARDEN_CROPS.map(crop => [crop.id, clampInt(saved.seeds?.[crop.id] ?? base.seeds[crop.id], 0, 99)])),
    produce: Object.fromEntries(GARDEN_CROPS.map(crop => [crop.id, clampInt(saved.produce?.[crop.id], 0, 999)])),
    harvests: clampInt(saved.harvests, 0, 9999),
    coins: clampInt(saved.coins ?? base.coins, 0, 99999),
    actions: clampInt(saved.actions, 0, 99999),
    day: clampInt(saved.day || 1, 1, 9999),
    petHelpReady: saved.petHelpReady !== false,
    order: GARDEN_CROPS.some(crop => crop.id === saved.order?.crop)
      ? { crop: saved.order.crop, amount: clampInt(saved.order.amount, 1, 8), reward: clampInt(saved.order.reward, 3, 99) }
      : base.order,
  }
}

function growWateredPlots(state) {
  state.plots.forEach(plot => {
    if (!plot.crop || !plot.watered) return
    plot.growth += 1
    if (plot.growth >= 2) {
      plot.stage = Math.min(cropById(plot.crop).stages, plot.stage + 1)
      plot.growth = 0
      plot.watered = false
    }
  })
}

export function actOnGardenPlot(input, index, tool = input.selectedTool, seed = input.selectedSeed) {
  // Vue passes a reactive Proxy here. normalizeGardenLifeState already rebuilds
  // every nested collection, so it is also the safe clone boundary.
  const state = normalizeGardenLifeState(input)
  const plot = state.plots[index]
  if (!plot) return { state, changed: false, message: '这块地暂时无法照料。' }
  let message = ''
  let changed = false
  const crop = cropById(seed)
  if (tool === 'hoe') {
    if (plot.crop) message = '这里已经有作物，成熟后先收获。'
    else if (plot.soil === 'tilled') message = '这块土已经翻松，可以播种。'
    else { plot.soil = 'tilled'; changed = true; message = '土壤翻松了，接下来可以选种子播种。' }
  } else if (tool === 'seed') {
    if (plot.crop) message = '这里已经种着作物。'
    else if (plot.soil !== 'tilled') message = '先用锄头翻地，种子才住得下来。'
    else if (!state.seeds[crop.id]) message = `${crop.seedLabel}用完了，可以用收获换种子。`
    else {
      plot.crop = crop.id; plot.stage = 0; plot.growth = 0; plot.watered = false
      state.seeds[crop.id] -= 1; changed = true; message = `${crop.label}已经种下，下一步给它浇水。`
    }
  } else if (tool === 'water') {
    if (!plot.crop) message = '这里还没有作物。'
    else if (plot.stage >= cropById(plot.crop).stages) message = '已经成熟，可以收获了。'
    else if (plot.watered) message = '水分已经足够，再完成一次照料行动就会继续成长。'
    else { plot.watered = true; changed = true; message = '浇好水了。继续照料其他地块，作物会一起成长。' }
  } else if (tool === 'harvest') {
    if (!plot.crop) message = '这里还没有可收获的作物。'
    else if (plot.stage < cropById(plot.crop).stages) message = '它还在生长，先浇水并照料别的地块。'
    else {
      const harvested = plot.crop
      state.produce[harvested] += 1
      state.harvests += 1
      state.plots[index] = { ...blankPlot(), soil: 'tilled' }
      changed = true; message = `${cropById(harvested).label}收进篮子了，可以交订单或换种子。`
    }
  }
  if (changed) {
    state.actions += 1
    growWateredPlots(state)
    if (state.actions % 10 === 0) { state.day += 1; state.petHelpReady = true }
  }
  return { state, changed, message }
}

export function buyGardenSeeds(input, cropId) {
  const state = normalizeGardenLifeState(input)
  const crop = cropById(cropId)
  const price = Math.max(2, crop.value - 1)
  if (state.coins < price) return { state, changed: false, message: '岛币还不够，先完成订单或收获其他作物。' }
  state.coins -= price
  state.seeds[crop.id] += 2
  return { state, changed: true, message: `换到2颗${crop.seedLabel}。` }
}

export function fulfillGardenOrder(input) {
  const state = normalizeGardenLifeState(input)
  const { crop, amount, reward } = state.order
  if (state.produce[crop] < amount) return { state, changed: false, message: `还需要${amount - state.produce[crop]}份${cropById(crop).label}。` }
  state.produce[crop] -= amount
  state.coins += reward
  const nextIndex = (GARDEN_CROPS.findIndex(item => item.id === crop) + state.day + state.harvests) % GARDEN_CROPS.length
  const next = GARDEN_CROPS[nextIndex]
  state.order = { crop: next.id, amount: 2 + (state.day % 2), reward: next.value * 3 }
  return { state, changed: true, message: `订单完成，收到${reward}枚岛币。新的委托已经送到。` }
}

export function usePetGardenHelp(input) {
  const state = normalizeGardenLifeState(input)
  if (!state.petHelpReady) return { state, changed: false, message: '咕团今天已经帮过忙了，明天再一起照料。' }
  const targets = state.plots.filter(plot => plot.crop && plot.stage < cropById(plot.crop).stages)
  if (!targets.length) return { state, changed: false, message: '先种下一些作物，咕团才知道该帮哪一块。' }
  targets.forEach(plot => { plot.watered = true })
  state.petHelpReady = false
  state.actions += 1
  growWateredPlots(state)
  return { state, changed: true, message: `咕团跑过田埂，帮${targets.length}块地浇好了水。` }
}

export function gardenCrop(id) { return cropById(id) }
