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

export function createCaseAccessRequest(studentId, reason) {
  return instance.post(`/students/${studentId}/access-requests`, { reason, scope: 'recent_30_days' })
}

export function getCaseAccessRequests() {
  return instance.get('/access-requests')
}

export function decideCaseAccessRequest(requestId, decision, note = '') {
  return instance.post(`/access-requests/${requestId}/decision`, { decision, note })
}

export function getStudentCaseContext(studentId, requestId = null) {
  return instance.get(`/students/${studentId}/case-context`, { params: requestId ? { request_id: requestId } : {} })
}

export function getStudentWorkProduct(studentId, requestId = null) {
  return instance.get(`/students/${studentId}/work-product`, { params: requestId ? { request_id: requestId } : {} })
}

export function decideStudentWorkProductTask(studentId, productId, taskIndex, decision, requestId = null) {
  return instance.post(`/students/${studentId}/work-product/task-decisions`, {
    product_id: productId,
    task_index: taskIndex,
    decision,
  }, { params: requestId ? { request_id: requestId } : {} })
}

export function generateStudentReviewReport(studentId, requestId = null) {
  return instance.post(`/students/${studentId}/review-reports`, null, { params: requestId ? { request_id: requestId } : {} })
}

export function getLatestStudentReviewReport(studentId, requestId = null) {
  return instance.get(`/students/${studentId}/review-reports/latest`, { params: requestId ? { request_id: requestId } : {} })
}

export function decideStudentReviewReport(studentId, reportId, decision, checklistConfirmed, evidenceGapAcknowledged = false, note = '', requestId = null) {
  return instance.post(`/students/${studentId}/review-reports/${reportId}/decision`, {
    decision,
    checklist_confirmed: checklistConfirmed,
    evidence_gap_acknowledged: evidenceGapAcknowledged,
    note,
  }, { params: requestId ? { request_id: requestId } : {} })
}

export function studentReviewReportPdfUrl(studentId, reportId, requestId = null) {
  const query = requestId ? `?request_id=${encodeURIComponent(requestId)}` : ''
  return `/api/teacher/students/${studentId}/review-reports/${encodeURIComponent(reportId)}.pdf${query}`
}

export function setStudentExternalAiAuthorization(studentId, active, authorityConfirmed = false, expiresDays = 30) {
  return instance.post(`/students/${studentId}/external-ai-authorization`, {
    active,
    authority_confirmed: authorityConfirmed,
    expires_days: expiresDays,
  })
}

export function setTeacherStudentAssignment(teacherUserId, studentUserId, active = true) {
  return instance.post('/assignments', { teacher_user_id: teacherUserId, student_user_id: studentUserId, active })
}

export function getTeacherAccounts(userId) {
  return instance.get('/accounts', { params: params(userId) })
}

export function updateTeacherAccount(accountId, userId, payload) {
  return instance.patch(`/accounts/${accountId}`, payload, { params: params(userId) })
}

export default instance

export const getTeacherTaskCapabilities = () => instance.get('/tasks/capabilities', { timeout: 10000 })
export const createTeacherCaseTask = payload => instance.post('/tasks/case-plans', payload, { timeout: 15000 })
export const getTeacherCaseTask = id => instance.get(`/tasks/durable-plans/${encodeURIComponent(id)}`, { timeout: 15000 })
export const decideTeacherCaseTask = (id, digest, approved) => instance.post(`/tasks/durable-plans/${encodeURIComponent(id)}/decision`, { digest, approved }, { timeout: 15000 })
export const executeTeacherCaseTask = id => instance.post(`/tasks/durable-plans/${encodeURIComponent(id)}/execute`, null, { timeout: 90000 })
export const getTeacherCaseExecution = id => instance.get(`/tasks/durable-plans/${encodeURIComponent(id)}/execution`, { timeout: 15000 })
export const checkTeacherCaseRevision = id => instance.post(`/tasks/durable-plans/${encodeURIComponent(id)}/revision-check`, null, { timeout: 15000 })
export const createTeacherCaseRevision = id => instance.post(`/tasks/durable-plans/${encodeURIComponent(id)}/revision-plans`, null, { timeout: 15000 })
export const terminateTeacherCaseTask = (id, digest, reason) => instance.post(`/tasks/durable-plans/${encodeURIComponent(id)}/terminate`, { digest, reason, confirmed: true }, { timeout: 15000 })
export const getExactTeacherReviewReport = (studentId, reportId, requestId) => instance.get(
  `/students/${studentId}/review-reports/${encodeURIComponent(reportId)}/detail`,
  { params: requestId ? { request_id: requestId } : {}, timeout: 15000 },
)

export const downloadTeacherCaseReport = (studentId, reportId, requestId) => instance.get(
  studentReviewReportPdfUrl(studentId, reportId, requestId).replace('/api/teacher', ''),
  { responseType: 'blob', timeout: 30000 },
)
export const getTeacherCaseHistory = (studentId, requestId) => instance.get('/tasks/case-history', { params: { student_id: studentId, access_request_id: requestId || undefined }, timeout: 15000 })
export const previewTeacherIntent = goal => instance.post('/tasks/intent-preview', { goal, confirmed: true }, { timeout: 18000 })
