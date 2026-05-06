import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowRight, ChevronRight, Zap, Target } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { submitIntake } from '@/lib/api'
import type { IntakeAnswers, CharacterEnum } from '@/types'
import { CHARACTER_INFO } from '@/types'

const QUESTIONS = [
  {
    id: 'intent',
    title: 'Intent Check',
    subtitle: 'Why are you here?',
    options: [
      { value: 'win_freedom', label: 'Win Freedom', desc: 'I want to build trust and earn real autonomy.' },
      { value: 'check_box', label: 'Check the Box', desc: "I'm only here because someone made me." },
    ],
  },
  {
    id: 'pressure',
    title: 'Pressure Gauge',
    subtitle: 'How heavy is the system on you right now?',
    type: 'slider',
    min: 1,
    max: 10,
    labels: ['Light', 'Crushing'],
  },
  {
    id: 'trap',
    title: 'Trap ID',
    subtitle: 'What usually pulls you off track?',
    options: [
      { value: 'friends', label: 'Friends', desc: 'Peer pressure, loyalty calls, old circles.' },
      { value: 'temper', label: 'Temper', desc: 'I react fast. Sometimes too fast.' },
      { value: 'home', label: 'Home', desc: 'Family stress, instability, no quiet space.' },
      { value: 'boredom', label: 'Boredom', desc: 'Idle time becomes risky time.' },
      { value: 'unknown', label: "Don't Know", desc: "I haven't figured out my pattern yet." },
    ],
  },
  {
    id: 'autonomy',
    title: 'Autonomy Prize',
    subtitle: 'What freedom matters most to you?',
    options: [
      { value: 'curfew', label: 'Curfew Flex', desc: 'Stay out later on trust, not rules.' },
      { value: 'testing', label: 'Less Testing', desc: 'Fewer drug tests when trust is high.' },
      { value: 'meetings', label: 'Fewer Meetings', desc: 'Cut check-ins when consistent.' },
      { value: 'walk', label: 'Walk Alone', desc: 'Freedom to move without supervision.' },
    ],
  },
  {
    id: 'collaboration',
    title: 'Collaboration',
    subtitle: 'Will you work with your mentor?',
    options: [
      { value: 'yes', label: "Yes — Let's Go", desc: 'I want someone in my corner.' },
      { value: 'we_will_see', label: "We'll See", desc: 'Trust is earned. Show me first.' },
    ],
  },
]

function assignCharacter(answers: IntakeAnswers): { character: CharacterEnum; characterName: string } {
  if (answers.intent === 'win_freedom' && answers.pressure_level >= 7) {
    return { character: 'challenger', characterName: 'The Challenger' }
  }
  if (answers.intent === 'win_freedom' && answers.trap === 'friends') {
    return { character: 'navigator', characterName: 'The Navigator' }
  }
  if (answers.intent === 'check_box') {
    return { character: 'straight_shooter', characterName: 'The Straight Shooter' }
  }
  if (answers.trap === 'boredom' || answers.trap === 'unknown') {
    return { character: 'strategist', characterName: 'The Strategist' }
  }
  return { character: 'navigator', characterName: 'The Navigator' }
}

function computeScore(answers: IntakeAnswers): number {
  let score = 50
  if (answers.intent === 'win_freedom') score += 20
  score += answers.pressure_level * 2
  if (answers.collaboration === 'yes') score += 15
  return Math.min(score, 99)
}

function normalizeAnswers(answers: Partial<IntakeAnswers> & Record<string, unknown>): IntakeAnswers {
  return {
    intent: (answers.intent as IntakeAnswers['intent']) || 'win_freedom',
    pressure_level: Number(answers.pressure ?? answers.pressure_level ?? 5),
    trap: (answers.trap as IntakeAnswers['trap']) || 'unknown',
    autonomy_prize: (answers.autonomy as IntakeAnswers['autonomy_prize']) || answers.autonomy_prize || 'curfew',
    collaboration: (answers.collaboration as IntakeAnswers['collaboration']) || 'we_will_see',
  } as IntakeAnswers
}

function apiAnswers(answers: IntakeAnswers) {
  const autonomyMap: Record<string, string> = {
    curfew: 'curfew',
    testing: 'less_testing',
    meetings: 'fewer_meetings',
    walk: 'trust_to_walk',
  }
  return {
    q1_intent: answers.intent,
    q2_heat_level: answers.pressure_level,
    q3_trap: answers.trap === 'unknown' ? 'dont_know' : answers.trap,
    q4_autonomy_prize: autonomyMap[answers.autonomy_prize] || answers.autonomy_prize,
    q5_collaboration: answers.collaboration === 'we_will_see' ? 'well_see' : answers.collaboration,
  }
}

