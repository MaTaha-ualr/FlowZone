import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, Shield, Star, Zap, Clock, Target, Flame, Hash, Trophy, Lock, CheckCircle, User } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { CHARACTER_INFO, SAFE_HARBOR_INFO } from '@/types'

const BADGES = [
  { key: 'first_check_in', name: 'First Check-In', icon: CheckCircle, desc: 'Completed your first vibe check', color: '#10B981' },
  { key: 'streak_7', name: '7-Day Streak', icon: Flame, desc: '7 consecutive days of check-ins', color: '#FF6B35' },
  { key: 'no_mask', name: 'No Mask', icon: Shield, desc: '10 sessions with zero masks detected', color: '#00A8E8' },
  { key: 'tactical_master', name: 'Tactical Master', icon: Target, desc: 'Accepted 20 tactical actions', color: '#D4AF37' },
  { key: 'vetted', name: 'Vetted', icon: Star, desc: 'Reached Vetted tier (250+)', color: '#D4AF37' },
  { key: 'voice_dump', name: 'Voice Dump', icon: Zap, desc: 'Completed your first voice session', color: '#6C5CE7' },
  { key: 'mentor_vouched', name: 'Mentor Vouched', icon: Trophy, desc: 'Received your first mentor vouch', color: '#D4AF37' },
  { key: 'document_ready', name: 'Document Ready', icon: Lock, desc: 'Uploaded first document to vault', color: '#00B4D8' },
]

function RainbowSVG({ score }: { score: number }) {
  const tiers = [
    { name: 'Watch', start: 0, end: 99, color: '#6366F1' },
    { name: 'Flex', start: 100, end: 249, color: '#10B981' },
    { name: 'Vetted', start: 250, end: 500, color: '#D4AF37' },
  ]
  const currentTier = tiers.find((t) => score >= t.start && score <= t.end) || tiers[0]
  const nextTier = tiers.find((t) => t.start > score)
  const progress = nextTier ? ((score - currentTier.start) / (nextTier.start - currentTier.start)) * 100 : 100

  return (
    <div className="relative w-48 h-48 mx-auto">
      <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
        <circle cx="50" cy="50" r="42" fill="none" stroke="#18181F" strokeWidth="8" />
        <circle cx="50" cy="50" r="42" fill="none" stroke={currentTier.color} strokeWidth="8" strokeDasharray={`${(progress / 100) * 264} 264`} strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-3xl text-brandGold">{score}</span>
        <span className="text-xs text-textMuted">{currentTier.name}</span>
      </div>
    </div>
  )
}

