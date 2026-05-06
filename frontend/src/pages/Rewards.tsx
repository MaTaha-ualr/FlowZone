import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowLeft, Lock, CheckCircle, Loader2 } from 'lucide-react'
import { Link } from 'react-router-dom'

import { getRewards, redeemReward, useApi } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import type { RewardsResponse, RewardItemResponse, RedeemedVouch } from '@/types'

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
  brandCrimson: '#DC2626',
  textPrimary: '#F8F8FA',
  textSecondary: '#A1A1AA',
  textMuted: '#71717A',
  watch: '#6366F1',
  flex: '#10B981',
  vetted: '#D4AF37',
}

/* ─── Mock data ─── */
const MOCK_REWARDS: RewardsResponse = {
  current_score: 142,
  available_vouches: [
    { key: 'late_checkin', name: 'Late Check-In', icon: '🌙', cost: 50, can_afford: true, locked: false },
    { key: 'curfew_extension', name: 'Curfew Extension', icon: '🚪', cost: 150, can_afford: false, locked: false },
    { key: 'reduced_meeting', name: 'Reduced Meeting', icon: '📅', cost: 200, can_afford: false, locked: true },
    { key: 'solo_pass', name: 'Solo Pass', icon: '🚶', cost: 300, can_afford: false, locked: true },
    { key: 'trust_premium', name: 'Trust Premium', icon: '⭐', cost: 500, can_afford: false, locked: true },
    { key: 'character_switch', name: 'Character Switch', icon: '🔄', cost: 75, can_afford: true, locked: false },
  ],
  redeemed_vouches: [
    { key: 'late_checkin', name: 'Late Check-In', icon: '🌙', redeemed_at: '2024-02-28T10:00:00Z', status: 'used' },
    { key: 'character_switch', name: 'Character Switch (Ace)', icon: '🔄', redeemed_at: '2024-02-25T10:00:00Z', status: 'used' },
  ] as RedeemedVouch[],
  can_redeem: true,
  next_unlock_tier: 'The Flex',
  next_unlock_score: 200,
}

type RedeemedVouchApi = Partial<RedeemedVouch> & {
  type?: string
  created_at?: string
}

/* ─── Confetti particle ─── */
function Confetti() {
  const particles = Array.from({ length: 30 }, (_, i) => ({
    id: i,
    x: Math.random() * 100,
    y: Math.random() * 100,
    color: [COLORS.brandGold, COLORS.flex, COLORS.watch, COLORS.brandBlue, COLORS.vetted][Math.floor(Math.random() * 5)],
    size: Math.random() * 6 + 4,
    duration: Math.random() * 1 + 0.5,
    delay: Math.random() * 0.3,
  }))

  return (
    <div className="pointer-events-none fixed inset-0 z-[60] overflow-hidden">
      {particles.map((p) => (
        <motion.div
          key={p.id}
          className="absolute rounded-sm"
          style={{
            left: `${p.x}%`,
            top: '-10px',
            width: p.size,
            height: p.size,
            background: p.color,
          }}
          initial={{ y: 0, opacity: 1, rotate: 0 }}
          animate={{
            y: '110vh',
            opacity: 0,
            rotate: Math.random() * 720 - 360,
          }}
          transition={{ duration: p.duration, delay: p.delay, ease: 'easeOut' }}
        />
      ))}
    </div>
  )
}

