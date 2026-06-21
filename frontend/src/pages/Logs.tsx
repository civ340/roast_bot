import { useEffect, useRef, useState } from 'react'
import { fetchLogs } from '../api/client'
import type { RequestLog } from '../types'

const PAGE_SIZE = 50
type Filter = 'all' | 'success' | 'error'

function statusColor(code: number) {
  if (code < 300) return 'text-green-400'
  if (code < 400) return 'text-yellow-400'
  return 'text-red-400'
}

function methodColor(method: string) {
  if (method === 'GET')    return 'bg-blue-900 text-blue-300'
  if (method === 'POST')   return 'bg-green-900 text-green-300'
  if (method === 'PUT')    return 'bg-yellow-900 text-yellow-300'
  if (method === 'DELETE') return 'bg-red-900 text-red-300'
  return 'bg-gray-800 text-gray-300'
}

function fmt(iso: string) {
  const utc = iso.endsWith('Z') ? iso : iso + 'Z'
  return new Date(utc).toLocaleString('zh-TW', { hour12: false, timeZone: 'Asia/Taipei' })
}

export default function Logs() {
  const [logs, setLogs] = useState<RequestLog[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [filter, setFilter] = useState<Filter>('all')
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [loading, setLoading] = useState(false)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = (p = page, f = filter) => {
    setLoading(true)
    fetchLogs(p, PAGE_SIZE, f)
      .then(d => { setLogs(d.logs); setTotal(d.total) })
      .finally(() => setLoading(false))
  }

  useEffect(() => { load(1, filter); setPage(1) }, [filter])
  useEffect(() => { load(page, filter) }, [page])

  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current)
    if (autoRefresh) timerRef.current = setInterval(() => load(1, filter), 5000)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [autoRefresh, filter])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const FILTERS: { key: Filter; label: string }[] = [
    { key: 'all',     label: '全部' },
    { key: 'success', label: '成功 2xx' },
    { key: 'error',   label: '失敗 4xx/5xx' },
  ]

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">📋 請求 Logs</h1>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={e => setAutoRefresh(e.target.checked)}
              className="accent-green-500"
            />
            每 5 秒自動更新
          </label>
          <button
            onClick={() => load(page, filter)}
            className="px-3 py-1 text-sm rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300"
          >
            ↻ 更新
          </button>
        </div>
      </div>

      <div className="flex gap-2">
        {FILTERS.map(f => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              filter === f.key
                ? 'bg-green-900/60 text-green-300 border border-green-700'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            {f.label}
          </button>
        ))}
        <span className="ml-auto text-sm text-gray-500 self-center">共 {total} 筆</span>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase tracking-wide">
              <th className="px-4 py-3 text-left">時間</th>
              <th className="px-4 py-3 text-left">方法</th>
              <th className="px-4 py-3 text-left">路徑</th>
              <th className="px-4 py-3 text-center">狀態</th>
              <th className="px-4 py-3 text-right">耗時</th>
            </tr>
          </thead>
          <tbody>
            {loading && logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-gray-500">載入中…</td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-gray-500">尚無記錄</td>
              </tr>
            ) : logs.map(log => (
              <tr key={log.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                <td className="px-4 py-2.5 text-gray-400 whitespace-nowrap">{fmt(log.created_at)}</td>
                <td className="px-4 py-2.5">
                  <span className={`px-2 py-0.5 rounded text-xs font-mono font-bold ${methodColor(log.method)}`}>
                    {log.method}
                  </span>
                </td>
                <td className="px-4 py-2.5 font-mono text-gray-300 max-w-xs truncate">{log.path}</td>
                <td className={`px-4 py-2.5 text-center font-mono font-bold ${statusColor(log.status_code)}`}>
                  {log.status_code}
                </td>
                <td className="px-4 py-2.5 text-right text-gray-400 font-mono">
                  {log.duration_ms} ms
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 rounded-lg bg-gray-800 text-gray-400 disabled:opacity-30 hover:bg-gray-700 text-sm"
          >
            ← 上一頁
          </button>
          <span className="text-sm text-gray-400">{page} / {totalPages}</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 rounded-lg bg-gray-800 text-gray-400 disabled:opacity-30 hover:bg-gray-700 text-sm"
          >
            下一頁 →
          </button>
        </div>
      )}
    </div>
  )
}
