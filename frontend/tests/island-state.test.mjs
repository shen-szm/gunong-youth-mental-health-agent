import assert from 'node:assert/strict'
import test from 'node:test'

import {
  clampIslandPosition,
  islandStorageKey,
  loadIslandState,
  resolveIslandPhase,
  saveIslandState,
} from '../src/game/island/islandState.js'

function memoryStorage() {
  const data = new Map()
  return {
    getItem: key => data.get(key) ?? null,
    setItem: (key, value) => data.set(key, value),
  }
}

test('island state clamps movement and rejects damaged saves', () => {
  const edge = clampIslandPosition({ x: -999, y: 9999 })
  assert.deepEqual(edge, { x: 92, y: 506 })
  const storage = memoryStorage()
  storage.setItem(islandStorageKey('student-1'), '{broken')
  assert.deepEqual(loadIslandState('student-1', storage).position, { x: 480, y: 492 })
})

test('island resolves day, dusk and night deterministically', () => {
  assert.equal(resolveIslandPhase(8), 'day')
  assert.equal(resolveIslandPhase(18), 'dusk')
  assert.equal(resolveIslandPhase(23), 'night')
  assert.equal(resolveIslandPhase(4), 'night')
})

test('island saves are scoped per student and contain no emotion inference', () => {
  const storage = memoryStorage()
  saveIslandState('student-1', { position: { x: 250, y: 220 }, lastPlace: 'garden', timePhase: 'dusk' }, storage)
  saveIslandState('student-2', { position: { x: 700, y: 330 }, lastPlace: 'dock', timePhase: 'night' }, storage)
  assert.equal(loadIslandState('student-1', storage).lastPlace, 'garden')
  assert.equal(loadIslandState('student-1', storage).timePhase, 'dusk')
  assert.equal(loadIslandState('student-2', storage).lastPlace, 'dock')
  assert.notEqual(islandStorageKey('student-1'), islandStorageKey('student-2'))
  assert.deepEqual(Object.keys(loadIslandState('student-1', storage)).sort(), ['lastPlace', 'position', 'timePhase'])
})

test('island does not persist before a student identity is available', () => {
  const storage = memoryStorage()
  saveIslandState('', { position: { x: 250, y: 220 }, lastPlace: 'garden' }, storage)
  assert.equal(islandStorageKey(''), '')
  assert.equal(loadIslandState('', storage).lastPlace, 'home')
})
