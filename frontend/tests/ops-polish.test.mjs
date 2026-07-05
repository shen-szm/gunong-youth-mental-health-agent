import assert from 'node:assert/strict'
import { readFile, stat } from 'node:fs/promises'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..')

async function source(path) {
  return readFile(join(root, path), 'utf8')
}

test('local frontend deploy script builds, uploads and reloads the known Tencent Cloud target', async () => {
  const scriptPath = join(root, 'deploy-frontend.ps1')
  const info = await stat(scriptPath)
  assert.ok(info.isFile())

  const script = await source('deploy-frontend.ps1')
  assert.match(script, /npm\.cmd run build/)
  assert.match(script, /43\.136\.69\.47/)
  assert.match(script, /\/opt\/shengyu\/frontend\/dist/)
  assert.match(script, /scp/)
  assert.match(script, /sudo nginx -t/)
  assert.match(script, /sudo systemctl reload nginx/)
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
