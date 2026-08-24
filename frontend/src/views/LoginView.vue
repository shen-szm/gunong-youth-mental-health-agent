<template>
  <!-- 登录页 -->
  <div class="login-page" :class="{ bgready: bgReady }">
    <!-- 白光流星层 -->
    <canvas ref="veilRef" class="veil-canvas" :class="{ gone: veilGone }"></canvas>

    <!-- 登录主体容器 -->
    <div class="login-container" :class="{ visible: containerVisible }">
      <!-- 左侧：每日一句 -->
      <div class="left-panel">
        <div class="quote-area">
          <div class="quote-icon">"</div>
          <p class="quote-text">{{ daily.quote }}</p>
          <p class="quote-author">—— {{ daily.author }}</p>
        </div>
        <div class="brand">
          <span class="brand-name">咕哝</span>
          <span class="brand-slogan">让每一句心声，都被温柔以待</span>
        </div>
      </div>

      <!-- 右侧：登录表单 -->
      <div class="right-panel">
        <div class="form-header">
          <h2>{{ mode === 'login' ? '欢迎回来' : '创建账号' }}</h2>
          <p>{{ mode === 'login' ? '很高兴再次见到你' : '加入咕哝，开始倾诉' }}</p>
        </div>

        <div class="tab-switch">
          <button :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
          <button :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
        </div>

        <div class="form-body">
          <div class="input-group">
            <label>用户名</label>
            <input v-model="form.username" placeholder="请输入用户名" class="input" autocomplete="username" />
          </div>
          <div class="input-group" v-if="mode === 'register'">
            <label>昵称</label>
            <input v-model="form.nickname" placeholder="如何称呼你？（可选）" class="input" />
          </div>
          <div class="input-group">
            <label>密码</label>
            <input v-model="form.password" type="password" placeholder="请输入密码" class="input" autocomplete="current-password" />
          </div>

          <p class="error" v-if="error">{{ error }}</p>

          <button class="btn-primary" @click="handleSubmit" :disabled="loading">
            <span v-if="loading" class="loading-dot"></span>
            <span v-else>{{ mode === 'login' ? '登 录' : '注 册' }}</span>
          </button>

          <div class="form-extras">
            <p v-if="mode === 'login'" class="forgot-hint">密码不会被系统展示；需要重置时请联系教师管理员。</p>
          </div>
        </div>
      </div>

    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { register, login } from '../api/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const mode = ref('login')
const loading = ref(false)
const error = ref('')
const form = ref({ username: '', password: '', nickname: '' })
const veilRef = ref(null)
const containerVisible = ref(false)
const veilGone = ref(false)
const bgReady = ref(false)


