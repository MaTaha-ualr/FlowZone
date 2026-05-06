import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Users,
  Activity,
  AlertTriangle,
  BarChart3,
  Search,
  Shield,
  Flame,
  ArrowRight,
  Loader2,
} from 'lucide-react'
import type { MentorRosterResponse, MentorYouthItem, SafeHarborEnum } from '@/types'
import { SAFE_HARBOR_INFO } from '@/types'
import { useAuth } from '@/context/AuthContext'
import { getMentorRoster } from '@/lib/api'

function MiniSparkline({ color }: { color: string }) {
  const points = [30, 45, 40, 60, 55, 70, 65, 80, 75, 90]
  const max = Math.max(...points)
  const min = Math.min(...points)
  const range = max - min || 1
  const w = 80
  const h = 24
  const path = points
    .map(
      (p, i) =>
        `${i === 0 ? 'M' : 'L'} ${(i / (points.length - 1)) * w} ${h - ((p - min) / range) * h}`,
    )
    .join(' ')
  return (
    <svg width={w} height={h} className="opacity-60">
      <path d={path} fill="none" stroke={color} strokeWidth={2} />
    </svg>
  )
}

export default function MentorDashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | SafeHarborEnum>('all')
  const [data, setData] = useState<MentorRosterResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    getMentorRoster()
      .then((d) => {
        if (cancelled) return
        setData(d as MentorRosterResponse)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Could not load roster')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const youthList: MentorYouthItem[] = data?.youth ?? []

  const filtered = useMemo(() => {
    return youthList.filter((y) => {
      const matchesSearch = y.name.toLowerCase().includes(search.toLowerCase())
      const matchesFilter = filter === 'all' || y.safe_harbor_floor === filter
      return matchesSearch && matchesFilter
    })
  }, [youthList, search, filter])

  const heading = user?.name ? `${user.name.split(' ')[0].toUpperCase()}'S ROSTER` : 'YOUR ROSTER'

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <h1 className="font-display text-3xl text-brandGold">{heading}</h1>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Youth', value: data?.total_youth ?? 0, icon: Users, color: '#00A8E8' },
          { label: 'Active Sessions', value: data?.active_sessions ?? 0, icon: Activity, color: '#10B981' },
          { label: 'Alerts', value: data?.alerts ?? 0, icon: AlertTriangle, color: '#DC2626' },
          { label: 'Avg Trust', value: data?.avg_trust ?? 0, icon: BarChart3, color: '#D4AF37' },
        ].map((s) => (
          <div key={s.label} className="p-4 rounded-fz-lg bg-bgElevated border border-borderSubtle">
            <div className="flex items-center gap-2 mb-2">
              <s.icon size={16} style={{ color: s.color }} />
              <span className="text-xs text-textMuted">{s.label}</span>
            </div>
            <div className="font-display text-2xl" style={{ color: s.color }}>
              {s.value}
            </div>
          </div>
        ))}
      </div>

      {/* Alerts Banner */}
      {(data?.alerts ?? 0) > 0 && (
        <div className="flex items-center gap-3 p-4 rounded-fz-lg bg-safeRed/10 border border-safeRed/20">
          <AlertTriangle size={20} className="text-safeRed shrink-0" />
          <div className="text-sm text-safeRed">
            <span className="font-semibold">{data?.alerts} youth</span> in red or yellow Safe
            Harbor. Review immediately.
          </div>
        </div>
      )}

      {/* Search & Filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-textMuted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search youth..."
            className="w-full pl-9 pr-3 py-2.5 rounded-fz-md bg-bgElevated border border-borderSubtle text-textPrimary placeholder:text-textMuted focus:border-brandGold focus:outline-none text-sm"
          />
        </div>
        <div className="flex gap-2">
          {(['all', 'green', 'yellow', 'red'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-2 rounded-fz-md text-xs font-medium border transition-colors ${
                filter === f
                  ? 'bg-brandGold text-textInverse border-brandGold'
                  : 'bg-bgElevated text-textSecondary border-borderSubtle hover:border-borderActive'
              }`}
            >
              {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* States */}
      {loading && (
        <div className="flex items-center justify-center py-16 text-textMuted">
          <Loader2 size={20} className="animate-spin mr-2" /> Loading roster…
        </div>
      )}
      {!loading && error && (
        <div className="flex items-center gap-2 p-4 rounded-fz-lg bg-safeRed/10 border border-safeRed/20 text-sm text-safeRed">
          <AlertTriangle size={16} /> {error}
        </div>
      )}
      {!loading && !error && filtered.length === 0 && (
        <div className="text-center py-16 text-textMuted text-sm">
          {youthList.length === 0
            ? 'No youth in the system yet.'
            : 'No youth match your search.'}
        </div>
      )}

      {/* Youth Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((y, i) => {
          const safeColor = SAFE_HARBOR_INFO[y.safe_harbor_floor].color
          return (
            <motion.div
              key={y.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(i * 0.04, 0.4) }}
              className="p-5 rounded-fz-lg bg-bgElevated border-2 transition-colors cursor-pointer hover:bg-bgHover"
              style={{ borderColor: safeColor + '40' }}
              onClick={() => navigate(`/mentor/notes/${y.id}`)}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: safeColor }} />
                  <span className="font-semibold text-textPrimary truncate">{y.name}</span>
                </div>
                <ArrowRight size={16} className="text-textMuted shrink-0" />
              </div>

              <div className="flex items-center gap-2 mb-3 flex-wrap">
                <span className="text-xs px-2 py-0.5 rounded-fz-sm bg-brandGold/10 text-brandGold uppercase">
                  {y.current_tier?.replace('the_', '') || 'watch'}
                </span>
                <span className="text-xs px-2 py-0.5 rounded-fz-sm bg-bgOverlay text-textMuted">
                  {y.age} yrs
                </span>
                {y.city && (
                  <span className="text-xs px-2 py-0.5 rounded-fz-sm bg-bgOverlay text-textMuted">
                    {y.city}
                  </span>
                )}
              </div>

              <div className="flex items-center justify-between mb-2">
                <div>
                  <div className="font-display text-xl text-brandGold">{y.display_score}</div>
                  <div className="text-xs text-textMuted">Trust Score</div>
                </div>
                <MiniSparkline color={safeColor} />
              </div>

              <div className="flex items-center gap-3 text-xs text-textMuted">
                <div className="flex items-center gap-1">
                  <Flame size={12} className="text-brandCrimson" /> {y.check_in_streak} day streak
                </div>
                <div className="flex items-center gap-1 truncate">
                  <Shield size={12} style={{ color: safeColor }} /> {y.current_character_name}
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
