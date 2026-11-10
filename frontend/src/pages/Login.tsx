import { useState } from 'react'
import { login } from '../api/client'

export default function Login({ onLoggedIn }: { onLoggedIn: (username: string) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const data = await login(username, password)
      onLoggedIn(data.username)
    } catch (err) {
      const status = (err as { response?: { status?: number } }).response?.status
      setError(status === 429 ? '登入失敗次數過多，請 15 分鐘後再試' : '帳號或密碼錯誤')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex items-center justify-center h-screen bg-gray-950 text-gray-100">
      <form onSubmit={handleSubmit} className="w-full max-w-sm bg-gray-900 border border-gray-800 rounded-xl p-8">
        <h1 className="text-xl font-bold mb-6 text-center">🐍 嗆辣後台登入</h1>

        <label className="block text-sm text-gray-400 mb-1">帳號</label>
        <input
          value={username}
          onChange={e => setUsername(e.target.value)}
          autoFocus
          className="w-full mb-4 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-green-500"
        />

        <label className="block text-sm text-gray-400 mb-1">密碼</label>
        <input
          type="password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          className="w-full mb-4 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-green-500"
        />

        {error && <p className="text-sm text-red-400 mb-4">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-2 bg-green-700 hover:bg-green-600 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
        >
          {submitting ? '登入中...' : '登入'}
        </button>
      </form>
    </div>
  )
}
