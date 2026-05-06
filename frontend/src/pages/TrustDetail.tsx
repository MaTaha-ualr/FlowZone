import { useEffect, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowLeft, ChevronDown, ChevronUp, Star, AlertTriangle, Shield, CheckCircle } from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from 'recharts'

import { get, getTrustScore, useApi } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import type { TrustScoreResponse, TrustDelta, VouchRecord, RainbowCircleResponse } from '@/types'

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
}

/* ─── Mock data ─── */
function genHistory(days = 30): TrustDelta[] {
  const today = new Date()
  const data: TrustDelta[] = []
  let score = 100
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    const delta = Math.random() > 0.75 ? (Math.random() > 0.4 ? Math.round((Math.random() * 6 + 1) * 10) / 10 : -Math.round(Math.random() * 12 + 3)) : Math.round((Math.random() * 2.5) * 10) / 10
    score += delta
    data.push({
      date: d.toISOString().slice(5, 10),
      score: Math.round(score * 10) / 10,
      delta,
      event: i === 5 ? 'Mask detected' : i === 12 ? 'Tier change' : i === 20 ? 'Vouch earned' : i === 8 ? 'Tactical Action' : undefined,
      event_type: i === 5 ? 'mask' : i === 12 ? 'tier_change' : i === 20 ? 'vouch' : i === 8 ? 'tactical_action' : undefined,
    })
  }
  return data
}

const mockVouches: VouchRecord[] = [
  { id: '1', mentor_name: 'Coach Ray', vouch_points: 25, created_at: '2024-03-01T10:00:00Z', note: 'Showed up every day this week.' },
]

const mockTrustScore: TrustScoreResponse = {
  user_id: 'demo',
  score: 142.0,
  display_score: 142,
  tier: 'The Watch',
  components: {
    consistency: 3,
    weight: 1.5,
    honesty: 25,
    regulation: 10,
    mentor_vouch: 0,
    penalty: -15,
    time_days: 12,
  },
  streak_days: 3,
  weight_multiplier: 1.5,
  masks_detected: 1,
  resets_completed: 1,
  traps_disclosed: 1,
  mentor_vouches: 0,
  days_active: 12,
}

function tierDisplayName(tier?: string): string {
  if (!tier) return 'The Watch'
  const normalized = tier.trim()
  if (normalized.toLowerCase().startsWith('the ')) return normalized
  const name = normalized
    .split('_')
    .filter((part) => part && part !== 'the')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
  return `The ${name || 'Watch'}`
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? value as Record<string, unknown> : {}
}

function normalizeTrustScore(data: unknown): TrustScoreResponse {
  const record = asRecord(data)
  if (record.score !== undefined && record.components) return data as TrustScoreResponse
  const score = Number(record.current_score ?? record.total_score ?? record.baseline_score ?? 0)
  return {
    ...mockTrustScore,
    user_id: typeof record.user_id === 'string' ? record.user_id : mockTrustScore.user_id,
    score,
    display_score: score,
    tier: tierDisplayName(typeof record.current_tier === 'string' ? record.current_tier : typeof record.tier === 'string' ? record.tier : undefined),
    components: {
      ...mockTrustScore.components,
      consistency: Number(record.check_in_streak ?? mockTrustScore.components.consistency),
    },
    streak_days: Number(record.check_in_streak ?? mockTrustScore.streak_days),
  }
}

/* ─── Animated count ─── */
function AnimatedCount({ value, duration = 800, decimals = 0, suffix = '' }: { value: number; duration?: number; decimals?: number; suffix?: string }) {
  const [display, setDisplay] = useState(0)
  useMemo(() => {
    let raf: number
    const start = performance.now()
    const from = display
    const to = value
    const step = (ts: number) => {
      const p = Math.min((ts - start) / duration, 1)
      const eased = 1 - Math.pow(1 - p, 3)
      setDisplay(from + (to - from) * eased)
      if (p < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])
  return <span>{decimals > 0 ? display.toFixed(decimals) : Math.round(display)}{suffix}</span>
}

/* ─── Tier ring component ─── */
function TierRingSVG({ percent, color, size = 120, stroke = 6, label }: { percent: number; color: string; size?: number; stroke?: number; label?: string }) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const offset = c - (percent / 100) * c
  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={size} height={size} className="-rotate-90">
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
          whileInView={{ strokeDashoffset: offset }}
          viewport={{ once: true }}
          transition={{ duration: 1.2, ease: 'easeOut' }}
          strokeLinecap="round"
        />
      </svg>
      {label && <span className="text-xs font-medium" style={{ color }}>{label}</span>}
    </div>
  )
}

