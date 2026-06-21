import { useEffect, useState } from 'react'
import { fetchSessions, fetchMessages } from '../api/client'
import type { SessionRecord, ConversationRecord } from '../types'

const ROAST_EMOJI: Record<number, string> = { 1: '😏', 2: '😈', 3: '🐍', 4: '☠️', 5: '👑' }
const EXCUSE_EMOJI: Record<number, string> = { 1: '📋', 2: '🎭', 3: '💣', 4: '🌀', 5: '🚀', 6: '👑' }

function levelEmoji(mode: string, level: number) {
  return mode === 'excuse' ? (EXCUSE_EMOJI[level] ?? '👑') : (ROAST_EMOJI[level] ?? '👑')
}

const MODE_LABEL: Record<string, string> = { roast: '嗆辣 🐍', excuse: '借口 📋' }
const NUCLEAR_LABEL: Record<string, string> = { roast: '💥 舌王', excuse: '👑 借口王' }

export default function Conversations() {
  const [sessions, setSessions] = useState<SessionRecord[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [messages, setMessages] = useState<ConversationRecord[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchSessions()
      .then(d => setSessions(d.sessions))
      .finally(() => setLoading(false))
  }, [])

  const openSession = (id: string) => {
    setSelected(id)
    fetchMessages(id).then(setMessages)
  }

  if (loading) return <div className="p-8 text-gray-500 animate-pulse">載入中...</div>

  return (
    <div className="flex h-full">
      {/* Session list */}
      <div className="w-80 shrink-0 border-r border-gray-800 overflow-y-auto">
        <div className="px-4 py-3 border-b border-gray-800 text-sm font-medium text-gray-400">
          對話記錄（{sessions.length}）
        </div>
        {sessions.length === 0 && (
          <div className="p-4 text-sm text-gray-600">還沒有對話記錄</div>
        )}
        {sessions.map(s => (
          <button
            key={s.id}
            onClick={() => openSession(s.id)}
            className={`w-full text-left px-4 py-3 border-b border-gray-800/50 hover:bg-gray-800 transition-colors ${
              selected === s.id ? 'bg-gray-800' : ''
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium truncate">
                {s.username ? `@${s.username}` : `User ${s.user_id}`}
              </span>
              <span className="text-xs text-gray-500 shrink-0 ml-2">
                {levelEmoji(s.mode, s.venom_level)} Lv.{s.venom_level}
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span className="text-gray-400">{MODE_LABEL[s.mode] ?? s.mode}</span>
              <span>{s.message_count} 則訊息</span>
              {s.nuclear_triggered && (
                <span className="text-purple-400">{NUCLEAR_LABEL[s.mode] ?? '💥'}</span>
              )}
              <span className="ml-auto">
                {new Date(s.created_at.endsWith('Z') ? s.created_at : s.created_at + 'Z').toLocaleDateString('zh-TW', { timeZone: 'Asia/Taipei' })}
              </span>
            </div>
          </button>
        ))}
      </div>

      {/* Message thread */}
      <div className="flex-1 overflow-y-auto p-6">
        {!selected && (
          <div className="flex items-center justify-center h-full text-gray-600">
            選擇左側對話查看內容
          </div>
        )}
        {selected && (
          <div className="max-w-2xl space-y-3">
            {messages.map(m => (
              <div
                key={m.id}
                className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm ${
                    m.role === 'user'
                      ? 'bg-blue-900/60 text-blue-100'
                      : 'bg-gray-800 text-gray-200'
                  }`}
                >
                  {m.role === 'bot' && m.venom_level && (
                    <div className="text-xs text-gray-500 mb-1">
                      {levelEmoji(sessions.find(s => s.id === selected)?.mode ?? '', m.venom_level)} Lv.{m.venom_level}
                    </div>
                  )}
                  <p className="whitespace-pre-wrap">{m.content}</p>
                  <div className="text-xs text-gray-500 mt-1 text-right">
                    {new Date(m.created_at.endsWith('Z') ? m.created_at : m.created_at + 'Z').toLocaleTimeString('zh-TW', {
                      hour: '2-digit',
                      minute: '2-digit',
                      timeZone: 'Asia/Taipei',
                    })}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
