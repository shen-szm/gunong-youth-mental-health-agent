import axios from "axios";

const instance = axios.create({ baseURL: "/api/mood" });

export function getMoodList(userId, days) {
  return instance.get("/list", { params: { user_id: userId, days } });
}
export function getMoodStats(userId, days) {
  return instance.get("/stats", { params: { user_id: userId, days } });
}
export function getMoodInsight(userId) {
  return instance.get("/insight", { params: { user_id: userId } });
}

export function getEmotionReport(days = 30) {
  return instance.get('/report', { params: { days } })
}

export function recordActivityReflection(activity, feeling, note = '') {
  return instance.post('/activity-reflection', { activity, feeling, note })
}
export function recordMood(data) {
  return instance.post("/record", data);
}
export function getTodayMood(userId) {
  return instance.get("/today", { params: { user_id: userId } });
}
