<template>
  <!-- 登录页 -->
  <div class="login-page">
    <!-- 白光流星层 -->
    <canvas ref="veilRef" class="veil-canvas" :class="{ gone: veilGone }" aria-hidden="true"></canvas>

    <!-- 登录主体容器 -->
    <div class="login-shell">
    <div class="login-container" :class="{ visible: containerVisible }">
      <!-- 左侧：每日一句 -->
      <div class="left-panel">
        <div class="quote-area">
          <div class="quote-icon" aria-hidden="true">“</div>
          <p class="quote-text">{{ daily.quote }}</p>
          <p class="quote-author">—— {{ daily.author }}</p>
        </div>
        <div class="brand">
          <span class="brand-mark" aria-hidden="true">咕</span>
          <span class="brand-copy">
            <span class="brand-name">咕哝</span>
            <span class="brand-slogan">让每一句心声，都被温柔以待</span>
          </span>
        </div>
      </div>

      <!-- 右侧：登录表单 -->
      <div class="right-panel">
        <div class="form-header">
          <span class="form-kicker">咕哝 · 教师入口</span>
          <h2>教师登录</h2>
          <p>仅限教师账号进入管理后台</p>
        </div>

        <form class="form-body" novalidate @submit.prevent="handleSubmit">
          <div class="input-group">
            <label for="login-username">用户名</label>
            <input
              id="login-username"
              ref="usernameRef"
              v-model.trim="form.username"
              name="username"
              placeholder="请输入用户名"
              class="input"
              autocomplete="username"
            />
          </div>
          <div class="input-group">
            <label for="login-password">密码</label>
            <div class="input-affix">
              <input
                id="login-password"
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                name="password"
                placeholder="请输入密码"
                class="input"
                autocomplete="current-password"
              />
              <button
                type="button"
                class="password-toggle"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                :aria-pressed="showPassword"
                @click="showPassword = !showPassword"
              >
                <EyeOff v-if="showPassword" :size="17" :stroke-width="1.8" aria-hidden="true" />
                <Eye v-else :size="17" :stroke-width="1.8" aria-hidden="true" />
              </button>
            </div>
          </div>

          <p class="form-message is-error" v-if="error" role="alert">{{ error }}</p>
          <p class="form-message is-success" v-else-if="notice" role="status">{{ notice }}</p>

          <button type="submit" class="btn-primary" :disabled="loading">
            <span v-if="loading" class="loading-dot" aria-hidden="true"></span>
            <span v-else>登 录</span>
          </button>

          <div class="form-extras">
            <p class="forgot-hint">密码不会被系统展示；需要重置时请联系教师管理员。</p>
            <RouterLink class="back-home" to="/login">学生端登录</RouterLink>
          </div>
        </form>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Eye, EyeOff } from '@lucide/vue'
import { useUserStore } from '../stores/user'
import { login } from '../api/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const mode = ref('login')
const loading = ref(false)
const error = ref('')
const notice = ref('')
const showPassword = ref(false)
const form = ref({ username: '', password: '', nickname: '' })
const usernameRef = ref(null)
const veilRef = ref(null)
const containerVisible = ref(false)
const veilGone = ref(false)


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
const INTRO_KEY = 'gy_login_intro_seen'
const INTRO = { move: 220, fadeStart: 520, fadeEnd: 1000 }

