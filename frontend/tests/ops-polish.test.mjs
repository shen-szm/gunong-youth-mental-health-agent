import assert from 'node:assert/strict'
import { readFile, stat } from 'node:fs/promises'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..')

async function source(path) {
  return readFile(join(root, path), 'utf8')
}

test('public source excludes production deployment details and uses a gated release workflow', async () => {
  await assert.rejects(stat(join(root, 'deploy-frontend.ps1')))
  const releaseInfo = await stat(join(root, 'scripts/release.ps1'))
  assert.ok(releaseInfo.isFile())

  const script = await source('scripts/release.ps1')
  assert.match(script, /verify-public-repo\.ps1/)
  assert.match(script, /\[switch\]\$Publish/)
  assert.match(script, /Release requires a clean worktree/)
  assert.doesNotMatch(script, /\bscp\b|\bsystemctl\b|\/opt\/shengyu/)
  assert.match(script, /github\.com/)
  assert.match(script, /gitee\.com/)
})

test('public verifier blocks sensitive output paths in the current tree and full history', async () => {
  const verifier = await source('scripts/verify-public-repo.ps1')
  for (const pathClass of ['logs?', 'output', 'tmp', 'release-archives', '\\\.codex-']) {
    assert.match(verifier, new RegExp(pathClass))
  }
  assert.match(verifier, /badHistoryPaths/)
  assert.match(verifier, /git ls-tree -r --name-only/)
})

test('mood insight remains local and guardian AI respects the global kill switch', async () => {
  const mood = await source('backend/api/mood.py')
  const guardian = await source('backend/guardian_engine.py')
  assert.match(mood, /local_descriptive_summary/)
  assert.doesNotMatch(mood, /ask_spark|record\.content|content\[:30\]/)
  assert.match(guardian, /not settings\.ALLOW_EXTERNAL_AI[\s\S]*?not settings\.ALLOW_GUARDIAN_EXTERNAL_AI/)
})

test('app exposes build metadata for visual deployment verification', async () => {
  const app = await source('frontend/src/App.vue')
  assert.match(app, /build-badge/)
  assert.match(app, /import\.meta\.env\.VITE_APP_VERSION/)
  assert.match(app, /import\.meta\.env\.VITE_BUILD_TIME/)
  assert.match(app, /console\.info\('\[咕哝\] build'/)
})

test('beian footer remains readable and compact on mobile screens', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')
  assert.match(room, /@media \(max-width: 520px\) \{[\s\S]*?\.beian-footer \{/)
  assert.match(room, /max-width:\s*calc\(100vw - 24px\)/)
  assert.match(room, /flex-wrap:\s*wrap/)
  assert.match(room, /env\(safe-area-inset-bottom\)/)
  assert.match(room, /font-size:\s*11px/)
})
