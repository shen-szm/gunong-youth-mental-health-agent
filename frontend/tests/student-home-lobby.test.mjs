import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const room = fs.readFileSync(new URL('../src/views/RoomHomeView.vue', import.meta.url), 'utf8')
const template = room.slice(0, room.indexOf('<script setup>'))

test('student home renders a theme lobby in front of a generated scene', () => {
  assert.match(template, /class="room lobby-home"/)
  assert.match(template, /:data-part="timeOfDay"/)
  assert.doesNotMatch(template, /(?<![\w-])(?:room-bg|bg-wrap)(?![\w-])|<img[^>]*温馨房间/)
  assert.doesNotMatch(room, /电脑端-(?:白天|傍晚|夜晚)|白天\.webp|夜晚\.webp/)
  assert.doesNotMatch(room, /\.bottom-nav|\.bnav-/)
  assert.match(room, /--lobby-scene: url\('\/images\/lobby\/lobby-scene-day\.svg'\)/)
})

test('home background assets are removed from public and build scripts', () => {
  for (const asset of ['电脑端-白天.webp', '电脑端-傍晚.webp', '电脑端-夜晚.webp', '白天.webp', '夜晚.webp', '白天.png', '夜晚.png']) {
    assert.ok(!fs.existsSync(new URL(`../public/images/${asset}`, import.meta.url)), `${asset} should be deleted`)
  }
  const optimizer = fs.readFileSync(new URL('../../scripts/optimize_web_assets.py', import.meta.url), 'utf8')
  assert.doesNotMatch(optimizer, /电脑端|白天|夜晚/)
})

