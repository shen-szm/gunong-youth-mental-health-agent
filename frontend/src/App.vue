<template>
  <div class="app-container" :data-part="part" :class="{ 'admin-full': route.path === '/admin', 'room-full': route.path === '/', 'chat-full': route.path === '/chat', 'trend-full': route.path === '/trend', 'profile-full': route.path === '/profile', 'login-full': route.path === '/teacher-login' || route.path === '/login', 'guardian-full': route.path.startsWith('/guardian') }">
    <Transition name="page" mode="out-in">
      <div :key="route.path" class="page-wrap">
        <router-view class="page-content" />
      </div>
    </Transition>
    <div class="build-badge" :title="buildTitle">v{{ appVersion }}</div>
    <!-- 首页是学生端主入口，自带完整导航；子页共用游戏化 dock。 -->
    <nav class="bottom-nav" aria-label="主导航" v-if="showBottomNav">
      <router-link to="/" class="nav-item" :class="{ active: false }">
        <span class="nav-icon" aria-hidden="true"><House :size="20" :stroke-width="1.8" /></span>
        <span class="nav-label">首页</span>
      </router-link>
      <router-link to="/chat" class="nav-item" :class="{ active: route.path === '/chat' }">
        <span class="nav-icon" aria-hidden="true"><MessageCircle :size="20" :stroke-width="1.8" /></span>
        <span class="nav-label">倾诉</span>
      </router-link>
      <router-link to="/trend" class="nav-item" :class="{ active: route.path === '/trend' }">
        <span class="nav-icon" aria-hidden="true"><ChartLine :size="20" :stroke-width="1.8" /></span>
        <span class="nav-label">回顾</span>
      </router-link>
      <router-link to="/profile" class="nav-item" :class="{ active: route.path === '/profile' }">
        <span class="nav-icon" aria-hidden="true"><UserRound :size="20" :stroke-width="1.8" /></span>
        <span class="nav-label">我的</span>
      </router-link>
      <button type="button" class="nav-item nav-sound" :class="{ active: soundOn }" :aria-pressed="soundOn" :aria-label="soundOn ? '关闭背景音乐' : '开启背景音乐'" @click="onToggleSound">
        <span class="nav-icon" aria-hidden="true"><Volume2 v-if="soundOn" :size="20" :stroke-width="1.8" /><VolumeX v-else :size="20" :stroke-width="1.8" /></span>
        <span class="nav-label">声音</span>
      </button>
    </nav>
    <LoginPromptModal />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { House, MessageCircle, ChartLine, UserRound, Volume2, VolumeX } from "@lucide/vue";
import { isBgmOn, stopBgm, subscribeBgm, toggleBgm } from "./utils/bgm";
import { useTimeOfDay } from "./utils/timeOfDay";
import LoginPromptModal from "./components/LoginPromptModal.vue";

