import axios from 'axios'

const robot = axios.create({ baseURL: '/api/robot', withCredentials: true })

export const getRobotLink = () => robot.get('/link')
export const createRobotLink = () => robot.post('/link')
export const revokeRobotLink = () => robot.delete('/link')
