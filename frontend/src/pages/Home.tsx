import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Zap,
  Shield,
  Star,
  ChevronRight,
  MessageSquare,
  Heart,
  Target,
  BarChart3,
  Users,
} from 'lucide-react'
import { PERSONAS } from '@/types'

const steps = [
  {
    icon: Heart,
    title: 'Vibe Check',
    desc: 'Check in with your emotional state. Are you Solid, Angry, Guarded, or Storm? Your vibe sets your character for the session.',
    color: '#00B4D8',
  },
  {
    icon: MessageSquare,
    title: 'The Dump',
    desc: "Unload what's on your mind. No judgment. Your character meets you where you are and helps you process.",
    color: '#6C5CE7',
  },
  {
    icon: Target,
    title: 'Tactical Action',
    desc: 'Leave with a concrete next step. Accept it, and build trust. Pass on it, and stay real -- but know the cost.',
    color: '#D4AF37',
  },
]

const tiers = [
  {
    name: 'Watch',
    color: '#6366F1',
    range: '0-99',
    desc: 'New to FlowZone. Building baseline trust. Every check-in counts.',
  },
  {
    name: 'Flex',
    color: '#10B981',
    range: '100-249',
    desc: 'Proving consistency. Unlock rewards, voice sessions, and deeper tools.',
  },
  {
    name: 'Vetted',
    color: '#D4AF37',
    range: '250+',
    desc: "Elite status. Full autonomy access. You've earned the system's highest trust.",
    // Note: using double quotes above to avoid apostrophe issues
  },
]

