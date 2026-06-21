import axios from 'axios'
import type { StatsOverview, SessionRecord, ConversationRecord, AppSettings, RequestLog } from '../types'

const api = axios.create({ baseURL: '/api' })

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
