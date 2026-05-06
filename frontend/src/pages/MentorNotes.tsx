import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft,
  Save,
  AlertTriangle,
  Star,
  CheckCircle,
  Clock,
  User,
  Shield,
  Hash,
  Loader2,
} from 'lucide-react'
import type { MentorYouthDashboard, SafeHarborEnum } from '@/types'
import { SAFE_HARBOR_INFO } from '@/types'
import { useAuth } from '@/context/AuthContext'
import { createMentorNote, getMentorDashboard, getMentorNotes } from '@/lib/api'

interface DisplayNote {
  id: string
  type: string
  content: string
  vouch_points: number
  risk_flag: boolean
  mentor_name: string | null
  created_at: string
}

const NOTE_TYPE_ICON: Record<string, typeof CheckCircle> = {
  check_in: CheckCircle,
  session: Star,
  incident: AlertTriangle,
  milestone: Star,
  flag: AlertTriangle,
  vouch: Star,
}

const NOTE_TYPE_COLOR: Record<string, string> = {
  check_in: '#10B981',
  session: '#00A8E8',
  incident: '#DC2626',
  milestone: '#D4AF37',
  flag: '#DC2626',
  vouch: '#D4AF37',
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function noteFromApi(raw: unknown): DisplayNote {
  const r = asRecord(raw)
  const id = typeof r.id === 'string' ? r.id : crypto.randomUUID()
  const type = typeof r.note_type === 'string' ? r.note_type : (typeof r.type === 'string' ? r.type : 'check_in')
  const content =
    typeof r.sanitized_content === 'string' && r.sanitized_content.length > 0
      ? r.sanitized_content
      : typeof r.content === 'string'
      ? r.content
      : typeof r.raw_content === 'string'
      ? r.raw_content
      : ''
  const vp = typeof r.vouch_points === 'number' ? r.vouch_points : 0
  const flag =
    r.risk_flag === true ||
    r.risk_flag_level === 'red' ||
    r.risk_flag_level === 'yellow'
  const mentor =
    typeof r.mentor_name === 'string'
      ? r.mentor_name
      : typeof r.mentor === 'string'
      ? r.mentor
      : null
  const created =
    typeof r.created_at === 'string'
      ? r.created_at
      : typeof r.date === 'string'
      ? r.date
      : new Date().toISOString()
  return { id, type, content, vouch_points: vp, risk_flag: flag, mentor_name: mentor, created_at: created }
}

function initialsOf(name: string): string {
  return name
    .split(/\s+/)
    .map((n) => n[0]?.toUpperCase() ?? '')
    .slice(0, 2)
    .join('')
}

export default function MentorNotes() {
  const { userId } = useParams<{ userId: string }>()
  const navigate = useNavigate()
  const { user: currentUser } = useAuth()

  const [youth, setYouth] = useState<MentorYouthDashboard['user'] | null>(null)
  const [notes, setNotes] = useState<DisplayNote[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')

  const [noteType, setNoteType] = useState<string>('check_in')
  const [content, setContent] = useState('')
  const [vouchPoints, setVouchPoints] = useState(0)
  const [riskFlag, setRiskFlag] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')

  useEffect(() => {
    if (!userId) return
    let cancelled = false
    setLoading(true)
    setError('')

    Promise.all([
      getMentorDashboard(userId),
      getMentorNotes(userId).catch(() => []),
    ])
      .then(([dashboard, notesRaw]) => {
        if (cancelled) return
        const d = dashboard as MentorYouthDashboard
        setYouth(d.user)
        const apiNotes = Array.isArray(notesRaw) ? notesRaw.map(noteFromApi) : []
        // The dashboard recent_notes are sanitized; the dedicated notes endpoint
        // gives the full list. Prefer dedicated when available, otherwise fall
        // back to the dashboard's recent_notes.
        if (apiNotes.length > 0) {
          setNotes(apiNotes)
        } else {
          setNotes(d.recent_notes.map(noteFromApi))
        }
      })
      .catch((err) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Could not load this youth')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [userId])

  const handleSave = async () => {
    if (!content.trim() || !userId || !currentUser) return
    setSaving(true)
    setSaveError('')
    try {
      const created = await createMentorNote({
        user_id: userId,
        mentor_id: currentUser.id,
        mentor_name: currentUser.name,
        note_type: noteType,
        content,
        vouch_points: vouchPoints,
        risk_flag_level: riskFlag ? 'red' : 'none',
      })
      setNotes((prev) => [noteFromApi(created), ...prev])
      setContent('')
      setVouchPoints(0)
      setRiskFlag(false)
      setNoteType('check_in')
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save note')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-16 flex items-center justify-center text-textMuted">
        <Loader2 size={20} className="animate-spin mr-2" /> Loading youth profile…
      </div>
    )
  }

  if (error || !youth) {
    return (
      <div className="max-w-4xl mx-auto space-y-4">
        <button
          onClick={() => navigate('/mentor/dashboard')}
          className="flex items-center gap-1 text-textMuted hover:text-textPrimary text-sm"
        >
          <ArrowLeft size={16} /> Back to Roster
        </button>
        <div className="flex items-center gap-2 p-4 rounded-fz-lg bg-safeRed/10 border border-safeRed/20 text-sm text-safeRed">
          <AlertTriangle size={16} /> {error || 'Youth not found'}
        </div>
      </div>
    )
  }

  const safeInfo = SAFE_HARBOR_INFO[youth.safe_harbor_floor as SafeHarborEnum]

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <button
        onClick={() => navigate('/mentor/dashboard')}
        className="flex items-center gap-1 text-textMuted hover:text-textPrimary transition-colors text-sm"
      >
        <ArrowLeft size={16} /> Back to Roster
      </button>

      {/* Youth Header */}
      <div className="p-6 rounded-fz-lg bg-bgElevated border border-borderSubtle">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-4 min-w-0">
            <div
              className="w-14 h-14 rounded-fz-lg flex items-center justify-center text-white font-bold text-lg shrink-0"
              style={{ background: safeInfo.color }}
            >
              {initialsOf(youth.name)}
            </div>
            <div className="min-w-0">
              <h1 className="font-display text-2xl text-brandGold truncate">{youth.name}</h1>
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                <span className="text-xs px-2 py-0.5 rounded-fz-sm bg-brandGold/10 text-brandGold uppercase">
                  {youth.current_tier?.replace('the_', '') || 'watch'}
                </span>
                <span className="text-xs px-2 py-0.5 rounded-fz-sm bg-bgOverlay text-textMuted">
                  {youth.age} yrs
                  {youth.city ? ` · ${youth.city}` : ''}
                </span>
                <span
                  className="text-xs px-2 py-0.5 rounded-fz-sm flex items-center gap-1"
                  style={{ backgroundColor: `${safeInfo.color}15`, color: safeInfo.color }}
                >
                  <Shield size={10} /> {safeInfo.label}
                </span>
              </div>
            </div>
          </div>
          <div className="text-right shrink-0">
            <div className="font-display text-3xl text-brandGold">{youth.display_score}</div>
            <div className="text-xs text-textMuted">Trust Score</div>
          </div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
          {[
            { label: 'Streak', value: `${youth.check_in_streak}d`, icon: Clock },
            { label: 'Character', value: youth.current_character_name, icon: User },
            { label: 'School', value: youth.school_name || '—', icon: Shield },
            { label: 'Score', value: youth.display_score, icon: Hash },
          ].map((s) => (
            <div key={s.label} className="p-2 rounded-fz-md bg-bgOverlay text-center">
              <div className="text-xs text-textMuted flex items-center justify-center gap-1">
                <s.icon size={10} /> {s.label}
              </div>
              <div className="font-semibold text-sm text-textPrimary mt-0.5 truncate">{s.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Note Editor */}
      <div className="p-5 rounded-fz-lg bg-bgElevated border border-borderSubtle space-y-4">
        <h2 className="font-display text-xl text-brandGold">NEW NOTE</h2>
        <div className="flex flex-wrap gap-2">
          {(['check_in', 'session', 'incident', 'milestone', 'flag'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setNoteType(t)}
              className={`px-3 py-1.5 rounded-fz-md text-xs font-medium border transition-colors ${
                noteType === t
                  ? 'bg-brandGold text-textInverse border-brandGold'
                  : 'bg-bgOverlay text-textSecondary border-borderSubtle'
              }`}
            >
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
            <input
              id="risk"
              type="checkbox"
              checked={riskFlag}
              onChange={(e) => setRiskFlag(e.target.checked)}
              className="accent-safeRed w-4 h-4"
            />
            <label htmlFor="risk" className="text-sm text-safeRed font-medium">
              Risk Flag
            </label>
          </div>
          <button
            onClick={handleSave}
            disabled={saving || !content.trim()}
            className="sm:ml-auto flex items-center gap-2 px-4 py-2 rounded-fz-md bg-brandGold text-textInverse text-sm font-medium hover:bg-brandGoldBright transition-colors disabled:opacity-50"
          >
            {saving ? (
              <div className="w-4 h-4 border-2 border-textInverse border-t-transparent rounded-full animate-spin" />
            ) : (
              <Save size={16} />
            )}
            Save Note
          </button>
        </div>
        {saveError && (
          <div className="flex items-center gap-2 px-3 py-2 rounded-fz-sm bg-safeRed/10 border border-safeRed/30 text-xs text-safeRed">
            <AlertTriangle size={12} /> {saveError}
          </div>
        )}
      </div>

      {/* Notes History */}
      <div className="space-y-3">
        <h2 className="font-display text-xl text-brandGold">NOTES HISTORY</h2>
        {notes.length === 0 && (
          <div className="text-sm text-textMuted py-8 text-center">No notes yet for {youth.name.split(' ')[0]}.</div>
        )}
        <AnimatePresence initial={false}>
          {notes.map((note) => {
            const TypeIcon = NOTE_TYPE_ICON[note.type] || CheckCircle
            const typeColor = NOTE_TYPE_COLOR[note.type] || '#A1A1AA'
            return (
              <motion.div
                key={note.id}
                layout
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="p-4 rounded-fz-md bg-bgElevated border border-borderSubtle"
              >
                <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <TypeIcon size={14} style={{ color: typeColor }} />
                    <span className="text-xs font-medium uppercase" style={{ color: typeColor }}>
                      {note.type.replace('_', ' ')}
                    </span>
                    <span className="text-xs text-textMuted">
                      {new Date(note.created_at).toLocaleDateString()}
                    </span>
                    {note.mentor_name && (
                      <span className="text-xs text-textMuted">· {note.mentor_name}</span>
                    )}
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
                <p className="text-sm text-textSecondary leading-relaxed whitespace-pre-wrap">
                  {note.content}
                </p>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </div>
  )
}
