import Phaser from 'phaser'
import { clampIslandPosition, ISLAND_PHASES, ISLAND_PLACES, ISLAND_WORLD, normalizeIslandPhase } from './islandState.js'
import { anchoredIslandScroll, clampIslandScroll, clampIslandZoom, ISLAND_ZOOM, panIslandScroll } from './islandZoom.js'
import { findIslandPath, resolveIslandMovement } from './islandNavigation.js'

const PHASE_LIGHTING = Object.freeze({
  day: { tint: 0xfff4df, veil: 0xffd8a6, veilAlpha: 0.02, lamps: 0.05, windows: 0, fire: 0.3, stars: 0, glints: 1 },
  dusk: { tint: 0xffc8a8, veil: 0x8d4d54, veilAlpha: 0.16, lamps: 0.55, windows: 0.55, fire: 0.8, stars: 0.22, glints: 0.8 },
  night: { tint: 0xd2a6b1, veil: 0x38213c, veilAlpha: 0.46, lamps: 1, windows: 1, fire: 1, stars: 0.9, glints: 0.5 },
})

const WINDOW_GLOWS = Object.freeze([
  [436, 319, 44, 26], [528, 319, 44, 26], [482, 242, 24, 18],
  [430, 126, 30, 26], [500, 126, 26, 22],
])

const STUDENT_FRAME = Object.freeze({ width: 40, height: 56 })
const STUDENT_COLUMNS = 6
const STUDENT_ROWS = Object.freeze({ down: 0, up: 1, side: 2 })
const STUDENT_WALK_FPS = 8
const STUDENT_IDLE_FPS = 1.3
const PATH_SPEED = 0.15
const MANUAL_SPEED = 0.17

const LAMP_POINTS = Object.freeze([
  [137, 352], [252, 387], [365, 405], [472, 385], [574, 330], [668, 275],
  [748, 242], [721, 158], [602, 138], [532, 184], [335, 280], [190, 292],
])

const STAR_POINTS = Object.freeze([
  [78, 42, 2], [142, 82, 1], [232, 45, 2], [309, 74, 1], [556, 48, 1],
  [636, 70, 2], [762, 45, 1], [846, 80, 2], [906, 39, 1], [28, 128, 1],
  [920, 176, 2], [880, 318, 1], [928, 372, 1], [40, 480, 2], [896, 498, 1],
])

const WATER_GLINTS = Object.freeze([
  [880, 178, 4], [902, 206, 3], [866, 232, 5], [918, 252, 2], [888, 286, 4],
  [928, 310, 3], [856, 356, 4], [910, 372, 5], [882, 404, 3], [930, 430, 2],
  [868, 462, 4], [120, 526, 4], [200, 532, 3], [300, 524, 5], [420, 534, 3],
  [560, 530, 4], [680, 526, 3], [780, 520, 4], [20, 78, 3], [62, 38, 4],
  [920, 58, 3], [940, 140, 2], [36, 220, 3], [928, 450, 2],
])

const FIREFLY_SPOTS = Object.freeze([
  [110, 240], [160, 280], [215, 255], [250, 315], [92, 330], [130, 460],
  [176, 470], [300, 455], [360, 485], [430, 470], [620, 455], [670, 445],
  [720, 420], [780, 300], [740, 220], [655, 300], [540, 440], [318, 420],
])

const PETAL_SPOTS = Object.freeze([
  [104, 168], [152, 196], [206, 158], [258, 205], [132, 252], [238, 246],
  [168, 448], [212, 436], [660, 442], [710, 456], [622, 418],
])

const BUTTERFLY_SPOTS = Object.freeze([
  [362, 430], [640, 304], [520, 212], [286, 336], [744, 386],
])

const BIRD_LANES = Object.freeze([
  [92, 26000, 0], [128, 34000, 6000], [64, 41000, 12000],
])

