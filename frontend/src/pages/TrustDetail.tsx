import { useEffect, useMemo, useRef, useState } from 'react'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
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

import {
  get,
  getTrustHistory,
  getTrustScore,
  getVouches,
  useApi,
  type TrustHistoryPoint,
  type TrustHistoryResponse,
} from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import type { RainbowCircleResponse } from '@/types'

const EMPTY_TRUST_HISTORY: TrustHistoryPoint[] = []

const COLORS = {
  bgBase: '#050507',
  bgElevated: '#0F0F14',
  bgOverlay: '#18181F',
  borderSubtle: '#2A2A35',
  brandGold: '#D4AF37',
  brandBlue: '#00A8E8',
  brandBlueGlow: '#00D4FF',
  brandCrimson: '#DC2626',
  textPrimary: '#F8F8FA',
  textSecondary: '#A1A1AA',
  textMuted: '#71717A',
  watch: '#6366F1',
  flex: '#10B981',
  vetted: '#D4AF37',
}

interface TrustSummary {
  user_id: string
  score: number
  display_score: number
  tier: string
  check_in_streak: number
  baseline_score: number
  next_tier: string | null
  points_to_next_tier: number | null
}

interface ChartPoint {
  date: string
  fullDate: string
  score: number
  event_type?: 'mask' | 'tier_change' | 'vouch' | 'tactical_action'
}

interface RecentChange {
  date: string
  event: string
  delta: number
  event_type?: ChartPoint['event_type']
}

interface VouchDisplay {
  id: string
  type: string
  name: string
  credits_spent: number
  status: string
  created_at: string | null
}

type FormulaKey = 'C' | 'W' | 'H' | 'R' | 'M' | 'P'

interface FormulaComponent {
  key: FormulaKey
  label: string
  value: number
  displayValue: string
  color: string
  desc: string
  status: string
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? value as Record<string, unknown> : {}
}

function numberValue(value: unknown, fallback = 0): number {
  const n = Number(value)
  return Number.isFinite(n) ? n : fallback
}

function stringValue(value: unknown, fallback = ''): string {
  return typeof value === 'string' && value.length > 0 ? value : fallback
}

function formatNumber(value: number, decimals = 1): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(decimals)
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

function normalizeTrustSummary(data: unknown, fallbackUser?: { id?: string; display_score?: number; current_trust_score?: number; current_tier?: string; check_in_streak?: number } | null): TrustSummary {
  const record = asRecord(data)
  const score = numberValue(record.current_score ?? record.score ?? record.total_score, fallbackUser?.current_trust_score ?? fallbackUser?.display_score ?? 0)
  return {
    user_id: stringValue(record.user_id, fallbackUser?.id ?? ''),
    score,
    display_score: numberValue(record.display_score, score),
    tier: tierDisplayName(stringValue(record.current_tier ?? record.tier, fallbackUser?.current_tier ?? 'the_watch')),
    check_in_streak: numberValue(record.check_in_streak, fallbackUser?.check_in_streak ?? 0),
    baseline_score: numberValue(record.baseline_score, score),
    next_tier: typeof record.next_tier === 'string' ? tierDisplayName(record.next_tier) : null,
    points_to_next_tier: record.points_to_next_tier === null || record.points_to_next_tier === undefined ? null : numberValue(record.points_to_next_tier),
  }
}

function eventTypeFor(point: TrustHistoryPoint): ChartPoint['event_type'] | undefined {
  if (point.penalty > 0) return 'mask'
  if (point.mentor > 0) return 'vouch'
  if (point.regulation > 0) return 'tactical_action'
  return undefined
}

function chartDataFrom(history: TrustHistoryPoint[]): ChartPoint[] {
  return history.map((point) => ({
    date: point.date.slice(5, 10),
    fullDate: point.date,
    score: Math.round(point.total * 10) / 10,
    event_type: eventTypeFor(point),
  }))
}

function recentChangesFrom(history: TrustHistoryPoint[]): RecentChange[] {
  return history
    .slice()
    .reverse()
    .map((point) => {
      const parts = []
      if (point.consistency) parts.push(`${point.consistency} day streak`)
      if (point.weight && point.weight !== 1) parts.push(`${formatNumber(point.weight)}x hard-day weight`)
      if (point.honesty) parts.push(`+${formatNumber(point.honesty)} honesty`)
      if (point.regulation) parts.push(`+${formatNumber(point.regulation)} regulation`)
      if (point.mentor) parts.push(`+${formatNumber(point.mentor)} mentor vouch`)
      if (point.penalty) parts.push(`-${formatNumber(point.penalty)} penalty`)

      return {
        date: point.date,
        event: parts.length > 0 ? parts.join(', ') : 'Trust snapshot recorded',
        delta: Math.round(point.total * 10) / 10,
        event_type: eventTypeFor(point),
      }
    })
    .slice(0, 5)
}