export default function Intake() {
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState<Partial<IntakeAnswers>>({})
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const { user } = useAuth()
  const navigate = useNavigate()

  const currentQ = QUESTIONS[step]

  const handleSelect = (value: string) => {
    setAnswers((prev) => ({ ...prev, [currentQ.id]: value }))
    if (currentQ.id === 'pressure') return
    setTimeout(() => {
      if (step < QUESTIONS.length - 1) setStep(step + 1)
    }, 250)
  }

  const handleSlider = (value: number) => {
    setAnswers((prev) => ({ ...prev, [currentQ.id]: value }))
  }

  const handleSubmit = async () => {
    if (!user) return
    const fullAnswers = normalizeAnswers(answers as Partial<IntakeAnswers> & Record<string, unknown>)
    setSubmitting(true)
    try {
      await submitIntake(user.id, apiAnswers(fullAnswers))
      setSubmitted(true)
    } catch {
      setSubmitting(false)
    }
  }

  const progress = ((step + 1) / QUESTIONS.length) * 100
  const fullAnswers = normalizeAnswers(answers as Partial<IntakeAnswers> & Record<string, unknown>)
  const result = submitted ? assignCharacter(fullAnswers) : null
  const score = submitted ? computeScore(fullAnswers) : 0

  if (submitted && result) {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center bg-bgBase">
        <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="text-center max-w-md p-6">
          <div className="w-20 h-20 rounded-full mx-auto mb-6 flex items-center justify-center" style={{ backgroundColor: `${CHARACTER_INFO[result.character]?.color || '#D4AF37'}20`, border: `3px solid ${CHARACTER_INFO[result.character]?.color || '#D4AF37'}` }}>
            <Zap size={36} style={{ color: CHARACTER_INFO[result.character]?.color || '#D4AF37' }} />
          </div>
          <h2 className="font-display text-4xl text-brandGold text-glow-gold mb-2">STRATEGIC INTAKE COMPLETE</h2>
          <p className="text-textSecondary mb-6">Your character has been assigned.</p>

          <div className="bg-bgElevated border border-borderSubtle rounded-fz-lg p-6 mb-6">
            <p className="text-textMuted text-sm mb-1">Assigned Character</p>
            <p className="font-display text-3xl mb-1" style={{ color: CHARACTER_INFO[result.character]?.color }}>{result.characterName}</p>
            <p className="text-textSecondary text-sm">{CHARACTER_INFO[result.character]?.description}</p>
          </div>

          <div className="bg-bgElevated border border-borderSubtle rounded-fz-lg p-6 mb-6">
            <p className="text-textMuted text-sm mb-1">Starting Trust Score</p>
            <p className="font-display text-5xl text-brandGold">{score}</p>
            <p className="text-textSecondary text-sm">Watch Tier</p>
          </div>

          <button onClick={() => navigate('/dashboard')} className="w-full flex items-center justify-center gap-2 py-3 rounded-fz-md bg-brandGold text-textInverse font-semibold hover:bg-brandGoldBright transition-colors">
            Enter FlowZone <ArrowRight size={18} />
          </button>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center bg-bgBase">
      <div className="w-full max-w-lg p-6">
        <div className="mb-6">
          <div className="h-1.5 bg-bgOverlay rounded-full overflow-hidden mb-3">
            <motion.div className="h-full bg-brandGold" initial={{ width: 0 }} animate={{ width: `${progress}%` }} transition={{ duration: 0.3 }} />
          </div>
          <p className="text-textMuted text-xs">Question {step + 1} of {QUESTIONS.length}</p>
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={currentQ.id}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
          >
            <h2 className="font-display text-2xl text-brandGold mb-1">{currentQ.title}</h2>
            <p className="text-textSecondary mb-6">{currentQ.subtitle}</p>

            {currentQ.type === 'slider' ? (
              <div className="space-y-6">
                <input
                  type="range"
                  min={currentQ.min}
                  max={currentQ.max}
                  value={(answers.pressure_level as number) || 5}
                  onChange={(e) => handleSlider(Number(e.target.value))}
                  className="w-full accent-brandGold"
                />
                <div className="flex justify-between text-xs text-textMuted">
                  <span>{currentQ.labels?.[0]}</span>
                  <span className="text-brandGold font-bold text-lg">{answers.pressure_level || 5}</span>
                  <span>{currentQ.labels?.[1]}</span>
                </div>
                <button onClick={() => setStep(step + 1)} className="w-full flex items-center justify-center gap-2 py-2.5 rounded-fz-md bg-brandGold text-textInverse font-semibold hover:bg-brandGoldBright transition-colors">
                  Continue <ChevronRight size={16} />
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {currentQ.options?.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => handleSelect(opt.value)}
                    className={`w-full text-left p-4 rounded-fz-lg border transition-all ${
                      (answers as Record<string, string>)[currentQ.id] === opt.value
                        ? 'border-brandGold bg-brandGold/10'
                        : 'border-borderSubtle bg-bgOverlay hover:border-borderActive'
                    }`}
                  >
                    <div className="font-semibold text-textPrimary">{opt.label}</div>
                    <div className="text-sm text-textSecondary">{opt.desc}</div>
                  </button>
                ))}
              </div>
            )}
          </motion.div>
        </AnimatePresence>

        {step === QUESTIONS.length - 1 && (
          <div className="mt-6">
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-fz-md bg-brandGold text-textInverse font-semibold hover:bg-brandGoldBright transition-colors disabled:opacity-50"
            >
              {submitting ? (
                <div className="w-5 h-5 border-2 border-textInverse border-t-transparent rounded-full animate-spin" />
              ) : (
                <>
                  <Target size={18} />
                  REVEAL CHARACTER
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
