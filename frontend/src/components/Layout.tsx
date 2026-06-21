import { NavLink, Outlet } from 'react-router-dom'

const nav = [
  { to: '/', label: '📊 總覽', end: true },
  { to: '/conversations', label: '💬 對話記錄' },
  { to: '/logs', label: '📋 請求 Logs' },
  { to: '/settings', label: '⚙️ 設定' },
]

export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      <aside className="w-48 shrink-0 bg-gray-900 flex flex-col border-r border-gray-800">
        <div className="px-5 py-4 border-b border-gray-800">
          <span className="text-lg font-bold tracking-wide">🐍 嗆辣後台</span>
        </div>
        <nav className="flex-1 py-4 space-y-1 px-2">
          {nav.map(n => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-green-900/50 text-green-300 font-medium'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