function prefersReducedMotion() {
  return !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

function revealLogin() {
  containerVisible.value = true
  veilGone.value = true
}

onMounted(() => {
  let seenIntro = false
  try { seenIntro = sessionStorage.getItem(INTRO_KEY) === '1' } catch {}
  if (prefersReducedMotion() || seenIntro) {
    revealLogin()
    return
  }
  try { sessionStorage.setItem(INTRO_KEY, '1') } catch {}

  const canvas = veilRef.value
  if (!canvas) { revealLogin(); return }
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
      delay: Math.random() * 160,
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

  const startAt = performance.now()
  let revealed = false

  function draw(now) {
    const t = now - startAt

    if (!revealed && t >= INTRO.fadeStart) {
      revealed = true
      containerVisible.value = true
    }
    if (t >= INTRO.fadeEnd) {
      veilGone.value = true
      return
    }

    const masterAlpha = t <= INTRO.fadeStart
      ? 1
      : Math.max(0, 1 - (t - INTRO.fadeStart) / (INTRO.fadeEnd - INTRO.fadeStart))

    ctx.clearRect(0, 0, W, H)

    // ── 底色（渐隐） ──
    ctx.fillStyle = `rgba(240, 246, 242, ${masterAlpha * 0.94})`
    ctx.fillRect(0, 0, W, H)

    // ── 柔和光晕 ──
    glowOrbs.forEach(orb => {
      orb.phase += orb.speed
      const ox = orb.x + Math.sin(orb.phase) * 30
      const oy = orb.y + Math.cos(orb.phase * 0.7) * 20
      const grad = ctx.createRadialGradient(ox, oy, 0, ox, oy, orb.r)
      grad.addColorStop(0, `rgba(140, 200, 178, ${orb.alpha * masterAlpha})`)
      grad.addColorStop(1, 'rgba(140, 200, 178, 0)')
      ctx.fillStyle = grad
      ctx.fillRect(ox - orb.r, oy - orb.r, orb.r * 2, orb.r * 2)
    })

    // ── 流星（向后划走，空间感） ──
    if (t > INTRO.move) {
      const progress = Math.min(1, (t - INTRO.move) / (INTRO.fadeEnd - INTRO.move))

      meteors.forEach(m => {
        if (t - INTRO.move < m.delay) return

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
          headGrad.addColorStop(1, 'rgba(230, 240, 255, 0)')
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
function switchMode(next) {
  if (mode.value === next) return
  mode.value = next
  error.value = ''
  notice.value = ''
  showPassword.value = false
}

async function handleSubmit() {
  if (loading.value) return
  error.value = ''
  notice.value = ''
  if (!form.value.username || !form.value.password) {
    error.value = '请填写用户名和密码'
    return
  }
  loading.value = true
  try {
    const resp = await login(form.value.username, form.value.password)
    const data = resp.data
    if (!data.is_admin) {
      await userStore.logout()
      error.value = '该账号不是教师账号，请使用学生端登录'
      return
    }
    userStore.login(data.user_id, data.nickname, true, !!data.is_super_admin, data.role)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/admin'
    router.push(redirect)
  } catch (e) {
    const detail = e.response?.data?.detail
    error.value = typeof detail === 'string' ? detail : '操作失败，请重试'
  } finally {
    loading.value = false
  }
}

</script>

<style scoped>
* { box-sizing: border-box; }

.login-page {
  position: relative;
  width: 100%;
  min-height: 100dvh;
  overflow-x: hidden;
  background:
    radial-gradient(52vmax 42vmax at 12% 8%, rgba(140, 200, 178, .30), transparent 68%),
    radial-gradient(46vmax 40vmax at 92% 90%, rgba(232, 196, 104, .16), transparent 70%),
    linear-gradient(150deg, #eef4f0 0%, #e7efea 45%, #eef2ee 100%);
  color: var(--m-ink);
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.login-shell {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 100dvh;
  padding: clamp(16px, 4vh, 44px) 20px;
}

.login-page::before,
.login-page::after {
  content: '';
  position: fixed;
  border-radius: 50%;
  pointer-events: none;
  filter: blur(8px);
}
.login-page::before {
  top: -14vmax;
  left: -10vmax;
  width: 42vmax;
  height: 42vmax;
  background: radial-gradient(circle, rgba(189, 219, 207, .34), transparent 68%);
  animation: login-drift 22s ease-in-out infinite;
}
.login-page::after {
  right: -12vmax;
  bottom: -16vmax;
  width: 46vmax;
  height: 46vmax;
  background: radial-gradient(circle, rgba(234, 212, 154, .18), transparent 70%);
  animation: login-drift 28s ease-in-out infinite reverse;
}
@keyframes login-drift {
  0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
  50% { transform: translate3d(3%, 2%, 0) scale(1.08); }
}

/* ── 白光流星 Canvas ── */
.veil-canvas {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
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
  display: grid;
  grid-template-columns: minmax(0, 1.04fr) minmax(340px, .96fr);
  width: min(920px, 100%);
  min-height: 520px;
  border-radius: 28px;
  overflow: hidden;
  background: rgba(255, 255, 255, .64);
  backdrop-filter: blur(26px) saturate(1.2);
  -webkit-backdrop-filter: blur(26px) saturate(1.2);
  border: 1px solid rgba(255, 255, 255, .78);
  box-shadow:
    0 30px 80px rgba(34, 48, 43, .16),
    0 2px 6px rgba(34, 48, 43, .05),
    inset 0 1px 0 rgba(255, 255, 255, .9);
  opacity: 0;
  transform: translateY(22px) scale(.985);
  transition: opacity .7s var(--m-ease), transform .7s var(--m-ease);
}

.login-container.visible {
  opacity: 1;
  transform: translateY(0) scale(1);
}

/* ── 左侧面板 ── */
.left-panel {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 40px;
  padding: 52px 44px;
  background:
    radial-gradient(circle at 1px 1px, rgba(255, 255, 255, .10) 1px, transparent 1.6px),
    linear-gradient(152deg, #4E7B6D 0%, #3F6C5F 52%, #2E5046 100%);
  background-size: 24px 24px, cover;
  color: #fff;
  position: relative;
  overflow: hidden;
}

/* 装饰光晕 */
.left-panel::before {
  content: '';
  position: absolute;
  top: -70px;
  right: -60px;
  width: 240px;
  height: 240px;
  background: radial-gradient(circle, rgba(189, 219, 207, .34) 0%, transparent 70%);
  border-radius: 50%;
  animation: morandi-float 9s ease-in-out infinite;
}

.left-panel::after {
  content: '';
  position: absolute;
  bottom: -50px;
  left: -50px;
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(234, 212, 154, .22) 0%, transparent 70%);
  border-radius: 50%;
  animation: morandi-float 12s ease-in-out infinite reverse;
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
  font-size: 64px;
  line-height: 1;
  color: rgba(255, 255, 255, 0.22);
  font-family: Georgia, 'Songti SC', serif;
  margin-bottom: -10px;
}

.quote-text {
  font-size: 19px;
  line-height: 1.9;
  color: rgba(255, 255, 255, 0.94);
  font-weight: 300;
  letter-spacing: 0.03em;
  margin: 0 0 16px 0;
  text-wrap: pretty;
}

.quote-author {
  font-size: 12.5px;
  color: rgba(255, 255, 255, 0.62);
  letter-spacing: 0.06em;
  margin: 0;
}

.brand {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: rgba(255, 255, 255, .14);
  border: 1px solid rgba(255, 255, 255, .26);
  font-size: 15px;
  font-weight: 700;
}

.brand-copy {
  display: grid;
  gap: 3px;
}

.brand-name {
  font-size: 17px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.96);
  letter-spacing: 0.22em;
}

.brand-slogan {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.62);
  letter-spacing: 0.04em;
}

/* ── 右侧面板 ── */
.right-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 52px 46px;
  background: rgba(255, 255, 255, .34);
}

.form-header {
  margin-bottom: 26px;
}

.form-kicker {
  display: inline-flex;
  align-items: center;
  margin-bottom: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--m-accent-soft);
  color: var(--m-accent-strong);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: .08em;
}

.form-header h2 {
  font-size: 27px;
  font-weight: 600;
  color: var(--m-ink);
  margin: 0 0 7px 0;
  letter-spacing: 0.01em;
}

.form-header p {
  font-size: 13px;
  color: var(--m-ink-3);
  margin: 0;
}

/* ── Tab 切换 ── */
.tab-switch {
  display: flex;
  gap: 4px;
  margin-bottom: 24px;
  background: rgba(34, 48, 43, .055);
  border-radius: 12px;
  padding: 4px;
}

.tab-switch button {
  flex: 1;
  padding: 8px;
  border-radius: 9px;
  font-size: 13.5px;
  color: var(--m-ink-3);
  background: none;
  border: none;
  cursor: pointer;
  transition: background .2s var(--m-ease), color .2s var(--m-ease), box-shadow .2s var(--m-ease);
}

.tab-switch button:hover {
  color: var(--m-ink-2);
}

.tab-switch button.active {
  background: #fff;
  color: var(--m-accent-strong);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(34, 48, 43, .10);
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
  font-weight: 600;
  color: var(--m-ink-2);
  margin-bottom: 7px;
  letter-spacing: 0.03em;
}

.input-affix {
  position: relative;
}

.input {
  width: 100%;
  padding: 12px 14px;
  background: rgba(255, 255, 255, .88);
  border: 1px solid var(--m-line);
  border-radius: 12px;
  color: var(--m-ink);
  font-size: 14px;
  transition: border-color .18s var(--m-ease), box-shadow .18s var(--m-ease), background .18s var(--m-ease);
  outline: none;
}

.input::placeholder {
  color: #9aa8a2;
}

.input:hover {
  border-color: #cbd6cf;
}

.input:focus {
  border-color: var(--m-accent);
  background: #fff;
  box-shadow: 0 0 0 3px rgba(74, 122, 108, .14);
}

.input-affix .input {
  padding-right: 46px;
}

.password-toggle {
  position: absolute;
  top: 50%;
  right: 6px;
  transform: translateY(-50%);
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 9px;
  background: transparent;
  color: var(--m-ink-3);
  cursor: pointer;
  transition: background .18s var(--m-ease), color .18s var(--m-ease);
}

.password-toggle:hover {
  background: var(--m-accent-soft);
  color: var(--m-accent-strong);
}

/* ── 按钮 ── */
.btn-primary {
  width: 100%;
  min-height: 46px;
  margin-top: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: var(--m-hero-grad);
  color: #fff;
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.10em;
  cursor: pointer;
  box-shadow: var(--m-hero-shadow);
  transition: transform .18s var(--m-ease), box-shadow .18s var(--m-ease), opacity .18s var(--m-ease);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--m-hero-shadow-hover);
}

.btn-primary:active:not(:disabled) {
  transform: translateY(0);
}

.btn-primary:disabled {
  opacity: 0.6;
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

/* ── 表单提示 ── */
.form-message {
  margin: 2px 0 12px;
  padding: 9px 12px;
  border-radius: 10px;
  font-size: 12.5px;
  line-height: 1.6;
}

.form-message.is-error {
  background: #fdf0ed;
  border: 1px solid #efc9c0;
  color: #8f3f36;
}

.form-message.is-success {
  background: var(--m-accent-soft);
  border: 1px solid #cfe3d8;
  color: var(--m-accent-strong);
}

.form-extras {
  display: grid;
  gap: 8px;
  justify-items: center;
  margin-top: 16px;
}

.forgot-hint {
  margin: 0;
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--m-ink-3);
  text-align: center;
}

.back-home {
  font-size: 12px;
  color: var(--m-accent-strong);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color .18s var(--m-ease);
}

.back-home:hover {
  border-bottom-color: currentColor;
}

/* ── 响应式 ── */
@media (max-width: 760px) {
  .login-shell {
    align-items: flex-start;
    padding: 12px;
  }
  .login-container {
    grid-template-columns: 1fr;
    width: 100%;
    min-height: 0;
    border-radius: 22px;
  }
  .left-panel {
    gap: 22px;
    padding: 26px 24px 24px;
  }
  .left-panel::before {
    width: 180px;
    height: 180px;
  }
  .left-panel::after {
    display: none;
  }
  .quote-icon {
    font-size: 40px;
    margin-bottom: -6px;
  }
  .quote-text {
    font-size: 15px;
    line-height: 1.75;
    margin-bottom: 6px;
  }
  .quote-author {
    font-size: 11.5px;
  }
  .brand-mark {
    width: 32px;
    height: 32px;
    border-radius: 10px;
  }
  .brand-name {
    font-size: 15px;
  }
  .right-panel {
    padding: 28px 24px 32px;
  }
  .form-header {
    margin-bottom: 20px;
  }
  .form-header h2 {
    font-size: 23px;
  }
  .tab-switch {
    margin-bottom: 20px;
  }
}

@media (max-height: 720px) and (min-width: 761px) {
  .login-container {
    min-height: 0;
  }
  .left-panel,
  .right-panel {
    padding-top: 38px;
    padding-bottom: 38px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .login-page::before,
  .login-page::after,
  .left-panel::before,
  .left-panel::after {
    animation: none;
  }
  .login-container {
    transition: none;
  }
}
</style>