export default function Profile() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<'stats' | 'badges' | 'settings'>('stats')

  if (!user) {
    return (
      <div className="flex items-center justify-center h-64 text-textMuted">
        <div className="w-6 h-6 border-2 border-brandGold border-t-transparent rounded-full animate-spin mr-3" />
        Loading profile...
      </div>
    )
  }

  const charInfo = CHARACTER_INFO[user.current_character]
  const safeInfo = SAFE_HARBOR_INFO[user.safe_harbor_floor]

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <button onClick={() => navigate('/dashboard')} className="flex items-center gap-1 text-textMuted hover:text-textPrimary transition-colors text-sm">
        <ArrowLeft size={16} /> Back to Dashboard
      </button>

      {/* Identity Card */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-bgElevated border border-borderSubtle rounded-fz-lg p-6">
        <div className="flex items-start gap-4">
          <div className="w-16 h-16 rounded-fz-lg flex items-center justify-center text-lg font-bold shrink-0" style={{ backgroundColor: charInfo?.color || '#D4AF37', color: '#fff' }}>
            {user.name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase()}
          </div>
          <div className="flex-1">
            <h1 className="font-display text-2xl text-brandGold">{user.name}</h1>
            <div className="flex flex-wrap items-center gap-2 mt-1">
              <span className="text-xs px-2 py-0.5 rounded-fz-sm bg-brandGold/10 text-brandGold">@{user.username}</span>
              <span className="text-xs px-2 py-0.5 rounded-fz-sm" style={{ backgroundColor: `${charInfo?.color}20`, color: charInfo?.color }}>{charInfo?.name}</span>
              <span className="text-xs px-2 py-0.5 rounded-fz-sm flex items-center gap-1" style={{ backgroundColor: `${safeInfo.color}15`, color: safeInfo.color }}>
                <Shield size={10} /> {safeInfo.label}
              </span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mt-6">
          <div className="text-center p-3 rounded-fz-md bg-bgOverlay">
            <div className="font-display text-2xl text-brandGold">{user.display_score}</div>
            <div className="text-xs text-textMuted">Trust Score</div>
          </div>
          <div className="text-center p-3 rounded-fz-md bg-bgOverlay">
            <div className="font-display text-2xl text-brandBlue">{user.check_in_streak}</div>
            <div className="text-xs text-textMuted">Day Streak</div>
          </div>
          <div className="text-center p-3 rounded-fz-md bg-bgOverlay">
            <div className="font-display text-2xl text-brandPurple">{user.current_tier}</div>
            <div className="text-xs text-textMuted">Tier</div>
          </div>
        </div>
      </motion.div>

      {/* Rainbow Circle */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="bg-bgElevated border border-borderSubtle rounded-fz-lg p-6">
        <h2 className="font-display text-xl text-brandGold mb-4 text-center">RAINBOW CIRCLE</h2>
        <RainbowSVG score={user.display_score} />
        <div className="flex items-center justify-center gap-4 mt-4">
          <div className="flex items-center gap-1.5 text-xs text-textMuted"><span className="w-2 h-2 rounded-full bg-tierWatch" /> Watch</div>
          <div className="flex items-center gap-1.5 text-xs text-textMuted"><span className="w-2 h-2 rounded-full bg-tierFlex" /> Flex</div>
          <div className="flex items-center gap-1.5 text-xs text-textMuted"><span className="w-2 h-2 rounded-full bg-tierVetted" /> Vetted</div>
        </div>
      </motion.div>

      {/* Character */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="bg-bgElevated border border-borderSubtle rounded-fz-lg p-6">
        <h2 className="font-display text-xl text-brandGold mb-4">YOUR CHARACTER</h2>
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-fz-lg flex items-center justify-center shrink-0" style={{ backgroundColor: `${charInfo?.color}20`, border: `2px solid ${charInfo?.color}` }}>
            <User size={24} style={{ color: charInfo?.color }} />
          </div>
          <div>
            <div className="font-semibold text-lg" style={{ color: charInfo?.color }}>{charInfo?.name}</div>
            <div className="text-sm text-textSecondary">{charInfo?.role}</div>
            <p className="text-sm text-textMuted mt-1">{charInfo?.description}</p>
          </div>
        </div>
      </motion.div>

      {/* Tabs */}
      <div className="flex gap-2">
        {(['stats', 'badges', 'settings'] as const).map((t) => (
          <button key={t} onClick={() => setActiveTab(t)} className={`px-4 py-2 rounded-fz-md text-sm font-medium transition-colors ${activeTab === t ? 'bg-brandGold text-textInverse' : 'bg-bgElevated text-textSecondary hover:text-textPrimary border border-borderSubtle'}`}>
            {t === 'stats' ? 'Stats' : t === 'badges' ? 'Badges' : 'Settings'}
          </button>
        ))}
      </div>

      {activeTab === 'stats' && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[ { label: 'Age', value: user.age, icon: Hash }, { label: 'City', value: user.city || '-', icon: Target }, { label: 'School', value: user.school_name || '-', icon: Clock }, { label: 'User Type', value: user.user_type, icon: Shield }, { label: 'Probation', value: user.has_probation ? 'Yes' : 'No', icon: Lock }, { label: 'Case Worker', value: user.has_case_worker ? 'Yes' : 'No', icon: User } ].map((s) => (
            <div key={s.label} className="p-4 rounded-fz-md bg-bgElevated border border-borderSubtle">
              <div className="flex items-center gap-1.5 text-textMuted text-xs mb-1"><s.icon size={12} /> {s.label}</div>
              <div className="font-semibold text-textPrimary">{s.value}</div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'badges' && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {BADGES.map((b) => (
            <div key={b.key} className="p-4 rounded-fz-md bg-bgElevated border border-borderSubtle text-center">
              <b.icon size={24} style={{ color: b.color }} className="mx-auto mb-2" />
              <div className="font-semibold text-sm text-textPrimary">{b.name}</div>
              <div className="text-xs text-textMuted mt-1">{b.desc}</div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'settings' && (
        <div className="space-y-4">
          <div className="p-4 rounded-fz-md bg-bgElevated border border-borderSubtle">
            <h3 className="font-semibold text-textPrimary mb-2">Account</h3>
            <p className="text-sm text-textSecondary">Name: {user.name}</p>
            <p className="text-sm text-textSecondary">Username: {user.username}</p>
            <p className="text-sm text-textSecondary">Email: {user.email || 'Not set'}</p>
            <p className="text-sm text-textSecondary">Phone: {user.phone || 'Not set'}</p>
          </div>
          <div className="p-4 rounded-fz-md bg-bgElevated border border-borderSubtle">
            <h3 className="font-semibold text-textPrimary mb-2">Notifications</h3>
            <div className="flex items-center gap-2">
              <input type="checkbox" checked className="accent-brandGold" readOnly />
              <span className="text-sm text-textSecondary">Session reminders</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
