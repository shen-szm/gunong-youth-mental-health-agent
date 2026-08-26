import Phaser from 'phaser'
import { clampIslandPosition, ISLAND_PHASES, ISLAND_PLACES, ISLAND_WORLD, normalizeIslandPhase } from './islandState.js'

const PHASE_LIGHTING = Object.freeze({
  day: { tint: 0xffffff, veil: 0xfff0c7, veilAlpha: 0.02, lamps: 0.08, stars: 0 },
  dusk: { tint: 0xffd5bd, veil: 0x6d385f, veilAlpha: 0.16, lamps: 0.46, stars: 0.18 },
  night: { tint: 0x8f9ccf, veil: 0x101b48, veilAlpha: 0.38, lamps: 0.9, stars: 0.82 },
})

const LAMP_POINTS = Object.freeze([
  [137, 352], [252, 387], [365, 405], [472, 385], [574, 330], [668, 275],
  [748, 242], [721, 158], [602, 138], [532, 184], [335, 280], [190, 292],
])

export async function createIslandGame({ parent, bridge, initialState, reducedMotion = false }) {
  class IslandScene extends Phaser.Scene {
    constructor() {
      super('HeartIsland')
      this.target = null
      this.activePlace = initialState.lastPlace || 'home'
      this.timePhase = normalizeIslandPhase(initialState.timePhase)
    }

    preload() {
      this.load.image('heart-island-base', '/images/island/heart-island-base.png')
      this.load.image('guguan-companion', '/images/guguan/guguan-idle.png')
      this.load.image('island-student-back', '/images/island/student-back.png')
    }

    create() {
      this.createWorld()
      this.createPlaces()
      this.createPlayer(initialState.position)
      this.applyPhase(this.timePhase)
      this.input.on('pointerdown', pointer => {
        if (pointer.y < 64 || pointer.y > ISLAND_WORLD.height - 62) return
        this.target = clampIslandPosition({ x: pointer.worldX, y: pointer.worldY })
        bridge.emit('agent', { phase: 'moving', text: '已经安排路线，正陪你向目的地走去', targetLabel: '地图上的位置' })
      })
      this.commandOff = bridge.on('command', command => this.handleCommand(command))
      this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => this.commandOff?.())
      bridge.emit('ready', { place: this.activePlace, timePhase: this.timePhase })
      this.reportPosition(true)
    }

    createWorld() {
      this.cameras.main.setBackgroundColor(0x18264a)
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
      for (const [x, y, size] of [[78,42,2],[142,82,1],[232,45,2],[309,74,1],[556,48,1],[636,70,2],[762,45,1],[846,80,2],[906,39,1]]) {
        this.stars.add(this.add.circle(x, y, size + 1, 0xffe5a1, 1))
      }
      this.lamps = LAMP_POINTS.map(([x, y]) => {
        const glow = this.add.circle(x, y, 15, 0xffc862, 0).setDepth(3).setBlendMode(Phaser.BlendModes.ADD)
        const core = this.add.circle(x, y, 3, 0xffe8aa, 0).setDepth(4)
        return { glow, core }
      })
    }

    createPlayer(position) {
      this.player = this.add.image(position.x, position.y, 'island-student-back').setDisplaySize(31, 72).setDepth(9)
      this.player.setData('lastReport', 0)
      this.companion = this.add.image(position.x + 34, position.y + 5, 'guguan-companion')
        .setDisplaySize(58, 58)
        .setDepth(8)
      if (!reducedMotion) {
        this.tweens.add({ targets: this.player, y: this.player.y - 2, yoyo: true, repeat: -1, duration: 820 })
        this.tweens.add({ targets: this.companion, y: this.companion.y - 3, yoyo: true, repeat: -1, duration: 1100 })
      }
    }

    createPlaces() {
      this.placeMarkers = new Map()
      for (const place of ISLAND_PLACES) {
        const marker = this.add.circle(place.x, place.y, 19, 0xf2cf83, 0.12).setDepth(5)
        marker.setStrokeStyle(2, 0xffdf98, 0.82)
        const label = this.add.text(place.x, place.y + 27, place.label, {
          fontFamily: 'Microsoft YaHei, sans-serif', fontSize: '13px', color: '#fff8e8',
          backgroundColor: '#171a2dcc', padding: { x: 8, y: 5 },
        }).setOrigin(0.5).setDepth(6)
        this.placeMarkers.set(place.id, { marker, label })
      }
    }

    applyPhase(phase, announce = false) {
      this.timePhase = normalizeIslandPhase(phase)
      const lighting = PHASE_LIGHTING[this.timePhase]
      const phaseMeta = ISLAND_PHASES.find(item => item.id === this.timePhase)
      this.background.setTint(lighting.tint)
      this.phaseVeil.setFillStyle(lighting.veil, lighting.veilAlpha)
      this.stars.setAlpha(lighting.stars)
      this.lamps.forEach(({ glow, core }) => {
        glow.setAlpha(lighting.lamps * 0.42)
        core.setAlpha(lighting.lamps)
      })
      if (announce) {
        bridge.emit('phase', { phase: this.timePhase, label: phaseMeta.label })
        bridge.emit('status', { text: `心岛已切换到${phaseMeta.label}，地图与进度保持不变。` })
      }
    }

    handleCommand(command) {
      if (command?.type === 'move') {
        this.target = null
        this.manualVector = command.direction || null
      }
      if (command?.type === 'stop') this.manualVector = null
      if (command?.type === 'phase') this.applyPhase(command.phase, true)
      if (command?.type === 'visit') {
        const place = ISLAND_PLACES.find(item => item.id === command.placeId)
        if (place) {
          this.target = { x: place.x, y: place.y }
          bridge.emit('agent', { phase: 'moving', text: `已经找到合适路线：前往${place.label}`, targetLabel: place.label })
        }
      }
      if (command?.type === 'interact') this.interact()
    }

    update(_, delta) {
      const vector = this.manualVector
      if (vector?.x || vector?.y) {
        this.target = null
        const length = Math.hypot(vector.x, vector.y) || 1
        this.movePlayer(vector.x / length * delta * 0.16, vector.y / length * delta * 0.16)
      } else if (this.target) {
        const dx = this.target.x - this.player.x
        const dy = this.target.y - this.player.y
        const distance = Math.hypot(dx, dy)
        if (distance < 7) {
          this.target = null
          this.interact()
        } else {
          this.movePlayer(dx / distance * delta * 0.14, dy / distance * delta * 0.14)
        }
      }
      this.reportPosition(false)
    }

    movePlayer(dx, dy) {
      const next = clampIslandPosition({ x: this.player.x + dx, y: this.player.y + dy })
      this.player.setPosition(next.x, next.y)
      if (dx) this.player.setFlipX(dx < 0)
      const followX = next.x + (dx < 0 ? 34 : -34)
      const followY = next.y + 7
      this.companion.setPosition(
        Phaser.Math.Linear(this.companion.x, followX, reducedMotion ? 1 : 0.18),
        Phaser.Math.Linear(this.companion.y, followY, reducedMotion ? 1 : 0.18),
      )
      this.companion.setFlipX(dx > 0)
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
    backgroundColor: 0x18264a,
    pixelArt: true,
    antialias: false,
    roundPixels: true,
    render: { antialias: false, pixelArt: true },
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH, width: ISLAND_WORLD.width, height: ISLAND_WORLD.height },
    scene: IslandScene,
    audio: { noAudio: true },
  })
}
