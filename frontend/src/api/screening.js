import axios from 'axios'

const instance = axios.create({ baseURL: '/api/screening' })

export function getScreeningSchema() {
  return instance.get('/schema')
}

export function submitScreening(payload) {
  return instance.post('/submit', payload)
}

export function getLatestScreening() {
  return instance.get('/latest')
}

export function acknowledgeScreening(contactedTrustedAdult = true) {
  return instance.post('/acknowledge', { contacted_trusted_adult: contactedTrustedAdult })
}

export function deleteScreening(runCode) {
  return instance.delete(`/${runCode}`)
}

export default instance