/* ─── Formula component ─── */
const FORMULA_COMPONENTS = [
  { key: 'C', label: 'CONSISTENCY', value: 3, color: COLORS.brandBlue, desc: 'Consecutive daily check-ins', status: "Streak active. Don't break it." },
  { key: 'W', label: 'WEIGHT', value: 1.5, color: '#FF8C00', desc: 'Multiplier for checking in on Hard Days', status: "You're carrying heat. It counts more." },
  { key: 'H', label: 'HONESTY BONUS', value: 25, color: COLORS.flex, desc: 'Proactively disclosing a Trap', status: 'You named it. That\'s real.' },
  { key: 'R', label: 'REGULATION', value: 10, color: COLORS.brandBlueGlow, desc: 'Completing Tactical Resets', status: 'You reset. That matters.' },
  { key: 'M', label: 'MENTOR VOUCH', value: 0, color: COLORS.textMuted, desc: 'Manually awarded by mentor', status: 'No vouches yet. Coach Ray is watching.' },
  { key: 'P', label: 'PENALTY', value: -15, color: COLORS.brandCrimson, desc: 'Detected Mask or masking behavior', status: 'You masked. The Engine caught it. Keep it real next time.' },
  { key: 'T', label: 'TIME', value: 12, color: COLORS.textMuted, desc: 'Days since first check-in (denominator)', status: 'Time normalizes your score. More days = fairer score.' },
]

