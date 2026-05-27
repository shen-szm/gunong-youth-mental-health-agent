import axios from "axios";

const instance = axios.create({ baseURL: "/api/user" });

export function register(username, password, nickname) {
  return instance.post("/register", { username, password, nickname });
}
export function login(username, password) {
  return instance.post("/login", { username, password });
}
export function getProfile(userId) {
  return instance.get(`/${userId}`);
}
export function updateProfile(userId, nickname, avatar) {
  return instance.put(`/${userId}`, null, { params: { nickname, avatar } });
}

export function recoverPassword(username) {
  return instance.get("/recover-password", { params: { username } });
}

export function resetPassword(userId, adminId, newPassword) {
  return instance.post(`/reset-password/${userId}`, null, { params: { admin_id: adminId, new_password: newPassword } });
}

// 导出基础实例供AdminView使用
export default instance;
