import { createApi } from './http'

const instance = createApi('/api/companion')

export function sendCompanionMessage(content) {
  return instance.post('/chat', { content })
}

export function getCompanionSafetyStatus() {
  return instance.get('/safety-status')
}

export function handoffCompanionToChat() {
  return instance.post('/handoff')
}
