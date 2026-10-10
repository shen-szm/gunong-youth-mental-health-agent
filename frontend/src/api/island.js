import axios from "axios";

const instance = axios.create({ baseURL: "/api/island" });

// ── Agent 运行 ──
export function runIslandAgent(trigger = "login") {
  return instance.post("/agent/run", {
    trigger,
  });
}
export function getIslandAgentHistory(limit = 20) {
  return instance.get("/agent/history", { params: { limit } });
}

// ── 游戏行为日志 ──
export function logIslandBehavior(eventType, place = null, activity = null, payload = {}) {
  return instance.post("/behavior/log", {
    event_type: eventType,
    place,
    activity,
    payload,
  });
}
export function getRecentBehaviors(days = 7) {
  return instance.get("/behavior/recent", { params: { days } });
}

// ── 环境指令 ──
export function getPendingCommands() {
  return instance.get("/commands");
}
export function ackCommands(commandIds) {
  return instance.post("/commands/ack", { command_ids: commandIds });
}

// ── 咕团互动 ──
export function getPetState() {
  return instance.get("/pet/state");
}
export function interactWithPet(action, message = "") {
  return instance.post("/pet/interact", { action, message });
}

// ── 情绪报告 ──
export function generateIslandReport(days = 7) {
  return instance.post("/report/generate", { days });
}
export function listIslandReports(limit = 10) {
  return instance.get("/report/list", { params: { limit } });
}
export function getIslandReport(reportCode) {
  return instance.get(`/report/${reportCode}`);
}
export function getReportDownloadUrl(reportCode) {
  return `/api/island/report/${reportCode}/download`;
}
