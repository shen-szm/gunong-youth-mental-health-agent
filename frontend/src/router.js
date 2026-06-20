import { createRouter, createWebHistory } from "vue-router";
import RoomHomeView from "./views/RoomHomeView.vue";
import HomeView from "./views/HomeView.vue";
import LoginView from "./views/LoginView.vue";
import ChatView from "./views/ChatView.vue";
import TrendView from "./views/TrendView.vue";
import ProfileView from "./views/ProfileView.vue";
import AdminView from "./views/AdminView.vue";
import { useUserStore } from "./stores/user";

const routes = [
  { path: "/", name: "Home", component: RoomHomeView },
  { path: "/home", name: "OldHome", component: HomeView },
  { path: "/login", name: "Login", component: LoginView },
  { path: "/chat", name: "Chat", component: ChatView },
  { path: "/trend", name: "Trend", component: TrendView },
  { path: "/profile", name: "Profile", component: ProfileView },
  { path: "/admin", name: "Admin", component: AdminView },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 普通页面自动绑定演示用户；/login 保留为教师隐藏入口
router.beforeEach(async (to) => {
  const userStore = useUserStore();
  if (to.path === "/login") return true;

  if (!userStore.isLoggedIn) {
    try {
      await userStore.ensureDemoSession();
    } catch {
      return "/login";
    }
  }

  return true;
});

export default router;
