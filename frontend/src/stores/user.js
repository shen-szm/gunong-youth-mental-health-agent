import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { closeSession, getCurrentSession } from "../api/user";

export const useUserStore = defineStore("user", () => {
  const userId = ref(localStorage.getItem("shengyu_user_id") || "");
  const nickname = ref(localStorage.getItem("shengyu_nickname") || "");
  const isAdmin = ref(localStorage.getItem("shengyu_is_admin") === "1");
  const isSuperAdmin = ref(localStorage.getItem("shengyu_is_super_admin") === "1");
  const isGuest = ref(localStorage.getItem("shengyu_is_guest") === "1");
  const role = ref(localStorage.getItem("shengyu_role") || (isAdmin.value ? "teacher" : "student"));
  const realName = ref(localStorage.getItem("shengyu_real_name") || "");
  const className = ref(localStorage.getItem("shengyu_class_name") || "");
  const studentNo = ref(localStorage.getItem("shengyu_student_no") || "");
  const sessionChecked = ref(false);
  let studentSessionPromise = null;

  const isLoggedIn = computed(() => !!userId.value);
  const isRealUser = computed(() => isLoggedIn.value && !isGuest.value);

  function login(id, name, admin = false, superAdmin = false, userRole = "", guest = false, profile = null) {
    isGuest.value = guest;
    userId.value = guest ? "" : id;
    nickname.value = name;
    isAdmin.value = admin;
    isSuperAdmin.value = superAdmin;
    role.value = userRole || (superAdmin ? "admin_teacher" : admin ? "teacher" : "student");
    realName.value = guest ? "" : (profile?.real_name || "");
    className.value = guest ? "" : (profile?.class_name || "");
    studentNo.value = guest ? "" : (profile?.student_no || "");
    localStorage.setItem("shengyu_user_id", userId.value);
    localStorage.setItem("shengyu_nickname", name);
    localStorage.setItem("shengyu_is_admin", admin ? "1" : "0");
    localStorage.setItem("shengyu_is_super_admin", superAdmin ? "1" : "0");
    localStorage.setItem("shengyu_is_guest", guest ? "1" : "0");
    localStorage.setItem("shengyu_role", role.value);
    localStorage.setItem("shengyu_real_name", realName.value);
    localStorage.setItem("shengyu_class_name", className.value);
    localStorage.setItem("shengyu_student_no", studentNo.value);
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
    isGuest.value = false;
    role.value = "student";
    realName.value = "";
    className.value = "";
    studentNo.value = "";
    localStorage.removeItem("shengyu_user_id");
    localStorage.removeItem("shengyu_nickname");
    localStorage.removeItem("shengyu_is_admin");
    localStorage.removeItem("shengyu_is_super_admin");
    localStorage.removeItem("shengyu_is_guest");
    localStorage.removeItem("shengyu_role");
    localStorage.removeItem("shengyu_real_name");
    localStorage.removeItem("shengyu_class_name");
    localStorage.removeItem("shengyu_student_no");
  }

  // 只恢复已有登录会话；绝不自动创建游客，游客由 enterGuestMode 显式进入。
  async function ensureStudentSession(forceRefresh = false) {
    if (!forceRefresh && sessionChecked.value) return null;
    if (studentSessionPromise) return studentSessionPromise;

    studentSessionPromise = (async () => {
      try {
        const response = await getCurrentSession();
        const data = response.data;
        login(data.user_id, data.nickname, !!data.is_admin, !!data.is_super_admin, data.role, !!data.is_guest, data);
        return data;
      } catch {
        if (!isGuest.value) clearLocalSession();
        return null;
      } finally {
        sessionChecked.value = true;
        studentSessionPromise = null;
      }
    })();
    return studentSessionPromise;
  }

  function enterGuestMode() {
    login("", "游客", false, false, "student", true);
    sessionChecked.value = true;
  }

  return {
    userId, nickname, isAdmin, isSuperAdmin, role, isGuest, isLoggedIn, isRealUser,
    realName, className, studentNo,
    login, logout, ensureStudentSession, enterGuestMode,
  };
});
