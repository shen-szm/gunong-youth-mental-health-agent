import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { closeSession, createGuestSession, getCurrentSession } from "../api/user";

export const useUserStore = defineStore("user", () => {
  const userId = ref(localStorage.getItem("shengyu_user_id") || "");
  const nickname = ref(localStorage.getItem("shengyu_nickname") || "");
  const isAdmin = ref(localStorage.getItem("shengyu_is_admin") === "1");
  const isSuperAdmin = ref(localStorage.getItem("shengyu_is_super_admin") === "1");
  const role = ref(localStorage.getItem("shengyu_role") || (isAdmin.value ? "teacher" : "student"));
  const sessionChecked = ref(false);
  let studentSessionPromise = null;

  const isLoggedIn = computed(() => !!userId.value);

  function login(id, name, admin = false, superAdmin = false, userRole = "") {
    userId.value = id;
    nickname.value = name;
    isAdmin.value = admin;
    isSuperAdmin.value = superAdmin;
    role.value = userRole || (superAdmin ? "admin_teacher" : admin ? "teacher" : "student");
    localStorage.setItem("shengyu_user_id", id);
    localStorage.setItem("shengyu_nickname", name);
    localStorage.setItem("shengyu_is_admin", admin ? "1" : "0");
    localStorage.setItem("shengyu_is_super_admin", superAdmin ? "1" : "0");
    localStorage.setItem("shengyu_role", role.value);
  }

  async function logout() {
    try { await closeSession(); } catch {}
    clearLocalSession();
    sessionChecked.value = false;
  }

  function clearLocalSession() {
    userId.value = "";
    nickname.value = "";
    isAdmin.value = false;
    isSuperAdmin.value = false;
    role.value = "student";
    localStorage.removeItem("shengyu_user_id");
    localStorage.removeItem("shengyu_nickname");
    localStorage.removeItem("shengyu_is_admin");
    localStorage.removeItem("shengyu_is_super_admin");
    localStorage.removeItem("shengyu_role");
  }

  async function ensureStudentSession(forceRefresh = false) {
    if (!forceRefresh && sessionChecked.value && isLoggedIn.value) return;

    if (!studentSessionPromise) {
      studentSessionPromise = (async () => {
        let response;
        try {
          response = await getCurrentSession();
        } catch {
          clearLocalSession();
          response = await createGuestSession();
        }
        const data = response.data;
        login(data.user_id, data.nickname, !!data.is_admin, !!data.is_super_admin, data.role);
        sessionChecked.value = true;
        return data;
      })().finally(() => {
        studentSessionPromise = null;
      });
    }

    return studentSessionPromise;
  }

  return { userId, nickname, isAdmin, isSuperAdmin, role, isLoggedIn, login, logout, ensureStudentSession };
});
