import { createApi } from './http'

const instance = createApi('/api/assessment')

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