export default function Rewards() {
  const { user } = useAuth()
  const [confirmVouch, setConfirmVouch] = useState<RewardItemResponse | null>(null)
  const [redeeming, setRedeeming] = useState(false)
  const [success, setSuccess] = useState(false)
  const [redeemedList, setRedeemedList] = useState<RedeemedVouch[]>(MOCK_REWARDS.redeemed_vouches)
  const [currentScore, setCurrentScore] = useState(MOCK_REWARDS.current_score)

  const rewardsApi = useApi<RewardsResponse>(() => getRewards() as Promise<RewardsResponse>, true)
  const rewards = rewardsApi.data || MOCK_REWARDS

  useEffect(() => {
    if (rewardsApi.data?.redeemed_vouches) {
      setRedeemedList(
        rewardsApi.data.redeemed_vouches.map((item: RedeemedVouchApi) => ({
          key: item.key || item.type || 'vouch',
          name: item.name || item.type || 'Vouch',
          icon: item.icon || '⭐',
          redeemed_at: item.redeemed_at || item.created_at || new Date().toISOString(),
          status: item.status === 'used' ? 'used' : 'active',
        })),
      )
    }
  }, [rewardsApi.data])

  const score = rewards.current_score || currentScore
  const nextScore = rewards.next_unlock_score || 200
  const progressPercent = Math.min((score / 500) * 100, 100)

  const handleRedeem = async () => {
    if (!confirmVouch) return
    setRedeeming(true)
    try {
      if (user?.id) {
        await redeemReward(user.id, confirmVouch.key)
        rewardsApi.refetch().catch(() => undefined)
      }
    } catch {
      // Demo fallback
    }
    setTimeout(() => {
      setRedeeming(false)
      setSuccess(true)
      setCurrentScore((s) => s - confirmVouch.cost)
      setRedeemedList((prev) => [
        {
          key: confirmVouch.key,
          name: confirmVouch.name,
          icon: confirmVouch.icon,
          redeemed_at: new Date().toISOString(),
          status: 'active',
        },
        ...prev,
      ])
      setTimeout(() => {
        setSuccess(false)
        setConfirmVouch(null)
      }, 1500)
    }, 800)
  }

  return (
    <div className="min-h-screen w-full" style={{ background: COLORS.bgBase, color: COLORS.textPrimary }}>
      {/* Ambient gold gradient */}
      <div
        className="pointer-events-none fixed inset-0"
        style={{ background: `radial-gradient(circle at 50% 100%, ${COLORS.brandGold}08, transparent 60%)` }}
      />

      {/* Success confetti */}
      <AnimatePresence>{success && <Confetti />}</AnimatePresence>

      {/* ─── Header ─── */}
      <div className="relative z-10 px-4 pt-6 sm:px-6">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <Link to="/" className="flex items-center gap-1 text-sm transition-colors hover:underline" style={{ color: COLORS.textMuted }}>
            <ArrowLeft size={16} />
            Dashboard
          </Link>
          <motion.div
            className="flex items-center gap-2 rounded-full px-4 py-2"
            style={{ background: COLORS.bgElevated, border: `1px solid ${COLORS.brandGold}40` }}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5, ease: [0.34, 1.56, 0.64, 1] }}
          >
            <span className="text-lg font-medium" style={{ fontFamily: 'JetBrains Mono', color: COLORS.brandGold }}>
              {score}
            </span>
            <span className="text-[10px] uppercase tracking-wider" style={{ color: COLORS.textMuted }}>
              Trust
            </span>
          </motion.div>
        </div>
        <div className="mx-auto mt-4 max-w-5xl">
          <motion.h1
            className="text-4xl font-normal tracking-wide sm:text-5xl"
            style={{ fontFamily: 'Bebas Neue, sans-serif' }}
            initial={{ y: 30, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          >
            VOUCH STORE
          </motion.h1>
          <p className="text-sm" style={{ color: COLORS.textSecondary }}>
            Trust earned. Freedom bought.
          </p>
        </div>
      </div>

      <main className="relative z-10 mx-auto max-w-5xl px-4 py-6 sm:px-6">
        {/* ─── Tier Unlock Progress ─── */}
        <motion.div
          className="mb-6 rounded-2xl border p-5"
          style={{ background: COLORS.bgElevated, borderColor: COLORS.borderSubtle }}
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <div className="flex items-center justify-between">
            {[
              { name: 'The Watch', color: COLORS.watch, status: 'UNLOCKED', range: '0-199', active: true },
              { name: 'The Flex', color: COLORS.flex, status: score >= 200 ? 'UNLOCKED' : `+${Math.max(0, 200 - score)} TO UNLOCK`, range: '200-499', active: score >= 200 },
              { name: 'The Vetted', color: COLORS.vetted, status: score >= 500 ? 'UNLOCKED' : `+${Math.max(0, 500 - score)} TO UNLOCK`, range: '500+', active: score >= 500 },
            ].map((tier, i) => (
              <motion.div
                key={tier.name}
                className="flex flex-col items-center gap-1"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.4, delay: 0.2 + i * 0.15 }}
              >
                <div
                  className="h-10 w-10 overflow-hidden rounded-lg"
                  style={{ background: `${tier.color}20`, opacity: tier.active ? 1 : 0.4 }}
                >
                  <img src={`/tier-${tier.name.toLowerCase().replace('the ', '')}.png`} alt={tier.name} className="h-full w-full object-cover" />
                </div>
                <span className="text-xs font-medium" style={{ color: tier.active ? tier.color : COLORS.textMuted }}>
                  {tier.name}
                </span>
                <span className="text-[10px]" style={{ color: COLORS.textMuted }}>
                  {tier.status}
                </span>
              </motion.div>
            ))}
          </div>
          <div className="relative mt-4 h-2 w-full overflow-hidden rounded-full" style={{ background: COLORS.borderSubtle }}>
            <motion.div
              className="absolute inset-y-0 left-0 rounded-full"
              style={{ background: `linear-gradient(90deg, ${COLORS.watch}, ${COLORS.flex})` }}
              initial={{ width: 0 }}
              animate={{ width: `${progressPercent}%` }}
              transition={{ duration: 1, ease: 'easeOut' }}
            />
            <div
              className="absolute top-1/2 h-4 w-4 -translate-y-1/2 rounded-full border-2"
              style={{
                left: `${progressPercent}%`,
                background: COLORS.bgElevated,
                borderColor: COLORS.brandGold,
                transform: `translate(-50%, -50%)`,
              }}
            />
          </div>
        </motion.div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_340px]">
          {/* ─── Main Column ─── */}
          <div className="flex flex-col gap-6">
            {/* Available Vouches */}
            <motion.div
              className="rounded-2xl border p-6"
              style={{ background: COLORS.bgElevated, borderColor: COLORS.borderSubtle }}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-xl font-semibold tracking-wide" style={{ fontFamily: 'Bebas Neue, sans-serif' }}>
                  AVAILABLE
                </h3>
                <span className="text-xs" style={{ color: COLORS.textMuted }}>
                  Spend your trust.
                </span>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {rewards.available_vouches.map((vouch, i) => {
                  const canAfford = vouch.can_afford && !vouch.locked
                  const locked = vouch.locked
                  const needMore = !vouch.can_afford && !vouch.locked
                  return (
                    <motion.div
                      key={vouch.key}
                      className="group relative flex flex-col items-center rounded-xl border p-4 text-center transition-all"
                      style={{
                        background: locked ? `${COLORS.bgOverlay}80` : COLORS.bgOverlay,
                        borderColor: canAfford ? `${COLORS.brandGold}40` : COLORS.borderSubtle,
                        opacity: locked ? 0.6 : 1,
                      }}
                      initial={{ y: 25, opacity: 0, scale: 0.95 }}
                      animate={{ y: 0, opacity: locked ? 0.6 : 1, scale: 1 }}
                      transition={{ duration: 0.4, delay: 0.25 + i * 0.1 }}
                      whileHover={!locked ? { y: -4, borderColor: COLORS.brandGold } : undefined}
                    >
                      {locked && (
                        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center rounded-xl" style={{ background: `${COLORS.bgBase}60` }}>
                          <Lock size={20} style={{ color: COLORS.textMuted }} />
                          <span className="mt-1 text-[10px] font-medium" style={{ color: COLORS.textMuted }}>
                            Unlock at The Flex
                          </span>
                        </div>
                      )}
                      <span className="text-3xl transition-transform group-hover:scale-110">{vouch.icon}</span>
                      <h4 className="mt-2 text-sm font-semibold" style={{ color: COLORS.textPrimary }}>
                        {vouch.name}
                      </h4>
                      <p className="mt-1 text-xs" style={{ color: COLORS.textSecondary }}>
                        {vouch.key === 'late_checkin' && 'Skip one daily check-in. No penalty.'}
                        {vouch.key === 'curfew_extension' && 'Stay out 2 hours later. One weekend night.'}
                        {vouch.key === 'reduced_meeting' && 'Skip one PO/case worker meeting.'}
                        {vouch.key === 'solo_pass' && 'Walk alone. No escort. One week.'}
                        {vouch.key === 'trust_premium' && 'Full autonomy review. All restrictions considered.'}
                        {vouch.key === 'character_switch' && 'Pick your character for one session.'}
                      </p>
                      <div className="mt-3 flex w-full items-center justify-between">
                        <span className="text-xs font-medium" style={{ fontFamily: 'JetBrains Mono', color: COLORS.brandGold }}>
                          {vouch.cost} TRUST
                        </span>
                        {canAfford && (
                          <button
                            className="rounded-lg px-3 py-1 text-xs font-bold uppercase transition-all active:scale-95"
                            style={{ background: COLORS.brandGold, color: COLORS.bgBase }}
                            onClick={() => setConfirmVouch(vouch)}
                          >
                            REDEEM
                          </button>
                        )}
                        {needMore && (
                          <span className="text-xs font-medium" style={{ color: COLORS.brandCrimson }}>
                            NEED {vouch.cost - score} MORE
                          </span>
                        )}
                        {locked && (
                          <span className="text-xs font-medium line-through" style={{ color: COLORS.textMuted }}>
                            {vouch.cost} TRUST
                          </span>
                        )}
                      </div>
                    </motion.div>
                  )
                })}
              </div>
            </motion.div>

            {/* Redeemed Vouches */}
            <motion.div
              className="rounded-2xl border p-5"
              style={{ background: COLORS.bgElevated, borderColor: COLORS.borderSubtle }}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              <h4 className="mb-3 text-base font-semibold" style={{ color: COLORS.textPrimary }}>
                REDEEMED
              </h4>
              <div className="flex flex-col gap-2">
                {redeemedList.map((item, i) => (
                  <motion.div
                    key={`${item.key}-${i}`}
                    className="flex items-center gap-3 rounded-lg p-2"
                    style={{ background: COLORS.bgOverlay }}
                    initial={{ y: 15, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ duration: 0.4, delay: 0.35 + i * 0.06 }}
                  >
                    <span className="text-lg">{item.icon}</span>
                    <div className="flex-1">
                      <p className="text-sm" style={{ color: COLORS.textPrimary }}>
                        {item.name}
                      </p>
                      <p className="text-xs" style={{ color: COLORS.textMuted }}>
                        Redeemed {new Date(item.redeemed_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                      </p>
                    </div>
                    <span
                      className="rounded px-1.5 py-0.5 text-[10px] font-medium uppercase"
                      style={{
                        background: item.status === 'active' ? `${COLORS.brandGold}15` : COLORS.bgElevated,
                        color: item.status === 'active' ? COLORS.brandGold : COLORS.textMuted,
                      }}
                    >
                      {item.status}
                    </span>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </div>

          {/* ─── Sidebar ─── */}
          <div className="flex flex-col gap-6">
            {/* How It Works */}
            <motion.div
              className="rounded-2xl border p-5"
              style={{ background: COLORS.bgElevated, borderColor: COLORS.borderSubtle }}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <h4 className="mb-3 text-base font-semibold" style={{ color: COLORS.textPrimary }}>
                HOW IT WORKS
              </h4>
              <div className="flex flex-col gap-2">
                {[
                  'Earn trust through FlowQuests and check-ins.',
                  'Cash in trust for vouches.',
                  'Spend vouches for real freedom.',
                  'Higher tiers unlock bigger moves.',
                ].map((step, i) => (
                  <p key={i} className="text-sm" style={{ color: COLORS.textSecondary }}>
                    {i + 1}. {step}
                  </p>
                ))}
              </div>
              <p className="mt-3 text-xs font-medium" style={{ color: COLORS.brandGold }}>
                Vouches are reviewed by your mentor before activation.
              </p>
            </motion.div>

            {/* Mentor Preview */}
            <motion.div
              className="rounded-2xl border p-5"
              style={{ background: COLORS.bgElevated, borderColor: COLORS.borderSubtle }}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              <div className="flex items-center gap-3">
                <div
                  className="h-12 w-12 overflow-hidden rounded-full flex items-center justify-center font-display text-lg"
                  style={{ background: COLORS.bgOverlay, color: COLORS.brandGold }}
                >
                  <img
                    src="/mentor-ray.jpg"
                    alt="Coach Ray"
                    className="h-full w-full object-cover"
                    onError={(e) => {
                      const img = e.currentTarget
                      img.style.display = 'none'
                      const parent = img.parentElement
                      if (parent && !parent.dataset.fallback) {
                        parent.dataset.fallback = '1'
                        parent.appendChild(document.createTextNode('CR'))
                      }
                    }}
                  />
                </div>
                <div>
                  <h4 className="text-sm font-semibold" style={{ color: COLORS.textPrimary }}>
                    Coach Ray Patterson
                  </h4>
                  <p className="text-xs" style={{ color: COLORS.textMuted }}>
                    Your Mentor
                  </p>
                </div>
              </div>
              <p className="mt-3 text-sm italic" style={{ color: COLORS.textSecondary }}>
                "Marcus, you're {nextScore - score} from The Flex. Keep showing up. The curfew extension is real."
              </p>
              <button className="mt-2 text-xs transition-colors hover:underline" style={{ color: COLORS.brandBlue }}>
                View mentor profile
              </button>
            </motion.div>
          </div>
        </div>
      </main>

      {/* ─── Redeem Modal ─── */}
      <AnimatePresence>
        {confirmVouch && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center px-4"
            style={{ background: `${COLORS.bgBase}cc` }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="w-full max-w-sm rounded-2xl border p-6 text-center"
              style={{ background: COLORS.bgOverlay, borderColor: COLORS.borderSubtle }}
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              {!success ? (
                <>
                  <span className="text-5xl">{confirmVouch.icon}</span>
                  <h3 className="mt-3 text-lg font-semibold" style={{ color: COLORS.textPrimary }}>
                    {confirmVouch.name}
                  </h3>
                  <p className="mt-1 text-sm" style={{ color: COLORS.textSecondary }}>
                    {confirmVouch.key === 'late_checkin' && 'Skip one daily check-in. No penalty.'}
                    {confirmVouch.key === 'character_switch' && 'Pick your character for one session.'}
                  </p>
                  <p className="mt-3 text-base font-medium" style={{ color: COLORS.brandGold }}>
                    Spend {confirmVouch.cost} TRUST?
                  </p>
                  <p className="text-xs" style={{ color: COLORS.textMuted }}>
                    You'll have {score - confirmVouch.cost} left.
                  </p>
                  <div className="mt-4 flex gap-2">
                    <button
                      className="flex-1 rounded-lg py-2 text-sm font-bold uppercase transition-all active:scale-95"
                      style={{ background: COLORS.brandGold, color: COLORS.bgBase }}
                      onClick={handleRedeem}
                      disabled={redeeming}
                    >
                      {redeeming ? (
                        <span className="flex items-center justify-center gap-1">
                          <Loader2 size={14} className="animate-spin" />
                          Processing...
                        </span>
                      ) : (
                        'CONFIRM'
                      )}
                    </button>
                    <button
                      className="flex-1 rounded-lg py-2 text-sm font-medium transition-colors"
                      style={{ color: COLORS.textMuted }}
                      onClick={() => setConfirmVouch(null)}
                      disabled={redeeming}
                    >
                      NAH
                    </button>
                  </div>
                </>
              ) : (
                <motion.div
                  initial={{ scale: 0.5, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }}
                >
                  <CheckCircle size={48} style={{ color: COLORS.flex }} className="mx-auto" />
                  <p className="mt-3 text-base font-medium" style={{ color: COLORS.textPrimary }}>
                    Redeemed.
                  </p>
                  <p className="text-sm" style={{ color: COLORS.textSecondary }}>
                    Your mentor will activate it.
                  </p>
                </motion.div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
