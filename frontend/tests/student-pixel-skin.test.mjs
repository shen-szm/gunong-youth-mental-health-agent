import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const testDir = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(testDir, '..', '..')

async function source(relativePath) {
  return readFile(path.join(projectRoot, relativePath), 'utf8')
}

const studentPixelFiles = [
  'frontend/src/App.vue',
  'frontend/src/views/StudentChatView.vue',
  'frontend/src/views/TrendView.vue',
  'frontend/src/views/ProfileView.vue',
  'frontend/src/views/TreeHoleView.vue',
  'frontend/src/views/HealingView.vue',
  'frontend/src/views/RoomHomeView.vue',
  'frontend/src/components/RoomActionBar.vue',
  'frontend/src/components/StudentAgentRail.vue',
  'frontend/src/components/StudentScreeningCard.vue',
  'frontend/src/components/StudentWellbeingAssessment.vue',
  'frontend/src/components/StudentLeisureHub.vue',
  'frontend/src/components/MusicListeningShelf.vue',
  'frontend/src/components/student/MoodRecordSheet.vue',
  'frontend/src/components/island/StudentIslandWorkspace.vue',
  'frontend/src/components/island/IslandPetHome.vue',
  'frontend/src/components/island/IslandBreathingRoom.vue',
  'frontend/src/components/island/IslandTidalBeach.vue',
  'frontend/src/components/island/IslandFishingGame.vue',
  'frontend/src/components/island/IslandHappinessExchange.vue',
  'frontend/src/components/island/IslandGardenGame.vue',
]

const nonStudentFiles = [
  'frontend/src/views/LoginView.vue',
  'frontend/src/views/AdminView.vue',
  'frontend/src/views/GuardianHomeView.vue',
  'frontend/src/views/GuardianCaseView.vue',
  'frontend/src/views/GuardianFollowUpsView.vue',
  'frontend/src/views/GuardianIntakeView.vue',
]

const marker = /\/\* 像素皮肤 3\.0/