// ─── 每日一句 ──────────────────────────────────────────────────────
const quotes = [
  { quote: '不要等待机会，而要创造机会。', author: '林肯' },
  { quote: '生活不是等待暴风雨过去，而是学会在雨中起舞。', author: '薇薇安·格林' },
  { quote: '你所浪费的今日，是昨日死去之人奢望的明天。', author: '佚名' },
  { quote: '把每一个平凡的日子，都过成不平凡的模样。', author: '村上春树' },
  { quote: '愿你出走半生，归来仍是少年。', author: '岳勇' },
  { quote: '心中有光，处处皆暖。', author: '泰戈尔' },
  { quote: '我们必须接受失望，因为它是有限的；但千万不可失去希望，因为它是无穷的。', author: '马丁·路德·金' },
  { quote: '所有的岁月都值得被温柔对待。', author: '三毛' },
  { quote: '即使慢，驰而不息，纵会落后，纵会失败，但必须能够到达他所向往的目标。', author: '鲁迅' },
  { quote: '你不必完美，你只需要真实。', author: '布芮妮·布朗' },
  { quote: '凡是过往，皆为序章。', author: '莎士比亚' },
  { quote: '懂得生活的人，随处都能找到快乐。', author: '雨果' },
  { quote: '生命的意义在于付出，在于给予，而不是接受。', author: '巴金' },
  { quote: '每一个不曾起舞的日子，都是对生命的辜负。', author: '尼采' },
  { quote: '勇气不是不恐惧，而是判断有比恐惧更重要的事。', author: '安布罗斯·雷德穆恩' },
  { quote: '只要还有明天，今天永远是起跑线。', author: '佚名' },
  { quote: '你的故事还没写完，不要提前画上句号。', author: '佚名' },
  { quote: '人生就像骑自行车，为了保持平衡，你必须不断前进。', author: '爱因斯坦' },
  { quote: '善待自己，你值得被温柔以待。', author: '佚名' },
  { quote: '世界上只有一种英雄主义，那就是认清生活的真相之后依然热爱生活。', author: '罗曼·罗兰' },
  { quote: '你无法控制风向，但可以调整风帆。', author: '佚名' },
  { quote: '最深的孤独，是不敢说出口的热爱。', author: '杨绛' },
  { quote: '如果你正在经历地狱，继续前行。', author: '丘吉尔' },
  { quote: '最好的时光，永远是当下这一刻。', author: '梭罗' },
  { quote: '生活以痛吻我，我却报之以歌。', author: '泰戈尔' },
  { quote: '别在冬天里，放弃一棵可能在春天开花的树。', author: '佚名' },
  { quote: '你不需要被所有人理解，只要被对的人理解就够了。', author: '佚名' },
  { quote: '在最深的绝望里，藏着最美的风景。', author: '佚名' },
  { quote: '做自己的光，照亮自己的路。', author: '佚名' },
  { quote: '慢慢来，比较快。', author: '几米' },
]

const daily = quotes[Math.floor(Math.random() * quotes.length)]

// ─── 白光流星 Canvas 动画 ────────────────────────────────────────────
let animId = null
let cleanupFn = null