function vouchesFromApi(raw: unknown): VouchDisplay[] {
  const record = asRecord(raw)
  const items = Array.isArray(record.vouches) ? record.vouches : []
  return items.map((item) => {
    const v = asRecord(item)
    const type = stringValue(v.type, 'vouch')
    return {
      id: stringValue(v.id, crypto.randomUUID()),
      type,
      name: type.split('_').map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(' '),
      credits_spent: numberValue(v.credits_spent),
      status: stringValue(v.status, 'active'),
      created_at: typeof v.created_at === 'string' ? v.created_at : null,
    }
  })
}

function formulaComponentsFrom(point: TrustHistoryPoint | undefined, summary: TrustSummary): FormulaComponent[] {
  const consistency = point?.consistency ?? summary.check_in_streak
  const weight = point?.weight ?? 1
  const honesty = point?.honesty ?? 0
  const regulation = point?.regulation ?? 0
  const mentor = point?.mentor ?? 0
  const penalty = point?.penalty ?? 0

  return [
    {
      key: 'C',
      label: 'CONSISTENCY',
      value: consistency,
      displayValue: formatNumber(consistency, 0),
      color: COLORS.brandBlue,
      desc: 'Consecutive daily check-ins recorded by the trust engine.',
      status: consistency > 0 ? 'Streak active.' : 'No check-in streak yet.',
    },
    {
      key: 'W',
      label: 'WEIGHT',
      value: weight,
      displayValue: `${formatNumber(weight)}x`,
      color: '#FF8C00',
      desc: 'Multiplier applied on hard-day vibes.',
      status: weight > 1 ? 'Hard-day weight applied.' : 'Normal day weight.',
    },
    {
      key: 'H',
      label: 'HONESTY BONUS',
      value: honesty,
      displayValue: `+${formatNumber(honesty)}`,
      color: COLORS.flex,
      desc: 'Credit for proactively naming traps or disclosures.',
      status: honesty > 0 ? 'Honesty credit recorded.' : 'No honesty bonus in the latest snapshot.',
    },
    {
      key: 'R',
      label: 'REGULATION',
      value: regulation,
      displayValue: `+${formatNumber(regulation)}`,
      color: COLORS.brandBlueGlow,
      desc: 'Credit for completing tactical reset or regulation work.',
      status: regulation > 0 ? 'Regulation credit recorded.' : 'No regulation credit in the latest snapshot.',
    },
    {
      key: 'M',
      label: 'MENTOR VOUCH',
      value: mentor,
      displayValue: `+${formatNumber(mentor)}`,
      color: COLORS.textMuted,
      desc: 'Manual mentor points awarded for observed progress.',
      status: mentor > 0 ? 'Mentor vouch included.' : 'No mentor vouch in the latest snapshot.',
    },
    {
      key: 'P',
      label: 'PENALTY',
      value: penalty,
      displayValue: `-${formatNumber(penalty)}`,
      color: COLORS.brandCrimson,
      desc: 'Deductions for detected masking or risk events.',
      status: penalty > 0 ? 'Penalty applied.' : 'No penalty in the latest snapshot.',
    },
  ]
}

function tierImageSlug(name: string): string {
  return name.toLowerCase().replace(/^the\s+/, '').replace(/\s+/g, '-')
}

