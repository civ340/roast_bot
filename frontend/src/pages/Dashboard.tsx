import { useEffect, useState } from 'react'
import { fetchStats } from '../api/client'
import type { StatsOverview } from '../types'
import StatCard from '../components/StatCard'
import VenomChart from '../components/VenomChart'

export default function Dashboard() {
  const [stats, setStats] = useState<StatsOverview | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    fetchStats()
      .then(setStats)
      .catch(() => setError(true))
  }, [])

  if (error) return (
    <div className="p-8 text-red-400">無法連線到後端，請確認服務是否啟動。</div>
  )

  if (!stats) return (
    <div className="p-8 text-gray-500 animate-pulse">載入中...</div>
  )

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-6">總覽</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="總用戶數" value={stats.total_users} icon="👤" />
        <StatCard label="對話場次" value={stats.total_sessions} icon="💬" />
        <StatCard label="用戶訊息數" value={stats.total_messages} icon="📨" />
        <StatCard
          label="解鎖舌王"
          value={stats.nuclear_unlocked}
          icon="💥"
          sub={`佔 ${stats.total_users ? Math.round((stats.nuclear_unlocked / stats.total_users) * 100) : 0}% 用戶`}
        />
      </div>

      <div className="max-w-md">
        <VenomChart data={stats.venom_level_distribution} />
      </div>
    </div>
  )
}
