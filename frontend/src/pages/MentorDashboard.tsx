import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Users, Activity, AlertTriangle, BarChart3, Search, Shield, Flame, ArrowRight } from 'lucide-react'
import type { MentorYouthItem, SafeHarborEnum } from '@/types'
import { SAFE_HARBOR_INFO } from '@/types'

const MOCK_YOUTH: MentorYouthItem[] = [
  { id: '1', name: 'Marcus Cole', age: 17, city: 'Atlanta', school_name: 'Westside High', current_trust_score: 142, display_score: 142, current_tier: 'Flex', safe_harbor_floor: 'yellow', current_character: 'challenger', current_character_name: 'The Challenger', check_in_streak: 5, last_session_at: '2025-01-20T14:00:00Z', has_alert: true },
  { id: '2', name: 'Aaliyah Nichols', age: 16, city: 'Chicago', school_name: 'Lincoln Park High', current_trust_score: 287, display_score: 287, current_tier: 'Vetted', safe_harbor_floor: 'green', current_character: 'navigator', current_character_name: 'The Navigator', check_in_streak: 21, last_session_at: '2025-01-21T09:30:00Z', has_alert: false },
  { id: '3', name: 'Jordan Smith', age: 15, city: 'Houston', school_name: 'Southwest Academy', current_trust_score: 67, display_score: 67, current_tier: 'Watch', safe_harbor_floor: 'red', current_character: 'straight_shooter', current_character_name: 'The Straight Shooter', check_in_streak: 0, last_session_at: '2025-01-15T11:00:00Z', has_alert: true },
  { id: '4', name: 'DeShawn Williams', age: 18, city: 'Detroit', school_name: 'Central High', current_trust_score: 175, display_score: 175, current_tier: 'Flex', safe_harbor_floor: 'green', current_character: 'strategist', current_character_name: 'The Strategist', check_in_streak: 12, last_session_at: '2025-01-19T16:00:00Z', has_alert: false },
  { id: '5', name: 'Kaya Nguyen', age: 16, city: 'Philadelphia', school_name: 'Northeast High', current_trust_score: 89, display_score: 89, current_tier: 'Watch', safe_harbor_floor: 'yellow', current_character: 'navigator', current_character_name: 'The Navigator', check_in_streak: 3, last_session_at: '2025-01-18T10:00:00Z', has_alert: false },
]

function MiniSparkline({ color }: { color: string }) {
  const points = [30, 45, 40, 60, 55, 70, 65, 80, 75, 90]
  const max = Math.max(...points)
  const min = Math.min(...points)
  const range = max - min || 1
  const w = 80
  const h = 24
  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${(i / (points.length - 1)) * w} ${h - ((p - min) / range) * h}`).join(' ')
  return (
    <svg width={w} height={h} className="opacity-60">
      <path d={path} fill="none" stroke={color} strokeWidth={2} />
    </svg>
  )
}

export default function MentorDashboard() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | SafeHarborEnum>('all')

  const totalYouth = MOCK_YOUTH.length
  const activeSessions = MOCK_YOUTH.filter((y) => y.last_session_at && new Date(y.last_session_at) > new Date(Date.now() - 7 * 86400000)).length
  const alerts = MOCK_YOUTH.filter((y) => y.has_alert).length
  const avgTrust = Math.round(MOCK_YOUTH.reduce((s, y) => s + y.display_score, 0) / totalYouth)

  const filtered = MOCK_YOUTH.filter((y) => {
    const matchesSearch = y.name.toLowerCase().includes(search.toLowerCase())
    const matchesFilter = filter === 'all' || y.safe_harbor_floor === filter
    return matchesSearch && matchesFilter
  })

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <h1 className="font-display text-3xl text-brandGold">COACH RAY&rsquo;S ROSTER</h1>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[{ label: 'Total Youth', value: totalYouth, icon: Users, color: '#00A8E8' }, { label: 'Active Sessions', value: activeSessions, icon: Activity, color: '#10B981' }, { label: 'Alerts', value: alerts, icon: AlertTriangle, color: '#DC2626' }, { label: 'Avg Trust', value: avgTrust, icon: BarChart3, color: '#D4AF37' }].map((s) => (
          <div key={s.label} className="p-4 rounded-fz-lg bg-bgElevated border border-borderSubtle">
            <div className="flex items-center gap-2 mb-2">
              <s.icon size={16} style={{ color: s.color }} />
              <span className="text-xs text-textMuted">{s.label}</span>
            </div>
            <div className="font-display text-2xl" style={{ color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Alerts Banner */}
      {alerts > 0 && (
        <div className="flex items-center gap-3 p-4 rounded-fz-lg bg-safeRed/10 border border-safeRed/20">
          <AlertTriangle size={20} className="text-safeRed shrink-0" />
          <div className="text-sm text-safeRed">
            <span className="font-semibold">{alerts} youth</span> in red or yellow Safe Harbor. Review immediately.
          </div>
        </div>
      )}

      {/* Search & Filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-textMuted" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search youth..." className="w-full pl-9 pr-3 py-2.5 rounded-fz-md bg-bgElevated border border-borderSubtle text-textPrimary placeholder:text-textMuted focus:border-brandGold focus:outline-none text-sm" />
        </div>
        <div className="flex gap-2">
          {(['all', 'green', 'yellow', 'red'] as const).map((f) => (
            <button key={f} onClick={() => setFilter(f)} className={`px-3 py-2 rounded-fz-md text-xs font-medium border transition-colors ${filter === f ? 'bg-brandGold text-textInverse border-brandGold' : 'bg-bgElevated text-textSecondary border-borderSubtle hover:border-borderActive'}`}>
              {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Youth Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((y, i) => {
          const safeColor = SAFE_HARBOR_INFO[y.safe_harbor_floor].color
          return (
            <motion.div
              key={y.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="p-5 rounded-fz-lg bg-bgElevated border-2 transition-colors cursor-pointer hover:bg-bgHover"
              style={{ borderColor: safeColor + '40' }}
              onClick={() => navigate(`/mentor/notes/${y.id}`)}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: safeColor }} />
                  <span className="font-semibold text-textPrimary">{y.name}</span>
                </div>
                <ArrowRight size={16} className="text-textMuted" />
              </div>

              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs px-2 py-0.5 rounded-fz-sm bg-brandGold/10 text-brandGold">{y.current_tier}</span>
                <span className="text-xs px-2 py-0.5 rounded-fz-sm bg-bgOverlay text-textMuted">{y.age} yrs</span>
                <span className="text-xs px-2 py-0.5 rounded-fz-sm bg-bgOverlay text-textMuted">{y.city}</span>
              </div>

              <div className="flex items-center justify-between mb-2">
                <div>
                  <div className="font-display text-xl text-brandGold">{y.display_score}</div>
                  <div className="text-xs text-textMuted">Trust Score</div>
                </div>
                <MiniSparkline color={safeColor} />
              </div>

              <div className="flex items-center gap-3 text-xs text-textMuted">
                <div className="flex items-center gap-1"><Flame size={12} className="text-brandCrimson" /> {y.check_in_streak} day streak</div>
                <div className="flex items-center gap-1"><Shield size={12} style={{ color: safeColor }} /> {y.current_character_name}</div>
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
