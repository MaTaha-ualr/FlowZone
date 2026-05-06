import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft,
  ChevronRight,
  Search,
  X,
  Check,
  AlertTriangle,
  Clock,
  MessageSquare,
  Shield,
  BarChart3,
  Hash,
  ArrowUpDown,
  Filter,
  Trash2,
  AlertCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { getSessions as fetchSessions, deleteSession as apiDeleteSession } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'

/* ─── Types ─── */

interface HistorySession {
  id: string
  date: string
  time: string
  day: string
  duration_minutes: number
  character: string
  character_role: string
  character_color: string
  vibe: string
  vibe_emoji: string
  vibe_color: string
  preview: string
  trust_delta: number
  tactical_action?: string
  tactical_accepted?: boolean
  mask_detected: boolean
  regulation_completed?: boolean
  messages: HistoryMessage[]
  trust_breakdown?: TrustBreakdown
  safe_harbor: 'green' | 'yellow' | 'red'
}

interface HistoryMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
}

interface TrustBreakdown {
  consistency: number
  weight: number
  weight_multiplier: number
  honesty: number
  regulation: number
  penalty: number
  total: number
}

/* ─── Inline API helpers ─── */

/* ─── Utils ─── */

const CHARACTER_MAP: Record<string, { name: string; role: string; color: string; avatar: string }> = {
  vex:  { name: 'VEX',  role: 'Challenger',        color: '#DC2626', avatar: '/character-vex.png' },
  yogi: { name: 'YOGI', role: 'Navigator',         color: '#00A8E8', avatar: '/character-yogi.png' },
  ace:  { name: 'ACE',  role: 'Straight Shooter',  color: '#10B981', avatar: '/character-ace.png' },
  nova: { name: 'NOVA', role: 'Strategist',        color: '#6C5CE7', avatar: '/character-nova.png' },
}

const CHARACTER_ALIASES: Record<string, string> = {
  challenger: 'vex',
  navigator: 'yogi',
  straight_shooter: 'ace',
  strategist: 'nova',
  vex: 'vex',
  yogi: 'yogi',
  ace: 'ace',
  nova: 'nova',
}

const VIBE_MAP: Record<string, { emoji: string; color: string }> = {
  solid:   { emoji: '💎', color: '#00B4D8' },
  angry:   { emoji: '🔥', color: '#FF6B35' },
  guarded: { emoji: '🔏', color: '#64748B' },
  storm:   { emoji: '⛈️', color: '#7C3AED' },
}

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

function fmtDate(iso: string) {
  const d = new Date(iso)
  return `${MONTHS[d.getMonth()]} ${d.getDate()}`
}
function fmtTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? value as Record<string, unknown> : {}
}

function stringValue(value: unknown, fallback = ''): string {
  return typeof value === 'string' && value.length > 0 ? value : fallback
}

function numberValue(value: unknown, fallback = 0): number {
  const number = Number(value)
  return Number.isFinite(number) ? number : fallback
}

function safeHarborValue(value: unknown): HistorySession['safe_harbor'] {
  if (value === 'yellow' || value === 'red') return value
  return 'green'
}

function characterKey(value: unknown): string {
  const raw = stringValue(value, 'navigator')
  return CHARACTER_ALIASES[raw] || 'yogi'
}

function historyFromApi(session: unknown): HistorySession {
  const record = asRecord(session)
  const started = stringValue(record.started_at, new Date().toISOString())
  const character = characterKey(record.character_active)
  const characterInfo = CHARACTER_MAP[character] || CHARACTER_MAP.yogi
  const vibe = stringValue(record.vibe_selected, 'solid')
  const vibeInfo = VIBE_MAP[vibe] || VIBE_MAP.solid
  return {
    id: stringValue(record.id, crypto.randomUUID()),
    date: started,
    time: fmtTime(started),
    day: new Date(started).toLocaleDateString(undefined, { weekday: 'long' }),
    duration_minutes: numberValue(record.duration_minutes),
    character,
    character_role: characterInfo.role,
    character_color: characterInfo.color,
    vibe,
    vibe_emoji: vibeInfo.emoji,
    vibe_color: vibeInfo.color,
    preview: record.is_active ? 'Active FlowQuest session' : 'FlowQuest session',
    trust_delta: numberValue(record.trust_score_delta),
    mask_detected: Boolean(record.mask_detected),
    messages: [],
    safe_harbor: safeHarborValue(record.safe_harbor_level),
  }
}

