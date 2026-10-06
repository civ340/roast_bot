import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Conversations from './pages/Conversations'
import Logs from './pages/Logs'
import Settings from './pages/Settings'
import { fetchMe } from './api/client'

export default function App() {
  const [username, setUsername] = useState<string | null>(null)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    fetchMe()
      .then(data => setUsername(data.username))
      .catch(() => setUsername(null))
      .finally(() => setChecking(false))
  }, [])

  if (checking) return <div className="flex h-screen items-center justify-center bg-gray-950 text-gray-500 animate-pulse">載入中...</div>

  if (!username) return <Login onLoggedIn={setUsername} />

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout username={username} onLogout={() => setUsername(null)} />}>
          <Route index element={<Dashboard />} />
          <Route path="conversations" element={<Conversations />} />
          <Route path="logs" element={<Logs />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
