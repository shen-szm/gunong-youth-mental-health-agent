<template>
  <div class="student-login">
    <div class="login-shell">
      <div class="login-card">
        <section class="brand-panel">
          <div class="brand">
            <span class="brand-mark" aria-hidden="true">咕</span>
            <span class="brand-copy">
              <span class="brand-name">咕哝</span>
              <span class="brand-slogan">让每一句心声，都被温柔以待</span>
            </span>
          </div>
          <p class="welcome">登录之后，心岛上的每一处都能陪你玩。</p>
          <ul class="perks">
            <li>倾诉与记录心情</li>
            <li>心岛游戏与咕团陪伴</li>
            <li>成长回顾与情绪小结</li>
          </ul>
        </section>

        <section class="form-panel">
          <header class="form-head">
            <h1>{{ mode === 'login' ? '欢迎回来' : '创建账号' }}</h1>
            <p>{{ mode === 'login' ? '登录后解锁全部功能' : '注册一个账号，开始心岛之旅' }}</p>
          </header>

          <div class="tab-switch" role="tablist" aria-label="登录或注册">
            <button type="button" role="tab" :aria-selected="mode === 'login'" :class="{ active: mode === 'login' }" @click="switchMode('login')">登录</button>
            <button type="button" role="tab" :aria-selected="mode === 'register'" :class="{ active: mode === 'register' }" @click="switchMode('register')">注册</button>
          </div>

          <form class="form-body" novalidate @submit.prevent="handleSubmit">
            <div class="input-group">
              <label for="student-username">用户名</label>
              <input
                id="student-username"
                v-model.trim="form.username"
                name="username"
                placeholder="请输入用户名"
                class="input"
                autocomplete="username"
              />
            </div>
            <div v-if="mode === 'register'" class="input-group">
              <label for="student-realname">姓名</label>
              <input
                id="student-realname"
                v-model.trim="form.realName"
                name="realName"
                placeholder="请输入真实姓名"
                class="input"
                autocomplete="name"
              />
            </div>
            <div v-if="mode === 'register'" class="input-group">
              <label for="student-class">班级</label>
              <input
                id="student-class"
                v-model.trim="form.className"
                name="className"
                placeholder="例如 初二（3）班"
                class="input"
                autocomplete="organization"
              />
            </div>
            <div v-if="mode === 'register'" class="input-group">
              <label for="student-no">学号</label>
              <input
                id="student-no"
                v-model.trim="form.studentNo"
                name="studentNo"
                placeholder="字母、数字或短横线"
                class="input"
                autocomplete="off"
              />
            </div>
            <div v-if="mode === 'register'" class="input-group">
              <label for="student-nickname">昵称</label>
              <input
                id="student-nickname"
                v-model.trim="form.nickname"
                name="nickname"
                placeholder="希望我们怎么称呼你？（可选）"
                class="input"
                autocomplete="nickname"
              />
            </div>
            <div class="input-group">
              <label for="student-password">密码</label>
              <div class="input-affix">
                <input
                  id="student-password"
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  name="password"
                  :placeholder="mode === 'register' ? '至少 10 位' : '请输入密码'"
                  class="input"
                  :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
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

            <p v-if="error" class="form-message is-error" role="alert">{{ error }}</p>
            <p v-else-if="notice" class="form-message is-success" role="status">{{ notice }}</p>

            <button type="submit" class="btn-primary" :disabled="loading">
              <span v-if="loading" class="loading-dot" aria-hidden="true"></span>
              <span v-else>{{ mode === 'login' ? '登 录' : '注 册' }}</span>
            </button>
          </form>

          <div class="guest-row">
            <button type="button" class="btn-guest" @click="enterGuest">先随便逛逛</button>
            <p class="guest-hint">游客可以浏览，但倾诉、游戏等功能需要登录后使用。</p>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Eye, EyeOff } from '@lucide/vue'
import { useUserStore } from '../stores/user'
import { register, login } from '../api/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const mode = ref('login')
const loading = ref(false)
const error = ref('')
const notice = ref('')
const showPassword = ref(false)
const form = ref({
  username: '',
  password: '',
  nickname: '',
  realName: '',
  className: '',
  studentNo: '',
})