onMounted(() => {
  const canvas = veilRef.value
  const ctx = canvas.getContext('2d')
  let W = canvas.width = window.innerWidth
  let H = canvas.height = window.innerHeight

  const resize = () => {
    W = canvas.width = window.innerWidth
    H = canvas.height = window.innerHeight
  }
  window.addEventListener('resize', resize)
  cleanupFn = () => window.removeEventListener('resize', resize)

  // 流星粒子 — 向观察者后方飞去（z轴远离）
  const meteors = Array.from({ length: 50 }, () => {
    const cx = W / 2 + (Math.random() - 0.5) * W * 0.3
    const cy = H / 2 + (Math.random() - 0.5) * H * 0.3
    return {
      x: cx + (Math.random() - 0.5) * 60,
      y: cy + (Math.random() - 0.5) * 60,
      z: Math.random() * 0.3,                 // 0~1 深度，0=远 1=近
      speed: 0.015 + Math.random() * 0.025,   // 深度增长速度
      size: 2 + Math.random() * 3,
      alpha: 0.5 + Math.random() * 0.5,
      delay: Math.random() * 40,
      trail: [],
    }
  })

  // 柔和光点
  const glowOrbs = Array.from({ length: 8 }, () => ({
    x: Math.random() * W,
    y: Math.random() * H,
    r: 80 + Math.random() * 160,
    alpha: 0.15 + Math.random() * 0.2,
    phase: Math.random() * Math.PI * 2,
    speed: 0.008 + Math.random() * 0.012,
  }))

  let frame = 0
  const START_MOVE = 50  // 第50帧开始流星移动
  const FADE_START = 100 // 第100帧开始消退
  const FADE_END = 180   // 第180帧完全消失

  function draw() {
    frame++

    // ── 计算整体透明度 ──
    let masterAlpha = 1
    if (frame >= FADE_START && frame < FADE_END) {
      masterAlpha = 1 - (frame - FADE_START) / (FADE_END - FADE_START)
    }
    if (frame >= FADE_END) {
      // 白光层消失，显示登录框
      veilGone.value = true
      bgReady.value = true
      setTimeout(() => { containerVisible.value = true }, 50)
      return
    }

    ctx.clearRect(0, 0, W, H)

    // ── 白色底色（渐隐） ──
    ctx.fillStyle = `rgba(255, 255, 255, ${masterAlpha * 0.95})`
    ctx.fillRect(0, 0, W, H)

    // ── 柔和光晕 ──
    glowOrbs.forEach(orb => {
      orb.phase += orb.speed
      const ox = orb.x + Math.sin(orb.phase) * 30
      const oy = orb.y + Math.cos(orb.phase * 0.7) * 20
      const grad = ctx.createRadialGradient(ox, oy, 0, ox, oy, orb.r)
      grad.addColorStop(0, `rgba(220, 235, 255, ${orb.alpha * masterAlpha})`)
      grad.addColorStop(1, `rgba(220, 235, 255, 0)`)
      ctx.fillStyle = grad
      ctx.fillRect(ox - orb.r, oy - orb.r, orb.r * 2, orb.r * 2)
    })

    // ── 流星（向后划走，空间感） ──
    if (frame > START_MOVE) {
      const progress = (frame - START_MOVE) / (FADE_END - START_MOVE)

      meteors.forEach(m => {
        if (frame - START_MOVE < m.delay) return

        // 深度递增 → 向远处飞去
        m.z += m.speed * (1 + progress * 4)

        // 透视投影：从屏幕中心向外扩散
        const spreadX = m.x - W / 2
        const spreadY = m.y - H / 2
        const scale = 1 + m.z * 8  // 越远越靠外
        const drawX = W / 2 + spreadX * scale
        const drawY = H / 2 + spreadY * scale

        // 近大远小
        const drawSize = Math.max(0.5, m.size * (1 - m.z))

        // 记录轨迹
        m.trail.push({ x: drawX, y: drawY, s: drawSize })
        if (m.trail.length > 18) m.trail.shift()

        // 绘制轨迹线（从细到粗，从暗到亮）
        if (m.trail.length > 1) {
          for (let i = 1; i < m.trail.length; i++) {
            const prev = m.trail[i - 1]
            const curr = m.trail[i]
            const ratio = i / m.trail.length
            const a = ratio * m.alpha * masterAlpha * (1 - m.z)
            const lw = Math.max(0.3, curr.s * 0.6 * ratio)
            ctx.beginPath()
            ctx.moveTo(prev.x, prev.y)
            ctx.lineTo(curr.x, curr.y)
            ctx.strokeStyle = `rgba(255, 255, 255, ${a})`
            ctx.lineWidth = lw
            ctx.lineCap = 'round'
            ctx.stroke()
          }
        }

        // 绘制头部光点
        if (m.z < 0.85) {
          const headA = m.alpha * masterAlpha * (1 - m.z * 1.2)
          const glowR = drawSize * 5
          const headGrad = ctx.createRadialGradient(drawX, drawY, 0, drawX, drawY, glowR)
          headGrad.addColorStop(0, `rgba(255, 255, 255, ${Math.max(0, headA)})`)
          headGrad.addColorStop(0.3, `rgba(230, 240, 255, ${Math.max(0, headA * 0.4)})`)
          headGrad.addColorStop(1, `rgba(230, 240, 255, 0)`)
          ctx.fillStyle = headGrad
          ctx.fillRect(drawX - glowR, drawY - glowR, glowR * 2, glowR * 2)
        }
      })
    }

    animId = requestAnimationFrame(draw)
  }

  animId = requestAnimationFrame(draw)
})

onUnmounted(() => {
  if (animId) cancelAnimationFrame(animId)
  if (cleanupFn) cleanupFn()
})

