import Phaser from 'phaser'
import { clampIslandPosition, ISLAND_PLACES, ISLAND_WORLD } from './islandState.js'

const COLORS = {
  water: 0x213b58,
  waterLight: 0x2e5970,
  shore: 0xe8c98c,
  grass: 0x6ea889,
  grassDark: 0x477963,
  path: 0xd7b980,
  glass: 0x172635,
  mint: 0xb9e0c8,
  coral: 0xe59b87,
  lavender: 0xa8a5dc,
}

export async function createIslandGame({ parent, bridge, initialState, reducedMotion = false }) {
  class IslandScene extends Phaser.Scene {
    constructor() {
      super('HeartIsland')
      this.target = null
      this.activePlace = initialState.lastPlace || 'home'
    }

    create() {
      this.drawWorld()
      this.createPlayer(initialState.position)
      this.createPlaces()
      this.input.on('pointerdown', pointer => {
        if (pointer.y < 68) return
        this.target = clampIslandPosition({ x: pointer.worldX, y: pointer.worldY })
        bridge.emit('agent', { phase: 'moving', text: '陪伴行动正在进行：前往你选择的位置' })
      })
      this.commandOff = bridge.on('command', command => this.handleCommand(command))
      this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => this.commandOff?.())
      bridge.emit('ready', { place: this.activePlace })
      this.reportPosition(true)
    }

    drawWorld() {
      this.cameras.main.setBackgroundColor(COLORS.water)
      const sea = this.add.graphics().setDepth(0)
      sea.fillStyle(COLORS.waterLight, 0.34)
      for (let y = 22; y < ISLAND_WORLD.height; y += 34) {
        for (let x = (y / 34) % 2 ? 18 : 2; x < ISLAND_WORLD.width; x += 52) {
          sea.fillRect(x, y, 23, 3)
          sea.fillStyle(COLORS.waterLight, 0.18)
          sea.fillRect(x + 24, y + 8, 12, 2)
          sea.fillStyle(COLORS.waterLight, 0.34)
        }
      }

      const island = this.add.graphics().setDepth(1)
      island.fillStyle(COLORS.shore, 1)
      island.fillRoundedRect(126, 105, 708, 354, 92)
      island.fillStyle(COLORS.grassDark, 1)
      island.fillRoundedRect(145, 121, 670, 319, 78)
      island.fillStyle(COLORS.grass, 1)
      island.fillRoundedRect(158, 132, 644, 292, 68)

      island.lineStyle(18, COLORS.path, 1)
      island.beginPath()
      island.moveTo(480, 405)
      island.lineTo(480, 300)
      island.lineTo(285, 270)
      island.moveTo(480, 300)
      island.lineTo(600, 185)
      island.moveTo(480, 300)
      island.lineTo(745, 338)
      island.strokePath()

      const details = this.add.graphics().setDepth(2)
      details.fillStyle(0x365f50, 1)
      for (const [x, y] of [[200,180],[240,372],[680,390],[745,185],[360,160],[170,300]]) {
        details.fillRect(x, y, 10, 26)
        details.fillStyle(0x87be8d, 1)
        details.fillRect(x - 12, y - 12, 34, 18)
        details.fillStyle(0x365f50, 1)
      }
    }

    createPlayer(position) {
      const texture = this.make.graphics({ x: 0, y: 0, add: false })
      texture.fillStyle(0x3d314f, 1).fillRect(7, 4, 18, 22)
      texture.fillStyle(0xf1c7a4, 1).fillRect(9, 6, 14, 10)
      texture.fillStyle(0xf4d68e, 1).fillRect(5, 16, 22, 13)
      texture.fillStyle(0x28384e, 1).fillRect(7, 29, 8, 7).fillRect(18, 29, 8, 7)
      texture.generateTexture('island-student', 32, 38)
      texture.destroy()
      this.player = this.add.image(position.x, position.y, 'island-student').setDepth(8)
      this.player.setData('lastReport', 0)
      if (!reducedMotion) this.tweens.add({ targets: this.player, scaleY: 0.97, yoyo: true, repeat: -1, duration: 820 })
    }

    createPlaces() {
      const colors = { home: COLORS.mint, garden: 0x97c28b, dock: COLORS.lavender, exchange: COLORS.coral }
      for (const place of ISLAND_PLACES) {
        const marker = this.add.rectangle(place.x, place.y, 66, 48, colors[place.id], 0.96).setDepth(5)
        marker.setStrokeStyle(4, COLORS.glass, 0.74)
        this.add.text(place.x, place.y + 39, place.label, {
          fontFamily: 'Microsoft YaHei, sans-serif', fontSize: '15px', color: '#fff9e9',
          backgroundColor: '#172635cc', padding: { x: 8, y: 4 },
        }).setOrigin(0.5).setDepth(6)
      }
    }

    handleCommand(command) {
      if (command?.type === 'move') {
        this.target = null
        this.manualVector = command.direction || null
      }
      if (command?.type === 'stop') this.manualVector = null
      if (command?.type === 'visit') {
        const place = ISLAND_PLACES.find(item => item.id === command.placeId)
        if (place) {
          this.target = { x: place.x, y: place.y }
          bridge.emit('agent', { phase: 'moving', text: `已规划路线：前往${place.label}` })
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
    }

    nearestPlace() {
      return ISLAND_PLACES.reduce((best, place) => {
        const distance = Phaser.Math.Distance.Between(this.player.x, this.player.y, place.x, place.y)
        return !best || distance < best.distance ? { ...place, distance } : best
      }, null)
    }

    interact() {
      const place = this.nearestPlace()
      if (!place || place.distance > 62) {
        bridge.emit('status', { text: '这里很安静。靠近一个地点后可以互动。', place: this.activePlace })
        return
      }
      this.activePlace = place.id
      bridge.emit('arrive', { place: place.id, label: place.label, hint: place.hint, position: { x: this.player.x, y: this.player.y } })
      bridge.emit('agent', { phase: 'arrived', text: `已完成路线并到达${place.label}，等待你的下一步` })
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
        nearby: place?.distance < 92 ? place.label : '岛屿小径',
      })
    }
  }

  return new Phaser.Game({
    type: Phaser.AUTO,
    parent,
    width: ISLAND_WORLD.width,
    height: ISLAND_WORLD.height,
    backgroundColor: COLORS.water,
    pixelArt: true,
    antialias: false,
    roundPixels: true,
    render: { antialias: false, pixelArt: true },
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH, width: ISLAND_WORLD.width, height: ISLAND_WORLD.height },
    scene: IslandScene,
    audio: { noAudio: true },
  })
}
