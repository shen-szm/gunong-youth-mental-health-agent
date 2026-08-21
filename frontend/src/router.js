import { createRouter, createWebHistory } from "vue-router";
import RoomHomeView from "./views/RoomHomeView.vue";
import HomeView from "./views/HomeView.vue";
import LoginView from "./views/LoginView.vue";
import ChatView from "./views/ChatView.vue";
import TrendView from "./views/TrendView.vue";
import ProfileView from "./views/ProfileView.vue";
import AdminView from "./views/AdminView.vue";
import GuardianHomeView from "./views/GuardianHomeView.vue";
import GuardianIntakeView from "./views/GuardianIntakeView.vue";
import GuardianCaseView from "./views/GuardianCaseView.vue";
import GuardianFollowUpsView from "./views/GuardianFollowUpsView.vue";
import { useUserStore } from "./stores/user";

const routes = [
  { path: "/", name: "Home", component: RoomHomeView },
  { path: "/home", name: "OldHome", component: HomeView },
  { path: "/login", redirect: "/" },
  { path: "/teacher-login", name: "Login", component: LoginView },
  { path: "/chat", name: "Chat", component: ChatView },
  { path: "/trend", name: "Trend", component: TrendView },
  { path: "/profile", name: "Profile", component: ProfileView },
  { path: "/admin", name: "Admin", component: AdminView },
  { path: "/guardian", name: "GuardianHome", component: GuardianHomeView },
  { path: "/guardian/new", name: "GuardianNew", component: GuardianIntakeView },
  { path: "/guardian/cases/:caseId", name: "GuardianCase", component: GuardianCaseView },
  { path: "/guardian/follow-ups", name: "GuardianFollowUps", component: GuardianFollowUpsView },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 };
  },
});

// 普通页面自动绑定演示用户；/teacher-login 保留为教师隐藏入口
router.beforeEach(async (to) => {
  const userStore = useUserStore();
  if (to.path === "/teacher-login") return true;

  if (to.path === "/admin" && !userStore.isAdmin) {
    return { path: "/teacher-login", query: { redirect: to.fullPath } };
  }

  try {
    await userStore.ensureDemoSession();
  } catch {
    return { path: "/teacher-login", query: { redirect: to.fullPath } };
  }

  if (to.path === "/admin" && !userStore.isAdmin) {
    return { path: "/teacher-login", query: { redirect: to.fullPath } };
  }

  return true;
});

export default router;
