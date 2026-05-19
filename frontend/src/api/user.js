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

// 导出基础实例供AdminView使用
export default instance;