export default function Home() {
  return (
    <div className="space-y-20 pb-20">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-fz-xl bg-bgElevated border border-borderSubtle">
        <div className="absolute inset-0 bg-noise opacity-50" />
        <div className="relative px-6 py-20 md:py-28 text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <h1 className="font-display text-5xl md:text-7xl text-brandGold text-glow-gold mb-4">
              THEY WATCH. YOU FLEX.
              <br />
              YOU GET VETTED.
            </h1>
            <p className="text-textSecondary text-lg md:text-xl max-w-2xl mx-auto mb-8">
              FlowZone is a Trust Engine for young people building their future. Check in. Speak truth. Earn your way to freedom.
            </p>
            <div className="flex items-center justify-center gap-4">
              <Link
                to="/register"
                className="flex items-center gap-2 px-6 py-3 rounded-fz-md bg-brandGold text-textInverse font-semibold hover:bg-brandGoldBright transition-colors"
              >
                <Zap size={18} />
                Join FlowZone
              </Link>
              <Link
                to="/login"
                className="flex items-center gap-2 px-6 py-3 rounded-fz-md border border-borderSubtle text-textSecondary hover:text-textPrimary hover:border-borderActive transition-colors"
              >
                Get In
                <ChevronRight size={16} />
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* How FlowQuest Works */}
      <section>
        <h2 className="font-display text-3xl text-brandGold mb-8 text-center">HOW FLOWQUEST WORKS</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {steps.map((s, i) => (
            <motion.div
              key={s.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.15 }}
              className="p-6 rounded-fz-lg bg-bgElevated border border-borderSubtle hover:border-borderActive transition-colors"
            >
              <div
                className="w-12 h-12 rounded-fz-md flex items-center justify-center mb-4"
                style={{ backgroundColor: `${s.color}15` }}
              >
                <s.icon size={22} style={{ color: s.color }} />
              </div>
              <h3 className="font-semibold text-lg text-textPrimary mb-2">{s.title}</h3>
              <p className="text-textSecondary text-sm leading-relaxed">{s.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Personas */}
      <section>
        <h2 className="font-display text-3xl text-brandGold mb-8 text-center">WHO SHOWS UP</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Object.entries(PERSONAS).map(([key, p], i) => (
            <motion.div
              key={key}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="p-5 rounded-fz-lg bg-bgElevated border border-borderSubtle hover:border-borderActive transition-all"
            >
              <div className="flex items-center gap-3 mb-4">
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm"
                  style={{ backgroundColor: p.color, color: '#fff' }}
                >
                  {p.avatar}
                </div>
                <div>
                  <div className="font-semibold text-textPrimary">{p.name}</div>
                  <div className="text-xs text-textMuted">
                    {p.age} &bull; {p.city}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 mb-3">
                <span
                  className="text-xs px-2 py-0.5 rounded-fz-sm font-medium"
                  style={{ backgroundColor: `${p.color}20`, color: p.color }}
                >
                  {p.character_name}
                </span>
                <span className="text-xs px-2 py-0.5 rounded-fz-sm bg-brandGold/10 text-brandGold">
                  {p.tier}
                </span>
              </div>
              <p className="text-textSecondary text-sm italic mb-3">&ldquo;{p.quote}&rdquo;</p>
              <div className="text-xs text-textMuted">
                <span className="text-brandCrimson">Trap:</span> {p.trap}
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Trust Engine Formula */}
      <section className="p-8 rounded-fz-xl bg-bgElevated border border-borderSubtle">
        <h2 className="font-display text-3xl text-brandGold mb-6 text-center">THE TRUST ENGINE</h2>
        <div className="text-center space-y-4">
          <p className="text-textSecondary text-sm">
            Your Trust Score is calculated from everything you bring to FlowZone:
          </p>
          <div className="font-mono text-lg md:text-2xl text-brandGold bg-bgOverlay inline-block px-6 py-4 rounded-fz-lg border border-borderSubtle">
            (C + W + H + R + M - P) / T
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 max-w-2xl mx-auto mt-4">
            {[
              { label: 'C', desc: 'Consistency', color: '#00A8E8' },
              { label: 'W', desc: 'Weight (pressure multiplier)', color: '#FF6B35' },
              { label: 'H', desc: 'Honesty (no masks)', color: '#10B981' },
              { label: 'R', desc: 'Regulation (vibe management)', color: '#6C5CE7' },
              { label: 'M', desc: 'Mentor Vouch', color: '#D4AF37' },
              { label: 'P', desc: 'Penalty (masks, drops)', color: '#DC2626' },
              { label: 'T', desc: 'Time (days active)', color: '#A1A1AA' },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-2 text-left">
                <span className="font-mono font-bold" style={{ color: item.color }}>
                  {item.label}
                </span>
                <span className="text-xs text-textSecondary">{item.desc}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trust Tiers */}
      <section>
        <h2 className="font-display text-3xl text-brandGold mb-8 text-center">TRUST TIERS</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {tiers.map((t, i) => (
            <motion.div
              key={t.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.15 }}
              className="p-6 rounded-fz-lg bg-bgElevated border border-borderSubtle text-center"
            >
              <div
                className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center"
                style={{ backgroundColor: `${t.color}15`, border: `2px solid ${t.color}` }}
              >
                <Shield size={28} style={{ color: t.color }} />
              </div>
              <h3 className="font-display text-2xl mb-1" style={{ color: t.color }}>
                {t.name}
              </h3>
              <p className="text-xs text-textMuted mb-3">{t.range} points</p>
              <p className="text-textSecondary text-sm">{t.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* For Mentors */}
      <section className="p-8 rounded-fz-xl bg-bgElevated border border-borderSubtle">
        <div className="flex flex-col md:flex-row items-center gap-8">
          <div className="flex-1">
            <h2 className="font-display text-3xl text-brandBlue text-glow-blue mb-4">FOR MENTORS</h2>
            <p className="text-textSecondary mb-4">
              Coach Ray and mentor staff get a real-time dashboard of every youth in their roster. Safe Harbor alerts, trust trends, session notes, and vouch power -- all in one place.
            </p>
            <div className="flex flex-wrap gap-3">
              <div className="flex items-center gap-1.5 text-sm text-textSecondary">
                <Users size={14} className="text-brandBlue" /> Youth Roster
              </div>
              <div className="flex items-center gap-1.5 text-sm text-textSecondary">
                <BarChart3 size={14} className="text-brandBlue" /> Trust Trends
              </div>
              <div className="flex items-center gap-1.5 text-sm text-textSecondary">
                <Star size={14} className="text-brandBlue" /> Vouch System
              </div>
            </div>
          </div>
          <div className="flex-1 bg-bgOverlay rounded-fz-lg p-6 border border-borderSubtle">
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-textSecondary">Total Youth</span>
                <span className="font-semibold text-textPrimary">12</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-textSecondary">Active Sessions</span>
                <span className="font-semibold text-brandBlue">3</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-textSecondary">Alerts</span>
                <span className="font-semibold text-safeRed">1</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-textSecondary">Avg Trust</span>
                <span className="font-semibold text-brandGold">142</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="text-center text-textMuted text-sm py-8 border-t border-borderSubtle">
        <p className="font-display text-lg text-brandGold mb-2">FLOWZONE</p>
        <p>Trust is earned. Flex is proven. You get vetted.</p>
      </footer>
    </div>
  )
}
