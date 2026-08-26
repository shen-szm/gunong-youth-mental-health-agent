import { clampIslandPosition, ISLAND_WORLD } from './islandState.js'

export const ISLAND_NAV_GRID = 24

// The character's feet, rather than the full sprite, collide with the painted scenery.
export const ISLAND_BLOCKERS = Object.freeze([
  { id: 'home', x: 356, y: 188, width: 252, height: 176 },
  { id: 'greenhouse', x: 304, y: 34, width: 252, height: 126 },
  { id: 'exchange-tree', x: 72, y: 68, width: 230, height: 238 },
  { id: 'north-cliff', x: 574, y: 40, width: 112, height: 92 },
  { id: 'east-water', x: 846, y: 72, width: 96, height: 430 },
])

const pointInside = (point, rect, padding = 8) => (
  point.x > rect.x - padding && point.x < rect.x + rect.width + padding &&
  point.y > rect.y - padding && point.y < rect.y + rect.height + padding
)

const clampMovementPosition = position => ({
  x: Math.min(872, Math.max(92, Number(position?.x) || 92)),
  y: Math.min(506, Math.max(82, Number(position?.y) || 82)),
})

export function isIslandPositionWalkable(position) {
  const point = clampIslandPosition(position)
  return !ISLAND_BLOCKERS.some(rect => pointInside(point, rect))
}

export function resolveIslandMovement(current, proposed) {
  // Keep sub-pixel precision while walking. Rounding every frame can swallow
  // movement on high-refresh-rate displays where a single step is < 0.5 px.
  const start = clampMovementPosition(current)
  const target = clampMovementPosition(proposed)
  if (isIslandPositionWalkable(target)) return target
  const slideX = { x: target.x, y: start.y }
  if (isIslandPositionWalkable(slideX)) return slideX
  const slideY = { x: start.x, y: target.y }
  if (isIslandPositionWalkable(slideY)) return slideY
  return start
}

function gridPoint(position) {
  return {
    x: Math.round(position.x / ISLAND_NAV_GRID),
    y: Math.round(position.y / ISLAND_NAV_GRID),
  }
}

function worldPoint(cell) {
  return clampIslandPosition({ x: cell.x * ISLAND_NAV_GRID, y: cell.y * ISLAND_NAV_GRID })
}

const cellKey = cell => `${cell.x}:${cell.y}`
const cellInBounds = cell => {
  const x = cell.x * ISLAND_NAV_GRID
  const y = cell.y * ISLAND_NAV_GRID
  return x >= 92 && x <= 872 && y >= 82 && y <= 506
}

function nearestWalkableCell(position) {
  const origin = gridPoint(clampIslandPosition(position))
  if (isIslandPositionWalkable(worldPoint(origin))) return origin
  for (let radius = 1; radius <= 8; radius += 1) {
    for (let y = -radius; y <= radius; y += 1) {
      for (let x = -radius; x <= radius; x += 1) {
        if (Math.max(Math.abs(x), Math.abs(y)) !== radius) continue
        const candidate = { x: origin.x + x, y: origin.y + y }
        if (!cellInBounds(candidate)) continue
        if (isIslandPositionWalkable(worldPoint(candidate))) return candidate
      }
    }
  }
  return gridPoint({ x: ISLAND_WORLD.width / 2, y: ISLAND_WORLD.height - 48 })
}

function heuristic(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y)
}

export function findIslandPath(startPosition, targetPosition) {
  const start = nearestWalkableCell(startPosition)
  const goal = nearestWalkableCell(targetPosition)
  const open = [start]
  const openKeys = new Set([cellKey(start)])
  const cameFrom = new Map()
  const gScore = new Map([[cellKey(start), 0]])
  const directions = [
    [1, 0], [-1, 0], [0, 1], [0, -1],
    [1, 1], [1, -1], [-1, 1], [-1, -1],
  ]

  while (open.length) {
    open.sort((a, b) => (gScore.get(cellKey(a)) + heuristic(a, goal)) - (gScore.get(cellKey(b)) + heuristic(b, goal)))
    const current = open.shift()
    const currentKey = cellKey(current)
    openKeys.delete(currentKey)
    if (current.x === goal.x && current.y === goal.y) {
      const cells = [current]
      let cursorKey = currentKey
      while (cameFrom.has(cursorKey)) {
        const previous = cameFrom.get(cursorKey)
        cells.push(previous)
        cursorKey = cellKey(previous)
      }
      return cells.reverse().slice(1).map(worldPoint)
    }

    for (const [dx, dy] of directions) {
      const next = { x: current.x + dx, y: current.y + dy }
      if (!cellInBounds(next)) continue
      const nextWorld = worldPoint(next)
      if (!isIslandPositionWalkable(nextWorld)) continue
      if (dx && dy) {
        if (!isIslandPositionWalkable(worldPoint({ x: current.x + dx, y: current.y }))) continue
        if (!isIslandPositionWalkable(worldPoint({ x: current.x, y: current.y + dy }))) continue
      }
      const nextKey = cellKey(next)
      const tentative = (gScore.get(currentKey) || 0) + (dx && dy ? Math.SQRT2 : 1)
      if (tentative >= (gScore.get(nextKey) ?? Infinity)) continue
      cameFrom.set(nextKey, current)
      gScore.set(nextKey, tentative)
      if (!openKeys.has(nextKey)) {
        open.push(next)
        openKeys.add(nextKey)
      }
    }
  }
  return []
}