const USERNAME_PATTERN = /^[A-Za-z0-9_.-]{3,50}$/
const STUDENT_NO_PATTERN = /^[A-Za-z0-9-]{3,40}$/

function errorMessage(e, fallback) {
  const detail = e?.response?.data?.detail
  return typeof detail === 'string' && detail ? detail : fallback
}

function switchMode(next) {
  if (mode.value === next) return
  mode.value = next
  error.value = ''
  notice.value = ''
  showPassword.value = false
}

function goAfterAuth(data) {
  userStore.login(data.user_id, data.nickname, !!data.is_admin, !!data.is_super_admin, data.role, !!data.is_guest, data)
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
  router.push(redirect)
}

async function handleSubmit() {
  if (loading.value) return
  error.value = ''
  notice.value = ''
  if (!form.value.username || !form.value.password) {
    error.value = '请填写用户名和密码'
    return
  }
  if (mode.value === 'register') {
    if (!USERNAME_PATTERN.test(form.value.username)) {
      error.value = '用户名需为 3-50 位字母、数字、下划线、点或短横线'
      return
    }
    if (form.value.password.length < 10) {
      error.value = '密码至少需要 10 位'
      return
    }
    if (!form.value.realName) {
      error.value = '请填写姓名'
      return
    }
    if (!form.value.className) {
      error.value = '请填写班级'
      return
    }
    if (!STUDENT_NO_PATTERN.test(form.value.studentNo)) {
      error.value = '学号需为 3-40 位字母、数字或短横线'
      return
    }
  }
  loading.value = true
  try {
    if (mode.value === 'login') {
      const resp = await login(form.value.username, form.value.password)
      goAfterAuth(resp.data)
    } else {
      const resp = await register(
        form.value.username,
        form.value.password,
        form.value.nickname,
        form.value.realName,
        form.value.className,
        form.value.studentNo,
      )
      goAfterAuth(resp.data)
    }
  } catch (e) {
    error.value = errorMessage(e, '操作失败，请重试')
  } finally {
    loading.value = false
  }
}

function enterGuest() {
  userStore.enterGuestMode()
  router.push('/')
}
</script>

<style scoped>
* { box-sizing: border-box; }

