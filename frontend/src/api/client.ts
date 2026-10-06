import axios from 'axios'
import type { StatsOverview, SessionRecord, ConversationRecord, AppSettings, RequestLog } from '../types'

const api = axios.create({ baseURL: '/api', withCredentials: true })

api.interceptors.response.use(
  r => r,
  err => {
    if (err.response?.status === 401 && !err.config?.url?.startsWith('/auth/')) {
      window.location.reload()
    }
    return Promise.reject(err)
  },
)

export const login = (username: string, password: string) =>
  api.post<{ username: string }>('/auth/login', { username, password }).then(r => r.data)

export const logout = () =>
  api.post('/auth/logout').then(r => r.data)

export const fetchMe = () =>
  api.get<{ username: string }>('/auth/me').then(r => r.data)

export const fetchStats = () =>
  api.get<StatsOverview>('/stats/overview').then(r => r.data)

export const fetchSessions = (page = 1, limit = 20) =>
  api.get<{ sessions: SessionRecord[]; total: number }>('/stats/sessions', {
    params: { page, limit },
  }).then(r => r.data)

export const fetchMessages = (sessionId: string) =>
  api.get<ConversationRecord[]>(`/stats/sessions/${sessionId}/messages`).then(r => r.data)

export const fetchLogs = (page = 1, limit = 50, status = 'all') =>
  api.get<{ logs: RequestLog[]; total: number }>('/stats/logs', {
    params: { page, limit, status },
  }).then(r => r.data)

export const fetchSettings = () =>
  api.get<AppSettings>('/settings').then(r => r.data)

export const saveSettings = (data: Partial<AppSettings>) =>
  api.put<AppSettings>('/settings', data).then(r => r.data)
