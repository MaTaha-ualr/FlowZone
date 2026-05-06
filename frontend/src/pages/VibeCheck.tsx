import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowLeft, Loader2 } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'

import { createSession, vibeCheck } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import type { VibeEnum, VibeCheckResponse, SessionResponse, SafeHarborEnum } from '@/types'

/* ─── Design tokens ─── */
const COLORS = {
  bgBase: '#050507',
  bgElevated: '#0F0F14',
  bgOverlay: '#18181F',
  borderSubtle: '#2A2A35',
  borderActive: '#3E3E4F',
  brandGold: '#D4AF37',
  brandGoldBright: '#FFD700',
  textPrimary: '#F8F8FA',
  textSecondary: '#A1A1AA',
  textMuted: '#71717A',
  vibeSolid: '#00B4D8',
  vibeAngry: '#FF6B35',
  vibeGuarded: '#64748B',
  vibeStorm: '#7C3AED',
  safeGreen: '#10B981',
  safeYellow: '#F59E0B',
  safeRed: '#DC2626',
  brandCrimson: '#DC2626',
  brandBlue: '#00A8E8',
}

const VIBES: {
  key: VibeEnum
  emoji: string
  label: string
  desc: string
  color: string
  character: string
}[] = [
  { key: 'solid', emoji: '💎', label: 'SOLID', desc: 'Feeling good. Stable. Clear.', color: COLORS.vibeSolid, character: 'Yogi' },
  { key: 'angry', emoji: '🔥', label: 'ANGRY', desc: 'Pressure. Frustration. Heat.', color: COLORS.vibeAngry, character: 'Vex' },
  { key: 'guarded', emoji: '🔏', label: 'GUARDED', desc: 'Closed off. Resistant. Walls up.', color: COLORS.vibeGuarded, character: 'Vex' },
  { key: 'storm', emoji: '⛈️', label: 'STORM', desc: 'Overwhelmed. Crisis. Can\'t breathe.', color: COLORS.vibeStorm, character: 'Yogi' },
]

function characterColorFromVibe(vibe: VibeEnum) {
  if (vibe === 'angry' || vibe === 'guarded') return COLORS.brandCrimson
  return COLORS.brandBlue
}

function safeHarborFromVibe(vibe: VibeEnum): SafeHarborEnum {
  if (vibe === 'storm') return 'red'
  if (vibe === 'angry' || vibe === 'guarded') return 'yellow'
  return 'green'
}

function safeHarborColor(level: string) {
  if (level === 'green') return COLORS.safeGreen
  if (level === 'yellow') return COLORS.safeYellow
  return COLORS.safeRed
}

