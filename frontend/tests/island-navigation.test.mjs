import assert from 'node:assert/strict'
import test from 'node:test'

import { findIslandPath, isIslandPositionWalkable, resolveIslandMovement } from '../src/game/island/islandNavigation.js'
import { ISLAND_PLACES, ISLAND_SPAWN } from '../src/game/island/islandState.js'

test('heart island supports free two-dimensional movement with scenery collision', () => {
  assert.equal(isIslandPositionWalkable({ x: 480, y: 270 }), false)
  assert.equal(isIslandPositionWalkable({ x: 480, y: 470 }), true)
  const slid = resolveIslandMovement({ x: 350, y: 400 }, { x: 400, y: 330 })
  assert.deepEqual(slid, { x: 400, y: 400 })
  const subPixelStep = resolveIslandMovement({ x: 480, y: 492 }, { x: 480.24, y: 491.68 })
  assert.deepEqual(subPixelStep, { x: 480.24, y: 491.68 })
})

test('click navigation routes around scenery instead of moving on one straight line', () => {
  const start = { x: 480, y: 492 }
  const path = findIslandPath(start, { x: 580, y: 174 })
  assert.ok(path.length > 4)
  assert.ok(path.every(isIslandPositionWalkable))
  const slopes = new Set(path.slice(1).map((point, index) => {
    const previous = path[index]
    return `${Math.sign(point.x - previous.x)}:${Math.sign(point.y - previous.y)}`
  }))
  assert.ok(slopes.size > 1)
})

test('all five activity entrances are reachable from the island spawn', () => {
  for (const place of ISLAND_PLACES) {
    const path = findIslandPath(ISLAND_SPAWN, place)
    assert.ok(path.length, `${place.label} should have a route`)
    assert.ok(path.every(isIslandPositionWalkable), `${place.label} route should stay walkable`)
  }
})
