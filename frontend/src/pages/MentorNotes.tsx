import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowLeft, Save, AlertTriangle, Star, CheckCircle, Clock, User, Shield, Hash } from 'lucide-react'
import type { MentorNote } from '@/types'
import { SAFE_HARBOR_INFO } from '@/types'

const MOCK_NOTES: MentorNote[] = [
  { id: '1', youth_id: '1', youth_name: 'Marcus Cole', mentor_id: 'm1', mentor_name: 'Coach Ray', note_type: 'check_in', content: 'Marcus checked in solid today. No masks detected. He talked about wanting to keep his curfew extension and asked how many more days until Flex tier. Clear goals = good sign.', vouch_points: 5, risk_flag: false, created_at: '2025-01-20T14:00:00Z' },
  { id: '2', youth_id: '1', youth_name: 'Marcus Cole', mentor_id: 'm1', mentor_name: 'Coach Ray', note_type: 'session', content: 'FlowQuest session was intense. Marcus started storm but navigated to solid after The Dump. Tactical action: write a letter to his PO before Friday. He accepted.', vouch_points: 8, risk_flag: false, created_at: '2025-01-18T16:00:00Z' },
  { id: '3', youth_id: '1', youth_name: 'Marcus Cole', mentor_id: 'm1', mentor_name: 'Coach Ray', note_type: 'incident', content: 'Red flag: Marcus mentioned his friend D pulled up to school trying to get him to skip. Marcus said no but was shaken. Need to watch for loyalty trap escalation.', vouch_points: 0, risk_flag: true, created_at: '2025-01-15T10:30:00Z' },
  { id: '4', youth_id: '1', youth_name: 'Marcus Cole', mentor_id: 'm1', mentor_name: 'Coach Ray', note_type: 'milestone', content: 'Marcus hit 5-day streak today. First time since intake. He was proud. I reinforced: consistency is what builds trust, not perfection. Vouched him forward.', vouch_points: 10, risk_flag: false, created_at: '2025-01-14T09:00:00Z' },
  { id: '5', youth_id: '1', youth_name: 'Marcus Cole', mentor_id: 'm1', mentor_name: 'Coach Ray', note_type: 'check_in', content: 'Guarded check-in. Marcus said he felt like nobody believes he can actually change. Used Navigator character to reframe: belief comes from action, not words. He stayed in the session.', vouch_points: 3, risk_flag: false, created_at: '2025-01-12T11:00:00Z' },
]

const YOUTH_MOCK = {
  id: '1', name: 'Marcus Cole', age: 17, city: 'Atlanta', school_name: 'Westside High',
  current_trust_score: 142, display_score: 142, current_tier: 'Flex', safe_harbor_floor: 'yellow' as const,
  current_character: 'challenger', current_character_name: 'The Challenger', check_in_streak: 5,
}

const NOTE_TYPE_ICON: Record<string, typeof CheckCircle> = {
  check_in: CheckCircle,
  session: Star,
  incident: AlertTriangle,
  milestone: Star,
  flag: AlertTriangle,
}

const NOTE_TYPE_COLOR: Record<string, string> = {
  check_in: '#10B981',
  session: '#00A8E8',
  incident: '#DC2626',
  milestone: '#D4AF37',
  flag: '#DC2626',
}

