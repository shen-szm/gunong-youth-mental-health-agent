import { createApi } from "./http";

const instance = createApi("/api/user");

export function register(username, password, nickname, realName, className, studentNo) {
  return instance.post("/register", {
    username,
    password,
    nickname,
    real_name: realName,
    class_name: className,
    student_no: studentNo,
  });
}
export function login(username, password) {
  return instance.post("/login", { username, password });
}
export function createGuestSession() {
  return instance.post("/guest-session");
}
export function getCurrentSession() {
  return instance.get("/me");
}
export function closeSession() {
  return instance.post("/logout");
}
export function getProfile(userId) {
  return instance.get(`/${userId}`);
}
export function updateProfile(userId, nickname, avatar) {
  return instance.put(`/${userId}`, null, { params: { nickname, avatar } });
}

export function resetPassword(userId, adminId, newPassword) {
  return instance.post(`/reset-password/${userId}`, null, { params: { admin_id: adminId, new_password: newPassword } });
}

export function changePassword(userId, oldPassword, newPassword1, newPassword2) {
  return instance.post("/change-password", { user_id: userId, old_password: oldPassword, new_password1: newPassword1, new_password2: newPassword2 });
}

// 导出基础实例供AdminView使用
export default instance;
