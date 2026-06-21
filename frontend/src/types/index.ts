export interface StatsOverview {
  total_users: number
  total_sessions: number
  total_messages: number
  nuclear_unlocked: number
  venom_level_distribution: { max_venom_level: number; count: number }[]
}

export interface ConversationRecord {
  id: number
  session_id: string
  user_id: number
  role: 'user' | 'bot'
  content: string
  venom_level: number | null
  created_at: string
}

export interface AppSettings {
  llm_provider:     string
  llm_model:        string
  llm_api_key:      string
  llm_base_url:     string
  telegram_enabled: string
  line_enabled:     string
  discord_enabled:  string
}

export interface RequestLog {
  id: number
  method: string
  path: string
  status_code: number
  duration_ms: number
  created_at: string
}

export interface SessionRecord {
  id: string
  user_id: number
  username: string | null
  mode: string
  venom_level: number
  nuclear_triggered: boolean
  created_at: string
  message_count: number
}
