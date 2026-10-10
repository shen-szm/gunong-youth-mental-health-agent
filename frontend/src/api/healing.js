import axios from 'axios'

const API = import.meta.env.VITE_API_BASE || ''

export const healingApi = {
  getChecklist(userId) {
    return axios.get(`${API}/api/healing/checklist`, { params: { user_id: userId } })
  },
  checkin(taskId) {
    return axios.post(`${API}/api/healing/checkin`, null, { params: { task_id: taskId } })
  },
  getEnergy(userId) {
    return axios.get(`${API}/api/healing/energy`, { params: { user_id: userId } })
  },
  getTravel(userId) {
    return axios.get(`${API}/api/healing/travel`, { params: { user_id: userId } })
  },
}
