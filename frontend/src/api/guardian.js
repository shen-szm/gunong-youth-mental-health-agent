import axios from 'axios'

const instance = axios.create({
  baseURL: '/api/guardian',
  withCredentials: true,
  timeout: 20000,
})

export function createGuardianCase(payload) {
  return instance.post('/cases', payload)
}

export function getGuardianCase(caseId) {
  return instance.get(`/cases/${caseId}`)
}

export function retryGuardianCase(caseId) {
  return instance.post(`/cases/${caseId}/retry`)
}

export function guardianReportUrl(caseId) {
  return `/api/guardian/cases/${caseId}/report.pdf`
}

export function getGuardianFollowUps() {
  return instance.get('/follow-ups')
}

export function submitGuardianFollowUp(id, payload) {
  return instance.post(`/follow-ups/${id}/responses`, payload)
}

export function simulateGuardianFollowUp(id) {
  return instance.post(`/follow-ups/${id}/simulate-due`)
}

export default instance
