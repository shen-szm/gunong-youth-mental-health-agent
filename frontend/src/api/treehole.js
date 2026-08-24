import axios from 'axios'

const API = import.meta.env.VITE_API_BASE || ''

export const treeholeApi = {
  createPost(userId, moodCard, content) {
    return axios.post(`${API}/api/treehole/post`, { user_id: userId, mood_card: moodCard, content })
  },
  getFeed(userId, limit = 20) {
    return axios.get(`${API}/api/treehole/feed`, { params: { user_id: userId, limit } })
  },
  addResonance(postId, userId) {
    return axios.post(`${API}/api/treehole/resonance/${postId}`, { user_id: userId || 0 })
  },
  getStats() {
    return axios.get(`${API}/api/treehole/stats`)
  },
}