// ─── 登录 / 注册逻辑 ────────────────────────────────────────────────
async function handleSubmit() {
  error.value = ''
  if (!form.value.username || !form.value.password) {
    error.value = '请填写用户名和密码'
    return
  }
  loading.value = true
  try {
    if (mode.value === 'login') {
      const resp = await login(form.value.username, form.value.password)
      const data = resp.data
      userStore.login(data.user_id, data.nickname, !!data.is_admin, !!data.is_super_admin, data.role)
      const redirect = route.query.redirect
      router.push(data.is_admin ? (redirect || '/admin') : '/')
    } else {
      await register(form.value.username, form.value.password, form.value.nickname)
      mode.value = 'login'
      error.value = '注册成功，请登录 ✓'
    }
  } catch (e) {
    error.value = e.response?.data?.detail || '操作失败，请重试'
  } finally {
    loading.value = false
  }
}

</script>

<style scoped>
* { box-sizing: border-box; }

.login-page {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #eef2f7;
  transition: background 0.8s ease;
}

.login-page.bgready {
  background: linear-gradient(145deg, #e8edf5 0%, #dfe6f0 30%, #d6dfea 60%, #e4e9f3 100%);
}

/* ── 白光流星 Canvas ── */
.veil-canvas {
  position: absolute;
  inset: 0;
  z-index: 10;
  pointer-events: none;
}

.veil-canvas.gone {
  display: none;
}

/* ── 登录容器浮现动画 ── */
.login-container {
  position: relative;
  z-index: 1;
  display: flex;
  width: min(860px, 94vw);
  min-height: 480px;
  border-radius: 24px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.42);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.55);
  box-shadow:
    0 8px 32px rgba(90, 120, 160, 0.08),
    0 1px 0 rgba(255, 255, 255, 0.6) inset;
  opacity: 0;
  transform: translateY(24px) scale(0.98);
  transition: opacity 0.8s ease, transform 0.8s ease;
}

.login-container.visible {
  opacity: 1;
  transform: translateY(0) scale(1);
}

/* ── 左侧面板 ── */
.left-panel {
  flex: 1;
  padding: 48px 40px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: linear-gradient(155deg, rgba(100, 140, 185, 0.55) 0%, rgba(85, 130, 175, 0.5) 50%, rgba(75, 120, 168, 0.55) 100%);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  position: relative;
  overflow: hidden;
}

/* 装饰光晕 */
.left-panel::before {
  content: '';
  position: absolute;
  top: -60px;
  right: -60px;
  width: 220px;
  height: 220px;
  background: radial-gradient(circle, rgba(160, 200, 240, 0.3) 0%, transparent 70%);
  border-radius: 50%;
  animation: morandi-float 8s ease-in-out infinite;
}

.left-panel::after {
  content: '';
  position: absolute;
  bottom: -40px;
  left: -40px;
  width: 160px;
  height: 160px;
  background: radial-gradient(circle, rgba(180, 215, 250, 0.2) 0%, transparent 70%);
  border-radius: 50%;
  animation: morandi-float 10s ease-in-out infinite reverse;
}

@keyframes morandi-float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-12px, -16px); }
}

.quote-area {
  position: relative;
  z-index: 1;
}

.quote-icon {
  font-size: 60px;
  line-height: 1;
  color: rgba(255, 255, 255, 0.25);
  font-family: Georgia, serif;
  margin-bottom: -8px;
}

.quote-text {
  font-size: 18px;
  line-height: 1.9;
  color: rgba(255, 255, 255, 0.92);
  font-weight: 300;
  letter-spacing: 0.04em;
  margin: 0 0 16px 0;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}

.quote-author {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.65);
  letter-spacing: 0.06em;
  margin: 0;
}

