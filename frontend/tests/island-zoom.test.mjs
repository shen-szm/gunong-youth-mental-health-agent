import assert from 'node:assert/strict'
import test from 'node:test'

import {
  anchoredIslandScroll,
  clampIslandScroll,
  clampIslandZoom,
  ISLAND_ZOOM,
  panIslandScroll,
} from '../src/game/island/islandZoom.js'
import { ISLAND_WORLD } from '../src/game/island/islandState.js'

const view = Object.freeze({ width: 960, height: 540 })

test('island zoom stays inside the readable range and falls back to 1x', () => {
  assert.equal(ISLAND_ZOOM.min, 1)
  assert.equal(ISLAND_ZOOM.max, 2.5)
  assert.equal(clampIslandZoom(1.6), 1.6)
  assert.equal(clampIslandZoom(0.2), 1)
  assert.equal(clampIslandZoom(9), 2.5)
  assert.equal(clampIslandZoom(Number.NaN), 1)
  assert.equal(clampIslandZoom('1.4'), 1.4)
})

test('island camera scroll is clamped to the world at every zoom level', () => {
  assert.deepEqual(
    clampIslandScroll({ scrollX: -20, scrollY: 900, zoom: 1, world: ISLAND_WORLD, view }),
    { scrollX: 0, scrollY: 0 },
  )
  assert.deepEqual(
    clampIslandScroll({ scrollX: 900, scrollY: -10, zoom: 2, world: ISLAND_WORLD, view }),
    { scrollX: 480, scrollY: 0 },
  )
  assert.deepEqual(
    clampIslandScroll({ scrollX: 240, scrollY: 135, zoom: 2, world: ISLAND_WORLD, view }),
    { scrollX: 240, scrollY: 135 },
  )
})

test('pinch keeps the anchor world point under the fingers while zooming', () => {
  const zoomed = anchoredIslandScroll({
    worldX: 480, worldY: 270, screenX: 480, screenY: 270, zoom: 2, world: ISLAND_WORLD, view,
  })
  assert.deepEqual(zoomed, { scrollX: 240, scrollY: 135 })
  assert.deepEqual(
    { x: (480 - zoomed.scrollX) * 2, y: (270 - zoomed.scrollY) * 2 },
    { x: 480, y: 270 },
  )
  const corner = anchoredIslandScroll({
    worldX: 100, worldY: 80, screenX: 480, screenY: 270, zoom: 2.5, world: ISLAND_WORLD, view,
  })
  assert.deepEqual(corner, { scrollX: 0, scrollY: 0 })
})

test('one-finger dragging pans the camera with the same direction as the finger', () => {
  const panned = panIslandScroll({
    scrollX: 240, scrollY: 135, deltaX: 30, deltaY: -16, zoom: 2, world: ISLAND_WORLD, view,
  })
  assert.deepEqual(panned, { scrollX: 225, scrollY: 143 })
  const edge = panIslandScroll({
    scrollX: 10, scrollY: 10, deltaX: 400, deltaY: 400, zoom: 2, world: ISLAND_WORLD, view,
  })
  assert.deepEqual(edge, { scrollX: 0, scrollY: 0 })
})