const route = useRoute();
const part = useTimeOfDay();
const showBottomNav = computed(() => route.path !== '/teacher-login' && route.path !== '/login' && ['/chat', '/trend', '/profile'].includes(route.path));
watch(() => route.path, path => {
  if (path === '/admin' || path === '/teacher-login' || path === '/login' || path.startsWith('/guardian')) stopBgm();
});
const soundOn = ref(isBgmOn());
let unsubscribeBgm = () => {};
onMounted(() => {
  unsubscribeBgm = subscribeBgm(value => { soundOn.value = value; });
});
onUnmounted(() => unsubscribeBgm());
async function onToggleSound() {
  soundOn.value = await toggleBgm();
}
const appVersion = import.meta.env.VITE_APP_VERSION || __APP_PACKAGE_VERSION__ || "local";
const buildTime = import.meta.env.VITE_BUILD_TIME || "";
const buildTitle = `咕哝 ${appVersion}`;
console.info('[咕哝] build', { version: appVersion, buildTime });
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
  padding-bottom: 0;
  box-shadow: none !important;
}
.admin-full .page-content {
  padding: 0;
}
.login-full {
  max-width: 100% !important;
  padding-bottom: 0;
  box-shadow: none !important;
}
.guardian-full {
  max-width: 100% !important;
  padding-bottom: 0;
  box-shadow: none !important;
  background: #F7F3E8;
}
/* 学生子页：全宽容器，页面自身居中内容；底栏与内容同宽 */
.trend-full,
.profile-full {
  max-width: 100% !important;
  box-shadow: none !important;
}
/* 学生子页容器跟随昼夜底色，避免内容下方露出浅色底 */
.chat-full[data-part],
.trend-full[data-part],
.profile-full[data-part] {
  background: #f5ecdc;
}
.chat-full[data-part="evening"],
.trend-full[data-part="evening"],
.profile-full[data-part="evening"] {
  background: #3a2c24;
}
.chat-full[data-part="night"],
.trend-full[data-part="night"],
.profile-full[data-part="night"] {
  background: #241c17;
}
.trend-full .page-content,
.profile-full .page-content {
  padding: 0;
}
.chat-full .page-content {
  padding: 0;
}
.guardian-full .page-content {
  padding: 0;
}
.login-full .page-content {
  padding: 0;
}
/* 房间主页全屏无内边距 */
.room-full .page-content {
  padding: 0;
}
.app-container.room-full {
  height: auto;
  min-height: 100dvh;
  padding-bottom: 0;
  overflow: visible;
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
  align-items: stretch;
  gap: 4px;
  height: calc(62px + env(safe-area-inset-bottom));
  padding: 4px 8px env(safe-area-inset-bottom);
  background: rgba(30, 23, 18, .96);
  border-top: 1px solid rgba(227, 194, 125, .16);
  z-index: 100;
  box-shadow: 0 -10px 26px rgba(18, 12, 8, .28);
}
.bottom-nav .nav-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  flex: 1;
  min-width: 0;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: rgba(241, 230, 210, .58);
  font-family: inherit;
  font-size: 10px;
  letter-spacing: .05em;
  text-decoration: none;
  cursor: pointer;
  transition: color var(--m-dur) var(--m-ease), background var(--m-dur) var(--m-ease);
}
.nav-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 26px;
  border-radius: 999px;
  transition: background var(--m-dur) var(--m-ease), transform var(--m-dur) var(--m-ease);
}
.bottom-nav .nav-item.active { color: #f0d29a; font-weight: 600; }
.bottom-nav .nav-item.active .nav-icon { background: rgba(227, 194, 125, .16); }
.bottom-nav .nav-item:active .nav-icon { transform: scale(.92); }
@media (min-width: 768px) {
  .bottom-nav {
    bottom: 16px;
    width: min(520px, calc(100% - 48px));
    max-width: 520px;
    height: 56px;
    padding: 5px;
    border: 1px solid rgba(227, 194, 125, .2);
    border-radius: 18px;
    box-shadow: 0 16px 40px rgba(18, 12, 8, .38), inset 0 1px 0 rgba(255, 240, 210, .08);
  }
  .chat-full .bottom-nav {
    width: min(760px, calc(100% - 24px));
    max-width: 760px;
  }
  .bottom-nav .nav-item {
    flex-direction: row;
    gap: 6px;
    font-size: 11.5px;
    letter-spacing: .02em;
  }
  .bottom-nav .nav-item:hover { background: rgba(227, 194, 125, .08); color: rgba(241, 230, 210, .82); }
  .bottom-nav .nav-item.active { background: rgba(227, 194, 125, .13); color: #f0d29a; }
  .nav-icon { width: auto; height: auto; }
  .bottom-nav .nav-item.active .nav-icon { background: transparent; }
}
.build-badge {
  position: fixed;
  right: 10px;
  bottom: 10px;
  z-index: 120;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(18, 24, 32, 0.42);
  color: rgba(255,255,255,0.74);
  font-size: 10px;
  line-height: 1.2;
  pointer-events: none;
  backdrop-filter: blur(8px);
}
.room-full .build-badge {
  bottom: 8px;
}
@media (max-width: 760px) {
  /* 窄屏底栏可见时，版本角标抬到导航上方，避免压住“我的” */
  .build-badge {
    right: 8px;
    bottom: calc(66px + env(safe-area-inset-bottom));
  }
  .room-full .build-badge {
    right: 8px;
    bottom: calc(96px + env(safe-area-inset-bottom));
  }
}
.login-full .build-badge {
  display: none;
}
.guardian-full .build-badge {
  display: none;
}
.admin-full .build-badge {
  display: none;
}
/* 学生端把版本号收进房间页脚，避免角标压住底栏和内容 */
.room-full .build-badge,
.chat-full .build-badge,
.trend-full .build-badge,
.profile-full .build-badge {
  display: none;
}

/* v5.1.0-alpha.41 页面切换淡出淡入。
   Transition 的直接子节点是带 :key="route.path" 的包裹层 —— 只有 key 变化时
   out-in 才会真正排序；router-view 自身 vnode 类型不变，直接包裹时不生效。 */
.page-enter-active { transition: opacity 220ms var(--m-ease-soft), transform 220ms var(--m-ease-soft); }
.page-leave-active { transition: opacity 140ms ease; }
.page-enter-from { opacity: 0; transform: translateY(8px) scale(.988); }
.page-leave-to { opacity: 0; }

/* 像素皮肤 3.0 · 学生底栏 */
.bottom-nav {
  border-top: 2px solid rgba(227, 194, 125, .24);
  box-shadow: 0 -4px 0 rgba(18, 12, 8, .18);
}
.bottom-nav .nav-item {
  border-radius: 4px;
  transition: color 160ms steps(2, end), background 160ms steps(2, end), transform 160ms steps(2, end);
}
.bottom-nav .nav-item:hover { transform: translate(-1px, -1px); }
.bottom-nav .nav-item:active { transform: translate(2px, 2px); }
/* 活跃项：底部细色条 + 图标轻微放大，与教师端侧栏活跃态同一套反馈 */
.bottom-nav .nav-item.active { box-shadow: inset 0 -2px 0 rgba(240, 210, 154, .85); }
.bottom-nav .nav-item.active .nav-icon { transform: scale(1.12); }
.bottom-nav .nav-item.active:active .nav-icon { transform: scale(1); }
.nav-icon {
  width: 38px;
  height: 24px;
  border-radius: 4px;
  background: rgba(241, 230, 210, .06);
}
.bottom-nav .nav-item.active { color: #f0d29a; }
.bottom-nav .nav-label {
  font-family: var(--px-font);
  font-size: 12px;
  letter-spacing: .02em;
  line-height: 1.2;
}
@media (min-width: 768px) {
  .bottom-nav {
    border: 2px solid rgba(227, 194, 125, .22);
    border-radius: 6px;
    padding: 4px;
  }
  .nav-icon { width: 24px; height: 24px; background: transparent; }
  .bottom-nav .nav-item { border-radius: 4px; }
  .bottom-nav .nav-item.active .nav-icon { background: transparent; }
}

@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
</style>
