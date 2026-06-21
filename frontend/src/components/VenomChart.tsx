interface Props {
  data: { max_venom_level: number; count: number }[]
}

const LEVEL_META: Record<number, { label: string; color: string }> = {
  1: { label: '小嘴一下', color: 'bg-blue-500' },
  2: { label: '嗆辣登場', color: 'bg-yellow-500' },
  3: { label: '蛇吻', color: 'bg-orange-500' },
  4: { label: '劇毒', color: 'bg-red-500' },
  5: { label: '蛇王', color: 'bg-purple-500' },
}

export default function VenomChart({ data }: Props) {
  const total = data.reduce((s, d) => s + Number(d.count), 0)
  const filled = [1, 2, 3, 4, 5].map(lv => ({
    level: lv,
    count: Number(data.find(d => d.max_venom_level === lv)?.count ?? 0),
  }))

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <h3 className="text-sm text-gray-400 mb-4">嗆辣等級分布</h3>
      <div className="space-y-3">
        {filled.map(({ level, count }) => {
          const meta = LEVEL_META[level]
          const pct = total ? Math.round((count / total) * 100) : 0
          return (
            <div key={level}>
              <div className="flex justify-between text-xs text-gray-400 mb-1">
                <span>Lv.{level} {meta.label}</span>
                <span>{count} 人 ({pct}%)</span>
              </div>
              <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${meta.color}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