export default function VibeCheck() {
  const [selected, setSelected] = useState<VibeEnum | null>(null)
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<VibeCheckResponse | null>(null)
  const navigate = useNavigate()
  const { user } = useAuth()

  const selectedVibe = useMemo(() => VIBES.find((v) => v.key === selected), [selected])
  const bgTint = selectedVibe ? `${selectedVibe.color}0D` : 'transparent'

  const handleContinue = async () => {
    if (!selected || !user?.id) return
    setLoading(true)
    try {
      const session = await createSession(user.id) as SessionResponse
      const vibeRes = await vibeCheck(session.id, selected, notes || null) as VibeCheckResponse
      setResult(vibeRes)
    } catch {
      // Fallback demo mode
      setResult({
        session_id: 'demo-session-id',
        vibe: selected,
        vibe_emoji: selectedVibe?.emoji || '💎',
        character_assigned: selected === 'solid' || selected === 'storm' ? 'navigator' : 'challenger',
        character_name: selected === 'solid' || selected === 'storm' ? 'Yogi' : 'Vex',
        message: `You're feeling ${selected}. ${selected === 'solid' || selected === 'storm' ? 'Yogi' : 'Vex'} is here to help you navigate.`,
        safe_harbor_level: safeHarborFromVibe(selected),
      })
    } finally {
      setLoading(false)
    }
  }

  const handleStart = () => {
    if (result?.session_id) {
      navigate(`/flowquest/${result.session_id}`)
    }
  }

  const today = new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })

  return (
    <div
      className="relative flex min-h-screen flex-col"
      style={{ background: `${COLORS.bgBase}`, transition: 'background 0.4s ease' }}
    >
      {/* Ambient tint overlay */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{ background: `radial-gradient(circle at 50% 50%, ${bgTint}, transparent 70%)`, transition: 'background 0.6s ease' }}
      />

      {/* ─── Header ─── */}
      <div className="relative z-10 px-4 pt-6 sm:px-6">
        <div className="mx-auto flex max-w-2xl items-center">
          <Link
            to="/"
            className="mr-4 flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
            style={{ color: COLORS.textMuted }}
          >
            <ArrowLeft size={20} />
          </Link>
          <div className="flex-1 text-center">
            <motion.h1
              className="text-4xl font-normal tracking-wide sm:text-5xl"
              style={{ fontFamily: 'Bebas Neue, sans-serif', color: COLORS.textPrimary }}
              initial={{ y: 30, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            >
              VIBE CHECK
            </motion.h1>
            <motion.p
              className="mt-1 text-base"
              style={{ color: COLORS.textSecondary }}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
            >
              How you feeling right now? No filter.
            </motion.p>
            <p className="mt-1 text-xs" style={{ color: COLORS.textMuted }}>
              {today}
            </p>
          </div>
          <div className="w-9" />
        </div>
      </div>

      {/* ─── Vibe Grid ─── */}
      <div className="relative z-10 mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 py-8 sm:px-6">
        <div className="grid grid-cols-2 gap-4 sm:gap-6">
          {VIBES.map((vibe, i) => {
            const isSelected = selected === vibe.key
            const dimmed = selected && !isSelected
            return (
              <motion.button
                key={vibe.key}
                className="group relative flex flex-col items-center justify-center gap-2 rounded-2xl border-2 p-4 text-center transition-all sm:min-h-[180px] sm:p-6"
                style={{
                  background: isSelected ? `${vibe.color}12` : COLORS.bgElevated,
                  borderColor: isSelected ? vibe.color : dimmed ? `${COLORS.borderSubtle}60` : COLORS.borderSubtle,
                  opacity: dimmed ? 0.4 : 1,
                  boxShadow: isSelected ? `0 0 24px ${vibe.color}30` : 'none',
                }}
                initial={{ y: 30, opacity: 0, scale: 0.95 }}
                animate={{ y: 0, opacity: dimmed ? 0.4 : 1, scale: isSelected ? 1.05 : 1 }}
                transition={{ duration: 0.5, delay: 0.3 + i * 0.12, ease: [0.16, 1, 0.3, 1] }}
                onClick={() => setSelected(vibe.key)}
                onMouseEnter={(e: React.MouseEvent<HTMLButtonElement>) => {
                  if (!selected) {
                    e.currentTarget.style.borderColor = vibe.color
                    e.currentTarget.style.boxShadow = `0 0 20px ${vibe.color}20`
                    e.currentTarget.style.transform = 'translateY(-8px)'
                  }
                }}
                onMouseLeave={(e: React.MouseEvent<HTMLButtonElement>) => {
                  if (!isSelected) {
                    e.currentTarget.style.borderColor = COLORS.borderSubtle
                    e.currentTarget.style.boxShadow = 'none'
                    e.currentTarget.style.transform = 'translateY(0)'
                  }
                }}
              >
                <span className="text-4xl sm:text-5xl">{vibe.emoji}</span>
                <h2
                  className="text-xl font-normal tracking-wide sm:text-2xl"
                  style={{ fontFamily: 'Bebas Neue, sans-serif', color: isSelected ? vibe.color : COLORS.textPrimary }}
                >
                  {vibe.label}
                </h2>
                <p className="text-xs sm:text-sm" style={{ color: COLORS.textSecondary }}>
                  {vibe.desc}
                </p>
                <p className="text-[10px] font-medium" style={{ color: vibe.color }}>
                  → {vibe.character}
                </p>
              </motion.button>
            )
          })}
        </div>

        {/* ─── Notes Field ─── */}
        <AnimatePresence>
          {selected && (
            <motion.div
              className="mt-4 flex flex-col gap-2"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            >
              <label className="text-xs" style={{ color: COLORS.textSecondary }}>
                Say more (optional)
              </label>
              <textarea
                className="min-h-[80px] resize-none rounded-xl border p-3 text-sm outline-none transition-colors focus:border-blue-500"
                style={{
                  background: COLORS.bgOverlay,
                  borderColor: COLORS.borderSubtle,
                  color: COLORS.textPrimary,
                }}
                placeholder="Got in a fight at school. Trey kept pushing."
                value={notes}
                onChange={(e) => setNotes(e.target.value.slice(0, 140))}
              />
              <p className="text-right text-xs" style={{ color: COLORS.textMuted }}>
                {notes.length}/140
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ─── Continue Button ─── */}
        <AnimatePresence>
          {selected && (
            <motion.div
              className="mt-4"
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 20, opacity: 0 }}
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            >
              <button
                className="w-full rounded-full py-3 text-sm font-bold uppercase tracking-wider transition-all active:scale-[0.97] disabled:opacity-40"
                style={{
                  background: COLORS.brandGold,
                  color: COLORS.bgBase,
                  boxShadow: `0 0 20px ${COLORS.brandGold}30`,
                }}
                onClick={handleContinue}
                disabled={loading}
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 size={16} className="animate-spin" />
                    Assigning character...
                  </span>
                ) : (
                  'Continue to FlowQuest'
                )}
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ─── Loading / Character Reveal Overlay ─── */}
      <AnimatePresence>
        {(loading || result) && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center"
            style={{ background: `${COLORS.bgBase}ee`, backdropFilter: 'blur(8px)' }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {loading && !result && (
              <div className="flex flex-col items-center gap-3">
                <Loader2 size={32} className="animate-spin" style={{ color: COLORS.brandGold }} />
                <p className="text-sm" style={{ color: COLORS.textSecondary }}>
                  Reading your vibe...
                </p>
              </div>
            )}

            {result && (
              <motion.div
                className="flex max-w-sm flex-col items-center gap-4 px-6 text-center"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
              >
                <motion.div
                  className="h-24 w-24 overflow-hidden rounded-2xl"
                  style={{
                    background: `${characterColorFromVibe(result.vibe)}20`,
                    border: `2px solid ${characterColorFromVibe(result.vibe)}`,
                  }}
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ duration: 0.4, delay: 0.3, ease: [0.34, 1.56, 0.64, 1] }}
                >
                  <img
                    src={`/character-${result.character_assigned === 'challenger' ? 'vex' : result.character_assigned === 'navigator' ? 'yogi' : result.character_assigned === 'straight_shooter' ? 'ace' : 'nova'}.png`}
                    alt={result.character_name}
                    className="h-full w-full object-cover"
                  />
                </motion.div>

                <motion.h2
                  className="text-3xl font-normal tracking-wide"
                  style={{ fontFamily: 'Bebas Neue, sans-serif', color: characterColorFromVibe(result.vibe) }}
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.4, delay: 0.4 }}
                >
                  {result.character_name.toUpperCase()} IS HERE
                </motion.h2>

                <motion.p
                  className="text-sm"
                  style={{ color: COLORS.textSecondary }}
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.4, delay: 0.5 }}
                >
                  {result.message}
                </motion.p>

                <motion.div
                  className="flex items-center gap-2 rounded-full px-3 py-1"
                  style={{ background: `${safeHarborColor(result.safe_harbor_level)}15` }}
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.4, delay: 0.6 }}
                >
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: safeHarborColor(result.safe_harbor_level) }} />
                  <span className="text-xs font-medium" style={{ color: safeHarborColor(result.safe_harbor_level) }}>
                    Safe Harbor: {result.safe_harbor_level.charAt(0).toUpperCase() + result.safe_harbor_level.slice(1)}
                  </span>
                </motion.div>

                <motion.div
                  className="mt-2 flex w-full flex-col gap-2"
                  initial={{ y: 30, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.5, delay: 0.7, ease: [0.34, 1.56, 0.64, 1] }}
                >
                  <button
                    className="w-full rounded-full py-3 text-sm font-bold uppercase tracking-wider transition-all active:scale-[0.97]"
                    style={{
                      background: COLORS.brandGold,
                      color: COLORS.bgBase,
                      boxShadow: `0 0 20px ${COLORS.brandGold}40`,
                      animation: 'pulse 2s infinite',
                    }}
                    onClick={handleStart}
                  >
                    START FLOWQUEST
                  </button>
                  <button
                    className="w-full rounded-full py-2 text-xs font-medium transition-colors"
                    style={{ color: COLORS.textMuted }}
                    onClick={() => {
                      setResult(null)
                      setSelected(null)
                      setNotes('')
                    }}
                  >
                    Change vibe
                  </button>
                </motion.div>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