export default function MentorNotes() {
  const { userId } = useParams<{ userId: string }>()
  const navigate = useNavigate()
  const [notes, setNotes] = useState<MentorNote[]>(MOCK_NOTES)
  const [noteType, setNoteType] = useState<string>('check_in')
  const [content, setContent] = useState('')
  const [vouchPoints, setVouchPoints] = useState(0)
  const [riskFlag, setRiskFlag] = useState(false)
  const [saving, setSaving] = useState(false)

  const youth = YOUTH_MOCK
  const safeInfo = SAFE_HARBOR_INFO[youth.safe_harbor_floor]

  const handleSave = () => {
    if (!content.trim()) return
    setSaving(true)
    setTimeout(() => {
      const newNote: MentorNote = {
        id: `new-${Date.now()}`,
        youth_id: userId || '1',
        youth_name: youth.name,
        mentor_id: 'm1',
        mentor_name: 'Coach Ray',
        note_type: noteType as MentorNote['note_type'],
        content,
        vouch_points: vouchPoints,
        risk_flag: riskFlag,
        created_at: new Date().toISOString(),
      }
      setNotes((prev) => [newNote, ...prev])
      setContent('')
      setVouchPoints(0)
      setRiskFlag(false)
      setSaving(false)
    }, 600)
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <button onClick={() => navigate('/mentor/dashboard')} className="flex items-center gap-1 text-textMuted hover:text-textPrimary transition-colors text-sm">
        <ArrowLeft size={16} /> Back to Roster
      </button>

      {/* Youth Header */}
      <div className="p-6 rounded-fz-lg bg-bgElevated border border-borderSubtle">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-fz-lg bg-charChallenger flex items-center justify-center text-white font-bold text-lg">
              MC
            </div>
            <div>
              <h1 className="font-display text-2xl text-brandGold">{youth.name}</h1>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs px-2 py-0.5 rounded-fz-sm bg-brandGold/10 text-brandGold">{youth.current_tier}</span>
                <span className="text-xs px-2 py-0.5 rounded-fz-sm bg-bgOverlay text-textMuted">{youth.age} yrs • {youth.city}</span>
                <span className="text-xs px-2 py-0.5 rounded-fz-sm flex items-center gap-1" style={{ backgroundColor: `${safeInfo.color}15`, color: safeInfo.color }}>
                  <Shield size={10} /> {safeInfo.label}
                </span>
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="font-display text-3xl text-brandGold">{youth.display_score}</div>
            <div className="text-xs text-textMuted">Trust Score</div>
          </div>
        </div>
        <div className="grid grid-cols-4 gap-3 mt-4">
          {[ { label: 'Streak', value: `${youth.check_in_streak}d`, icon: Clock }, { label: 'Character', value: youth.current_character_name, icon: User }, { label: 'School', value: youth.school_name || '-', icon: Shield }, { label: 'Score', value: youth.display_score, icon: Hash } ].map((s) => (
            <div key={s.label} className="p-2 rounded-fz-md bg-bgOverlay text-center">
              <div className="text-xs text-textMuted flex items-center justify-center gap-1"><s.icon size={10} /> {s.label}</div>
              <div className="font-semibold text-sm text-textPrimary mt-0.5">{s.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Note Editor */}
      <div className="p-5 rounded-fz-lg bg-bgElevated border border-borderSubtle space-y-4">
        <h2 className="font-display text-xl text-brandGold">NEW NOTE</h2>
        <div className="flex flex-wrap gap-2">
          {(['check_in', 'session', 'incident', 'milestone', 'flag'] as const).map((t) => (
            <button key={t} onClick={() => setNoteType(t)} className={`px-3 py-1.5 rounded-fz-md text-xs font-medium border transition-colors ${noteType === t ? 'bg-brandGold text-textInverse border-brandGold' : 'bg-bgOverlay text-textSecondary border-borderSubtle'}`}>
              {t.replace('_', ' ')}
            </button>
          ))}
        </div>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="What happened today? Be specific."
          rows={4}
          className="w-full px-3 py-2.5 rounded-fz-md bg-bgOverlay border border-borderSubtle text-textPrimary placeholder:text-textMuted focus:border-brandGold focus:outline-none text-sm resize-none"
        />
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="flex items-center gap-3">
            <span className="text-sm text-textSecondary">Vouch</span>
            <input
              type="range"
              min={0}
              max={50}
              value={vouchPoints}
              onChange={(e) => setVouchPoints(Number(e.target.value))}
              className="w-32 accent-brandGold"
            />
            <span className="text-sm font-bold text-brandGold w-8">{vouchPoints}</span>
          </div>
          <div className="flex items-center gap-2">
            <input id="risk" type="checkbox" checked={riskFlag} onChange={(e) => setRiskFlag(e.target.checked)} className="accent-safeRed w-4 h-4" />
            <label htmlFor="risk" className="text-sm text-safeRed font-medium">Risk Flag</label>
          </div>
          <button
            onClick={handleSave}
            disabled={saving || !content.trim()}
            className="sm:ml-auto flex items-center gap-2 px-4 py-2 rounded-fz-md bg-brandGold text-textInverse text-sm font-medium hover:bg-brandGoldBright transition-colors disabled:opacity-50"
          >
            {saving ? <div className="w-4 h-4 border-2 border-textInverse border-t-transparent rounded-full animate-spin" /> : <Save size={16} />}
            Save Note
          </button>
        </div>
      </div>

      {/* Notes History */}
      <div className="space-y-3">
        <h2 className="font-display text-xl text-brandGold">NOTES HISTORY</h2>
        <AnimatePresence>
          {notes.map((note) => {
            const TypeIcon = NOTE_TYPE_ICON[note.note_type] || CheckCircle
            const typeColor = NOTE_TYPE_COLOR[note.note_type] || '#A1A1AA'
            return (
              <motion.div
                key={note.id}
                layout
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-4 rounded-fz-md bg-bgElevated border border-borderSubtle"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <TypeIcon size={14} style={{ color: typeColor }} />
                    <span className="text-xs font-medium uppercase" style={{ color: typeColor }}>{note.note_type.replace('_', ' ')}</span>
                    <span className="text-xs text-textMuted">{new Date(note.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {note.risk_flag && <AlertTriangle size={14} className="text-safeRed" />}
                    {note.vouch_points > 0 && (
                      <span className="text-xs px-2 py-0.5 rounded-fz-sm bg-brandGold/10 text-brandGold font-medium">
                        +{note.vouch_points} vouch
                      </span>
                    )}
                  </div>
                </div>
                <p className="text-sm text-textSecondary leading-relaxed">{note.content}</p>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </div>
  )
}
