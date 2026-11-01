import axios from "axios";

const instance = axios.create({ baseURL: "/api/chat" });

export function startChatSession(forceNew = false, continueFromSessionId = null) {
  return instance.post("/sessions", {
    force_new: forceNew,
    continue_from_session_id: continueFromSessionId,
  });
}
export function sendMessage(_userId, content, inputType = "text", sessionId = null, idempotencyKey = null) {
  return instance.post("/send", { session_id: sessionId, message: content, input_type: inputType, idempotency_key: idempotencyKey });
}
export function getChatHistory(_userId, sessionId = null) {
  return instance.get("/history", { params: { session_id: sessionId, limit: 50 } });
}
export function getChatSessionCount() {
  return instance.get("/sessions/count");
}
export function completeChatSession(sessionId) {
  return instance.post(`/sessions/${encodeURIComponent(sessionId)}/complete`);
}
export function resolveChatSafety(sessionId, currentSafe, contactedTrustedAdult) {
  return instance.post(`/sessions/${encodeURIComponent(sessionId)}/resolve-safety`, {
    current_safe: currentSafe,
    contacted_trusted_adult: contactedTrustedAdult,
  });
}
export function createChatSafetyHandoff(source = "happiness_exchange") {
  return instance.post("/sessions/safety-handoff", { source });
}
export function getLatestChatSummary() {
  return instance.get("/sessions/latest-summary");
}
export function deleteChatSummary(sessionId) {
  return instance.delete(`/sessions/${encodeURIComponent(sessionId)}/summary`);
}