test('home chat panel shows the guguan companion instead of the book logo', () => {
  assert.doesNotMatch(room, /logo\.jpg/)
  assert.ok((room.match(/:src="selectedPetFrame"/g) || []).length >= 5,
    'header, welcome, messages, typing row and summary orb reuse the guguan frame')
  assert.match(room, /\.ai-logo \{[\s\S]*?object-fit: contain[\s\S]*?image-rendering: pixelated/)
})

test('lobby exposes one oversized confession CTA and four large cards', () => {
  assert.equal((template.match(/class="lobby-card /g) || []).length, 4)
  assert.match(template, /class="lobby-grid"/)
  assert.match(template, /class="lobby-primary-cta"/)
  const ctaRule = room.match(/\.lobby-primary-cta \{([\s\S]*?)\}/)[1]
  const minHeight = Number(ctaRule.match(/min-height:\s*(\d+)px/)[1])
  assert.ok(minHeight >= 60, `CTA min-height ${minHeight}px must be at least 60px`)
  assert.match(room, /@media \(max-width: 760px\)[\s\S]*?\.lobby-primary-cta \{[\s\S]*?min-height: 62px/)
  assert.match(room, /\.lobby-grid \{[\s\S]*?grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)/)
  assert.match(room, /\.lobby-card \{[\s\S]*?min-height: 132px/)
})

test('daily card keeps check-in wiring and the guide badge targets the CTA', () => {
  assert.match(template, /class="lobby-card lobby-card-daily room-status-checkin"/)
  assert.match(template, /selectRoomFeature\('daily', \$event\)/)
  assert.match(template, /<button ref="chatNavButton"[^>]*class="lobby-primary-cta"[\s\S]*?guide-target-badge[\s\S]*?<\/button>/)
  assert.match(template, /aria-label="摸摸咕团，和它玩一下"/)
  assert.match(template, /class="beian-footer"/)
})

test('home hero pet reacts to taps with a visible pixel flourish', () => {
  assert.match(template, /class="lobby-pet-stage"/)
  assert.match(template, /@click="petGuguanHome"/)
  assert.match(template, /class="lobby-pet-reaction"/)
  assert.match(template, /class="lobby-card lobby-card-pet"[\s\S]*?openWorkspacePanel\('pet', \$event\.currentTarget\)/)
  assert.match(room, /function petGuguanHome\(event\)/)
  assert.match(room, /petReactionTimer = setTimeout/)
  assert.match(room, /if \(petReactionTimer\) clearTimeout\(petReactionTimer\)/)
  assert.match(room, /@keyframes lobby-pet-heart/)
  assert.match(room, /@keyframes lobby-pet-halo-pop/)
  assert.match(room, /prefers-reduced-motion: reduce[\s\S]*?animation: none !important/)
})

test('lobby layers generated pixel scenes under gradients and hairlines', () => {
  const lobbyCss = room.slice(room.indexOf('主题大厅 3.1'))
  assert.match(lobbyCss, /radial-gradient/)
  assert.match(lobbyCss, /repeating|linear-gradient/)
  assert.match(lobbyCss, /--lobby-scene: url\('\/images\/lobby\/lobby-scene-evening\.svg'\)/)
  assert.match(lobbyCss, /--lobby-scene: url\('\/images\/lobby\/lobby-scene-night\.svg'\)/)
  assert.match(lobbyCss, /background-size: auto, auto, auto, cover/)
  const sceneUrls = [...lobbyCss.matchAll(/url\('([^']+)'\)/g)].map((match) => match[1])
  assert.equal(sceneUrls.length, 3)
  for (const sceneUrl of sceneUrls) {
    assert.match(sceneUrl, /^\/images\/lobby\/lobby-scene-(day|evening|night)\.svg$/)
    const svg = fs.readFileSync(new URL(`../public${sceneUrl}`, import.meta.url), 'utf8')
    assert.match(svg, /viewBox="0 0 1600 1000"/)
    assert.match(svg, /shape-rendering="crispEdges"/)
  }
  assert.doesNotMatch(lobbyCss, /\.(?:webp|png|jpe?g)\b/i)
  assert.match(lobbyCss, /\.lobby-home\.day \{[\s\S]*?--lobby-bg: #f7f1e7/)
  assert.match(lobbyCss, /\.lobby-home\.evening \{[\s\S]*?--lobby-bg: #211713/)
  assert.match(lobbyCss, /\.lobby-home\.night \{[\s\S]*?--lobby-bg: #130f0d/)
})

test('lobby background animates with drifting pixel clouds, stars and fireflies', () => {
  assert.match(template, /class="lobby-ambient" aria-hidden="true"/)
  assert.match(template, /class="ambient-clouds"/)
  assert.match(template, /class="ambient-cloud ambient-cloud-a"/)
  assert.match(room, /\.ambient-clouds \{[\s\S]*?mask-image: linear-gradient\(90deg, #000 0 30%, transparent 40% 60%, #000 70% 100%\)/)
  assert.match(template, /class="ambient-stars"[\s\S]*?v-for="n in 14"/)
  assert.match(template, /class="ambient-fireflies"[\s\S]*?v-for="n in 6"/)
  assert.match(template, /class="ambient-shooting-star"/)
  assert.match(room, /\.lobby-ambient \{[\s\S]*?position: fixed[\s\S]*?pointer-events: none/)
  assert.match(room, /@keyframes lobby-cloud-drift/)
  assert.match(room, /@keyframes lobby-star-twinkle/)
  assert.match(room, /@keyframes lobby-firefly-drift/)
  assert.match(room, /@keyframes lobby-shooting-star/)
  assert.match(room, /@keyframes lobby-ambient-breathe/)
  assert.equal((room.match(/--lobby-ambient-star:/g) || []).length, 3)
  assert.match(room, /@media \(max-width: 760px\) \{\s*\.ambient-cloud-b,[\s\S]*?display: none/)
  assert.match(room, /prefers-reduced-motion: reduce[\s\S]*?\.lobby-ambient \{\s*display: none/)
})

test('celestial layer follows the real sun and lunar phase', () => {
  assert.match(template, /class="lobby-celestial"[\s\S]*?viewBox="0 0 1600 1000"[\s\S]*?preserveAspectRatio="xMidYMax slice"/)
  assert.match(template, /v-for="\(cell, index\) in celestialState\.rects"/)
  assert.match(room, /const SYNODIC_MONTH = 29\.530588853/)
  assert.match(room, /const NEW_MOON_EPOCH = Date\.UTC\(2000, 0, 6, 18, 14\)/)
  assert.match(room, /function moonLitRows\(radius, step, phase, fill, opacity\)/)
  assert.match(room, /const celestialState = computed\(\(\) => \{[\s\S]*?hour >= 6 && hour < 18[\s\S]*?moonLitRows\(110, 9, phase/)
  assert.match(room, /celestialNow\.value = now/)
  assert.match(room, /\.lobby-celestial \{[\s\S]*?position: fixed[\s\S]*?pointer-events: none/)
  for (const theme of ['day', 'evening', 'night']) {
    const svg = fs.readFileSync(new URL(`../public/images/lobby/lobby-scene-${theme}.svg`, import.meta.url), 'utf8')
    assert.doesNotMatch(svg, /#f3d69d|#ecb06a|#f2e3c0|#d8a967|#c98a4e|#cba968/, `${theme} scene must not bake a sun or moon`)
  }
  const generator = fs.readFileSync(new URL('../scripts/gen_lobby_scenes.py', import.meta.url), 'utf8')
  assert.match(generator, /日月由首页动态天象层绘制/)
})

test('pixel accents stay a warm layered skin, not a NES.css skin swap', () => {
  assert.match(room, /--lobby-pixel-font: 'Fusion Pixel Lobby'/)
  assert.match(room, /\.lobby-title \{[\s\S]*?font-family: var\(--lobby-pixel-font\)[\s\S]*?font-size: 48px/)
  assert.match(room, /\.lobby-primary-cta \{[\s\S]*?box-shadow:\s*0 6px 0 var\(--lobby-cta-shadow\)/)
  assert.match(room, /\.lobby-cta-label \{[\s\S]*?font-size: 24px/)
  assert.match(room, /\.lobby-card \{[\s\S]*?box-shadow: 4px 4px 0 var\(--lobby-pixel-shadow\)/)
  assert.match(room, /outline: 3px dashed var\(--lobby-gold\)/)
  assert.match(room, /\.lobby-card\.room-status-checkin:hover \{[\s\S]*?box-shadow: 6px 6px 0 var\(--lobby-pixel-shadow\)/)
  assert.match(room, /\.lobby-hello time \{[\s\S]*?font-family: var\(--lobby-pixel-font\)/)
  assert.match(room, /\.lobby-home \.room-onboarding-step \{[\s\S]*?font-family: var\(--lobby-pixel-font\)/)
  assert.match(room, /\.lobby-card::before \{[\s\S]*?left top \/ 5px 5px no-repeat/)
  assert.match(room, /\.lobby-hero::before,[\s\S]*?animation: lobby-pixel-twinkle 2\.8s steps\(2, end\)/)
  assert.match(room, /\.lobby-pill::before \{[\s\S]*?background: var\(--lobby-gold\)/)
  assert.match(room, /\.lobby-home \.splash-logo > span:first-child \{[\s\S]*?font-size: 48px/)
  const css = fs.readFileSync(new URL('../src/style.css', import.meta.url), 'utf8')
  assert.match(css, /font-family: 'Fusion Pixel Lobby'/)
  const font = fs.statSync(new URL('../src/assets/fonts/fusion-pixel-sc-lobby.woff2', import.meta.url))
  assert.ok(font.size < 10 * 1024, `pixel subset ${font.size} bytes should stay small`)
})
