import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { createDemoSession } from "../api/user";

export const useUserStore = defineStore("user", () => {
  const userId = ref(localStorage.getItem("shengyu_user_id") || "");
  const nickname = ref(localStorage.getItem("shengyu_nickname") || "");
  const isAdmin = ref(localStorage.getItem("shengyu_is_admin") === "1");
  let demoSessionPromise = null;

  const isLoggedIn = computed(() => !!userId.value);

  function login(id, name, admin = false) {
    userId.value = id;
    nickname.value = name;
    isAdmin.value = admin;
    localStorage.setItem("shengyu_user_id", id);
    localStorage.setItem("shengyu_nickname", name);
    localStorage.setItem("shengyu_is_admin", admin ? "1" : "0");
  }

  function logout() {
    userId.value = "";
    nickname.value = "";
    isAdmin.value = false;
    localStorage.removeItem("shengyu_user_id");
    localStorage.removeItem("shengyu_nickname");
    localStorage.removeItem("shengyu_is_admin");
  }

  async function ensureDemoSession() {
    if (isLoggedIn.value) return;

    if (!demoSessionPromise) {
      demoSessionPromise = (async () => {
        const response = await createDemoSession();
        const data = response.data;
        login(data.user_id, data.nickname, !!data.is_admin);
        return data;
      })().finally(() => {
        demoSessionPromise = null;
      });
    }

    return demoSessionPromise;
  }

  return { userId, nickname, isAdmin, isLoggedIn, login, logout, ensureDemoSession };
});