export async function createIslandGame({ parent, bridge, initialState, reducedMotion = false }) {
  class IslandScene extends Phaser.Scene {
    constructor() {
      super('HeartIsland')
      this.target = null
      this.path = []
      this.activePlace = initialState.lastPlace || 'home'
      this.timePhase = normalizeIslandPhase(initialState.timePhase)
      this.lastDust = 0
      this.speed = 0
      this.facing = 'down'
      this.animKey = null
      this.lastDir = { x: 0, y: 1 }
      this.touchPoints = new Map()
      this.pinch = null
      this.drag = null
      this.lastReportedZoom = 0
      this.manualCameraUntil = 0
    }

    preload() {
      this.load.on('progress', value => bridge.emit('loading', {
        progress: 20 + Math.round(value * 75),
        text: value < 0.55 ? '正在加载心岛地图' : '正在准备咕团与角色',
      }))
      this.load.once('complete', () => bridge.emit('loading', { progress: 96, text: '正在点亮心岛' }))
      this.load.image('heart-island-base', '/images/island/heart-island-base.webp')
      this.load.image('guguan-companion', '/images/guguan/guguan-idle.webp')
      this.load.spritesheet('island-student', '/images/island/student-back.webp', {
        frameWidth: STUDENT_FRAME.width,
        frameHeight: STUDENT_FRAME.height,
      })
    }

    create() {
      // Pixel art stays crisp through the nearest-neighbour filter, but moving
      // sub-pixel positions should not be snapped to the 960x540 world grid.
      this.cameras.main.roundPixels = false
      this.cameras.main.setBounds(0, 0, ISLAND_WORLD.width, ISLAND_WORLD.height)
      this.input.addPointer(1)
      this.createWorld()
      this.createPlaces()
      this.createAmbient()
      this.createPlayer(initialState.position)
      this.applyPhase(this.timePhase)
      this.welcomeGlow(initialState.position)
      this.input.on('pointerdown', pointer => this.handlePointerDown(pointer))
      this.input.on('pointermove', pointer => this.handlePointerMove(pointer))
      this.input.on('pointerup', pointer => this.handlePointerUp(pointer))
      this.input.on('wheel', (pointer, _over, _deltaX, deltaY) => this.handleWheel(pointer, deltaY))
      this.commandOff = bridge.on('command', command => this.handleCommand(command))
      this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => this.commandOff?.())
      this.reportZoom(true)
      bridge.emit('ready', { place: this.activePlace, timePhase: this.timePhase })
      this.reportPosition(true)
    }

    cameraView() {
      return { width: this.cameras.main.width, height: this.cameras.main.height }
    }

    activeTouchPoints() {
      return [...this.touchPoints.values()]
    }

    handlePointerDown(pointer) {
      if (pointer.wasTouch) {
        this.touchPoints.set(pointer.id, { x: pointer.x, y: pointer.y })
        if (this.touchPoints.size >= 2) {
          this.startPinch()
          this.drag = null
          return
        }
      }
      this.drag = {
        id: pointer.id,
        startX: pointer.x,
        startY: pointer.y,
        lastX: pointer.x,
        lastY: pointer.y,
        moved: false,
        startedAt: this.time.now,
        touch: pointer.wasTouch,
      }
    }

    handlePointerMove(pointer) {
      if (pointer.wasTouch && this.touchPoints.has(pointer.id)) {
        this.touchPoints.set(pointer.id, { x: pointer.x, y: pointer.y })
      }
      if (this.pinch) {
        if (this.touchPoints.size >= 2) this.updatePinch()
        return
      }
      const drag = this.drag
      if (!drag || drag.id !== pointer.id || !pointer.isDown) return
      if (!drag.moved) {
        const travelled = Math.hypot(pointer.x - drag.startX, pointer.y - drag.startY)
        if (travelled < ISLAND_ZOOM.tapSlop) return
        drag.moved = true
        drag.lastX = pointer.x
        drag.lastY = pointer.y
        return
      }
      const deltaX = pointer.x - drag.lastX
      const deltaY = pointer.y - drag.lastY
      drag.lastX = pointer.x
      drag.lastY = pointer.y
      const camera = this.cameras.main
      if (camera.zoom <= ISLAND_ZOOM.min + 0.001) return
      const scroll = panIslandScroll({
        scrollX: camera.scrollX,
        scrollY: camera.scrollY,
        deltaX,
        deltaY,
        zoom: camera.zoom,
        world: ISLAND_WORLD,
        view: this.cameraView(),
      })
      camera.setScroll(scroll.scrollX, scroll.scrollY)
      this.manualCameraUntil = this.time.now + 2500
    }

    handlePointerUp(pointer) {
      if (pointer.wasTouch) this.touchPoints.delete(pointer.id)
      if (this.pinch) {
        if (this.touchPoints.size < 2) {
          this.pinch = null
          this.drag = null
        }
        return
      }
      const drag = this.drag
      if (!drag || drag.id !== pointer.id) return
      this.drag = null
      if (drag.moved) return
      if (!drag.touch && !pointer.leftButtonReleased()) return
      if (this.time.now - drag.startedAt > ISLAND_ZOOM.tapDuration) return
      this.walkTo(pointer)
    }

    startPinch() {
      const [first, second] = this.activeTouchPoints()
      if (!first || !second) return
      const screenX = (first.x + second.x) / 2
      const screenY = (first.y + second.y) / 2
      const anchor = this.cameras.main.getWorldPoint(screenX, screenY)
      this.pinch = {
        distance: Math.max(24, Math.hypot(first.x - second.x, first.y - second.y)),
        zoom: this.cameras.main.zoom,
        worldX: anchor.x,
        worldY: anchor.y,
      }
    }

    updatePinch() {
      if (!this.pinch) return
      const [first, second] = this.activeTouchPoints()
      if (!first || !second) return
      const screenX = (first.x + second.x) / 2
      const screenY = (first.y + second.y) / 2
      const distance = Math.max(24, Math.hypot(first.x - second.x, first.y - second.y))
      const zoom = clampIslandZoom(this.pinch.zoom * (distance / this.pinch.distance))
      const scroll = anchoredIslandScroll({
        worldX: this.pinch.worldX,
        worldY: this.pinch.worldY,
        screenX,
        screenY,
        zoom,
        world: ISLAND_WORLD,
        view: this.cameraView(),
      })
      this.cameras.main.setZoom(zoom)
      this.cameras.main.setScroll(scroll.scrollX, scroll.scrollY)
      this.manualCameraUntil = this.time.now + 2500
      this.reportZoom()
    }

    handleWheel(pointer, deltaY) {
      if (!deltaY) return
      const factor = deltaY > 0 ? 1 / ISLAND_ZOOM.step : ISLAND_ZOOM.step
      this.zoomMapAt(this.cameras.main.zoom * factor, pointer.x, pointer.y)
    }

    walkTo(pointer) {
      if (pointer.y < 64 || pointer.y > ISLAND_WORLD.height - 62) return
      this.path = findIslandPath(this.player, { x: pointer.worldX, y: pointer.worldY })
      this.target = this.path.shift() || null
      bridge.emit('agent', { phase: 'moving', text: '已经安排路线，正陪你向目的地走去', targetLabel: '地图上的位置' })
    }

    zoomMapAt(nextZoom, screenX = this.cameras.main.width / 2, screenY = this.cameras.main.height / 2) {
      const camera = this.cameras.main
      const zoom = clampIslandZoom(nextZoom)
      if (Math.abs(zoom - camera.zoom) < 0.001) return
      const anchor = camera.getWorldPoint(screenX, screenY)
      const scroll = anchoredIslandScroll({
        worldX: anchor.x,
        worldY: anchor.y,
        screenX,
        screenY,
        zoom,
        world: ISLAND_WORLD,
        view: this.cameraView(),
      })
      camera.setZoom(zoom)
      camera.setScroll(scroll.scrollX, scroll.scrollY)
      this.manualCameraUntil = this.time.now + 2500
      this.reportZoom()
    }

    zoomStep(direction) {
      const factor = direction > 0 ? ISLAND_ZOOM.step : 1 / ISLAND_ZOOM.step
      this.zoomMapAt(this.cameras.main.zoom * factor)
    }

    resetMapZoom() {
      this.cameras.main.setZoom(ISLAND_ZOOM.min)
      this.cameras.main.setScroll(0, 0)
      this.manualCameraUntil = 0
      this.reportZoom()
    }

    reportZoom(force = false) {
      const zoom = Math.round(this.cameras.main.zoom * 100) / 100
      if (!force && zoom === this.lastReportedZoom) return
      this.lastReportedZoom = zoom
      bridge.emit('zoom', { zoom, min: ISLAND_ZOOM.min, max: ISLAND_ZOOM.max })
    }

    keepPlayerInFrame(moving) {
      if (!moving) return
      const camera = this.cameras.main
      if (camera.zoom <= ISLAND_ZOOM.min + 0.001) return
      if (this.time.now < this.manualCameraUntil) return
      const viewWidth = camera.width / camera.zoom
      const viewHeight = camera.height / camera.zoom
      const marginX = Math.min(150, viewWidth * 0.24)
      const marginY = Math.min(90, viewHeight * 0.24)
      let targetX = camera.scrollX
      let targetY = camera.scrollY
      if (this.player.x < targetX + marginX) targetX = this.player.x - marginX
      else if (this.player.x > targetX + viewWidth - marginX) targetX = this.player.x - viewWidth + marginX
      if (this.player.y < targetY + marginY) targetY = this.player.y - marginY
      else if (this.player.y > targetY + viewHeight - marginY) targetY = this.player.y - viewHeight + marginY
      if (targetX === camera.scrollX && targetY === camera.scrollY) return
      const scroll = clampIslandScroll({
        scrollX: targetX,
        scrollY: targetY,
        zoom: camera.zoom,
        world: ISLAND_WORLD,
        view: this.cameraView(),
      })
      camera.setScroll(scroll.scrollX, scroll.scrollY)
    }

    createWorld() {
      this.cameras.main.setBackgroundColor(0x224b5c)
      this.background = this.add.image(ISLAND_WORLD.width / 2, ISLAND_WORLD.height / 2, 'heart-island-base')
        .setDisplaySize(ISLAND_WORLD.width, ISLAND_WORLD.height)
        .setDepth(0)
      this.phaseVeil = this.add.rectangle(
        ISLAND_WORLD.width / 2,
        ISLAND_WORLD.height / 2,
        ISLAND_WORLD.width,
        ISLAND_WORLD.height,
        0xffffff,
        0,
      ).setDepth(1).setBlendMode(Phaser.BlendModes.MULTIPLY)

      this.stars = this.add.container(0, 0).setDepth(2)
      for (const [x, y, size] of STAR_POINTS) {
        const star = this.add.rectangle(x, y, size + 1, size + 1, 0xffe5a1, 1)
        this.stars.add(star)
        if (!reducedMotion) {
          this.tweens.add({
            targets: star,
            alpha: { from: 0.25, to: 0.95 },
            duration: 900 + (x * 7 + y * 3) % 900,
            yoyo: true,
            repeat: -1,
            delay: (x + y) % 700,
          })
        }
      }
      for (const [x, y] of [[78, 42], [636, 70], [906, 39]]) {
        const cross = this.add.container(x, y)
        cross.add(this.add.rectangle(0, 0, 7, 1, 0xffe5a1, 0.9))
        cross.add(this.add.rectangle(0, 0, 1, 7, 0xffe5a1, 0.9))
        this.stars.add(cross)
      }

      this.lamps = LAMP_POINTS.map(([x, y]) => {
        const pool = this.add.ellipse(x, y + 2, 40, 14, 0xffc862, 1).setAlpha(0)
          .setDepth(2).setBlendMode(Phaser.BlendModes.ADD)
        const glow = this.add.circle(x, y, 13, 0xffc862, 1).setAlpha(0)
          .setDepth(3).setBlendMode(Phaser.BlendModes.ADD)
        const core = this.add.circle(x, y, 2.5, 0xffe8aa, 1).setAlpha(0).setDepth(4)
        if (!reducedMotion) {
          this.tweens.add({
            targets: glow,
            scaleX: { from: 0.86, to: 1.14 },
            scaleY: { from: 0.9, to: 1.08 },
            duration: 1600 + (x % 900),
            yoyo: true,
            repeat: -1,
            ease: 'Sine.easeInOut',
          })
        }
        return { glow, core, pool }
      })

      this.windowGlows = WINDOW_GLOWS.map(([x, y, width, height]) => {
        const glow = this.add.ellipse(x, y, width, height, 0xffc86a, 1).setAlpha(0)
          .setDepth(3).setBlendMode(Phaser.BlendModes.ADD)
        if (!reducedMotion) {
          this.tweens.add({
            targets: glow,
            scaleX: { from: 0.94, to: 1.05 },
            scaleY: { from: 0.94, to: 1.05 },
            duration: 1500 + (x % 800),
            yoyo: true,
            repeat: -1,
            ease: 'Sine.easeInOut',
          })
        }
        return glow
      })

      this.fireGlow = this.add.container(704, 166).setDepth(3)
      const fireHalo = this.add.circle(0, 0, 20, 0xff9d4a, 0.5).setBlendMode(Phaser.BlendModes.ADD)
      const flameOuter = this.add.rectangle(0, -4, 10, 16, 0xf08b3e, 0.95)
      const flameInner = this.add.rectangle(0, -2, 5, 10, 0xffd778, 1)
      this.fireGlow.add([fireHalo, flameOuter, flameInner])
      if (!reducedMotion) {
        this.tweens.add({
          targets: [flameOuter, flameInner],
          scaleX: { from: 0.82, to: 1.16 },
          scaleY: { from: 0.9, to: 1.12 },
          duration: 420,
          yoyo: true,
          repeat: -1,
          ease: 'Sine.easeInOut',
        })
        this.tweens.add({
          targets: fireHalo,
          alpha: { from: 0.32, to: 0.62 },
          scale: { from: 0.85, to: 1.12 },
          duration: 900,
          yoyo: true,
          repeat: -1,
          ease: 'Sine.easeInOut',
        })
      }
    }

    createPlayer(position) {
      const start = clampIslandPosition(position)
      this.companionSide = 1
      this.playerShadow = this.add.ellipse(start.x, start.y - 1, 24, 8, 0x10241a, 0.3).setDepth(7)
      this.player = this.add.sprite(start.x, start.y, 'island-student', STUDENT_ROWS.down * STUDENT_COLUMNS + 4)
        .setOrigin(0.5, 1)
        .setDepth(9)
      this.createStudentAnimations()
      this.playPlayerAnimation(false)
      this.player.setData('lastReport', 0)

      this.companionShadow = this.add.ellipse(start.x + 30, start.y + 2, 32, 10, 0x10241a, 0.26).setDepth(7)
      this.companion = this.add.image(start.x + 30, start.y + 2, 'guguan-companion')
        .setOrigin(0.5, 0.9)
        .setDisplaySize(40, 40)
        .setDepth(8)

      if (!reducedMotion) {
        // Idle motion must never write to x/y: position tweens fight the
        // navigation loop and can trap a character on the first waypoint.
        this.tweens.add({ targets: this.companion, angle: 1.6, yoyo: true, repeat: -1, duration: 1900 })
      }
    }

    createStudentAnimations() {
      for (const [direction, row] of Object.entries(STUDENT_ROWS)) {
        const start = row * STUDENT_COLUMNS
        if (!this.anims.exists(`student-walk-${direction}`)) {
          this.anims.create({
            key: `student-walk-${direction}`,
            frames: this.anims.generateFrameNumbers('island-student', { start, end: start + 3 }),
            frameRate: STUDENT_WALK_FPS,
            repeat: -1,
          })
        }
        if (!this.anims.exists(`student-idle-${direction}`)) {
          this.anims.create({
            key: `student-idle-${direction}`,
            frames: this.anims.generateFrameNumbers('island-student', { start: start + 4, end: start + 5 }),
            frameRate: STUDENT_IDLE_FPS,
            repeat: -1,
          })
        }
      }
    }

    playPlayerAnimation(walking) {
      const idleFrame = STUDENT_ROWS[this.facing] * STUDENT_COLUMNS + 4
      if (reducedMotion) {
        this.player.anims.stop()
        this.player.setFrame(idleFrame)
        return
      }
      const key = `student-${walking ? 'walk' : 'idle'}-${this.facing}`
      if (this.animKey !== key) {
        this.animKey = key
        this.player.play(key)
      }
      this.player.anims.timeScale = walking
        ? Phaser.Math.Clamp(this.speed / PATH_SPEED, 0.75, 1.3)
        : 1
    }

    setFacing(dx, dy) {
      const length = Math.hypot(dx, dy)
      if (length < 0.0001) return
      const nx = dx / length
      const ny = dy / length
      const horizontal = Math.abs(nx) >= Math.abs(ny) * 0.85
      const facing = horizontal ? 'side' : ny > 0 ? 'down' : 'up'
      const flip = horizontal && nx < 0
      if (facing === this.facing && flip === this.player.flipX) return
      this.facing = facing
      this.player.setFlipX(flip)
      this.animKey = null
      if (facing === 'side') this.companionSide = flip ? 1 : -1
      if (reducedMotion) {
        this.player.setFrame(STUDENT_ROWS[facing] * STUDENT_COLUMNS + 4)
      }
    }

    createPlaces() {
      this.placeMarkers = new Map()
      for (const place of ISLAND_PLACES) {
        const marker = this.add.container(place.x, place.y - 44).setDepth(6)
        const halo = this.add.circle(0, 0, 11, 0xffd37a, 0.14).setBlendMode(Phaser.BlendModes.ADD)
        const darkV = this.add.rectangle(0, 0, 5, 15, 0x3a2718, 0.9)
        const darkH = this.add.rectangle(0, 0, 15, 5, 0x3a2718, 0.9)
        const goldV = this.add.rectangle(0, 0, 3, 11, 0xffe4a3, 1)
        const goldH = this.add.rectangle(0, 0, 11, 3, 0xffe4a3, 1)
        const core = this.add.rectangle(0, 0, 5, 5, 0xfff3c4, 1)
        marker.add([halo, darkV, darkH, goldV, goldH, core])

        const label = this.add.text(place.x, place.y + 28, place.label, {
          fontFamily: '"Fusion Pixel Student", "Microsoft YaHei", sans-serif',
          fontSize: '11px',
          color: '#fff6dd',
          padding: { x: 7, y: 4 },
        }).setOrigin(0.5).setDepth(7)
        const labelBg = this.add.rectangle(place.x, place.y + 28, label.width + 4, label.height + 2, 0x241a12, 0.8)
          .setDepth(6)
        labelBg.setStrokeStyle(1, 0xd7b06a, 0.55)

        if (!reducedMotion) {
          this.tweens.add({
            targets: marker,
            y: place.y - 47,
            duration: 1100 + (place.x % 500),
            yoyo: true,
            repeat: -1,
            ease: 'Sine.easeInOut',
          })
          this.tweens.add({ targets: halo, alpha: { from: 0.08, to: 0.24 }, duration: 1400, yoyo: true, repeat: -1 })
        }
        this.placeMarkers.set(place.id, { marker, label, labelBg })
      }
    }

    createAmbient() {
      this.waterGlints = this.add.container(0, 0).setDepth(2)
      for (const [x, y, length] of WATER_GLINTS) {
        const glint = this.add.rectangle(x, y, length, 1, 0xcdf3ea, 0.7)
        this.waterGlints.add(glint)
        if (!reducedMotion) {
          this.tweens.add({
            targets: glint,
            alpha: { from: 0.08, to: 0.92 },
            scaleX: { from: 0.6, to: 1.4 },
            duration: 1200 + (x * 3 + y) % 1500,
            yoyo: true,
            repeat: -1,
            delay: (x + y) % 1100,
          })
        }
      }

      this.smoke = []
      for (const [sx, sy] of [[544, 176], [481, 39]]) {
        for (let index = 0; index < 4; index += 1) {
          const puff = this.add.circle(sx + index * 2, sy - index * 3, 2 + index * 1.2, 0xd9d2c4, 0)
            .setDepth(3)
          this.smoke.push(puff)
          if (!reducedMotion) {
            this.tweens.add({
              targets: puff,
              y: sy - 48 - index * 4,
              x: sx + 16 + index * 5,
              alpha: { from: 0.32, to: 0 },
              scaleX: { from: 0.8, to: 2.1 },
              scaleY: { from: 0.8, to: 2.1 },
              duration: 3200 + index * 450,
              repeat: -1,
              delay: index * 800,
              ease: 'Sine.easeOut',
            })
          }
        }
      }

      this.fireflies = this.add.container(0, 0).setDepth(3)
      for (const [x, y] of FIREFLY_SPOTS) {
        const fly = this.add.rectangle(x, y, 3, 3, 0xffe58a, 0)
          .setBlendMode(Phaser.BlendModes.ADD)
        this.fireflies.add(fly)
        if (!reducedMotion) {
          this.tweens.add({
            targets: fly,
            alpha: { from: 0, to: 1 },
            x: x + ((x * 3) % 11) - 5,
            y: y + ((y * 5) % 13) - 6,
            duration: 1500 + (x + y) % 1600,
            yoyo: true,
            repeat: -1,
            delay: (x * 2 + y) % 1800,
            ease: 'Sine.easeInOut',
          })
        }
      }

      this.petals = this.add.container(0, 0).setDepth(3)
      for (let index = 0; index < PETAL_SPOTS.length; index += 1) {
        const [x, y] = PETAL_SPOTS[index]
        const petal = this.add.rectangle(x, y, 3, 2, index % 3 === 0 ? 0xf2c9c0 : 0xf6e3bd, 0.85)
        this.petals.add(petal)
        if (!reducedMotion) {
          this.tweens.add({
            targets: petal,
            x: x + 26 + (index % 4) * 7,
            y: y + 42 + (index % 5) * 8,
            alpha: { from: 0.85, to: 0 },
            angle: 90,
            duration: 4200 + (index % 6) * 700,
            repeat: -1,
            delay: index * 450,
            ease: 'Sine.easeInOut',
          })
        }
      }

      this.butterflies = this.add.container(0, 0).setDepth(3)
      for (let index = 0; index < BUTTERFLY_SPOTS.length; index += 1) {
        const [x, y] = BUTTERFLY_SPOTS[index]
        const butterfly = this.add.container(x, y)
        butterfly.add(this.add.rectangle(-2, 0, 3, 3, index % 2 ? 0xf5e4b0 : 0xcfe3ea, 0.95))
        butterfly.add(this.add.rectangle(2, 0, 3, 3, index % 2 ? 0xf5e4b0 : 0xcfe3ea, 0.95))
        butterfly.add(this.add.rectangle(0, 0, 1, 3, 0x3a2b22, 0.9))
        this.butterflies.add(butterfly)
        if (!reducedMotion) {
          this.tweens.add({
            targets: butterfly,
            x: x + 10 + (index % 3) * 5,
            y: y - 8 - (index % 4) * 4,
            duration: 1400 + index * 260,
            yoyo: true,
            repeat: -1,
            ease: 'Sine.easeInOut',
          })
          this.tweens.add({
            targets: butterfly,
            scaleX: { from: 0.7, to: 1.15 },
            duration: 260,
            yoyo: true,
            repeat: -1,
          })
        }
      }

      this.birds = this.add.container(0, 0).setDepth(2)
      for (let index = 0; index < BIRD_LANES.length; index += 1) {
        const [y, duration, delay] = BIRD_LANES[index]
        const bird = this.add.container(-30, y)
        bird.add(this.add.rectangle(-2, 0, 3, 1, 0x2c3440, 0.85))
        bird.add(this.add.rectangle(2, 0, 3, 1, 0x2c3440, 0.85))
        this.birds.add(bird)
        if (!reducedMotion) {
          this.tweens.add({
            targets: bird,
            x: ISLAND_WORLD.width + 40,
            y: y + 14,
            duration,
            delay,
            repeat: -1,
            ease: 'Linear',
          })
        }
      }
    }

    welcomeGlow(position) {
      const start = clampIslandPosition(position)
      const ring = this.add.ellipse(start.x, start.y, 34, 14)
        .setStrokeStyle(2, 0xffe0a0, 0.85)
        .setDepth(7)
      if (reducedMotion) {
        this.time.delayedCall(600, () => ring.destroy())
        return
      }
      this.tweens.add({
        targets: ring,
        scaleX: 3.4,
        scaleY: 3.4,
        alpha: 0,
        duration: 1300,
        ease: 'Sine.easeOut',
        onComplete: () => ring.destroy(),
      })
    }

    applyPhase(phase, announce = false) {
      this.timePhase = normalizeIslandPhase(phase)
      const lighting = PHASE_LIGHTING[this.timePhase]
      const phaseMeta = ISLAND_PHASES.find(item => item.id === this.timePhase)
      this.background.setTint(lighting.tint)
      this.phaseVeil.setFillStyle(lighting.veil, lighting.veilAlpha)
      this.stars.setAlpha(lighting.stars)
      this.lamps.forEach(({ glow, core, pool }) => {
        glow.setAlpha(lighting.lamps * 0.22)
        core.setAlpha(lighting.lamps)
        pool.setAlpha(lighting.lamps * 0.1)
      })
      this.windowGlows?.forEach(glow => glow.setAlpha(lighting.windows))
      if (this.fireGlow) this.fireGlow.setAlpha(lighting.fire)
      if (this.waterGlints) this.waterGlints.setAlpha(lighting.glints)
      if (this.fireflies) this.fireflies.setVisible(this.timePhase === 'night')
      if (this.petals) this.petals.setVisible(this.timePhase !== 'night')
      if (this.butterflies) this.butterflies.setVisible(this.timePhase !== 'night')
      if (this.birds) this.birds.setVisible(this.timePhase === 'day')
      if (announce) {
        bridge.emit('phase', { phase: this.timePhase, label: phaseMeta.label })
        bridge.emit('status', { text: `心岛已切换到${phaseMeta.label}，地图与进度保持不变。` })
      }
    }

    handleCommand(command) {
      if (command?.type === 'move') {
        this.target = null
        this.path = []
        this.manualVector = command.direction || null
      }
      if (command?.type === 'stop') this.manualVector = null
      if (command?.type === 'phase') this.applyPhase(command.phase, true)
      if (command?.type === 'visit') {
        const place = ISLAND_PLACES.find(item => item.id === command.placeId)
        if (place) {
          this.path = findIslandPath(this.player, place)
          this.target = this.path.shift() || null
          bridge.emit('agent', { phase: 'moving', text: `已经找到合适路线：前往${place.label}`, targetLabel: place.label })
          // Clicking the place the player is already standing beside produces
          // an empty route. Treat that as arrival instead of leaving the Agent
          // rail forever in “moving”.
          if (!this.target) this.interact()
        }
      }
      if (command?.type === 'interact') this.interact()
      if (command?.type === 'zoom') {
        if (command.action === 'in') this.zoomStep(1)
        else if (command.action === 'out') this.zoomStep(-1)
        else this.resetMapZoom()
      }
    }

    update(_, delta) {
      const dt = Math.min(delta, 50)
      const vector = this.manualVector
      const hasInput = Boolean(vector?.x || vector?.y)
      const wantsMove = hasInput || Boolean(this.target)
      const targetSpeed = wantsMove ? (hasInput ? MANUAL_SPEED : PATH_SPEED) : 0
      const easing = 1 - Math.exp(-dt / (wantsMove ? 70 : 40))
      this.speed += (targetSpeed - this.speed) * easing
      if (this.speed < 0.002) this.speed = 0

      let moving = false
      if (hasInput) {
        this.target = null
        const length = Math.hypot(vector.x, vector.y) || 1
        this.lastDir = { x: vector.x / length, y: vector.y / length }
        this.stepPlayer(this.lastDir.x * this.speed * dt, this.lastDir.y * this.speed * dt)
        moving = this.speed > 0.004
      } else if (this.target) {
        moving = this.followPath(this.speed * dt)
      } else if (this.speed > 0.004) {
        this.stepPlayer(this.lastDir.x * this.speed * dt, this.lastDir.y * this.speed * dt)
        moving = true
      }

      this.updateCompanion(dt, moving)
      this.playPlayerAnimation(moving || this.speed > 0.01)
      this.keepPlayerInFrame(moving)
      if (moving && this.time.now - this.lastDust > 240) {
        this.lastDust = this.time.now
        this.spawnDust()
      }
      this.reportPosition(false)
    }

    followPath(budget) {
      let moved = false
      let guard = 0
      while (budget > 0.01 && this.target && guard < 32) {
        guard += 1
        const dx = this.target.x - this.player.x
        const dy = this.target.y - this.player.y
        const distance = Math.hypot(dx, dy)
        if (distance <= Math.max(budget, 0.01)) {
          if (distance > 0) {
            this.stepPlayer(dx, dy)
            moved = true
          }
          budget -= distance
          this.target = this.path.shift() || null
          if (!this.target) {
            this.speed = 0
            this.interact()
            break
          }
        } else {
          const ratio = budget / distance
          this.stepPlayer(dx * ratio, dy * ratio)
          budget = 0
          moved = true
        }
      }
      return moved
    }

    stepPlayer(dx, dy) {
      if (!dx && !dy) return
      const length = Math.hypot(dx, dy)
      if (length > 0.0001) this.lastDir = { x: dx / length, y: dy / length }
      const next = resolveIslandMovement(this.player, { x: this.player.x + dx, y: this.player.y + dy })
      this.player.setPosition(next.x, next.y)
      this.setFacing(dx, dy)
      this.playerShadow.setPosition(next.x, next.y - 1)
    }

    updateCompanion(dt, moving) {
      const targetX = this.player.x + this.companionSide * (moving ? 30 : 26)
      const targetY = this.player.y + 3
      const tau = reducedMotion ? 0 : moving ? 100 : 240
      const blend = reducedMotion ? 1 : 1 - Math.exp(-dt / tau)
      this.companion.x += (targetX - this.companion.x) * blend
      this.companion.y += (targetY - this.companion.y) * blend
      this.companionShadow.setPosition(this.companion.x, this.companion.y + 2)
    }

    spawnDust() {
      for (let index = 0; index < 2; index += 1) {
        const dust = this.add.circle(
          this.player.x + (index ? 7 : -7),
          this.player.y - 1,
          2,
          0xe6d6b5,
          0.4,
        ).setDepth(7.5)
        this.tweens.add({
          targets: dust,
          x: dust.x + (index ? 5 : -5),
          y: dust.y - 7,
          alpha: 0,
          scaleX: 2,
          scaleY: 2,
          duration: 520,
          onComplete: () => dust.destroy(),
        })
      }
    }

    nearestPlace() {
      return ISLAND_PLACES.reduce((best, place) => {
        const distance = Phaser.Math.Distance.Between(this.player.x, this.player.y, place.x, place.y)
        return !best || distance < best.distance ? { ...place, distance } : best
      }, null)
    }

    interact() {
      const place = this.nearestPlace()
      if (!place || place.distance > 64) {
        bridge.emit('status', { text: '沿着星灯再走近一点，就能和这里互动。', place: this.activePlace })
        return
      }
      this.activePlace = place.id
      bridge.emit('arrive', { place: place.id, label: place.label, hint: place.hint, position: { x: this.player.x, y: this.player.y } })
      bridge.emit('agent', { phase: 'arrived', text: `已到达${place.label}，正在准备适合此处的轻量活动`, targetLabel: place.label })
    }

    reportPosition(force) {
      const now = this.time.now
      const lastPosition = this.player.getData('lastReportedPosition')
      const currentPosition = { x: Math.round(this.player.x), y: Math.round(this.player.y) }
      if (!force && lastPosition?.x === currentPosition.x && lastPosition?.y === currentPosition.y) return
      if (!force && now - this.player.getData('lastReport') < 1200) return
      this.player.setData('lastReport', now)
      this.player.setData('lastReportedPosition', currentPosition)
      const place = this.nearestPlace()
      bridge.emit('position', {
        position: currentPosition,
        place: this.activePlace,
        nearby: place?.distance < 92 ? place.label : '星灯小径',
        timePhase: this.timePhase,
      })
    }
  }

  return new Phaser.Game({
    type: Phaser.AUTO,
    parent,
    width: ISLAND_WORLD.width,
    height: ISLAND_WORLD.height,
    backgroundColor: 0x224b5c,
    pixelArt: true,
    antialias: false,
    roundPixels: true,
    render: { antialias: false, pixelArt: true },
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH, width: ISLAND_WORLD.width, height: ISLAND_WORLD.height },
    scene: IslandScene,
    audio: { noAudio: true },
  })
}