function AnimatedCount({ value, duration = 800, decimals = 0, suffix = '' }: { value: number; duration?: number; decimals?: number; suffix?: string }) {
  const [display, setDisplay] = useState(0)
  const displayRef = useRef(0)
  const prefersReducedMotion = useReducedMotion()

  useEffect(() => {
    if (prefersReducedMotion) {
      displayRef.current = value
      setDisplay(value)
      return
    }

    let raf = 0
    const start = performance.now()
    const from = displayRef.current
    const to = value
    const step = (ts: number) => {
      const p = Math.min((ts - start) / duration, 1)
      const eased = 1 - Math.pow(1 - p, 3)
      const next = from + (to - from) * eased
      displayRef.current = next
      setDisplay(next)
      if (p < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [value, duration, prefersReducedMotion])

  return <span>{decimals > 0 ? display.toFixed(decimals) : Math.round(display)}{suffix}</span>
}

function TierRingSVG({ percent, color, size = 120, stroke = 6, label }: { percent: number; color: string; size?: number; stroke?: number; label?: string }) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const offset = c - (Math.max(0, Math.min(100, percent)) / 100) * c
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

function FormulaCard({ comp, expanded, onToggle }: { comp: FormulaComponent; expanded: boolean; onToggle: () => void }) {
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
          {comp.displayValue}
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

  const daysRequested = timeRange === '7D' ? 7 : timeRange === '30D' ? 30 : timeRange === '90D' ? 90 : 180

  const scoreApi = useApi<TrustSummary>(async () => {
    if (!user?.id) throw new Error('No user loaded')
    return normalizeTrustSummary(await getTrustScore(user.id), user)
  }, false)
  const rainbowApi = useApi<RainbowCircleResponse>(() => get('/api/v1/profile/rainbow-circle'), false)
  const historyApi = useApi<TrustHistoryResponse>(() => {
    if (!user?.id) throw new Error('No user loaded')
    return getTrustHistory(user.id, daysRequested)
  }, false)
  const vouchesApi = useApi<VouchDisplay[]>(async () => {
    if (!user?.id) throw new Error('No user loaded')
    return vouchesFromApi(await getVouches(user.id))
  }, false)

  const { refetch: refetchScore } = scoreApi
  const { refetch: refetchRainbow } = rainbowApi
  const { refetch: refetchHistory } = historyApi
  const { refetch: refetchVouches } = vouchesApi

  useEffect(() => {
    if (user?.id) {
      refetchScore().catch(() => undefined)
      refetchRainbow().catch(() => undefined)
      refetchHistory().catch(() => undefined)
      refetchVouches().catch(() => undefined)
    }
  }, [refetchHistory, refetchRainbow, refetchScore, refetchVouches, user?.id, daysRequested])

  const trustScore = scoreApi.data || normalizeTrustSummary(null, user)
  const rainbow = rainbowApi.data
  const historyPoints = historyApi.data?.history ?? EMPTY_TRUST_HISTORY
  const chartData = useMemo(() => chartDataFrom(historyPoints), [historyPoints])
  const recentChanges = useMemo(() => recentChangesFrom(historyPoints), [historyPoints])
  const latestPoint = historyPoints.at(-1)
  const formulaComponents = useMemo(() => formulaComponentsFrom(latestPoint, trustScore), [latestPoint, trustScore])

  const currentScore = rainbow?.score ?? trustScore.score
  const tierName = rainbow?.current_tier_name || trustScore.tier
  const tierColor = rainbow?.current_tier_color || (tierName === 'The Watch' ? COLORS.watch : tierName === 'The Flex' ? COLORS.flex : COLORS.vetted)
  const minTierScore = rainbow?.min_score_in_tier ?? 0
  const maxTierScore = rainbow?.max_score_in_tier ?? currentScore
  const progressPercent = rainbow?.progress_percent ?? 100
  const nextTier = rainbow?.all_tiers.find((tier) => tier.threshold > currentScore) ?? null
  const vouches = vouchesApi.data ?? []
  const latestContribution = latestPoint?.total ?? 0

  return (
    <div className="min-h-screen w-full" style={{ background: COLORS.bgBase, color: COLORS.textPrimary }}>
      <div className="px-4 pt-6 sm:px-6">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-1 text-sm transition-colors hover:underline" style={{ color: COLORS.textMuted }}>
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
            Live score, formula components, and vouch history from the backend.
          </p>
        </div>
      </div>

      <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_380px]">
          <div className="flex flex-col gap-6">
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
                {['(', 'C', 'x', 'W', ')', '+', 'H', '+', 'R', '+', 'M', '-', 'P'].map((token, i) => (
                  <motion.span
                    key={`${token}-${i}`}
                    className={['C', 'W', 'H', 'R', 'M', 'P'].includes(token) ? 'cursor-pointer rounded px-1 py-0.5 transition-colors' : 'rounded px-1 py-0.5'}
                    style={{
                      color: ['C', 'W', 'H', 'R', 'M', 'P'].includes(token)
                        ? formulaComponents.find((c) => c.key === token)?.color || COLORS.textPrimary
                        : COLORS.textMuted,
                    }}
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ duration: 0.3, delay: 0.2 + i * 0.05 }}
                    onClick={() => {
                      if (['C', 'W', 'H', 'R', 'M', 'P'].includes(token)) {
                        setExpandedKey(expandedKey === token ? null : token)
                      }
                    }}
                  >
                    {token}
                  </motion.span>
                ))}
              </div>

              <div className="flex flex-col gap-2">
                {formulaComponents.map((comp) => (
                  <FormulaCard
                    key={comp.key}
                    comp={comp}
                    expanded={expandedKey === comp.key}
                    onToggle={() => setExpandedKey(expandedKey === comp.key ? null : comp.key)}
                  />
                ))}
              </div>

              <div className="mt-4 rounded-lg p-3 text-center text-sm" style={{ background: COLORS.bgOverlay, fontFamily: 'JetBrains Mono' }}>
                <span style={{ color: COLORS.brandBlue }}>{formulaComponents[0].displayValue}</span>
                {' x '}
                <span style={{ color: '#FF8C00' }}>{formulaComponents[1].displayValue}</span>
                {' + '}
                <span style={{ color: COLORS.flex }}>{formatNumber(formulaComponents[2].value)}</span>
                {' + '}
                <span style={{ color: COLORS.brandBlueGlow }}>{formatNumber(formulaComponents[3].value)}</span>
                {' + '}
                <span style={{ color: COLORS.textMuted }}>{formatNumber(formulaComponents[4].value)}</span>
                {' - '}
                <span style={{ color: COLORS.brandCrimson }}>{formatNumber(formulaComponents[5].value)}</span>
                {' = '}
                <span className="font-medium" style={{ color: COLORS.brandGold }}>
                  {latestPoint ? formatNumber(latestContribution) : 'no snapshot yet'}
                </span>
              </div>
            </motion.div>

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
                {historyApi.loading ? (
                  <div className="flex h-full items-center justify-center text-sm" style={{ color: COLORS.textMuted }}>
                    Loading trust history...
                  </div>
                ) : chartData.length === 0 ? (
                  <div className="flex h-full flex-col items-center justify-center gap-1 text-center">
                    <p className="text-sm font-medium" style={{ color: COLORS.textSecondary }}>
                      No trust snapshots yet
                    </p>
                    <p className="text-xs" style={{ color: COLORS.textMuted }}>
                      Run a FlowQuest or check in to create your first scored day.
                    </p>
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="trustDetailFill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={COLORS.brandGold} stopOpacity={0.15} />
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
                        formatter={(value: number) => [value, 'Snapshot']}
                      />
                      <Area type="monotone" dataKey="score" stroke={COLORS.brandGold} strokeWidth={3} fill="url(#trustDetailFill)" dot={{ r: 3, fill: COLORS.brandGold }} activeDot={{ r: 5, fill: COLORS.brandGold }} />
                      {chartData
                        .filter((d) => d.event_type)
                        .map((d) => (
                          <ReferenceLine
                            key={d.fullDate}
                            x={d.date}
                            stroke={
                              d.event_type === 'mask'
                                ? COLORS.brandCrimson
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
                )}
              </div>
              <div className="mt-3 flex flex-wrap gap-3">
                {[
                  { color: COLORS.brandCrimson, label: 'Penalty', icon: AlertTriangle },
                  { color: COLORS.brandBlue, label: 'Mentor vouch', icon: Shield },
                  { color: COLORS.flex, label: 'Regulation', icon: CheckCircle },
                ].map((item) => (
                  <div key={item.label} className="flex items-center gap-1 text-xs" style={{ color: COLORS.textMuted }}>
                    <item.icon size={12} style={{ color: item.color }} />
                    {item.label}
                  </div>
                ))}
              </div>
            </motion.div>

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
              {recentChanges.length === 0 ? (
                <p className="text-sm" style={{ color: COLORS.textMuted }}>
                  No recent scored changes yet.
                </p>
              ) : (
                <div className="flex flex-col gap-2">
                  {recentChanges.map((item, i) => (
                    <motion.div
                      key={`${item.date}-${i}`}
                      className="flex items-center justify-between rounded-lg p-2"
                      style={{ background: COLORS.bgOverlay }}
                      initial={{ x: 15, opacity: 0 }}
                      animate={{ x: 0, opacity: 1 }}
                      transition={{ duration: 0.4, delay: 0.35 + i * 0.08 }}
                    >
                      <div>
                        <p className="text-xs" style={{ color: COLORS.textMuted }}>
                          {new Date(item.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
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
                        {formatNumber(item.delta)}
                      </span>
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>
          </div>

          <div className="flex flex-col gap-6">
            <motion.div
              className="rounded-2xl border p-6"
              style={{ background: COLORS.bgElevated, borderColor: COLORS.borderSubtle }}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <div className="mb-4 flex flex-col items-center">
                <div className="mb-2 h-16 w-16 overflow-hidden rounded-xl flex items-center justify-center font-display text-base" style={{ background: `${tierColor}20`, color: tierColor }}>
                  <img
                    src={`/tier-${tierImageSlug(tierName)}.png`}
                    alt={tierName}
                    className="h-full w-full object-cover opacity-80"
                    onError={(e) => {
                      const img = e.currentTarget
                      img.style.display = 'none'
                      img.parentElement?.appendChild(document.createTextNode(tierName.replace(/^The\s+/, '').toUpperCase()))
                    }}
                  />
                </div>
                <h2 className="text-2xl font-normal tracking-wide" style={{ fontFamily: 'Bebas Neue, sans-serif', color: tierColor }}>
                  {tierName.toUpperCase()}
                </h2>
                <p className="text-xs" style={{ color: COLORS.textMuted }}>
                  {formatNumber(minTierScore, 0)} - {rainbow?.max_score_in_tier === null ? 'no cap' : formatNumber(maxTierScore, 0)}
                </p>
                <p className="mt-1 text-2xl font-medium" style={{ fontFamily: 'JetBrains Mono', color: COLORS.textPrimary }}>
                  {formatNumber(currentScore)}
                </p>
              </div>
              <TierRingSVG percent={progressPercent} color={tierColor} size={140} stroke={8} />

              <div className="mt-6 border-t pt-4" style={{ borderColor: COLORS.borderSubtle }}>
                {nextTier ? (
                  <>
                    <div className="flex items-center gap-3">
                      <div
                        className="h-12 w-12 overflow-hidden rounded-lg opacity-70 flex items-center justify-center font-display text-base"
                        style={{ background: `${nextTier.color}20`, color: nextTier.color }}
                      >
                        <img
                          src={`/tier-${tierImageSlug(nextTier.name)}.png`}
                          alt={nextTier.name}
                          className="h-full w-full object-cover"
                          onError={(e) => {
                            const img = e.currentTarget
                            img.style.display = 'none'
                            img.parentElement?.appendChild(document.createTextNode(nextTier.name.replace(/^The\s+/, '').toUpperCase()))
                          }}
                        />
                      </div>
                      <div>
                        <h3 className="text-lg font-normal tracking-wide" style={{ fontFamily: 'Bebas Neue, sans-serif', color: nextTier.color }}>
                          {nextTier.name.toUpperCase()}
                        </h3>
                        <p className="text-xs" style={{ color: COLORS.textMuted }}>
                          Unlocks at {formatNumber(nextTier.threshold, 0)}
                        </p>
                      </div>
                    </div>
                    <p className="mt-2 text-sm font-medium" style={{ color: COLORS.brandGold }}>
                      +{formatNumber(Math.max(0, nextTier.threshold - currentScore))} to unlock
                    </p>
                  </>
                ) : (
                  <p className="text-sm" style={{ color: COLORS.brandGold }}>
                    Top tier unlocked.
                  </p>
                )}
              </div>
            </motion.div>

            <motion.div
              className="rounded-2xl border p-5"
              style={{ background: COLORS.bgElevated, borderColor: COLORS.borderSubtle }}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              <h4 className="mb-3 text-base font-semibold" style={{ color: COLORS.textPrimary }}>
                REDEEMED VOUCHES
              </h4>
              <div className="mb-2 flex items-baseline gap-1">
                <span className="text-2xl font-medium" style={{ fontFamily: 'JetBrains Mono', color: COLORS.textPrimary }}>
                  {vouches.length}
                </span>
                <span className="text-xs" style={{ color: COLORS.textMuted }}>
                  active or historical
                </span>
              </div>
              {vouchesApi.loading ? (
                <p className="text-sm" style={{ color: COLORS.textMuted }}>
                  Loading vouches...
                </p>
              ) : vouches.length === 0 ? (
                <p className="text-sm" style={{ color: COLORS.textMuted }}>
                  None yet.
                </p>
              ) : (
                <div className="flex flex-col gap-2">
                  {vouches.map((vouch) => (
                    <div key={vouch.id} className="rounded-lg p-2" style={{ background: COLORS.bgOverlay }}>
                      <div className="flex items-center gap-2">
                        <Star size={14} style={{ color: COLORS.brandGold }} />
                        <span className="text-sm font-medium" style={{ color: COLORS.textPrimary }}>
                          {vouch.name}
                        </span>
                      </div>
                      <p className="text-xs" style={{ color: COLORS.textMuted }}>
                        {formatNumber(vouch.credits_spent, 0)} credits - {vouch.status}
                        {vouch.created_at ? ` - ${new Date(vouch.created_at).toLocaleDateString()}` : ''}
                      </p>
                    </div>
                  ))}
                </div>
              )}
              <p className="mt-3 text-xs" style={{ color: COLORS.textMuted }}>
                Vouches shown here come from the trust backend, not static demo rows.
              </p>
            </motion.div>
          </div>
        </div>
      </main>
    </div>
  )
}
