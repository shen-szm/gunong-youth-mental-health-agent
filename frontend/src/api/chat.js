import axios from "axios";

const instance = axios.create({ baseURL: "/api/chat" });

export function sendMessage(userId, content, inputType = "text") {
  return instance.post("/send", { user_id: userId, message: content, input_type: inputType });
}
export function getChatHistory(userId) {
  return instance.get("/history", { params: { user_id: userId, limit: 50 } });
}
