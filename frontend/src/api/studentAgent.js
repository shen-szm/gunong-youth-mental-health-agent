import axios from 'axios'

const instance = axios.create({ baseURL: '/api/student-agent' })

export function getLatestStudentAgentRun() {
  return instance.get('/runs/latest')
}

export function getStudentAgentRun(runCode) {
  return instance.get(`/runs/${encodeURIComponent(runCode)}`)
}

export function getStudentSupportTimeline(days = 30, limit = 20) {
  return instance.get('/timeline', { params: { days, limit } })
}

export function deleteStudentAgentRun(runCode) {
  return instance.delete(`/runs/${encodeURIComponent(runCode)}`)
}
