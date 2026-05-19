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

// 全局路由守卫：未登录跳转登录页
router.beforeEach((to, from, next) => {
  const userStore = useUserStore();
  const needAuth = to.path !== "/login";
  if (needAuth && !userStore.isLoggedIn) {
    next("/login");
  } else {
    next();
  }
});

export default router;
