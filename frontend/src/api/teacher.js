import axios from 'axios'

const instance = axios.create({ baseURL: '/api/teacher' })

function params(userId, extra = {}) {
  return { user_id: userId, ...extra }
}

export function getTeacherOverview(userId) {
  return instance.get('/class-overview', { params: params(userId) })
}

export function getTeacherEmotionTrend(userId, days = 30) {
  return instance.get('/emotion-trend', { params: params(userId, { days }) })
}

export function getTeacherStudents(userId) {
  return instance.get('/student-list', { params: params(userId) })
}

export function getTeacherWarnings(userId) {
  return instance.get('/warning-list', { params: params(userId) })
}

export function getTeacherWarningDetail(warningId, userId) {
  return instance.get(`/warning/${warningId}/detail`, { params: params(userId) })
}

export function handleTeacherWarning(warningId, userId, note) {
  return instance.post(`/warning/${warningId}/handle`, { note }, { params: params(userId) })
}

export function getLessonTemplates(userId) {
  return instance.get('/lesson-plan/templates', { params: params(userId) })
}

export function generateLesson(userId, payload) {
  return instance.post('/lesson-plan/generate', payload, { params: params(userId) })
}

export function getStudentProfile(studentId, userId) {
  return instance.get(`/students/${studentId}/profile`, { params: params(userId) })
}

export function requestSensitiveContext(studentId, userId, reason) {
  return instance.post(`/students/${studentId}/sensitive-context/access`, { reason }, { params: params(userId) })
}

export function getTeacherAccounts(userId) {
  return instance.get('/accounts', { params: params(userId) })
}

export function updateTeacherAccount(accountId, userId, payload) {
  return instance.patch(`/accounts/${accountId}`, payload, { params: params(userId) })
}

export default instance
