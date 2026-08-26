/*
 * Garden merge engine adapted from the traversal / single-merge rules in
 * Gabriele Cirulli's 2048 (MIT): https://github.com/gabrielecirulli/2048
 * The numeric board, product vocabulary and persistence contract are specific
 * to Heart Island. See THIRD_PARTY_NOTICES.md for the full attribution.
 */

export const GARDEN_SIZE = 4
export const GARDEN_MAX_TIER = 6

export const GARDEN_CROPS = Object.freeze([
  { tier: 1, label: '嫩芽', mark: '芽' },
  { tier: 2, label: '香草', mark: '草' },
  { tier: 3, label: '雏菊', mark: '花' },
  { tier: 4, label: '金瓜', mark: '瓜' },
  { tier: 5, label: '暖阳花', mark: '阳' },
  { tier: 6, label: '心光果', mark: '光' },
])

const emptyBoard = () => Array(GARDEN_SIZE * GARDEN_SIZE).fill(0)
const cloneBoard = board => board.slice(0, GARDEN_SIZE * GARDEN_SIZE)
const indexOf = (row, column) => row * GARDEN_SIZE + column

function emptyIndexes(board) {
  const result = []
  board.forEach((value, index) => { if (!value) result.push(index) })
  return result
}

export function addGardenSeed(board, random = Math.random) {
  const next = cloneBoard(board)
  const empty = emptyIndexes(next)
  if (!empty.length) return next
  const slot = empty[Math.min(empty.length - 1, Math.floor(random() * empty.length))]
  next[slot] = random() < 0.88 ? 1 : 2
  return next
}

export function createGardenBoard(random = Math.random) {
  return addGardenSeed(addGardenSeed(emptyBoard(), random), random)
}

function collapseLine(line) {
  const values = line.filter(Boolean)
  const result = []
  let gained = 0
  let merges = 0
  for (let cursor = 0; cursor < values.length; cursor += 1) {
    const current = values[cursor]
    if (current === values[cursor + 1]) {
      const merged = Math.min(GARDEN_MAX_TIER, current + 1)
      result.push(merged)
      gained += 2 ** merged
      merges += 1
      cursor += 1
    } else {
      result.push(current)
    }
  }
  while (result.length < GARDEN_SIZE) result.push(0)
  return { line: result, gained, merges }
}

function readLine(board, lineIndex, direction) {
  const horizontal = direction === 'left' || direction === 'right'
  const reverse = direction === 'right' || direction === 'down'
  const line = []
  for (let offset = 0; offset < GARDEN_SIZE; offset += 1) {
    const position = reverse ? GARDEN_SIZE - 1 - offset : offset
    const row = horizontal ? lineIndex : position
    const column = horizontal ? position : lineIndex
    line.push(board[indexOf(row, column)])
  }
  return line
}

function writeLine(board, lineIndex, direction, line) {
  const horizontal = direction === 'left' || direction === 'right'
  const reverse = direction === 'right' || direction === 'down'
  for (let offset = 0; offset < GARDEN_SIZE; offset += 1) {
    const position = reverse ? GARDEN_SIZE - 1 - offset : offset
    const row = horizontal ? lineIndex : position
    const column = horizontal ? position : lineIndex
    board[indexOf(row, column)] = line[offset]
  }
}

export function moveGarden(board, direction, random = Math.random) {
  if (!['up', 'right', 'down', 'left'].includes(direction)) {
    return { board: cloneBoard(board), moved: false, gained: 0, merges: 0 }
  }
  const source = cloneBoard(board)
  const next = cloneBoard(board)
  let gained = 0
  let merges = 0
  for (let lineIndex = 0; lineIndex < GARDEN_SIZE; lineIndex += 1) {
    const collapsed = collapseLine(readLine(source, lineIndex, direction))
    writeLine(next, lineIndex, direction, collapsed.line)
    gained += collapsed.gained
    merges += collapsed.merges
  }
  const moved = next.some((value, index) => value !== source[index])
  return { board: moved ? addGardenSeed(next, random) : next, moved, gained, merges }
}

export function canMoveGarden(board) {
  if (emptyIndexes(board).length) return true
  for (let row = 0; row < GARDEN_SIZE; row += 1) {
    for (let column = 0; column < GARDEN_SIZE; column += 1) {
      const value = board[indexOf(row, column)]
      if (column + 1 < GARDEN_SIZE && value === board[indexOf(row, column + 1)]) return true
      if (row + 1 < GARDEN_SIZE && value === board[indexOf(row + 1, column)]) return true
    }
  }
  return false
}

export function harvestGarden(board) {
  const next = cloneBoard(board)
  const highest = Math.max(...next)
  if (highest < 5) return { board: next, harvested: false, tier: highest }
  const index = next.indexOf(highest)
  next[index] = 0
  return { board: addGardenSeed(next), harvested: true, tier: highest }
}

export function normalizeGardenBoard(value) {
  if (!Array.isArray(value) || value.length !== GARDEN_SIZE * GARDEN_SIZE) return createGardenBoard()
  return value.map(item => Math.max(0, Math.min(GARDEN_MAX_TIER, Math.floor(Number(item) || 0))))
}