.student-login {
  position: relative;
  width: 100%;
  min-height: 100dvh;
  overflow-x: hidden;
  background: #F7F3E8;
  color: var(--m-ink, #2A3245);
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

.login-card {
  display: grid;
  grid-template-columns: minmax(0, 1.02fr) minmax(340px, .98fr);
  width: min(920px, 100%);
  min-height: 540px;
  border-radius: 16px;
  overflow: hidden;
  background: #FDFBF6;
  border: 1px solid #E4DED0;
  box-shadow: 0 18px 44px rgba(46, 58, 89, .10);
}

.brand-panel {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 36px;
  padding: 52px 44px;
  background: #2E3A59;
  color: #F2EEE4;
  position: relative;
  overflow: hidden;
}

.brand { position: relative; z-index: 1; display: flex; align-items: center; gap: 12px; }

.brand-mark {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 8px;
  background: #66BB8D;
  border: 1px solid #8FCBA6;
  color: #2E3A59;
  font-size: 15px;
  font-weight: 700;
}

.brand-copy { display: grid; gap: 3px; }
.brand-name { font-size: 17px; font-weight: 600; letter-spacing: .22em; }
.brand-slogan { font-size: 11px; color: #E9C4C8; letter-spacing: .04em; }

.welcome {
  position: relative;
  z-index: 1;
  font-size: 19px;
  line-height: 1.9;
  font-weight: 300;
  color: #F2EEE4;
  margin: 0;
  text-wrap: pretty;
}

.perks {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 13px;
  color: #BFC4D1;
}

.perks li::before {
  content: '◇';
  margin-right: 8px;
  color: #E8C783;
}

.form-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 52px 46px;
  background: #FDFBF6;
}

.form-head { margin-bottom: 24px; }
.form-head h1 { font-size: 27px; font-weight: 600; margin: 0 0 7px; letter-spacing: .01em; }
.form-head p { font-size: 13px; color: var(--m-ink-3, #868C9B); margin: 0; }

.tab-switch {
  display: flex;
  gap: 4px;
  margin-bottom: 22px;
  background: #F1EBDB;
  border-radius: 12px;
  padding: 4px;
}

.tab-switch button {
  flex: 1;
  padding: 8px;
  border-radius: 9px;
  font-size: 13.5px;
  color: var(--m-ink-3, #868C9B);
  background: none;
  border: none;
  cursor: pointer;
  transition: background .2s var(--m-ease, ease), color .2s var(--m-ease, ease), box-shadow .2s var(--m-ease, ease);
}

.tab-switch button.active {
  background: #fff;
  color: var(--m-accent-strong, #55A87C);
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(46, 58, 89, .10);
}

.form-body { display: flex; flex-direction: column; }
.input-group { margin-bottom: 16px; }
.input-group label { display: block; font-size: 12px; font-weight: 600; color: var(--m-ink-2, #5A6478); margin-bottom: 7px; letter-spacing: .03em; }
.input-affix { position: relative; }

.input {
  width: 100%;
  padding: 12px 14px;
  background: #FDFBF6;
  border: 1px solid #E4DED0;
  border-radius: 10px;
  color: var(--m-ink, #2A3245);
  font-size: 14px;
  outline: none;
  transition: border-color .18s var(--m-ease, ease), box-shadow .18s var(--m-ease, ease), background .18s var(--m-ease, ease);
}

.input::placeholder { color: #868C9B; }
.input:focus { border-color: var(--m-accent, #55A87C); background: #fff; box-shadow: 0 0 0 3px rgba(85, 168, 124, .18); }
.input-affix .input { padding-right: 46px; }

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
  color: var(--m-ink-3, #868C9B);
  cursor: pointer;
}

.btn-primary {
  width: 100%;
  min-height: 46px;
  margin-top: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #55A87C;
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: .10em;
  cursor: pointer;
  box-shadow: 0 6px 16px rgba(85, 168, 124, .26);
  transition: transform .18s var(--m-ease, ease), box-shadow .18s var(--m-ease, ease), opacity .18s var(--m-ease, ease);
}

.btn-primary:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 10px 22px rgba(85, 168, 124, .32); }
.btn-primary:disabled { opacity: .6; cursor: not-allowed; }

.loading-dot {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, .4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin .7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.form-message { margin: 2px 0 12px; padding: 9px 12px; border-radius: 10px; font-size: 12.5px; line-height: 1.6; }
.form-message.is-error { background: #F7E7E9; border: 1px solid #E9C4C8; color: #B95C66; }
.form-message.is-success { background: var(--m-accent-soft, #e3f2e8); border: 1px solid #c5e3d1; color: var(--m-accent-strong, #55A87C); }

.guest-row { display: grid; gap: 8px; justify-items: center; margin-top: 18px; }

.btn-guest {
  padding: 9px 22px;
  border-radius: 10px;
  border: 1px solid #E4DED0;
  background: #FDFBF6;
  color: var(--m-ink-2, #5A6478);
  font-size: 13px;
  cursor: pointer;
  transition: background .18s var(--m-ease, ease), border-color .18s var(--m-ease, ease);
}

.btn-guest:hover { background: #fff; border-color: var(--m-accent, #55A87C); }

.guest-hint { margin: 0; font-size: 11.5px; color: var(--m-ink-3, #868C9B); text-align: center; }

@media (max-width: 760px) {
  .login-shell { align-items: flex-start; padding: 12px; }
  .login-card { grid-template-columns: 1fr; width: 100%; min-height: 0; border-radius: 14px; }
  .brand-panel { gap: 18px; padding: 26px 24px 24px; }
  .welcome { font-size: 15px; line-height: 1.75; }
  .perks { display: none; }
  .form-panel { padding: 28px 24px 32px; }
  .form-head h1 { font-size: 23px; }
}
</style>
