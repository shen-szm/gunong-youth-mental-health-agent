import axios from 'axios'

const instance = axios.create({ baseURL: '/api/assessment' })

export function getAssessmentSchema() {
  return instance.get('/schema')
}

export function submitAssessment(payload) {
  return instance.post('/submit', payload)
}

export function getLatestAssessment() {
  return instance.get('/latest')
}

export function deleteAssessment(code) {
  return instance.delete(`/${code}`)
}

export default instance