.brand {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.brand-name {
  font-size: 20px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.95);
  letter-spacing: 0.15em;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.brand-slogan {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  letter-spacing: 0.05em;
}

/* ── 右侧面板 ── */
.right-panel {
  width: 360px;
  padding: 48px 40px;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.form-header {
  margin-bottom: 28px;
}

.form-header h2 {
  font-size: 24px;
  font-weight: 600;
  color: rgba(40, 60, 90, 0.85);
  margin: 0 0 6px 0;
  letter-spacing: 0.02em;
}

.form-header p {
  font-size: 13px;
  color: rgba(80, 100, 130, 0.5);
  margin: 0;
}

/* ── Tab 切换 ── */
.tab-switch {
  display: flex;
  gap: 4px;
  margin-bottom: 24px;
  background: rgba(150, 175, 210, 0.12);
  border-radius: 10px;
  padding: 3px;
}

.tab-switch button {
  flex: 1;
  padding: 8px;
  border-radius: 8px;
  font-size: 14px;
  color: rgba(80, 100, 130, 0.45);
  background: none;
  border: none;
  cursor: pointer;
  transition: all 0.25s;
}

.tab-switch button.active {
  background: rgba(255, 255, 255, 0.55);
  color: rgba(50, 80, 120, 0.9);
  font-weight: 600;
  box-shadow: 0 1px 4px rgba(80, 110, 150, 0.06);
}

/* ── 表单 ── */
.form-body {
  display: flex;
  flex-direction: column;
}

.input-group {
  margin-bottom: 16px;
}

.input-group label {
  display: block;
  font-size: 12px;
  color: rgba(60, 85, 115, 0.55);
  margin-bottom: 6px;
  letter-spacing: 0.04em;
}

.input {
  width: 100%;
  padding: 11px 14px;
  background: rgba(255, 255, 255, 0.35);
  border: 1px solid rgba(150, 175, 210, 0.3);
  border-radius: 10px;
  color: rgba(30, 50, 80, 0.85);
  font-size: 14px;
  transition: border-color 0.2s, background 0.2s;
  outline: none;
}

.input::placeholder {
  color: rgba(140, 160, 190, 0.4);
}

.input:focus {
  border-color: rgba(100, 140, 190, 0.45);
  background: rgba(255, 255, 255, 0.5);
}

/* ── 按钮 ── */
.btn-primary {
  width: 100%;
  padding: 13px;
  margin-top: 4px;
  background: linear-gradient(135deg, rgba(90, 135, 180, 0.75), rgba(75, 120, 165, 0.75));
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.12em;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.15s;
  box-shadow: 0 4px 20px rgba(90, 125, 168, 0.2);
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.88;
  transform: translateY(-1px);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── 加载动画 ── */
.loading-dot {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── 错误提示 ── */
.error {
  font-size: 12px;
  color: #a06060;
  margin-bottom: 10px;
  margin-top: -6px;
  padding-left: 2px;
}

/* ── 找回密码弹窗 ── */
.form-extras { text-align: center; margin-top: 12px; }
.link-forgot { background: none; border: none; font-size: 12px; color: rgba(90, 135, 180, 0.7); cursor: pointer; transition: color 0.2s; }
.link-forgot:hover { color: rgba(90, 135, 180, 1); }

.forgot-modal { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; backdrop-filter: blur(4px); }
.forgot-panel { background: white; border-radius: 20px; width: min(360px, 90vw); padding: 28px; box-shadow: 0 20px 60px rgba(0,0,0,0.15); }
.forgot-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.forgot-header h3 { font-size: 18px; color: rgba(40, 60, 90, 0.85); margin: 0; }
.forgot-close { background: none; border: none; font-size: 18px; color: #999; cursor: pointer; }
.forgot-body { display: flex; flex-direction: column; gap: 12px; }
.forgot-hint { font-size: 12px; color: rgba(80, 100, 130, 0.5); margin: 0 0 4px; }
.forgot-error { font-size: 12px; color: #a06060; margin: 0; }
.forgot-success { font-size: 14px; color: #5B8C7E; margin: 0; padding: 10px; background: rgba(91,140,126,0.08); border-radius: 10px; }
.forgot-success strong { color: #3D6B5E; font-size: 16px; letter-spacing: 0.1em; }

/* ── 响应式 ── */
@media (max-width: 600px) {
  .login-container { flex-direction: column; width: 92vw; min-height: auto; }
  .left-panel { padding: 32px 28px 24px; border-right: none; border-bottom: 1px solid rgba(255,255,255,0.25); }
  .right-panel { width: 100%; padding: 28px 28px 36px; }
  .quote-text { font-size: 15px; }
}
</style>
