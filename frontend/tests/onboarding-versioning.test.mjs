import assert from 'node:assert/strict'
import { readFile, stat } from 'node:fs/promises'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..')

async function source(path) {
  return readFile(join(root, path), 'utf8')
}

test('first-run guide nudges visitors to complete an action before disappearing', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /completeFirstRunGuide\('chat'\)/)
  assert.match(room, /completeFirstRunGuide\('treehole'\)/)
  assert.match(room, /稍后再说/)
  assert.match(room, /guide-secondary/)
  assert.match(room, /guide-option-grid/)
  assert.match(room, /localStorage\.setItem\(FIRST_RUN_GUIDE_KEY, '1'\)/)
})

test('daily ritual card has richer visual hierarchy and action categories', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /ritual-orb/)
  assert.match(room, /ritual-meta-row/)
  assert.match(room, /ritual-chip/)
  assert.match(room, /倾诉/)
  assert.match(room, /共鸣/)
  assert.match(room, /治愈/)
})

test('window hotspot copy is softened instead of showing blunt outing text', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.doesNotMatch(room, />出去看看</)
  assert.match(room, /窗外有新风景/)
})

test('small release increments patch version and records changelog', async () => {
  const pkg = JSON.parse(await source('frontend/package.json'))
  const lock = JSON.parse(await source('frontend/package-lock.json'))
  const changelogPath = join(root, 'CHANGELOG.md')
  const info = await stat(changelogPath)
  assert.ok(info.isFile())
  const changelog = await source('CHANGELOG.md')

  assert.equal(pkg.version, '3.2.1')
  assert.equal(lock.version, '3.2.1')
  assert.equal(lock.packages[''].version, '3.2.1')
  assert.match(changelog, /## \[3\.2\.1\] - 2026-07-06/)
  assert.match(changelog, /小更新/)
})

test('deploy script publishes semantic version plus git commit for visible build badge', async () => {
  const script = await source('deploy-frontend.ps1')

  assert.match(script, /package\.json/)
  assert.match(script, /VITE_APP_VERSION = "\$pkgVersion\+\$gitSha"/)
})
