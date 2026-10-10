import axios from 'axios'

const instance = axios.create({ baseURL: '/api/companion', withCredentials: true })

export function sendCompanionMessage(content) {
  return instance.post('/chat', { content })
}

export function getCompanionSafetyStatus() {
  return instance.get('/safety-status')
}

export function handoffCompanionToChat() {
  return instance.post('/handoff')
}
