import { createRouter, createWebHistory } from "vue-router";
import RoomHomeView from "./views/RoomHomeView.vue";
import HomeView from "./views/HomeView.vue";
import LoginView from "./views/LoginView.vue";
import StudentLoginView from "./views/StudentLoginView.vue";
import StudentChatView from "./views/StudentChatView.vue";
import TrendView from "./views/TrendView.vue";
import ProfileView from "./views/ProfileView.vue";
import AdminView from "./views/AdminView.vue";
import GuardianHomeView from "./views/GuardianHomeView.vue";
import GuardianIntakeView from "./views/GuardianIntakeView.vue";
import GuardianCaseView from "./views/GuardianCaseView.vue";
import GuardianFollowUpsView from "./views/GuardianFollowUpsView.vue";
import { useUserStore } from "./stores/user";

const routes = [
  { path: "/", name: "Home", component: RoomHomeView, meta: { guestViewable: true } },
  { path: "/room", redirect: "/" },
  { path: "/home", name: "OldHome", component: HomeView, meta: { guestViewable: true } },
  { path: "/login", name: "StudentLogin", component: StudentLoginView },
  { path: "/teacher-login", name: "Login", component: LoginView },
  { path: "/chat", name: "Chat", component: StudentChatView, meta: { requiresRealUser: true } },
  { path: "/trend", name: "Trend", component: TrendView, meta: { requiresRealUser: true } },
  { path: "/profile", name: "Profile", component: ProfileView, meta: { guestViewable: true } },
  { path: "/admin", name: "Admin", component: AdminView, meta: { requiresTeacher: true } },
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

// 只恢复已有会话，绝不自动创建游客；游客由登录页的“先随便逛逛”显式进入。
router.beforeEach(async (to) => {
  const userStore = useUserStore();
  await userStore.ensureStudentSession();

  if (to.path === "/login" && userStore.isRealUser) {
    return typeof to.query.redirect === "string" ? to.query.redirect : "/";
  }
  if (to.path === "/teacher-login" && userStore.isAdmin) {
    return "/admin";
  }
  if (to.meta?.requiresTeacher && !userStore.isAdmin) {
    return { path: "/teacher-login", query: { redirect: to.fullPath } };
  }
  if (to.meta?.requiresRealUser && !userStore.isRealUser) {
    return { path: "/login", query: { redirect: to.fullPath } };
  }
  return true;
});

export default router;
