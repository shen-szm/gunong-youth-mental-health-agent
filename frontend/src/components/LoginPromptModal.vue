<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="login-prompt-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="login-prompt-title"
      @click.self="close"
    >
      <div class="login-prompt-card">
        <h2 id="login-prompt-title">登录后即可使用</h2>
        <p>游客可以浏览心岛，倾诉、游戏和记录心情需要登录后才能使用。</p>
        <div class="login-prompt-actions">
          <button type="button" class="btn-primary" @click="goLogin">去登录</button>
          <button type="button" class="btn-ghost" @click="close">继续逛逛</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LOGIN_REQUIRED_EVENT } from '../api/http'

const open = ref(false)
const route = useRoute()
const router = useRouter()

function onLoginRequired() {
  if (route.path === '/login' || route.path === '/teacher-login') return
  open.value = true
}

function close() {
  open.value = false
}

function goLogin() {
  open.value = false
  router.push({ path: '/login', query: { redirect: route.fullPath } })
}

onMounted(() => window.addEventListener(LOGIN_REQUIRED_EVENT, onLoginRequired))
onUnmounted(() => window.removeEventListener(LOGIN_REQUIRED_EVENT, onLoginRequired))
</script>

<style scoped>
.login-prompt-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(20, 28, 24, .42);
  backdrop-filter: blur(4px);
}

.login-prompt-card {
  width: min(360px, 100%);
  padding: 26px 24px 22px;
  border-radius: 20px;
  background: #fff;
  box-shadow: 0 24px 60px rgba(20, 28, 24, .28);
  text-align: center;
  color: var(--m-ink, #2c3b35);
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.login-prompt-card h2 {
  margin: 0 0 10px;
  font-size: 19px;
  font-weight: 600;
}

.login-prompt-card p {
  margin: 0 0 20px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--m-ink-3, #6d7c76);
}

.login-prompt-actions {
  display: grid;
  gap: 10px;
}

.btn-primary {
  min-height: 44px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #7C8B7D, #7C8B7D);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: .08em;
  cursor: pointer;
}

.btn-ghost {
  min-height: 40px;
  border: 1px solid var(--m-line, #d9e2dc);
  border-radius: 12px;
  background: transparent;
  color: var(--m-ink-2, #4a5a53);
  font-size: 13px;
  cursor: pointer;
}
</style>