function FormulaCard({ comp, expanded, onToggle }: { comp: typeof FORMULA_COMPONENTS[0]; expanded: boolean; onToggle: () => void }) {
  return (
    <motion.div
      className="cursor-pointer overflow-hidden rounded-xl border"
      style={{ background: COLORS.bgElevated, borderColor: expanded ? comp.color : COLORS.borderSubtle }}
      onClick={onToggle}
      layout
    >
      <div className="flex items-center gap-3 px-4 py-3">
        <span
          className="flex h-8 w-8 items-center justify-center rounded-lg text-sm font-bold"
          style={{ background: `${comp.color}20`, color: comp.color }}
        >
          {comp.key}
        </span>
        <div className="flex-1">
          <span className="text-sm font-semibold" style={{ color: COLORS.textPrimary }}>
            {comp.label}
          </span>
        </div>
        <span className="text-lg font-medium" style={{ fontFamily: 'JetBrains Mono', color: comp.color }}>
          {comp.value > 0 && comp.key !== 'T' ? (comp.key === 'W' ? `${comp.value}x` : `+${comp.value}`) : comp.value}
        </span>
        {expanded ? <ChevronUp size={16} style={{ color: COLORS.textMuted }} /> : <ChevronDown size={16} style={{ color: COLORS.textMuted }} />}
      </div>
      <AnimatePresence>
        {expanded && (
          <motion.div
            className="px-4 pb-4"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <p className="text-sm" style={{ color: COLORS.textSecondary }}>
              {comp.desc}
            </p>
            <p className="mt-1 text-xs font-medium" style={{ color: comp.color }}>
              {comp.status}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default function TrustDetail() {
  const { user } = useAuth()
  const [expandedKey, setExpandedKey] = useState<string | null>(null)
  const [timeRange, setTimeRange] = useState<'7D' | '30D' | '90D' | 'ALL'>('30D')

  const scoreApi = useApi<TrustScoreResponse>(async () => {
    if (!user?.id) throw new Error('No user loaded')
    return normalizeTrustScore(await getTrustScore(user.id))
  }, false)
  const rainbowApi = useApi<RainbowCircleResponse>(() => get('/api/v1/profile/rainbow-circle'), false)
  const { refetch: refetchScore } = scoreApi
  const { refetch: refetchRainbow } = rainbowApi

  useEffect(() => {
    if (user?.id) {
      refetchScore().catch(() => undefined)
      refetchRainbow().catch(() => undefined)
    }
  }, [refetchRainbow, refetchScore, user?.id])

  const trustScore = scoreApi.data || mockTrustScore
  const rainbow = rainbowApi.data

  const history = useMemo(() => {
    const days = timeRange === '7D' ? 7 : timeRange === '30D' ? 30 : timeRange === '90D' ? 90 : 180
    return genHistory(days)
  }, [timeRange])

  const currentScore = trustScore.score
  const tierName = trustScore.tier
  const tierColor = tierName === 'The Watch' ? COLORS.watch : tierName === 'The Flex' ? COLORS.flex : COLORS.vetted
  const maxTierScore = rainbow?.max_score_in_tier || 200
  const minTierScore = rainbow?.min_score_in_tier || 0
  const progressPercent = rainbow?.progress_percent || ((currentScore - minTierScore) / (maxTierScore - minTierScore)) * 100

  return (
    <div className="min-h-screen w-full" style={{ background: COLORS.bgBase, color: COLORS.textPrimary }}>
      {/* ─── Header ─── */}
      <div className="px-4 pt-6 sm:px-6">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <Link to="/" className="flex items-center gap-1 text-sm transition-colors hover:underline" style={{ color: COLORS.textMuted }}>
            <ArrowLeft size={16} />
            Dashboard
          </Link>
          <div className="text-right">
            <span className="text-4xl font-medium sm:text-5xl" style={{ fontFamily: 'JetBrains Mono', color: COLORS.brandGold }}>
              <AnimatedCount value={currentScore} decimals={1} />
            </span>
            <p className="text-xs uppercase tracking-wider" style={{ color: COLORS.textMuted }}>
              Trust Score
            </p>
          </div>
        </div>
        <div className="mx-auto mt-4 max-w-5xl">
          <motion.h1
            className="text-4xl font-normal tracking-wide sm:text-5xl"
            style={{ fontFamily: 'Bebas Neue, sans-serif' }}
            initial={{ y: 30, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          >
            TRUST ENGINE
          </motion.h1>
          <p className="text-sm" style={{ color: COLORS.textSecondary }}>
            Full formula. Full transparency. No cap.
          </p>
        </div>
      </div>

      <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_380px]">
          {/* ─── Main Column ─── */}
          <div className="flex flex-col gap-6">
            {/* Formula Visualization */}
            <motion.div
              className="rounded-2xl border p-6"
              style={{ background: COLORS.bgElevated, borderColor: COLORS.borderSubtle }}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.1 }}
            >
              <h3 className="mb-4 text-xl font-semibold tracking-wide" style={{ fontFamily: 'Bebas Neue, sans-serif' }}>
                THE FORMULA
              </h3>
              <div className="mb-6 flex flex-wrap items-center justify-center gap-2 text-xl sm:text-2xl" style={{ fontFamily: 'JetBrains Mono' }}>
                {['(', 'C', '+', 'W', '+', 'H', '+', 'R', '+', 'M', '-', 'P', ')', '/', 'T'].map((token, i) => (
                  <motion.span
                    key={i}
                    className="cursor-pointer rounded px-1 py-0.5 transition-colors"
                    style={{
                      color: ['C', 'W', 'H', 'R', 'M', 'P', 'T'].includes(token) ? FORMULA_COMPONENTS.find((c) => c.key === token)?.color || COLORS.textPrimary : COLORS.textMuted,
                    }}
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ duration: 0.3, delay: 0.2 + i * 0.05 }}
                    onClick={() => {
                      if (['C', 'W', 'H', 'R', 'M', 'P', 'T'].includes(token)) {
                        setExpandedKey(expandedKey === token ? null : token)
                      }
                    }}
                  >
                    {token}
                  </motion.span>
                ))}
              </div>

              <div className="flex flex-col gap-2">
                {FORMULA_COMPONENTS.map((comp) => (
                  <FormulaCard
                    key={comp.key}
                    comp={comp}
                    expanded={expandedKey === comp.key}
                    onToggle={() => setExpandedKey(expandedKey === comp.key ? null : comp.key)}
                  />
                ))}
              </div>

              <div className="mt-4 rounded-lg p-3 text-center text-sm" style={{ background: COLORS.bgOverlay, fontFamily: 'JetBrains Mono' }}>
                <span style={{ color: COLORS.brandBlue }}>{trustScore.components.consistency}</span>
                {' + '}
                <span style={{ color: '#FF8C00' }}>{trustScore.components.weight}x</span>
                {' + '}
                <span style={{ color: COLORS.flex }}>{trustScore.components.honesty}</span>
                {' + '}
                <span style={{ color: COLORS.brandBlueGlow }}>{trustScore.components.regulation}</span>
                {' + '}
                <span style={{ color: COLORS.textMuted }}>{trustScore.components.mentor_vouch}</span>
                {' - '}
                <span style={{ color: COLORS.brandCrimson }}>{Math.abs(trustScore.components.penalty)}</span>
                {' ) / '}
                <span style={{ color: COLORS.textMuted }}>{trustScore.components.time_days}</span>
                {' = '}
                <span className="font-medium" style={{ color: COLORS.brandGold }}>
                  {currentScore.toFixed(1)}
                </span>
              </div>
            </motion.div>

            {/* Score History Chart */}
            <motion.div
              className="rounded-2xl border p-6"
              style={{ background: COLORS.bgElevated, borderColor: COLORS.borderSubtle }}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-xl font-semibold tracking-wide" style={{ fontFamily: 'Bebas Neue, sans-serif' }}>
                  TRUST HISTORY
                </h3>
                <div className="flex gap-1">
                  {(['7D', '30D', '90D', 'ALL'] as const).map((range) => (
                    <button
                      key={range}
                      className="rounded-md px-2 py-1 text-xs font-medium transition-colors"
                      style={{
                        background: timeRange === range ? COLORS.brandGold : COLORS.bgOverlay,
                        color: timeRange === range ? COLORS.bgBase : COLORS.textMuted,
                      }}
                      onClick={() => setTimeRange(range)}
                    >
                      {range}
                    </button>
                  ))}
                </div>
              </div>
              <div className="h-64 w-full sm:h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={history} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="trustDetailFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={COLORS.brandGold} stopOpacity={0.15} />
                        <stop offset="95%" stopColor={COLORS.brandGold} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={COLORS.borderSubtle} vertical={false} />
                    <XAxis dataKey="date" tick={{ fill: COLORS.textMuted, fontSize: 10, fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: COLORS.textMuted, fontSize: 10, fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} domain={[0, 500]} />
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
                    <Area type="monotone" dataKey="score" stroke={COLORS.brandGold} strokeWidth={3} fill="url(#trustDetailFill)" dot={{ r: 3, fill: COLORS.brandGold }} activeDot={{ r: 5, fill: COLORS.brandGold }} />
                    {history
                      .filter((d) => d.event_type)
                      .map((d, i) => (
                        <ReferenceLine
                          key={i}
                          x={d.date}
                          stroke={
                            d.event_type === 'mask'
                              ? COLORS.brandCrimson
                              : d.event_type === 'tier_change'
                                ? COLORS.vetted
                                : d.event_type === 'vouch'
                                  ? COLORS.brandBlue
                                  : COLORS.flex
                          }
                          strokeDasharray="3 3"
                          strokeWidth={1}
                        />
                      ))}
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              {/* Event markers legend */}
              <div className="mt-3 flex flex-wrap gap-3">
                {[
                  { color: COLORS.brandCrimson, label: 'Mask detected', icon: AlertTriangle },
                  { color: COLORS.vetted, label: 'Tier unlock', icon: Star },
                  { color: COLORS.brandBlue, label: 'Mentor vouch', icon: Shield },
                  { color: COLORS.flex, label: 'Tactical Action', icon: CheckCircle },
                ].map((item) => (
                  <div key={item.label} className="flex items-center gap-1 text-xs" style={{ color: COLORS.textMuted }}>
                    <item.icon size={12} style={{ color: item.color }} />
                    {item.label}
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Recent Deltas */}
            <motion.div
              className="rounded-2xl border p-5"
              style={{ background: COLORS.bgElevated, borderColor: COLORS.borderSubtle }}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              <h4 className="mb-3 text-base font-semibold" style={{ color: COLORS.textPrimary }}>
                RECENT CHANGES
              </h4>
              <div className="flex flex-col gap-2">
                {[
                  { date: 'Mar 12, 9:30 AM', event: 'Vibe Check: Solid', delta: 4.8 },
                  { date: 'Mar 11, 8:15 PM', event: 'FlowQuest with Vex completed', delta: 3.2 },
                  { date: 'Mar 10, 7:45 PM', event: 'Tactical Reset completed', delta: 1.0 },
                  { date: 'Mar 9, 6:00 PM', event: 'Mask detected during check-in', delta: -15.0 },
                  { date: 'Mar 9, 6:05 PM', event: 'Honesty Bonus: Trap disclosed', delta: 25.0 },
                ].map((item, i) => (
                  <motion.div
                    key={i}
                    className="flex items-center justify-between rounded-lg p-2"
                    style={{ background: COLORS.bgOverlay }}
                    initial={{ x: 15, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    transition={{ duration: 0.4, delay: 0.35 + i * 0.08 }}
                  >
                    <div>
                      <p className="text-xs" style={{ color: COLORS.textMuted }}>
                        {item.date}
                      </p>
                      <p className="text-sm" style={{ color: COLORS.textPrimary }}>
                        {item.event}
                      </p>
                    </div>
                    <span
                      className="text-xs font-medium"
                      style={{
                        color: item.delta > 0 ? COLORS.brandGold : item.delta < 0 ? COLORS.brandCrimson : COLORS.textMuted,
                      }}
                    >
                      {item.delta > 0 ? '+' : ''}
                      {item.delta.toFixed(1)}
                    </span>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </div>

          {/* ─── Sidebar ─── */}
          <div className="flex flex-col gap-6">
            {/* Tier Progression */}
            <motion.div
              className="rounded-2xl border p-6"
              style={{ background: COLORS.bgElevated, borderColor: COLORS.borderSubtle }}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <div className="mb-4 flex flex-col items-center">
                <div className="mb-2 h-16 w-16 overflow-hidden rounded-xl" style={{ background: `${tierColor}20` }}>
                  <img src={`/tier-${tierName.toLowerCase().replace('the ', '')}.png`} alt={tierName} className="h-full w-full object-cover opacity-80" />
                </div>
                <h2 className="text-2xl font-normal tracking-wide" style={{ fontFamily: 'Bebas Neue, sans-serif', color: tierColor }}>
                  {tierName.toUpperCase()}
                </h2>
                <p className="text-xs" style={{ color: COLORS.textMuted }}>
                  {minTierScore} — {maxTierScore}
                </p>
                <p className="mt-1 text-2xl font-medium" style={{ fontFamily: 'JetBrains Mono', color: COLORS.textPrimary }}>
                  {currentScore}
                </p>
              </div>
              <TierRingSVG percent={progressPercent} color={tierColor} size={140} stroke={8} />

              {/* Next Tier Preview */}
              <div className="mt-6 border-t pt-4" style={{ borderColor: COLORS.borderSubtle }}>
                <div className="flex items-center gap-3">
                  <div className="h-12 w-12 overflow-hidden rounded-lg opacity-60" style={{ background: `${COLORS.flex}20` }}>
                    <img src="/tier-flex.png" alt="The Flex" className="h-full w-full object-cover" />
                  </div>
                  <div>
                    <h3 className="text-lg font-normal tracking-wide" style={{ fontFamily: 'Bebas Neue, sans-serif', color: COLORS.flex }}>
                      THE FLEX
                    </h3>
                    <p className="text-xs" style={{ color: COLORS.textMuted }}>
                      200 — 499
                    </p>
                  </div>
                </div>
                <p className="mt-2 text-sm font-medium" style={{ color: COLORS.brandGold }}>
                  +{Math.round((200 - currentScore) * 10) / 10} to unlock
                </p>
                <p className="mt-1 text-xs" style={{ color: COLORS.textMuted }}>
                  The Flex benefits:
                </p>
                <ul className="mt-1 flex flex-col gap-1">
                  {['Curfew extension vouches', 'Reduced check-in frequency', 'Mentor priority access'].map((b) => (
                    <li key={b} className="text-xs" style={{ color: COLORS.textSecondary }}>
                      • {b}
                    </li>
                  ))}
                </ul>
              </div>
            </motion.div>

            {/* Vouch History */}
            <motion.div
              className="rounded-2xl border p-5"
              style={{ background: COLORS.bgElevated, borderColor: COLORS.borderSubtle }}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              <h4 className="mb-3 text-base font-semibold" style={{ color: COLORS.textPrimary }}>
                VOUCHES
              </h4>
              <div className="mb-2 flex items-baseline gap-1">
                <span className="text-2xl font-medium" style={{ fontFamily: 'JetBrains Mono', color: COLORS.textPrimary }}>
                  {trustScore.mentor_vouches}
                </span>
                <span className="text-xs" style={{ color: COLORS.textMuted }}>
                  earned
                </span>
              </div>
              {mockVouches.length === 0 ? (
                <p className="text-sm" style={{ color: COLORS.textMuted }}>
                  None yet
                </p>
              ) : (
                <div className="flex flex-col gap-2">
                  {mockVouches.map((vouch) => (
                    <div key={vouch.id} className="rounded-lg p-2" style={{ background: COLORS.bgOverlay }}>
                      <div className="flex items-center gap-2">
                        <Star size={14} style={{ color: COLORS.brandGold }} />
                        <span className="text-sm font-medium" style={{ color: COLORS.textPrimary }}>
                          +{vouch.vouch_points} from {vouch.mentor_name}
                        </span>
                      </div>
                      <p className="text-xs" style={{ color: COLORS.textMuted }}>
                        {new Date(vouch.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  ))}
                </div>
              )}
              <p className="mt-3 text-xs" style={{ color: COLORS.textMuted }}>
                Vouches come from mentors seeing your moves.
              </p>
              <p className="text-xs" style={{ color: COLORS.brandBlue }}>
                Coach Ray can vouch when you've shown out.
              </p>
            </motion.div>
          </div>
        </div>
      </main>
    </div>
  )
}
