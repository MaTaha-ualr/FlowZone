import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import {
  Flame,
  Zap,
  MessageSquare,
  FileUp,
  Mic,
  CheckCircle,
  AlertTriangle,
  Upload,
  Star,
  Scale,
  ArrowRight,
  Shield,
  Clock,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'
import { Link } from 'react-router-dom'

import { get, getActivityFeed, getCurrentSession, getTrustHistory, endSession, useApi, type TrustHistoryResponse } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import TacticalReset from '@/components/TacticalReset'
import { GetHelpButton } from '@/components/CrisisSupport'
import type {
  UserProfileResponse,
  RainbowCircleResponse,
  SessionResponse,
  ActivityItem,
  TrustDelta,
} from '@/types'

const EMPTY_TRUST_HISTORY: TrustHistoryResponse['history'] = []

/* ─── Design tokens ─── */
const COLORS = {
  bgBase: '#050507',
  bgElevated: '#0F0F14',
  bgOverlay: '#18181F',
  borderSubtle: '#2A2A35',
  borderActive: '#3E3E4F',
  brandGold: '#D4AF37',
  brandGoldBright: '#FFD700',
  brandBlue: '#00A8E8',
  brandBlueGlow: '#00D4FF',
  brandPurple: '#6C5CE7',
  brandCrimson: '#DC2626',
  textPrimary: '#F8F8FA',
  textSecondary: '#A1A1AA',
  textMuted: '#71717A',
  watch: '#6366F1',
  flex: '#10B981',
  vetted: '#D4AF37',
  safeGreen: '#10B981',
  safeYellow: '#F59E0B',
  safeRed: '#DC2626',
  vibeSolid: '#00B4D8',
  vibeAngry: '#FF6B35',
  vibeGuarded: '#64748B',
  vibeStorm: '#7C3AED',
}

/* ─── Real-data transforms ─── */

/**
 * Convert backend trust history into chart points, computing the day-over-day
 * delta from consecutive totals. History is oldest-first from the API.
 */
function toChartData(history: TrustHistoryResponse['history']): TrustDelta[] {
  return history.map((point, i) => {
    const prev = i > 0 ? history[i - 1].total : point.total
    const delta = Math.round((point.total - prev) * 10) / 10
    return {
      date: point.date.slice(5, 10),
      fullDate: point.date,
      score: Math.round(point.total * 10) / 10,
      delta,
    }
  })
}

/**
 * Derive a recent-activity feed from real trust history. Each meaningful score
 * change becomes a traceable item — no fabricated events. A dedicated activity
 * endpoint can replace this later without changing the UI.
 */
function toActivities(history: TrustHistoryResponse['history']): ActivityItem[] {
  const items: ActivityItem[] = []
  for (let i = 1; i < history.length; i++) {
    const point = history[i]
    const delta = Math.round((point.total - history[i - 1].total) * 10) / 10
    if (delta === 0) continue

    const droppedByPenalty = delta < 0 && point.penalty < history[i - 1].penalty
    items.push({
      id: point.date,
      type: droppedByPenalty ? 'mask' : delta > 0 ? 'vouch' : 'tactical_action',
      title: delta > 0 ? 'Trust score went up' : droppedByPenalty ? 'Penalty applied' : 'Trust score dipped',
      description: `Score moved to ${Math.round(point.total * 10) / 10}`,
      timestamp: new Date(point.date).toISOString(),
      delta,
    })
  }
  // Most recent first.
  return items.reverse().slice(0, 8)
}

/* ─── Animated number ─── */
function AnimatedNumber({ value, duration = 800, decimals = 0 }: { value: number; duration?: number; decimals?: number }) {
  const [display, setDisplay] = useState(0)
  const startRef = useRef<number | null>(null)
  const fromRef = useRef(0)
  const toRef = useRef(value)

  useEffect(() => {
    fromRef.current = display
    toRef.current = value
    startRef.current = null
    let raf: number
    const step = (ts: number) => {
      if (startRef.current === null) startRef.current = ts
      const p = Math.min((ts - startRef.current) / duration, 1)
      const eased = 1 - Math.pow(1 - p, 3)
      const current = fromRef.current + (toRef.current - fromRef.current) * eased
      setDisplay(current)
      if (p < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, duration])

  return <span>{decimals > 0 ? display.toFixed(decimals) : Math.round(display)}</span>
}

/* ─── Tier progress ring ─── */
function TierRing({ percent, color, size = 140, stroke = 8 }: { percent: number; color: string; size?: number; stroke?: number }) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const offset = c - (percent / 100) * c

  return (
    <svg width={size} height={size} className="transform -rotate-90">
      <circle cx={size / 2} cy={size / 2} r={r} stroke={COLORS.borderSubtle} strokeWidth={stroke} fill="none" />
      <motion.circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        stroke={color}
        strokeWidth={stroke}
        fill="none"
        strokeDasharray={c}
        initial={{ strokeDashoffset: c }}
        animate={{ strokeDashoffset: offset }}
        transition={{ duration: 1.2, ease: 'easeOut' }}
        strokeLinecap="round"
      />
    </svg>
  )
}

/* ─── Safe Harbor dot ─── */
function SafeHarborDot({ level, size = 12 }: { level: string; size?: number }) {
  const color = level === 'green' ? COLORS.safeGreen : level === 'yellow' ? COLORS.safeYellow : COLORS.safeRed
  const pulse = level === 'yellow' || level === 'red'
  return (
    <span
      className={pulse ? 'animate-pulse' : ''}
      style={{
        display: 'inline-block',
        width: size,
        height: size,
        borderRadius: '50%',
        background: color,
        boxShadow: pulse ? `0 0 8px ${color}` : 'none',
      }}
    />
  )
}

/* ─── Character helpers ─── */
function characterColor(c: string) {
  if (c === 'challenger') return COLORS.brandCrimson
  if (c === 'navigator') return COLORS.brandBlue
  if (c === 'straight_shooter') return COLORS.flex
  return COLORS.brandPurple
}

function characterName(c: string) {
  if (c === 'challenger') return 'Vex'
  if (c === 'navigator') return 'Yogi'
  if (c === 'straight_shooter') return 'Ace'
  return 'Nova'
}

function characterStyle(c: string) {
  if (c === 'challenger') return 'Challenger'
  if (c === 'navigator') return 'Navigator'
  if (c === 'straight_shooter') return 'Straight Shooter'
  return 'Strategist'
}

function characterDesc(c: string) {
  if (c === 'challenger') return 'Pushback, direct, for angry/guarded states. Not your PO.'
  if (c === 'navigator') return 'Calm, steady, for solid/storm states. Helps you find your way.'
  if (c === 'straight_shooter') return 'Real talk, no filter. For when you need honesty without the sugar.'
  return 'Tactical, analytical. For when you need a plan, not a pep talk.'
}

function characterQuote(c: string) {
  if (c === 'challenger') return "I'm not your PO — I don't care about the moral lecture."
  if (c === 'navigator') return 'Breathe. We got time to figure this out.'
  if (c === 'straight_shooter') return "Let's cut the noise. What's really going on?"
  return 'Every problem has a move. Let me show you the board.'
}

/* ─── Activity icon ─── */
function ActivityIcon({ type }: { type: ActivityItem['type'] }) {
  switch (type) {
    case 'check_in':
    case 'vibe_check':
      return <CheckCircle size={18} style={{ color: COLORS.flex }} />
    case 'flowquest':
      return <MessageSquare size={18} style={{ color: COLORS.brandPurple }} />
    case 'document':
      return <Upload size={18} style={{ color: COLORS.brandBlue }} />
    case 'mask':
      return <AlertTriangle size={18} style={{ color: COLORS.brandCrimson }} />
    case 'vouch':
      return <Star size={18} style={{ color: COLORS.brandGold }} />
    case 'tier_change':
      return <Shield size={18} style={{ color: COLORS.vetted }} />
    case 'tactical_action':
      return <Zap size={18} style={{ color: COLORS.brandBlueGlow }} />
    default:
      return <Clock size={18} style={{ color: COLORS.textMuted }} />
  }
}

/* ─── Main page ─── */
export default function Dashboard() {
  const { user } = useAuth()

  const profileApi = useApi<UserProfileResponse>(() => get(`/api/v1/profile/me`), true)
  const rainbowApi = useApi<RainbowCircleResponse>(() => get(`/api/v1/profile/rainbow-circle`), true)
  const sessionApi = useApi<SessionResponse>(() => {
    if (!user?.id) return Promise.reject(new Error('No user loaded'))
    return getCurrentSession(user.id) as Promise<SessionResponse>
  }, false)
  const { refetch: refetchSession } = sessionApi

  const historyApi = useApi<TrustHistoryResponse>(() => {
    if (!user?.id) return Promise.reject(new Error('No user loaded'))
    return getTrustHistory(user.id, 14)
  }, false)
  const { refetch: refetchHistory } = historyApi

  const activityApi = useApi<ActivityItem[]>(() => {
    if (!user?.id) return Promise.reject(new Error('No user loaded'))
    return getActivityFeed(user.id, 8) as Promise<ActivityItem[]>
  }, false)
  const { refetch: refetchActivity } = activityApi

  useEffect(() => {
    if (user?.id) {
      refetchSession().catch(() => undefined)
      refetchHistory().catch(() => undefined)
      refetchActivity().catch(() => undefined)
    }
  }, [refetchSession, refetchHistory, refetchActivity, user?.id])

  const [ending, setEnding] = useState(false)
  const [resetOpen, setResetOpen] = useState(false)

  const profile = profileApi.data || user
  const rainbow = rainbowApi.data
  const session = sessionApi.data

  const history = historyApi.data?.history ?? EMPTY_TRUST_HISTORY
  const chartData = useMemo(() => toChartData(history), [history])
  const fallbackActivities = useMemo(() => toActivities(history), [history])
  const activities = activityApi.data ?? fallbackActivities

  const handleEndSession = useCallback(async () => {
    if (!session?.id) return
    setEnding(true)
    try {
      await endSession(session.id)
      toast.success('Session ended.')
      await Promise.all([
        refetchSession().catch(() => undefined),
        refetchHistory().catch(() => undefined),
        refetchActivity().catch(() => undefined),
      ])
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not end the session.')
    } finally {
      setEnding(false)
    }
  }, [session?.id, refetchSession, refetchHistory, refetchActivity])

  const tierColor = rainbow?.current_tier_color || COLORS.watch
  const progressPercent = rainbow?.progress_percent || 0
  const currentScore = profile?.current_trust_score || 142
  const streak = profile?.check_in_streak || 3
  const safeHarbor = profile?.safe_harbor_floor || 'yellow'
  const character = profile?.current_character || 'challenger'

  const maxTierScore = rainbow?.max_score_in_tier || 200

  return (
    <div className="min-h-screen w-full" style={{ background: COLORS.bgBase, color: COLORS.textPrimary }}>
      {/* ─── Sticky Status Header ─── */}
      <motion.header
        className="sticky top-0 z-40 border-b px-4 py-4 sm:px-6"
        style={{ background: `${COLORS.bgBase}ee`, borderColor: COLORS.borderSubtle, backdropFilter: 'blur(12px)' }}
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          {/* Left — Identity */}
          <div className="flex items-center gap-3">
            <div className="relative">
              <div
                className="flex h-12 w-12 items-center justify-center rounded-full text-sm font-bold"
                style={{ background: COLORS.bgElevated, border: `2px solid ${characterColor(character)}`, color: characterColor(character) }}
              >
                {profile?.name?.[0] || 'M'}
              </div>
              <div className="absolute bottom-0 right-0">
                <SafeHarborDot level={safeHarbor} />
              </div>
            </div>
            <div className="hidden sm:block">
              <p className="text-base font-semibold" style={{ color: COLORS.textPrimary }}>
                {profile?.name || 'Marcus'}
              </p>
              <p className="text-xs" style={{ color: COLORS.textSecondary }}>
                Keep the streak alive.
              </p>
            </div>
            <div className="ml-2 flex items-center gap-1 rounded-full px-2 py-1" style={{ background: `${COLORS.brandGold}15` }}>
              <Flame size={14} style={{ color: COLORS.brandGold }} />
              <span className="text-xs font-medium" style={{ color: COLORS.brandGold }}>
                {streak} DAY STREAK
              </span>
            </div>
          </div>

          {/* Center — Trust Score (desktop) */}
          <div className="hidden flex-col items-center md:flex">
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-medium tracking-tight" style={{ color: COLORS.brandGold, fontFamily: 'JetBrains Mono, monospace' }}>
                <AnimatedNumber value={currentScore} />
              </span>
              <span className="text-xs uppercase tracking-wider" style={{ color: COLORS.textMuted }}>
                Trust
              </span>
            </div>
            <div className="mt-1 h-1 w-40 overflow-hidden rounded-full" style={{ background: COLORS.borderSubtle }}>
              <motion.div
                className="h-full rounded-full"
                style={{ background: `linear-gradient(90deg, ${COLORS.watch}, ${COLORS.flex})` }}
                initial={{ width: 0 }}
                animate={{ width: `${progressPercent}%` }}
                transition={{ duration: 1, ease: 'easeOut' }}
              />
            </div>
            <p className="mt-1 text-xs" style={{ color: COLORS.textMuted }}>
              {rainbow?.current_tier_name || 'The Watch'} → {rainbow?.all_tiers?.find((t) => t.threshold > currentScore)?.name || 'The Flex'}
            </p>
          </div>

          {/* Right — Character + Quick Vibe */}
          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-full px-3 py-1 sm:flex" style={{ background: COLORS.bgElevated, border: `1px solid ${COLORS.borderSubtle}` }}>
              <div className="h-8 w-8 overflow-hidden rounded-md" style={{ background: `${characterColor(character)}20`, border: `1px solid ${characterColor(character)}` }}>
                <img src={`/character-${character === 'challenger' ? 'vex' : character === 'navigator' ? 'yogi' : character === 'straight_shooter' ? 'ace' : 'nova'}.png`} alt="" className="h-full w-full object-cover opacity-80" />
              </div>
              <div className="flex flex-col leading-none">
                <span className="text-xs font-semibold" style={{ color: COLORS.textPrimary }}>
                  {characterName(character).toUpperCase()}
                </span>
                <span className="text-[10px]" style={{ color: COLORS.textMuted }}>
                  {characterStyle(character)}
                </span>
              </div>
            </div>
            <Link
              to="/vibe-check"
              className="rounded-full px-3 py-1.5 text-xs font-medium transition-colors"
              style={{ background: COLORS.bgElevated, border: `1px solid ${COLORS.brandGold}`, color: COLORS.brandGold }}
            >
              CHECK VIBE
            </Link>
          </div>
        </div>
      </motion.header>

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_360px]">
          {/* ─── Left Column ─── */}
          <div className="flex flex-col gap-6">
            {/* Quick Actions */}
            <motion.div
              className="grid grid-cols-2 gap-3 sm:grid-cols-4"
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            >
              {[
                { icon: MessageSquare, label: 'Run a FlowQuest', sub: 'Start session', accent: COLORS.brandGold, to: '/flowquest' },
                { icon: Zap, label: 'Check your vibe', sub: 'Mood check', accent: COLORS.brandBlue, to: '/vibe-check' },
                { icon: FileUp, label: 'Drop a document', sub: 'Upload', accent: COLORS.brandPurple, to: '/documents' },
                { icon: Mic, label: 'Speak it out', sub: 'Voice note', accent: COLORS.flex, to: '/voice' },
              ].map((action, i) => (
                <motion.div
                  key={action.label}
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.4, delay: 0.15 + i * 0.08, ease: [0.16, 1, 0.3, 1] }}
                >
                  <Link
                    to={action.to}
                    className="group flex flex-col items-center justify-center gap-2 rounded-2xl border p-4 transition-all hover:scale-[1.03] active:scale-[0.97]"
                    style={{
                      background: COLORS.bgElevated,
                      borderColor: action.accent + '40',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = action.accent
                      e.currentTarget.style.boxShadow = `0 0 20px ${action.accent}20`
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = action.accent + '40'
                      e.currentTarget.style.boxShadow = 'none'
                    }}
                  >
                    <action.icon size={32} style={{ color: action.accent }} />
                    <span className="text-center text-sm font-semibold" style={{ color: COLORS.textPrimary }}>
                      {action.label}
                    </span>
                    <span className="text-center text-xs" style={{ color: COLORS.textMuted }}>
                      {action.sub}
                    </span>
                  </Link>
                </motion.div>
              ))}
            </motion.div>

            {/* Active Session */}
            {session?.is_active && (
              <motion.div
                className="relative overflow-hidden rounded-2xl border-l-[3px] p-5"
                style={{ background: COLORS.bgElevated, borderLeftColor: COLORS.brandGold }}
                initial={{ y: 30, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              >
                <div
                  className="absolute inset-0 opacity-[0.03]"
                  style={{
                    background: `linear-gradient(90deg, transparent, ${COLORS.brandGold}, transparent)`,
                    backgroundSize: '200% 100%',
                    animation: 'shimmer 3s linear infinite',
                  }}
                />
                <style>{`
                  @keyframes shimmer {
                    0% { background-position: -200% 0; }
                    100% { background-position: 200% 0; }
                  }
                `}</style>
                <div className="relative flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3">
                    <div className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider" style={{ background: `${COLORS.brandGold}15`, color: COLORS.brandGold }}>
                      FlowQuest Active
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 overflow-hidden rounded-md" style={{ background: `${characterColor(session.character_active)}20`, border: `1px solid ${characterColor(session.character_active)}` }}>
                      <img src={`/character-${session.character_active === 'challenger' ? 'vex' : session.character_active === 'navigator' ? 'yogi' : session.character_active === 'straight_shooter' ? 'ace' : 'nova'}.png`} alt="" className="h-full w-full object-cover opacity-80" />
                    </div>
                    <div>
                      <p className="text-base font-semibold" style={{ color: COLORS.textPrimary }}>
                        {characterName(session.character_active)} is waiting.
                      </p>
                      <p className="text-xs" style={{ color: COLORS.textMuted }}>
                        Started {session.started_at ? new Date(session.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'recently'} • {session.vibe_selected || 'Solid'} vibe
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/flowquest/${session.id}`}
                      className="rounded-full px-4 py-2 text-xs font-semibold transition-all hover:scale-105 active:scale-95"
                      style={{ background: COLORS.brandGold, color: COLORS.bgBase }}
                    >
                      RESUME
                    </Link>
                    <button
                      className="rounded-full px-3 py-2 text-xs font-medium transition-colors hover:text-red-400 disabled:opacity-50 disabled:cursor-not-allowed"
                      style={{ color: COLORS.textMuted }}
                      onClick={handleEndSession}
                      disabled={ending}
                      aria-label="End the active FlowQuest session"
                    >
                      {ending ? 'ENDING…' : 'END'}
                    </button>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Trust Overview Card */}
            <motion.div
              className="rounded-2xl border p-6"
              style={{ background: COLORS.bgElevated, borderColor: COLORS.borderSubtle }}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-xl font-semibold tracking-wide" style={{ fontFamily: 'Bebas Neue, sans-serif', color: COLORS.textPrimary }}>
                  TRUST ENGINE
                </h3>
                <span className="text-xs" style={{ color: COLORS.textMuted }}>
                  Last 14 days
                </span>
              </div>

              <div className="mb-6 h-48 w-full">
                {historyApi.loading ? (
                  <div className="flex h-full items-center justify-center text-xs" style={{ color: COLORS.textMuted }}>
                    Loading your trust history…
                  </div>
                ) : chartData.length === 0 ? (
                  <div className="flex h-full flex-col items-center justify-center gap-1 text-center">
                    <p className="text-sm font-medium" style={{ color: COLORS.textSecondary }}>
                      No trust history yet
                    </p>
                    <p className="text-xs" style={{ color: COLORS.textMuted }}>
                      Check in and run a FlowQuest to start building your score.
                    </p>
                  </div>
                ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="trustFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={COLORS.brandGold} stopOpacity={0.2} />
                        <stop offset="95%" stopColor={COLORS.brandGold} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={COLORS.borderSubtle} vertical={false} />
                    <XAxis dataKey="date" tick={{ fill: COLORS.textMuted, fontSize: 10, fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: COLORS.textMuted, fontSize: 10, fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} domain={['auto', 'auto']} />
                    <Tooltip
                      contentStyle={{
                        background: COLORS.bgOverlay,
                        border: `1px solid ${COLORS.borderSubtle}`,
                        borderRadius: 12,
                        color: COLORS.textPrimary,
                        fontSize: 12,
                      }}
                      formatter={(value: number) => [value, 'Score']}
                    />
                    <Area type="monotone" dataKey="score" stroke={COLORS.brandGold} strokeWidth={2} fill="url(#trustFill)" dot={false} activeDot={{ r: 4, fill: COLORS.brandGold }} />
                  </AreaChart>
                </ResponsiveContainer>
                )}
              </div>

              {/* Key Stats */}
              <div className="grid grid-cols-3 gap-4 border-t pt-4" style={{ borderColor: COLORS.borderSubtle }}>
                <div className="flex flex-col items-center gap-1">
                  <div className="flex items-center gap-1">
                    <Flame size={16} style={{ color: COLORS.brandGold }} />
                    <span className="text-2xl font-medium" style={{ fontFamily: 'JetBrains Mono', color: COLORS.textPrimary }}>
                      <AnimatedNumber value={streak} />
                    </span>
                  </div>
                  <span className="text-xs" style={{ color: COLORS.textMuted }}>
                    Day streak
                  </span>
                </div>
                <div className="flex flex-col items-center gap-1">
                  <div className="flex items-center gap-1">
                    <Scale size={16} style={{ color: COLORS.brandBlue }} />
                    <span className="text-2xl font-medium" style={{ fontFamily: 'JetBrains Mono', color: COLORS.textPrimary }}>
                      1.5x
                    </span>
                  </div>
                  <span className="text-xs" style={{ color: COLORS.textMuted }}>
                    Current weight
                  </span>
                </div>
                <div className="flex flex-col items-center gap-1">
                  <div className="flex items-center gap-1">
                    <Star size={16} style={{ color: COLORS.brandGold }} />
                    <span className="text-2xl font-medium" style={{ fontFamily: 'JetBrains Mono', color: COLORS.textPrimary }}>
                      0
                    </span>
                  </div>
                  <span className="text-xs" style={{ color: COLORS.textMuted }}>
                    Vouches earned
                  </span>
                </div>
              </div>

              <Link
                to="/trust"
                className="mt-4 inline-flex items-center gap-1 text-xs font-medium transition-colors hover:underline"
                style={{ color: COLORS.brandGold }}
              >
                Full Breakdown <ArrowRight size={12} />
              </Link>
            </motion.div>

            {/* Recent Activity */}
            <motion.div
              className="rounded-2xl border p-6"
              style={{ background: COLORS.bgElevated, borderColor: COLORS.borderSubtle }}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
            >
              <h3 className="mb-4 text-xl font-semibold tracking-wide" style={{ fontFamily: 'Bebas Neue, sans-serif', color: COLORS.textPrimary }}>
                RECENT MOVES
              </h3>
              {!historyApi.loading && !activityApi.loading && activities.length === 0 && (
                <p className="text-sm" style={{ color: COLORS.textMuted }}>
                  No recent activity yet. Your check-ins and score changes will show up here.
                </p>
              )}
              <div className="flex flex-col gap-3">
                {activities.map((act, i) => (
                  <motion.div
                    key={act.id}
                    className="flex items-center gap-3 rounded-xl p-3 transition-colors hover:bg-white/5"
                    style={{ border: `1px solid ${COLORS.borderSubtle}` }}
                    initial={{ x: 20, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    transition={{ duration: 0.4, delay: 0.35 + i * 0.08, ease: [0.16, 1, 0.3, 1] }}
                  >
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg" style={{ background: COLORS.bgOverlay }}>
                      <ActivityIcon type={act.type} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium" style={{ color: COLORS.textPrimary }}>
                        {act.title}
                      </p>
                      <p className="text-xs" style={{ color: COLORS.textMuted }}>
                        {new Date(act.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                        {', '}
                        {new Date(act.timestamp).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                    {act.delta !== undefined && (
                      <span className="text-xs font-medium" style={{ color: act.delta >= 0 ? COLORS.brandGold : COLORS.brandCrimson }}>
                        {act.delta >= 0 ? '+' : ''}
                        {act.delta}
                      </span>
                    )}
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </div>

          {/* ─── Right Sidebar ─── */}
          <div className="flex flex-col gap-6">
            {/* Character Card */}
            <motion.div
              className="flex flex-col items-center rounded-2xl border p-6 text-center"
              style={{ background: COLORS.bgElevated, borderColor: COLORS.borderSubtle }}
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            >
              <motion.div
                className="mb-3 h-20 w-20 overflow-hidden rounded-2xl"
                style={{
                  background: `${characterColor(character)}20`,
                  border: `2px solid ${characterColor(character)}`,
                }}
                animate={{ y: [-4, 4, -4] }}
                transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
              >
                <img
                  src={`/character-${character === 'challenger' ? 'vex' : character === 'navigator' ? 'yogi' : character === 'straight_shooter' ? 'ace' : 'nova'}.png`}
                  alt={characterName(character)}
                  className="h-full w-full object-cover opacity-90"
                />
              </motion.div>
              <h2 className="text-3xl font-normal tracking-wide" style={{ fontFamily: 'Bebas Neue, sans-serif', color: COLORS.textPrimary }}>
                {characterName(character).toUpperCase()}
              </h2>
              <p className="mt-1 text-sm font-semibold" style={{ color: characterColor(character) }}>
                {characterStyle(character)}
              </p>
              <p className="mt-2 text-sm" style={{ color: COLORS.textSecondary }}>
                {characterDesc(character)}
              </p>
              <p className="mt-3 text-base italic" style={{ fontFamily: 'Permanent Marker, cursive', color: `${characterColor(character)}b0` }}>
                "{characterQuote(character)}"
              </p>
            </motion.div>

            {/* Tier Progress */}
            <motion.div
              className="flex flex-col items-center rounded-2xl border p-6"
              style={{ background: COLORS.bgElevated, borderColor: COLORS.borderSubtle }}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="mb-3 text-center">
                <span className="text-lg font-normal tracking-wide" style={{ fontFamily: 'Bebas Neue, sans-serif', color: tierColor }}>
                  {rainbow?.current_tier_name?.toUpperCase() || 'THE WATCH'} {rainbow?.current_tier_emoji || '👁️'}
                </span>
              </div>
              <div className="relative">
                <TierRing percent={progressPercent} color={tierColor} size={140} stroke={8} />
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-3xl font-medium" style={{ fontFamily: 'JetBrains Mono', color: COLORS.textPrimary }}>
                    <AnimatedNumber value={currentScore} />
                  </span>
                  <span className="text-xs" style={{ color: COLORS.textMuted }}>
                    / {maxTierScore}
                  </span>
                </div>
              </div>
              <p className="mt-3 text-xs" style={{ color: COLORS.textMuted }}>
                {rainbow?.all_tiers?.find((t) => t.threshold > currentScore)?.name || 'The Flex'} at {maxTierScore}
              </p>
              <p className="text-xs font-medium" style={{ color: COLORS.brandGold }}>
                +{Math.round((maxTierScore - currentScore) * 10) / 10} to {rainbow?.all_tiers?.find((t) => t.threshold > currentScore)?.name || 'The Flex'}
              </p>
            </motion.div>

            {/* Safe Harbor */}
            <motion.div
              className="rounded-2xl border-l-[3px] p-5"
              style={{
                background: COLORS.bgElevated,
                borderColor: COLORS.borderSubtle,
                borderLeftColor: safeHarbor === 'green' ? COLORS.safeGreen : safeHarbor === 'yellow' ? COLORS.safeYellow : COLORS.safeRed,
              }}
              initial={{ x: 20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.35, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="flex items-center gap-2">
                <SafeHarborDot level={safeHarbor} size={20} />
                <h4 className="text-base font-semibold uppercase tracking-wide" style={{ color: safeHarbor === 'green' ? COLORS.safeGreen : safeHarbor === 'yellow' ? COLORS.safeYellow : COLORS.safeRed }}>
                  SAFE HARBOR: {safeHarbor}
                </h4>
              </div>
              <p className="mt-2 text-sm" style={{ color: COLORS.textSecondary }}>
                {safeHarbor === 'green'
                  ? 'All clear. No elevated concerns on file.'
                  : safeHarbor === 'yellow'
                    ? 'Caution level. Trauma history on file. Check in daily.'
                    : 'Critical level. Immediate intervention needed.'}
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <button
                  onClick={() => setResetOpen(true)}
                  className="rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
                  style={{ background: `${COLORS.brandGold}15`, color: COLORS.brandGold, border: `1px solid ${COLORS.brandGold}40` }}
                >
                  Run Tactical Reset
                </button>
                {safeHarbor !== 'green' && <GetHelpButton />}
              </div>
              {safeHarbor === 'red' && (
                <p className="mt-2 text-xs" style={{ color: COLORS.safeRed }}>
                  If you&apos;re in danger or thinking about hurting yourself, use Get Help now.
                </p>
              )}
            </motion.div>

            {/* Tactical Actions */}
            <motion.div
              className="rounded-2xl border p-5"
              style={{ background: COLORS.bgElevated, borderColor: COLORS.borderSubtle }}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
            >
              <h4 className="mb-3 text-base font-semibold" style={{ color: COLORS.textPrimary }}>
                YOUR MOVES
              </h4>
              <div className="flex flex-col gap-2">
                {[
                  { text: 'Attend first period tomorrow', due: 'Due tomorrow', urgent: true },
                  { text: 'Check in with Coach Ray', due: 'Due Mar 14', urgent: false },
                ].map((item, i) => (
                  <motion.div
                    key={i}
                    className="flex items-center gap-2 rounded-lg p-2"
                    style={{ background: COLORS.bgOverlay }}
                    initial={{ x: -15, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    transition={{ duration: 0.4, delay: 0.45 + i * 0.08, ease: [0.16, 1, 0.3, 1] }}
                  >
                    <input type="checkbox" className="h-4 w-4 accent-amber-500" />
                    <span className="flex-1 text-sm" style={{ color: COLORS.textPrimary }}>
                      {item.text}
                    </span>
                    <span className="text-[10px] font-medium" style={{ color: item.urgent ? COLORS.safeYellow : COLORS.textMuted }}>
                      {item.due}
                    </span>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </div>
        </div>
      </main>

      <TacticalReset open={resetOpen} onOpenChange={setResetOpen} />
    </div>
  )
}