/* ─── Components ─── */

function HexAvatar({ color, src, size = 40 }: { color: string; src?: string; size?: number }) {
  return (
    <div
      className="relative flex items-center justify-center overflow-hidden"
      style={{
        width: size,
        height: size,
        clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)',
        border: `2px solid ${color}`,
        background: '#0F0F14',
      }}
    >
      {src ? (
        <img src={src} alt="" className="object-cover w-full h-full" />
      ) : (
        <span className="text-[10px] font-bold" style={{ color }}>FZ</span>
      )}
    </div>
  )
}

export default function SessionHistory() {
  const navigate = useNavigate()
  const { user } = useAuth()

  const [sessions, setSessions] = useState<HistorySession[]>([])
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string>('')
  const [search, setSearch] = useState('')
  const [timeFilter, setTimeFilter] = useState<'all' | 'month' | 'week'>('all')
  const [charFilter, setCharFilter] = useState<string>('all')
  const [vibeFilter, setVibeFilter] = useState<string>('all')
  const [sortNewest, setSortNewest] = useState(true)
  const [detailSession, setDetailSession] = useState<HistorySession | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [showFilters, setShowFilters] = useState(false)

  // Load real data on mount. No mock fallback — empty state is honest.
  useEffect(() => {
    if (!user?.id) return
    setLoading(true)
    fetchSessions(user.id)
      .then((data) => {
        const mapped = Array.isArray(data) ? data.map(historyFromApi) : []
        setSessions(mapped)
      })
      .catch(() => setSessions([]))
      .finally(() => setLoading(false))
  }, [user?.id])

  const filtered = useMemo(() => {
    let result = [...sessions]

    // Search
    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter((s) =>
        s.preview.toLowerCase().includes(q) ||
        s.messages.some((m) => m.content.toLowerCase().includes(q))
      )
    }

    // Time
    const now = new Date()
    if (timeFilter === 'week') {
      const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
      result = result.filter((s) => new Date(s.date) >= weekAgo)
    } else if (timeFilter === 'month') {
      const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
      result = result.filter((s) => new Date(s.date) >= monthAgo)
    }

    // Character
    if (charFilter !== 'all') {
      result = result.filter((s) => s.character === charFilter)
    }

    // Vibe
    if (vibeFilter !== 'all') {
      result = result.filter((s) => s.vibe === vibeFilter)
    }

    // Sort
    result.sort((a, b) => {
      const diff = new Date(a.date).getTime() - new Date(b.date).getTime()
      return sortNewest ? -diff : diff
    })

    return result
  }, [sessions, search, timeFilter, charFilter, vibeFilter, sortNewest])

  const totalTrust = sessions.reduce((sum, s) => sum + Math.max(0, s.trust_delta), 0)
  const totalSessions = sessions.length

  const vibes = ['all', 'solid', 'angry', 'guarded', 'storm']

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#050507' }}>
      <div className="max-w-[800px] mx-auto px-4 py-8">
        {/* ─── Header ─── */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-1 text-xs font-medium transition-colors hover:text-white mb-4"
            style={{ color: '#71717A' }}
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Dashboard</span>
          </button>

          <h1 className="text-4xl sm:text-5xl font-bold tracking-wide uppercase" style={{ color: '#F8F8FA', fontFamily: 'Bebas Neue, sans-serif' }}>
            SESSION HISTORY
          </h1>
          <p className="text-sm mt-1" style={{ color: '#A1A1AA' }}>
            Every FlowQuest you ran. Every vibe you checked.
          </p>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="flex flex-wrap gap-4 mt-4 text-xs"
            style={{ color: '#71717A' }}
          >
            <span>{totalSessions} sessions total</span>
            <span>|</span>
            <span style={{ color: '#D4AF37' }}>{totalTrust.toFixed(1)} trust earned</span>
            <span>|</span>
            <span>3 day streak</span>
          </motion.div>
        </motion.div>

        {/* ─── Filters ─── */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="mt-6 space-y-3"
        >
          <div className="flex flex-wrap items-center gap-3">
            {/* Search */}
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: '#71717A' }} />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search transcripts..."
                className="w-full rounded-full pl-9 pr-4 py-2 text-sm outline-none border"
                style={{ backgroundColor: '#18181F', color: '#F8F8FA', borderColor: '#2A2A35' }}
              />
              {search && (
                <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2">
                  <X className="w-4 h-4" style={{ color: '#71717A' }} />
                </button>
              )}
            </div>

            <button
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center gap-2 px-4 py-2 rounded-full text-sm border transition-colors"
              style={{ color: '#A1A1AA', borderColor: '#2A2A35', backgroundColor: showFilters ? '#22222C' : 'transparent' }}
            >
              <Filter className="w-4 h-4" />
              Filters
            </button>

            <button
              onClick={() => setSortNewest(!sortNewest)}
              className="flex items-center gap-2 px-4 py-2 rounded-full text-sm border transition-colors"
              style={{ color: '#A1A1AA', borderColor: '#2A2A35' }}
            >
              <ArrowUpDown className="w-4 h-4" />
              {sortNewest ? 'Newest' : 'Oldest'}
            </button>
          </div>

          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="flex flex-wrap gap-3 overflow-hidden"
              >
                {/* Time */}
                <div className="flex gap-1 p-1 rounded-lg border" style={{ backgroundColor: '#0F0F14', borderColor: '#2A2A35' }}>
                  {(['all','month','week'] as const).map((t) => (
                    <button
                      key={t}
                      onClick={() => setTimeFilter(t)}
                      className="px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
                      style={{
                        backgroundColor: timeFilter === t ? '#D4AF37' : 'transparent',
                        color: timeFilter === t ? '#050507' : '#A1A1AA',
                      }}
                    >
                      {t === 'all' ? 'All Time' : t === 'month' ? 'This Month' : 'This Week'}
                    </button>
                  ))}
                </div>

                {/* Character */}
                <div className="flex items-center gap-2">
                  <span className="text-xs" style={{ color: '#71717A' }}>Character:</span>
                  <select
                    value={charFilter}
                    onChange={(e) => setCharFilter(e.target.value)}
                    className="px-3 py-1.5 rounded-md text-xs border outline-none"
                    style={{ backgroundColor: '#18181F', color: '#F8F8FA', borderColor: '#2A2A35' }}
                  >
                    <option value="all">All Characters</option>
                    <option value="vex">Vex</option>
                    <option value="yogi">Yogi</option>
                    <option value="ace">Ace</option>
                    <option value="nova">Nova</option>
                  </select>
                </div>

                {/* Vibe */}
                <div className="flex items-center gap-2">
                  <span className="text-xs" style={{ color: '#71717A' }}>Vibe:</span>
                  <div className="flex gap-1">
                    {vibes.map((v) => (
                      <button
                        key={v}
                        onClick={() => setVibeFilter(v === vibeFilter ? 'all' : v)}
                        className="w-8 h-8 rounded-full flex items-center justify-center text-sm border transition-colors"
                        style={{
                          borderColor: vibeFilter === v ? (VIBE_MAP[v]?.color || '#2A2A35') : '#2A2A35',
                          backgroundColor: vibeFilter === v ? `${VIBE_MAP[v]?.color || '#2A2A35'}20` : 'transparent',
                        }}
                      >
                        {v === 'all' ? 'All' : VIBE_MAP[v]?.emoji}
                      </button>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* ─── Session List ─── */}
        <div className="mt-6 space-y-4">
          {loading && (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-32 rounded-lg animate-pulse" style={{ backgroundColor: '#0F0F14' }} />
              ))}
            </div>
          )}

          {!loading && filtered.length === 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center py-20 text-center"
            >
              <HexAvatar color="#71717A" size={80} />
              <h3 className="text-xl font-semibold mt-4" style={{ color: '#F8F8FA' }}>No FlowQuests yet.</h3>
              <p className="text-sm mt-1 max-w-xs" style={{ color: '#A1A1AA' }}>
                Run your first session and start building trust.
              </p>
              <button
                onClick={() => navigate('/flowquest')}
                className="mt-6 px-6 py-2.5 rounded-lg text-sm font-medium"
                style={{ backgroundColor: '#D4AF37', color: '#050507' }}
              >
                START A FLOWQUEST
              </button>
            </motion.div>
          )}

          <AnimatePresence mode="popLayout">
            {filtered.map((sess, idx) => {
              const char = CHARACTER_MAP[sess.character] || CHARACTER_MAP.vex
              const vibe = VIBE_MAP[sess.vibe] || VIBE_MAP.angry
              return (
                <motion.div
                  key={sess.id}
                  layout
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ delay: idx * 0.08, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                  onClick={() => setDetailSession(sess)}
                  className={cn(
                    'group relative rounded-lg border p-5 cursor-pointer transition-all',
                    'hover:-translate-y-0.5 hover:shadow-md'
                  )}
                  style={{
                    backgroundColor: '#0F0F14',
                    borderColor: '#2A2A35',
                  }}
                >
                  {/* Left accent strip */}
                  <div
                    className="absolute left-0 top-4 bottom-4 w-1 rounded-full"
                    style={{ backgroundColor: vibe.color }}
                  />

                  <div className="flex flex-col sm:flex-row gap-4 pl-3">
                    {/* Left column: Date + Character */}
                    <div className="flex sm:flex-col items-center sm:items-start gap-3 sm:gap-1 sm:w-28 shrink-0">
                      <div className="text-center sm:text-left">
                        <p className="text-lg font-bold" style={{ color: '#F8F8FA' }}>{fmtDate(sess.date)}</p>
                        <p className="text-xs" style={{ color: '#71717A' }}>{sess.day}</p>
                        <p className="text-xs" style={{ color: '#71717A' }}>{sess.time}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <HexAvatar color={char.color} src={char.avatar} size={32} />
                        <span className="text-xs font-bold" style={{ color: '#F8F8FA' }}>{char.name}</span>
                      </div>
                    </div>

                    {/* Center column: Vibe + Preview + Tags */}
                    <div className="flex-1 min-w-0">
                      <div
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium mb-2"
                        style={{ backgroundColor: `${vibe.color}15`, color: vibe.color, border: `1px solid ${vibe.color}30` }}
                      >
                        <span>{vibe.emoji}</span>
                        <span className="uppercase tracking-wider">{sess.vibe}</span>
                      </div>

                      <p className="text-sm italic line-clamp-2" style={{ color: '#A1A1AA' }}>
                        "{sess.preview}"
                      </p>

                      {sess.tactical_action && (
                        <div className="flex items-center gap-1 mt-2 text-xs" style={{ color: '#D4AF37' }}>
                          <Check className="w-3 h-3" />
                          {sess.tactical_action}
                        </div>
                      )}

                      <div className="flex flex-wrap items-center gap-2 mt-2">
                        {sess.mask_detected && (
                          <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full" style={{ color: '#DC2626', backgroundColor: 'rgba(220,38,38,0.08)' }}>
                            <AlertTriangle className="w-3 h-3" /> Mask detected
                          </span>
                        )}
                        {sess.regulation_completed && (
                          <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full" style={{ color: '#10B981', backgroundColor: 'rgba(16,185,129,0.08)' }}>
                            <Check className="w-3 h-3" /> Regulation done
                          </span>
                        )}
                        {sess.tactical_accepted && (
                          <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full" style={{ color: '#D4AF37', backgroundColor: 'rgba(212,175,55,0.08)' }}>
                            <Check className="w-3 h-3" /> Action locked
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Right column: Trust + Chevron */}
                    <div className="flex sm:flex-col items-center sm:items-end gap-2 sm:gap-1 shrink-0">
                      <span
                        className="text-2xl font-mono font-medium"
                        style={{ color: sess.trust_delta >= 0 ? '#D4AF37' : '#DC2626' }}
                      >
                        {sess.trust_delta >= 0 ? '+' : ''}{sess.trust_delta}
                      </span>
                      <span className="text-[10px] uppercase tracking-wider" style={{ color: '#71717A' }}>TRUST</span>
                      <ChevronRight className="w-4 h-4 sm:mt-2" style={{ color: '#71717A' }} />
                    </div>
                  </div>
                </motion.div>
              )
            })}
          </AnimatePresence>
        </div>
      </div>

      {/* ─── Detail Drawer ─── */}
      <AnimatePresence>
        {detailSession && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setDetailSession(null)}
              className="fixed inset-0 z-40 bg-black/50"
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
              className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-[480px] border-l overflow-y-auto"
              style={{ backgroundColor: '#0F0F14', borderColor: '#2A2A35' }}
            >
              <div className="p-6 space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                  <h3
                    className="text-lg font-bold tracking-wide"
                    style={{ color: '#F8F8FA', fontFamily: 'Bebas Neue, sans-serif' }}
                  >
                    SESSION DETAIL
                  </h3>
                  <button
                    onClick={() => setDetailSession(null)}
                    className="p-2 rounded-full transition-colors hover:bg-white/5"
                    style={{ color: '#A1A1AA' }}
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {/* Meta bar */}
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs" style={{ color: '#71717A' }}>
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {fmtDate(detailSession.date)} {detailSession.time}
                  </span>
                  <span className="flex items-center gap-1">
                    <MessageSquare className="w-3 h-3" />
                    {detailSession.duration_minutes} min
                  </span>
                  <span className="flex items-center gap-1">
                    <Hash className="w-3 h-3" />
                    {detailSession.character.toUpperCase()}
                  </span>
                </div>

                {/* Vibe + Safe Harbor */}
                <div className="p-4 rounded-lg border" style={{ backgroundColor: '#18181F', borderColor: '#2A2A35' }}>
                  <div className="flex items-center gap-4">
                    <span className="text-3xl">{detailSession.vibe_emoji}</span>
                    <div>
                      <p className="text-sm font-bold uppercase" style={{ color: '#F8F8FA' }}>{detailSession.vibe}</p>
                      <div className="flex items-center gap-1.5 mt-1">
                        <Shield className="w-3 h-3" style={{
                          color: detailSession.safe_harbor === 'green' ? '#10B981'
                            : detailSession.safe_harbor === 'yellow' ? '#F59E0B'
                            : '#DC2626'
                        }} />
                        <span className="text-xs capitalize" style={{ color: '#A1A1AA' }}>
                          Safe Harbor: {detailSession.safe_harbor}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Transcript */}
                <div className="space-y-3">
                  <h4 className="text-sm font-semibold uppercase tracking-wider" style={{ color: '#71717A' }}>Transcript</h4>
                  {detailSession.messages.map((msg, i) => (
                    <div
                      key={i}
                      className={cn(
                        'p-3 rounded-lg text-sm',
                        msg.role === 'user' && 'border-l-[3px]',
                        msg.role === 'system' && 'text-center'
                      )}
                      style={{
                        backgroundColor: msg.role === 'user' ? '#18181F' : msg.role === 'assistant' ? '#0F0F14' : 'transparent',
                        borderColor: msg.role === 'user' ? '#D4AF37' : '#2A2A35',
                        color: msg.role === 'system' ? '#DC2626' : '#F8F8FA',
                        border: msg.role === 'system' ? `1px solid rgba(220,38,38,0.3)` : msg.role === 'user' ? `1px solid #2A2A35` : `1px solid #2A2A35`,
                        borderLeftWidth: msg.role === 'user' ? 3 : 1,
                      }}
                    >
                      <p className={cn(msg.role === 'user' && 'italic')}>
                        {msg.content}
                      </p>
                      <span className="text-[10px] mt-1 block" style={{ color: '#71717A' }}>
                        {fmtTime(msg.timestamp)}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Tactical Action */}
                {detailSession.tactical_action && (
                  <div
                    className="p-4 rounded-lg border-l-[3px]"
                    style={{ backgroundColor: '#18181F', borderLeftColor: '#D4AF37', borderColor: '#2A2A35', borderWidth: 1, borderLeftWidth: 3 }}
                  >
                    <p className="text-xs uppercase tracking-wider mb-1" style={{ color: '#D4AF37' }}>Tactical Action</p>
                    <p className="text-sm font-medium" style={{ color: '#F8F8FA' }}>{detailSession.tactical_action}</p>
                    <p className="text-xs mt-1" style={{ color: detailSession.tactical_accepted ? '#10B981' : '#A1A1AA' }}>
                      {detailSession.tactical_accepted ? '✓ Accepted' : 'Pending'}
                    </p>
                  </div>
                )}

                {/* Trust Breakdown */}
                {detailSession.trust_breakdown && (
                  <div className="p-4 rounded-lg border" style={{ backgroundColor: '#18181F', borderColor: '#2A2A35' }}>
                    <div className="flex items-center gap-2 mb-3">
                      <BarChart3 className="w-4 h-4" style={{ color: '#D4AF37' }} />
                      <span className="text-sm font-semibold" style={{ color: '#F8F8FA' }}>Trust Breakdown</span>
                    </div>
                    <div className="space-y-2 text-sm">
                      {[
                        { label: 'Consistency', value: detailSession.trust_breakdown.consistency },
                        { label: `Weight (${detailSession.trust_breakdown.weight_multiplier}x)`, value: detailSession.trust_breakdown.weight },
                        { label: 'Honesty', value: detailSession.trust_breakdown.honesty },
                        { label: 'Regulation', value: detailSession.trust_breakdown.regulation },
                        ...(detailSession.trust_breakdown.penalty !== 0 ? [{ label: 'Penalty', value: detailSession.trust_breakdown.penalty }] : []),
                      ].map((item) => (
                        <div key={item.label} className="flex justify-between">
                          <span style={{ color: '#A1A1AA' }}>{item.label}</span>
                          <span className="font-mono" style={{ color: item.value >= 0 ? '#D4AF37' : '#DC2626' }}>
                            {item.value >= 0 ? '+' : ''}{item.value}
                          </span>
                        </div>
                      ))}
                      <div className="pt-2 border-t flex justify-between font-semibold" style={{ borderColor: '#2A2A35' }}>
                        <span style={{ color: '#F8F8FA' }}>Total</span>
                        <span className="font-mono" style={{ color: detailSession.trust_breakdown.total >= 0 ? '#D4AF37' : '#DC2626' }}>
                          {detailSession.trust_breakdown.total >= 0 ? '+' : ''}{detailSession.trust_breakdown.total}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Mask Alert */}
                {detailSession.mask_detected && (
                  <div className="p-4 rounded-lg border flex items-start gap-3" style={{ backgroundColor: 'rgba(220,38,38,0.06)', borderColor: 'rgba(220,38,38,0.3)' }}>
                    <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" style={{ color: '#DC2626' }} />
                    <div>
                      <p className="text-sm font-medium" style={{ color: '#DC2626' }}>Mask Detected</p>
                      <p className="text-xs mt-0.5" style={{ color: '#A1A1AA' }}>
                        Vibe mismatch: said '{detailSession.vibe}' but text read 'storm'
                      </p>
                    </div>
                  </div>
                )}

                {/* Footer */}
                <button
                  onClick={() => setDeleteTarget(detailSession.id)}
                  className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm transition-colors hover:bg-red-500/10"
                  style={{ color: '#DC2626' }}
                >
                  <Trash2 className="w-4 h-4" />
                  Delete session
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ─── Delete Confirmation ─── */}
      <AnimatePresence>
        {deleteTarget && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[60] bg-black/60 flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="w-full max-w-sm rounded-xl border p-6 space-y-4 text-center"
              style={{ backgroundColor: '#18181F', borderColor: '#2A2A35' }}
            >
              <AlertTriangle className="w-10 h-10 mx-auto" style={{ color: '#DC2626' }} />
              <h3 className="text-lg font-bold" style={{ color: '#F8F8FA' }}>This session will be gone.</h3>
              <p className="text-sm" style={{ color: '#A1A1AA' }}>No undo. The trust history stays, but the transcript is deleted.</p>
              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setDeleteTarget(null)}
                  className="flex-1 py-2.5 rounded-lg text-sm font-medium transition-colors hover:bg-white/5"
                  style={{ color: '#A1A1AA', backgroundColor: '#22222C' }}
                >
                  Keep it
                </button>
                <button
                  onClick={async () => {
                    if (!deleteTarget) return
                    setDeleting(true)
                    setDeleteError('')
                    try {
                      await apiDeleteSession(deleteTarget)
                      setSessions((prev) => prev.filter((s) => s.id !== deleteTarget))
                      setDeleteTarget(null)
                      setDetailSession(null)
                    } catch (err) {
                      setDeleteError(
                        err instanceof Error ? err.message : 'Could not delete this session.',
                      )
                    } finally {
                      setDeleting(false)
                    }
                  }}
                  disabled={deleting}
                  className="flex-1 py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                  style={{ backgroundColor: '#DC2626', color: '#F8F8FA' }}
                >
                  {deleting ? 'Deleting…' : 'Delete'}
                </button>
                {deleteError && (
                  <div className="basis-full text-xs mt-2" style={{ color: '#DC2626' }}>
                    {deleteError}
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