function block(css, selector) {
  const match = css.match(new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\\{([\\s\\S]*?)\\}`))
  assert.ok(match, `${selector} block exists`)
  return match[1]
}

test('student pixel font is declared with swap and shared tokens', async () => {
  const css = await source('frontend/src/style.css')

  const face = css.match(/@font-face\s*\{([\s\S]*?)\}/g)?.find(entry => entry.includes("'Fusion Pixel Student'"))
  assert.ok(face, 'Fusion Pixel Student @font-face exists')
  assert.match(face, /fusion-pixel-sc-student\.woff2/)
  assert.match(face, /format\('woff2'\)/)
  assert.match(face, /font-display:\s*swap/)

  assert.match(css, /--px-font:\s*'Fusion Pixel Student'/)
  assert.match(css, /--px-gold:\s*#b07a45/)
  assert.match(css, /--px-line:\s*rgba\(90, 62, 38, \.28\)/)
  assert.match(css, /--px-shadow:\s*rgba\(74, 52, 32, \.28\)/)
  assert.match(css, /--px-hard-lg:\s*4px 4px 0 var\(--px-shadow\)/)
  assert.match(css, /--px-hard-sm:\s*3px 3px 0 var\(--px-shadow\)/)

  // 共享 --m-radius 仍服务登录页，像素重映射只能放在 .game-page 内。
  assert.match(css, /--m-radius-lg:\s*18px/)
  assert.match(css, /--m-radius-md:\s*12px/)
  assert.match(css, /--m-radius-sm:\s*8px/)
  assert.doesNotMatch(css, /--m-radius-lg:\s*6px/)
})

test('student pixel font subset is a small woff2 asset', async () => {
  const font = await readFile(path.join(projectRoot, 'frontend/src/assets/fonts/fusion-pixel-sc-student.woff2'))
  assert.equal(font.subarray(0, 4).toString('latin1'), 'wOF2')
  assert.ok(font.length >= 20000 && font.length <= 64000, `subset is ${font.length} bytes`)
})

test('game-page themes remap radii and expose day/evening/night pixel tokens', async () => {
  const css = await source('frontend/src/styles/game-theme.css')

  const base = block(css, '.game-page')
  assert.match(base, /--m-radius-lg:\s*6px/)
  assert.match(base, /--m-radius-md:\s*4px/)
  assert.match(base, /--m-radius-sm:\s*3px/)
  assert.match(base, /--px-line:\s*rgba\(90, 62, 38, 0\.28\)/)
  assert.match(base, /--px-gold:\s*#b07a45/)
  assert.match(base, /--px-shadow:\s*rgba\(74, 52, 32, 0\.22\)/)

  const evening = block(css, '.game-page[data-part="evening"]')
  assert.match(evening, /--px-line:\s*rgba\(226, 192, 132, 0\.30\)/)
  assert.match(evening, /--px-gold:\s*#e2c084/)
  assert.match(evening, /--px-shadow:\s*rgba\(0, 0, 0, 0\.45\)/)

  const night = block(css, '.game-page[data-part="night"]')
  assert.match(night, /--px-line:\s*rgba\(227, 194, 125, 0\.28\)/)
  assert.match(night, /--px-gold:\s*#e3c27d/)
  assert.match(night, /--px-shadow:\s*rgba\(0, 0, 0, 0\.5\)/)

  const card = block(css, '.game-card')
  assert.match(card, /border:\s*2px solid var\(--px-line/)
  assert.match(card, /border-radius:\s*6px/)
  assert.match(card, /box-shadow:\s*4px 4px 0 var\(--px-shadow/)

  const pill = block(css, '.game-pill')
  assert.match(pill, /border:\s*2px solid var\(--px-line/)
  assert.match(pill, /border-radius:\s*4px/)
  assert.match(pill, /font-family:\s*var\(--px-font\)/)
})

test('every student surface carries the pixel-skin layer', async () => {
  for (const file of studentPixelFiles) {
    const content = await source(file)
    assert.match(content, marker, `${file} has the pixel-skin marker`)
    assert.match(content, /var\(--px-/, `${file} consumes pixel tokens`)
  }
})

test('teacher, guardian and login surfaces stay off the pixel skin', async () => {
  for (const file of nonStudentFiles) {
    const content = await source(file)
    assert.doesNotMatch(content, marker, `${file} has no pixel-skin marker`)
    assert.doesNotMatch(content, /--px-(font|gold|line|shadow)/, `${file} references no pixel tokens`)
  }
})

test('pixel layer keeps guarded student constraints', async () => {
  const chat = await source('frontend/src/views/StudentChatView.vue')
  assert.equal(chat.includes('backdrop-filter'), false, 'chat page stays glass-free')

  const app = await source('frontend/src/App.vue')
  assert.match(app, /class="nav-item nav-sound"/)
  assert.match(app, /#f0d29a/)

  const rail = await source('frontend/src/components/StudentAgentRail.vue')
  assert.match(rail, /@media \(min-width: 900px\) and \(max-width: 1087px\) \{\s*\.student-agent-toggle \{ width: 188px; \}/)
  assert.match(rail, /@media \(min-width: 900px\) and \(max-width: 1235px\) \{\s*\.student-agent-shell\.is-open \.student-agent-rail \{ width: 320px; \}/)
  assert.match(rail, /backdrop-filter: blur\(20px\) saturate\(1\.08\)/)
  assert.match(rail, /backdrop-filter: blur\(26px\) saturate\(1\.06\)/)
  assert.match(rail, /\.agent-step-list::before/)

  const home = await source('frontend/src/views/RoomHomeView.vue')
  assert.match(home, /rgba\(18, 21, 27, \.96\)/)
  assert.match(home, /\.music-panel\{border-radius:6px!important\}/)
})

test('pixel layer adds no new !important rules outside reduced-motion guards', async () => {
  for (const file of studentPixelFiles) {
    const content = await source(file)
    const start = content.search(marker)
    assert.ok(start >= 0, `${file} has the pixel-skin marker`)
    const appended = content.slice(start)
    const reducedMotion = appended.search(/@media\s*\(prefers-reduced-motion/)
    const authored = reducedMotion >= 0 ? appended.slice(0, reducedMotion) : appended
    assert.equal(authored.includes('!important'), false, `${file} pixel block avoids !important`)
  }
})
