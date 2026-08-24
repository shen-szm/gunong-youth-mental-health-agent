import assert from 'node:assert/strict'
import test from 'node:test'

import {
  clampIslandPosition,
  islandStorageKey,
  loadIslandState,
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
  const normalized = ((edge.x - 480) / 322) ** 2 + ((edge.y - 282) / 142) ** 2
  assert.ok(normalized <= 1.01)
  const storage = memoryStorage()
  storage.setItem(islandStorageKey('student-1'), '{broken')
  assert.deepEqual(loadIslandState('student-1', storage).position, { x: 480, y: 398 })
})

test('island saves are scoped per student and contain no emotion inference', () => {
  const storage = memoryStorage()
  saveIslandState('student-1', { position: { x: 250, y: 220 }, lastPlace: 'garden' }, storage)
  saveIslandState('student-2', { position: { x: 700, y: 330 }, lastPlace: 'dock' }, storage)
  assert.equal(loadIslandState('student-1', storage).lastPlace, 'garden')
  assert.equal(loadIslandState('student-2', storage).lastPlace, 'dock')
  assert.notEqual(islandStorageKey('student-1'), islandStorageKey('student-2'))
  assert.deepEqual(Object.keys(loadIslandState('student-1', storage)).sort(), ['lastPlace', 'position'])
})

test('island does not persist before a student identity is available', () => {
  const storage = memoryStorage()
  saveIslandState('', { position: { x: 250, y: 220 }, lastPlace: 'garden' }, storage)
  assert.equal(islandStorageKey(''), '')
  assert.equal(loadIslandState('', storage).lastPlace, 'home')
})
