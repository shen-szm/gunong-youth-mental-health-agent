import assert from 'node:assert/strict'
import { readFile, stat } from 'node:fs/promises'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..')

async function source(path) {
  return readFile(join(root, path), 'utf8')
}

test('first-run guide requires a chat confession before completion', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /guideStage = ref\('computer'\)/)
  assert.match(room, /handleGuideChatTarget/)
  assert.match(room, /guideStage\.value = 'confession'/)
  assert.match(room, /completeFirstRunAfterChat/)
  assert.match(room, /guideStage\.value = 'mood-card'/)
  assert.match(room, /localStorage\.setItem\(FIRST_RUN_GUIDE_KEY, FIRST_RUN_GUIDE_VERSION\)/)
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

test('window hotspot label is hidden until hover and uses subtle copy', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.doesNotMatch(room, />出去看看</)
  assert.doesNotMatch(room, /<h2>[^<]*出去看看<\/h2>/)
  assert.doesNotMatch(room, />窗外有新风景</)
  assert.match(room, />看看窗外</)
  assert.match(room, /\.window-label \{[\s\S]*?opacity:\s*0/)
  assert.match(room, /\.zone-window:hover \.window-label \{[\s\S]*?opacity:\s*1/)
})

test('small release continues from latest 4.3.0 baseline and records changelog', async () => {
  const pkg = JSON.parse(await source('frontend/package.json'))
  const lock = JSON.parse(await source('frontend/package-lock.json'))
  const changelogPath = join(root, 'CHANGELOG.md')
  const info = await stat(changelogPath)
  assert.ok(info.isFile())
  const changelog = await source('CHANGELOG.md')

  assert.equal(pkg.version, '4.3.1')
  assert.equal(lock.version, '4.3.1')
  assert.equal(lock.packages[''].version, '4.3.1')
  assert.match(changelog, /## \[4\.3\.0\] - 2026-07-06/)
  assert.match(changelog, /4\.2\.5 -> 4\.3\.0/)
})

test('deploy script publishes semantic version plus git commit for visible build badge', async () => {
  const script = await source('deploy-frontend.ps1')

  assert.match(script, /package\.json/)
  assert.match(script, /VITE_APP_VERSION = "\$pkgVersion\+\$gitSha"/)
})
test('splash version uses build metadata instead of a hard-coded badge', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')
  const vite = await source('frontend/vite.config.js')

  assert.match(room, /V\{\{ splashVersion \}\}/)
  assert.match(room, /import\.meta\.env\.VITE_APP_VERSION/)
  assert.doesNotMatch(room, /<span class="splash-version">V\d+\.\d+/)
  assert.match(vite, /package\.json/)
  assert.match(vite, /__APP_PACKAGE_VERSION__/)
})
