import Phaser from 'phaser'

// Built with Phaser 3's documented Scene, timed-event, tween and input patterns.
// Phaser and the MIT-licensed example source are credited in THIRD_PARTY_NOTICES.md.

const WIDTH = 760
const HEIGHT = 300

export async function createFishingGame({ parent, onEvent = () => {}, reducedMotion = false }) {
  let sceneRef = null
  const queued = []
  const controller = {
    command(command) {
      if (sceneRef) sceneRef.handleCommand(command)
      else queued.push(command)
    },
    destroy() { game?.destroy(true) },
  }

  class FishingScene extends Phaser.Scene {
    constructor() {
      super('HeartIslandFishing')
      this.state = 'idle'
      this.reeling = false
      this.marker = 0.42
      this.target = 0.55
      this.progress = 0
      this.tension = 0.3
      this.elapsed = 0
    }

    create() {
      sceneRef = this
      this.drawWorld()
      this.drawGauge()
      queued.splice(0).forEach(command => this.handleCommand(command))
      onEvent({ type: 'ready' })
    }

    drawWorld() {
      this.cameras.main.setBackgroundColor(0x356f78)
      const water = this.add.graphics()
      water.fillGradientStyle(0x4e9b9c, 0x4e9b9c, 0x285e70, 0x285e70, 1)
      water.fillRect(0, 0, WIDTH, HEIGHT)
      for (let y = 24; y < 220; y += 28) {
        for (let x = (y / 28) % 2 ? 12 : 38; x < WIDTH; x += 86) {
          water.lineStyle(2, 0xffd69a, 0.24)
          water.lineBetween(x, y, x + 30, y)
        }
      }
      const pier = this.add.graphics()
      pier.fillStyle(0x784735, 1)
      pier.fillRect(0, 216, WIDTH, 84)
      pier.fillStyle(0xa66845, 1)
      for (let x = 0; x < WIDTH; x += 56) pier.fillRect(x, 219, 50, 70)
      this.float = this.add.circle(WIDTH * 0.54, 104, 8, 0xffd083, 1).setStrokeStyle(3, 0x6f3f35)
      this.ripple = this.add.circle(WIDTH * 0.54, 104, 22, 0xffffff, 0).setStrokeStyle(2, 0xffe0aa, 0)
      this.fishShadow = this.add.ellipse(WIDTH * 0.36, 154, 52, 18, 0x193c4b, 0.38)
      if (!reducedMotion) {
        this.tweens.add({ targets: this.float, y: 109, duration: 950, yoyo: true, repeat: -1, ease: 'Sine.InOut' })
        this.tweens.add({ targets: this.fishShadow, x: WIDTH * 0.67, duration: 3600, yoyo: true, repeat: -1, ease: 'Sine.InOut' })
      }
    }

    drawGauge() {
      this.gauge = this.add.graphics().setDepth(5)
      this.progressText = this.add.text(24, 254, '准备好时抛竿', {
        fontFamily: 'Microsoft YaHei, sans-serif', fontSize: '15px', color: '#fff4df', fontStyle: 'bold',
      }).setDepth(6)
      this.renderGauge()
    }

    renderGauge() {
      const x = 255
      const y = 252
      const width = 470
      const height = 22
      this.gauge.clear()
      this.gauge.fillStyle(0x3c2a2b, 0.78).fillRoundedRect(x, y, width, height, 8)
      if (this.state === 'hooked') {
        const targetX = x + this.target * width
        this.gauge.fillStyle(0xffd083, 0.28).fillRoundedRect(targetX - 45, y + 3, 90, height - 6, 6)
        this.gauge.fillStyle(this.tension > 0.84 ? 0xe17363 : 0xfff0bd, 1).fillCircle(x + this.marker * width, y + height / 2, 8)
        this.gauge.lineStyle(2, 0xffe2b2, 0.5).strokeRoundedRect(x, y, width, height, 8)
        this.gauge.fillStyle(0xa8c38b, 1).fillRoundedRect(x, y + 30, width * this.progress, 8, 4)
      }
    }

    handleCommand(command) {
      if (command?.type === 'cast') this.cast()
      if (command?.type === 'reel') this.reeling = !!command.active
    }

    cast() {
      if (!['idle', 'result'].includes(this.state)) return
      this.state = 'waiting'
      this.progress = 0
      this.tension = 0.3
      this.marker = 0.42
      this.elapsed = 0
      this.progressText.setText('水面很安静，留意浮标的动静')
      onEvent({ type: 'state', state: 'waiting', message: '已经抛竿，留意水面涟漪。' })
      this.biteTimer?.remove(false)
      this.biteTimer = this.time.delayedCall(1100 + Math.random() * 1300, () => this.startHook())
    }

    startHook() {
      if (this.state !== 'waiting') return
      this.state = 'hooked'
      this.ripple.setStrokeStyle(2, 0xffe0aa, 0.82)
      this.progressText.setText('按住空格或收线，让浮标跟住金色区域')
      onEvent({ type: 'state', state: 'hooked', message: '鱼咬钩了。按住收线，松开可以降低张力。' })
    }

    finish(result) {
      this.state = 'result'
      this.reeling = false
      this.ripple.setStrokeStyle(2, 0xffe0aa, 0)
      if (result === 'caught') {
        this.progressText.setText('收线成功，新朋友已记入图鉴')
        onEvent({ type: 'caught', fishIndex: Math.floor(Math.random() * 3) })
      } else if (result === 'tension') {
        this.progressText.setText('鱼线太紧了，松手慢一点就好')
        onEvent({ type: 'state', state: 'result', message: '鱼游走了。这里没有损失，下一竿可以少按一会。' })
      } else {
        this.progressText.setText('它游走了，想继续时再抛一竿')
        onEvent({ type: 'state', state: 'result', message: '这次没有收线，但已经完成了一轮等待。' })
      }
    }

    update(_, delta) {
      if (this.state !== 'hooked') return
      const seconds = Math.min(0.05, delta / 1000)
      this.elapsed += seconds
      this.target = 0.5 + Math.sin(this.elapsed * 1.7) * 0.27 + Math.sin(this.elapsed * 3.9) * 0.07
      const pull = this.reeling ? 0.31 : -0.2
      this.marker = Phaser.Math.Clamp(this.marker + pull * seconds, 0.03, 0.97)
      this.tension = Phaser.Math.Clamp(this.tension + (this.reeling ? 0.25 : -0.34) * seconds, 0.05, 1)
      const aligned = Math.abs(this.marker - this.target) < 0.12
      this.progress = Phaser.Math.Clamp(this.progress + (aligned ? 0.24 : -0.09) * seconds, 0, 1)
      this.float.setX(WIDTH * (0.26 + this.target * 0.55))
      this.ripple.setPosition(this.float.x, this.float.y)
      this.renderGauge()
      onEvent({ type: 'meter', progress: this.progress, tension: this.tension })
      if (this.tension >= 0.98) this.finish('tension')
      else if (this.progress >= 1) this.finish('caught')
      else if (this.elapsed > 18) this.finish('escaped')
    }
  }

  const game = new Phaser.Game({
    type: Phaser.AUTO,
    parent,
    width: WIDTH,
    height: HEIGHT,
    backgroundColor: 0x356f78,
    pixelArt: true,
    antialias: false,
    roundPixels: true,
    render: { antialias: false, pixelArt: true },
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH, width: WIDTH, height: HEIGHT },
    scene: FishingScene,
    audio: { noAudio: true },
  })
  return controller
}
