<template>
  <div class="app-container" v-if="userStore.userId" :class="{ 'admin-full': route.path === '/admin', 'room-full': route.path === '/', 'chat-full': route.path === '/chat' }">
    <router-view class="page-content" />
    <!-- 房间主页和管理后台不显示底部导航 -->
    <nav class="bottom-nav" v-if="route.path !== '/admin' && route.path !== '/'">
      <router-link to="/" :class="{ active: route.path === '/' }" @click="router.push('/')">
        <span class="nav-icon">🏠</span>
        <span class="nav-label">首页</span>
      </router-link>
      <router-link to="/chat" :class="{ active: route.path === '/chat' }" @click="router.push('/chat')">
        <span class="nav-icon">💬</span>
        <span class="nav-label">倾诉</span>
      </router-link>
      <router-link to="/trend" :class="{ active: route.path === '/trend' }" @click="router.push('/trend')">
        <span class="nav-icon">📊</span>
        <span class="nav-label">趋势</span>
      </router-link>
      <router-link to="/profile" :class="{ active: route.path === '/profile' }" @click="router.push('/profile')">
        <span class="nav-icon">👤</span>
        <span class="nav-label">我的</span>
      </router-link>
    </nav>
  </div>
  <LoginView v-else />
</template>

<script setup>
import { useRoute, useRouter } from "vue-router";
import { useUserStore } from "./stores/user";
import LoginView from "./views/LoginView.vue";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
</script>

<style scoped>
.app-container {
  max-width: 100%;
  margin: 0 auto;
  min-height: 100vh;
  background: var(--bg);
  position: relative;
  padding-bottom: 70px;
}

/* 手机端居中窄布局 */
@media (min-width: 768px) {
  .app-container {
    max-width: 480px;
    margin: 0 auto;
    box-shadow: 0 0 40px rgba(0,0,0,0.06);
  }
  /* 房间主页电脑端全屏 */
  .app-container.room-full {
    max-width: 100% !important;
    box-shadow: none !important;
  }
  /* 聊天页电脑端全屏 */
  .app-container.chat-full {
    max-width: 100% !important;
    box-shadow: none !important;
  }
}

/* 管理后台使用全宽 */
.admin-full {
  max-width: 100% !important;
  box-shadow: none !important;
}
/* 房间主页全屏无内边距 */
.room-full .page-content {
  padding: 0;
}
.page-content {
  padding: 16px;
}
@media (min-width: 768px) {
  .page-content {
    padding: 24px;
  }
  .room-full .page-content {
    padding: 0;
  }
}
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 100%;
  display: flex;
  justify-content: space-around;
  align-items: center;
  height: 60px;
  background: var(--card);
  border-top: 1px solid var(--border);
  z-index: 100;
  box-shadow: 0 -2px 8px rgba(0,0,0,0.04);
}
@media (min-width: 768px) {
  .bottom-nav {
    max-width: 480px;
  }
  .room-full .bottom-nav,
  .chat-full .bottom-nav {
    max-width: 100%;
    left: 0;
    transform: none;
  }
}
.bottom-nav a {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-decoration: none;
  color: var(--text-secondary);
  font-size: 12px;
  flex: 1;
  padding: 6px 0;
  transition: color 0.2s;
}
.bottom-nav a.active {
  color: var(--primary);
}
.nav-icon {
  font-size: 22px;
  margin-bottom: 2px;
}
</style>
