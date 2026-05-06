import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft,
  MoreVertical,
  Mic,
  Send,
  Check,
  X,
  AlertTriangle,
  Volume2,
  Shield,
  BarChart3,
  Clock,
  MessageSquare,
  Hash,
  Flame,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  createSession,
  endSession as endSessionApi,
  deleteSession as deleteSessionApi,
  startNewSession as startNewSessionApi,
  getChatHistory as getChatHistoryApi,
  getToken,
  sendChatMessage as sendChatMessageApi,
  webSocketUrl,
} from '@/lib/api'
import { useAuth } from '@/context/AuthContext'

/* ─── Types ─── */

interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  character?: string
  voice_url?: string
  mask_detected?: boolean
  action_item?: ActionItem
  trust_delta?: number
}

interface ActionItem {
  id: string
  description: string
  status: 'pending' | 'accepted' | 'passed'
}

interface SessionState {
  id: string
  character: string
  character_role: string
  character_color: string
  vibe: string
  vibe_emoji: string
  safe_harbor: 'green' | 'yellow' | 'red'
  trust_score: number
  trust_delta: number
  started_at: string
  message_count: number
}

/* ─── Inline API helpers (since src/lib/api.ts doesn't exist) ─── */

async function getChatHistory(sessionId: string): Promise<ChatMessage[]> {
  try {
    const history = await getChatHistoryApi(sessionId)
    const historyRecord = asRecord(history)
    const messages = Array.isArray(history) ? history : Array.isArray(historyRecord.messages) ? historyRecord.messages : []
    return messages.map(toChatMessage)
  } catch {
    return []
  }
}

async function sendChatMessage(sessionId: string, content: string): Promise<ChatMessage> {
  return toChatMessage(await sendChatMessageApi(sessionId, content))
}

async function endSession(sessionId: string) {
  return endSessionApi(sessionId)
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? value as Record<string, unknown> : {}
}

function stringValue(value: unknown, fallback = ''): string {
  return typeof value === 'string' && value.length > 0 ? value : fallback
}

function numberValue(value: unknown): number | undefined {
  const number = Number(value)
  return Number.isFinite(number) ? number : undefined
}

function roleValue(value: unknown): ChatMessage['role'] {
  if (value === 'user' || value === 'assistant' || value === 'system') return value
  return 'assistant'
}

function actionItemValue(value: unknown): ActionItem | undefined {
  const record = asRecord(value)
  if (!record.description) return undefined
  const status = record.status === 'accepted' || record.status === 'passed' ? record.status : 'pending'
  return {
    id: stringValue(record.id, crypto.randomUUID()),
    description: stringValue(record.description),
    status,
  }
}

function toChatMessage(data: unknown): ChatMessage {
  const dataRecord = asRecord(data)
  const source = dataRecord.message ? asRecord(dataRecord.message) : dataRecord
  const trustDelta = numberValue(source.trust_delta ?? dataRecord.trust_score_delta)
  return {
    id: stringValue(source.id, stringValue(source.message_id, stringValue(dataRecord.message_id, crypto.randomUUID()))),
    role: roleValue(source.role),
    content: stringValue(source.content, stringValue(dataRecord.content)),
    timestamp: stringValue(source.timestamp, stringValue(dataRecord.timestamp, new Date().toISOString())),
    character: stringValue(source.character, stringValue(dataRecord.character)) || undefined,
    mask_detected: typeof source.mask_detected === 'boolean' ? source.mask_detected : typeof dataRecord.mask_detected === 'boolean' ? dataRecord.mask_detected : undefined,
    action_item: actionItemValue(source.action_item),
    trust_delta: trustDelta,
  }
}

/* ─── Utils ─── */

const nowISO = () => new Date().toISOString()

const CHARACTER_MAP: Record<string, { name: string; role: string; color: string; avatar: string }> = {
  vex: { name: 'VEX', role: 'Challenger', color: '#DC2626', avatar: '/character-vex.png' },
  yogi: { name: 'YOGI', role: 'Navigator', color: '#00A8E8', avatar: '/character-yogi.png' },
  ace:  { name: 'ACE',  role: 'Straight Shooter', color: '#10B981', avatar: '/character-ace.png' },
  nova: { name: 'NOVA', role: 'Strategist', color: '#6C5CE7', avatar: '/character-nova.png' },
}

const CHARACTER_ALIASES: Record<string, string> = {
  challenger: 'vex',
  navigator: 'yogi',
  straight_shooter: 'ace',
  strategist: 'nova',
  vex: 'vex',
  yogi: 'yogi',
  ace: 'ace',
  nova: 'nova',
}

const VIBE_MAP: Record<string, { emoji: string; color: string }> = {
  solid:   { emoji: '💎', color: '#00B4D8' },
  angry:   { emoji: '🔥', color: '#FF6B35' },
  guarded: { emoji: '🔏', color: '#64748B' },
  storm:   { emoji: '⛈️', color: '#7C3AED' },
}

/* ─── Components ─── */

function characterKey(value: unknown, fallback = 'vex'): string {
  return CHARACTER_ALIASES[stringValue(value, fallback)] || fallback
}

function safeHarborValue(value: unknown, fallback: SessionState['safe_harbor']): SessionState['safe_harbor'] {
  if (value === 'green' || value === 'yellow' || value === 'red') return value
  return fallback
}

function HexAvatar({ color, src, size = 40, pulse = false }: { color: string; src?: string; size?: number; pulse?: boolean }) {
  return (
    <div
      className={cn('relative flex items-center justify-center overflow-hidden', pulse && 'animate-pulse')}
      style={{
        width: size,
        height: size,
        clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)',
        border: `2px solid ${color}`,
        background: '#0F0F14',
      }}
    >
      {src ? (
        <img src={src} alt="" className="object-cover w-full h-full" />
      ) : (
        <span className="text-[10px] font-bold" style={{ color }}>FZ</span>
      )}
    </div>
  )
}

function StatusDot({ status }: { status: 'connected' | 'thinking' | 'disconnected' }) {
  const color = status === 'connected' ? '#10B981' : status === 'thinking' ? '#F59E0B' : '#DC2626'
  return (
    <span className="relative flex h-2.5 w-2.5">
      <span
        className={cn('absolute inline-flex h-full w-full rounded-full opacity-75', status !== 'disconnected' && 'animate-ping')}
        style={{ backgroundColor: color }}
      />
      <span className="relative inline-flex rounded-full h-2.5 w-2.5" style={{ backgroundColor: color }} />
    </span>
  )
}

function ThinkingDots() {
  return (
    <div className="flex items-center gap-1 px-3 py-2">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="block h-1.5 w-1.5 rounded-full"
          style={{ backgroundColor: '#6C5CE7' }}
          animate={{ y: [0, -4, 0] }}
          transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.2 }}
        />
      ))}
    </div>
  )
}

function WaveformBars({ count = 48, active = false, color = '#DC2626' }: { count?: number; active?: boolean; color?: string }) {
  return (
    <div className="flex items-center justify-center gap-[2px] h-12">
      {Array.from({ length: count }).map((_, i) => (
        <motion.div
          key={i}
          className="w-[3px] rounded-full"
          style={{ backgroundColor: color }}
          animate={
            active
              ? { height: [4, Math.random() * 32 + 4, 4] }
              : { height: 4 }
          }
          transition={{
            duration: 0.4,
            repeat: active ? Infinity : 0,
            delay: i * 0.02,
          }}
        />
      ))}
    </div>
  )
}

/* ─── Main Page ─── */

export default function FlowQuest() {
  const navigate = useNavigate()
  const { sessionId: routeSessionId } = useParams<{ sessionId?: string }>()
  const [searchParams] = useSearchParams()
  const { user } = useAuth()
  const requestedSessionId = routeSessionId || searchParams.get('sessionId') || ''
  const [sessionId, setSessionId] = useState(requestedSessionId)

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const [wsStatus, setWsStatus] = useState<'connected' | 'thinking' | 'disconnected'>('disconnected')
  const [session, setSession] = useState<SessionState>({
    id: sessionId,
    character: 'vex',
    character_role: 'Challenger',
    character_color: '#DC2626',
    vibe: 'angry',
    vibe_emoji: '🔥',
    safe_harbor: 'green',
    trust_score: 142,
    trust_delta: 4.8,
    started_at: nowISO(),
    message_count: 0,
  })
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [showEndModal, setShowEndModal] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [recording, setRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [hasStarted, setHasStarted] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)

  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const streamingMessageIdRef = useRef<string | null>(null)
  const initialMessageSentRef = useRef(false)
  const recordingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const character = CHARACTER_MAP[characterKey(session.character)] || CHARACTER_MAP.vex

  useEffect(() => {
    setSessionId(requestedSessionId)
  }, [requestedSessionId])

  useEffect(() => {
    let cancelled = false
    if (sessionId || !user?.id) return
    createSession(user.id)
      .then((created: unknown) => {
        if (cancelled) return
        const createdSession = asRecord(created)
        const createdId = stringValue(createdSession.id)
        if (!createdId) throw new Error('Session id missing')
        setSessionId(createdId)
        setSession((current) => ({
          ...current,
          id: createdId,
          character: characterKey(createdSession.character_active, current.character),
          vibe: stringValue(createdSession.vibe_selected, current.vibe),
          safe_harbor: safeHarborValue(createdSession.safe_harbor_level, current.safe_harbor),
          trust_delta: numberValue(createdSession.trust_score_delta) ?? current.trust_delta,
          started_at: stringValue(createdSession.started_at, current.started_at),
        }))
        navigate(`/flowquest/${createdId}`, { replace: true })
      })
      .catch(() => {
        if (!cancelled) setSessionId('demo-session')
      })
    return () => {
      cancelled = true
    }
  }, [navigate, sessionId, user?.id])

  // WebSocket connection
  const connectWebSocket = useCallback(() => {
    if (!sessionId) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    const token = getToken()
    if (!token) return
    const ws = new WebSocket(webSocketUrl(`/ws/${sessionId}?token=${encodeURIComponent(token)}`))
    wsRef.current = ws

    ws.onopen = () => setWsStatus('connected')
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'connected') {
          setWsStatus('connected')
        } else if (data.type === 'chunk') {
          const id = streamingMessageIdRef.current || crypto.randomUUID()
          streamingMessageIdRef.current = id
          setIsThinking(false)
          setWsStatus('thinking')
          setMessages((prev) => {
            const existing = prev.find((msg) => msg.id === id)
            if (existing) {
              return prev.map((msg) => (
                msg.id === id ? { ...msg, content: `${msg.content}${data.content || ''}` } : msg
              ))
            }
            return [...prev, {
              id,
              role: 'assistant',
              content: data.content || '',
              timestamp: nowISO(),
              character: session.character,
            }]
          })
        } else if (data.type === 'done') {
          const id = streamingMessageIdRef.current
          if (!id && data.content) {
            setMessages((prev) => [...prev, toChatMessage(data)])
          }
          streamingMessageIdRef.current = null
          setIsThinking(false)
          setWsStatus('connected')
          if (data.trust_delta) {
            setSession((s) => ({ ...s, trust_score: s.trust_score + data.trust_delta, trust_delta: data.trust_delta }))
          }
        } else if (data.type === 'error') {
          streamingMessageIdRef.current = null
          setIsThinking(false)
          setWsStatus('disconnected')
          setMessages((prev) => [...prev, {
            id: crypto.randomUUID(),
            role: 'system',
            content: data.message || 'AI response failed. Please retry.',
            timestamp: nowISO(),
          }])
        } else if (data.type === 'message') {
          const msg: ChatMessage = {
            id: data.id || crypto.randomUUID(),
            role: data.role || 'assistant',
            content: data.content,
            timestamp: data.timestamp || nowISO(),
            character: data.character,
            mask_detected: data.mask_detected,
            action_item: data.action_item,
            trust_delta: data.trust_delta,
          }
          setMessages((prev) => [...prev, msg])
          setIsThinking(false)
          setWsStatus('connected')
          if (data.trust_delta) {
            setSession((s) => ({ ...s, trust_score: s.trust_score + data.trust_delta, trust_delta: data.trust_delta }))
          }
        } else if (data.type === 'thinking') {
          setIsThinking(true)
          setWsStatus('thinking')
        } else if (data.type === 'mask_detected') {
          const alertMsg: ChatMessage = {
            id: crypto.randomUUID(),
            role: 'system',
            content: "Something's off. Your words don't match your vibe.",
            timestamp: nowISO(),
            mask_detected: true,
          }
          setMessages((prev) => [...prev, alertMsg])
        }
      } catch {
        // ignore malformed
      }
    }
    ws.onclose = () => {
      streamingMessageIdRef.current = null
      setWsStatus('disconnected')
    }
    ws.onerror = () => setWsStatus('disconnected')
  }, [session.character, sessionId])

  // Fallback polling
  const pollMessages = useCallback(async () => {
    if (!sessionId) return
    try {
      const history = await getChatHistory(sessionId)
      if (history.length > messages.length) {
        setMessages(history)
      }
    } catch {
      // silent fail
    }
  }, [sessionId, messages.length])

  useEffect(() => {
    if (!sessionId) return
    // Try WebSocket first, fall back to polling
    connectWebSocket()
    const pollInterval = setInterval(() => {
      if (wsStatus === 'disconnected') {
        pollMessages()
        connectWebSocket()
      }
    }, 5000)
    return () => {
      clearInterval(pollInterval)
      wsRef.current?.close()
    }
  }, [connectWebSocket, pollMessages, sessionId, wsStatus])

  // Initial history load
  useEffect(() => {
    if (!sessionId) return
    getChatHistory(sessionId).then((hist) => {
      if (hist.length > 0) {
        setMessages(hist)
        setHasStarted(true)
      }
    })
  }, [sessionId])

  // Auto-scroll
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, autoScroll])

  const handleScroll = () => {
    if (!scrollRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current
    const nearBottom = scrollHeight - scrollTop - clientHeight < 60
    setAutoScroll(nearBottom)
  }

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || !sessionId) return
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text.trim(),
      timestamp: nowISO(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsThinking(true)
    setWsStatus('thinking')
    setHasStarted(true)
    setAutoScroll(true)

    // Try WebSocket first
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'message', content: text.trim(), vibe: session.vibe || undefined }))
    } else {
      // Fallback to HTTP
      try {
        const response = await sendChatMessage(sessionId, text.trim())
        setMessages((prev) => [...prev, response])
        setIsThinking(false)
        setWsStatus('connected')
      } catch {
        setIsThinking(false)
        setWsStatus('disconnected')
      }
    }
  }, [session.vibe, sessionId])

  useEffect(() => {
    const initialMessage = searchParams.get('msg')
    if (!sessionId || !initialMessage || initialMessageSentRef.current) return
    initialMessageSentRef.current = true
    void sendMessage(initialMessage)
  }, [searchParams, sendMessage, sessionId])

  const handleEndSession = async () => {
    try {
      await endSession(sessionId)
    } catch {
      // silent
    }
    setShowEndModal(false)
    navigate('/dashboard')
  }

  const handleStartNewConversation = async () => {
    if (!user?.id) return
    try {
      const fresh = (await startNewSessionApi(user.id)) as { id: string }
      setMessages([])
      setHasStarted(false)
      setSessionId(fresh.id)
      navigate(`/flowquest/${fresh.id}`, { replace: true })
    } catch (err) {
      console.warn('Could not start a new conversation', err)
    }
  }

  const handleDeleteConversation = async () => {
    if (!sessionId) return
    if (!window.confirm('Delete this conversation? The transcript is gone for good. Trust history stays.')) {
      return
    }
    try {
      await deleteSessionApi(sessionId)
    } catch (err) {
      console.warn('Could not delete this conversation', err)
    }
    navigate('/sessions')
  }

  const startRecording = () => {
    setRecording(true)
    setRecordingTime(0)
    recordingTimerRef.current = setInterval(() => {
      setRecordingTime((t) => t + 1)
    }, 1000)
  }

  const stopRecording = () => {
    setRecording(false)
    if (recordingTimerRef.current) clearInterval(recordingTimerRef.current)
    // Simulate voice message
    const duration = recordingTime
    const voiceMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: `[Voice message — ${duration}s]`,
      timestamp: nowISO(),
      voice_url: '#',
    }
    setMessages((prev) => [...prev, voiceMsg])
    setRecordingTime(0)
    setIsThinking(true)
    setTimeout(() => {
      setIsThinking(false)
      const reply: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: "I hear you. Keep talking — I'm listening.",
        timestamp: nowISO(),
        character: session.character,
      }
      setMessages((prev) => [...prev, reply])
    }, 2000)
  }

  const formatTime = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const formatDuration = (sec: number) => `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`

  const quickPrompts = ["Had a rough day", "Need a move", "Just venting"]

  return (
    <div className="fixed inset-0 flex flex-col" style={{ backgroundColor: '#050507' }}>
      {/* ─── Header ─── */}
      <motion.header
        initial={{ y: -72 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="shrink-0 z-20 flex items-center justify-between px-4 h-[72px] border-b"
        style={{ backgroundColor: 'rgba(5,5,7,0.8)', backdropFilter: 'blur(12px)', borderColor: '#2A2A35' }}
      >
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-1 text-xs font-medium transition-colors hover:text-white"
            style={{ color: '#71717A' }}
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Dashboard</span>
          </button>
          <span className="text-[10px] uppercase tracking-wider" style={{ color: '#71717A' }}>FlowQuest</span>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <HexAvatar color={character.color} src={character.avatar} size={40} pulse={isThinking} />
            <div className="absolute -bottom-0.5 -right-0.5">
              <StatusDot status={wsStatus} />
            </div>
          </div>
          <div className="flex flex-col items-start">
            <span className="text-sm font-semibold tracking-wide" style={{ color: character.color }}>{character.name}</span>
            <span className="text-[10px]" style={{ color: '#71717A' }}>{character.role}</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div
            className="px-2.5 py-1 rounded-full text-xs font-medium border"
            style={{ color: '#D4AF37', borderColor: 'rgba(212,175,55,0.3)', backgroundColor: 'rgba(212,175,55,0.08)' }}
          >
            {session.trust_score.toFixed(0)}
          </div>
          <div className="relative">
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="p-2 rounded-full transition-colors"
              style={{ color: '#A1A1AA' }}
            >
              <MoreVertical className="w-5 h-5" />
            </button>
            <AnimatePresence>
              {menuOpen && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="absolute right-0 top-10 w-48 rounded-lg border shadow-lg overflow-hidden z-50"
                  style={{ backgroundColor: '#18181F', borderColor: '#2A2A35' }}
                >
                  <button
                    onClick={() => { void handleStartNewConversation(); setMenuOpen(false) }}
                    className="w-full text-left px-4 py-2.5 text-sm transition-colors hover:bg-white/5"
                    style={{ color: '#D4AF37' }}
                  >
                    Start new conversation
                  </button>
                  <button
                    onClick={() => { setShowEndModal(true); setMenuOpen(false) }}
                    className="w-full text-left px-4 py-2.5 text-sm transition-colors hover:bg-white/5"
                    style={{ color: '#F8F8FA' }}
                  >
                    End Session
                  </button>
                  <button
                    onClick={() => { navigate('/sessions'); setMenuOpen(false) }}
                    className="w-full text-left px-4 py-2.5 text-sm transition-colors hover:bg-white/5"
                    style={{ color: '#A1A1AA' }}
                  >
                    View History
                  </button>
                  <button
                    onClick={() => setDrawerOpen(true)}
                    className="w-full text-left px-4 py-2.5 text-sm transition-colors hover:bg-white/5"
                    style={{ color: '#A1A1AA' }}
                  >
                    Session Info
                  </button>
                  <div className="h-px" style={{ backgroundColor: '#2A2A35' }} />
                  <button
                    onClick={() => { void handleDeleteConversation(); setMenuOpen(false) }}
                    className="w-full text-left px-4 py-2.5 text-sm transition-colors hover:bg-white/5"
                    style={{ color: '#DC2626' }}
                  >
                    Delete this conversation
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </motion.header>

      {/* ─── Message Area ─── */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-4 py-6 space-y-4"
        style={{ backgroundColor: 'rgba(5,5,7,0.6)' }}
      >
        <AnimatePresence initial={false}>
          {!hasStarted && messages.length === 0 && (
            <motion.div
              key="empty"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center h-full gap-4 text-center"
            >
              <HexAvatar color={character.color} src={character.avatar} size={80} />
              <p className="text-lg font-semibold" style={{ color: '#F8F8FA' }}>
                Start your FlowQuest. What's on your mind right now?
              </p>
              <p className="text-sm max-w-xs" style={{ color: '#A1A1AA' }}>
                This is The Dump — say what you mean. No filter. {character.name} is here.
              </p>
              <div className="flex flex-wrap gap-2 justify-center mt-2">
                {quickPrompts.map((p) => (
                  <button
                    key={p}
                    onClick={() => sendMessage(p)}
                    className="px-4 py-2 rounded-full text-sm border transition-colors hover:bg-white/5"
                    style={{ color: '#A1A1AA', borderColor: '#2A2A35' }}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {messages.map((msg, idx) => {
            const isUser = msg.role === 'user'
            const isSystem = msg.role === 'system'
            const showAvatar = msg.role === 'assistant' && messages[idx - 1]?.role !== 'assistant'

            if (isSystem) {
              return (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className={cn(
                    'flex justify-center',
                    msg.mask_detected && 'my-2'
                  )}
                >
                  <div
                    className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border"
                    style={{
                      color: msg.mask_detected ? '#DC2626' : '#D4AF37',
                      borderColor: msg.mask_detected ? 'rgba(220,38,38,0.4)' : 'rgba(212,175,55,0.3)',
                      backgroundColor: msg.mask_detected ? 'rgba(220,38,38,0.08)' : 'rgba(212,175,55,0.06)',
                    }}
                  >
                    {msg.mask_detected && <AlertTriangle className="w-3 h-3" />}
                    {msg.content}
                  </div>
                </motion.div>
              )
            }

            return (
              <motion.div
                key={msg.id}
                initial={isUser ? { opacity: 0, x: 30, scale: 0.95 } : { opacity: 0, x: -30 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                className={cn('flex gap-3', isUser ? 'justify-end' : 'justify-start')}
              >
                {!isUser && showAvatar && (
                  <div className="flex flex-col items-center gap-1 pt-1">
                    <HexAvatar color={character.color} src={character.avatar} size={32} />
                    <span className="text-[10px] font-bold" style={{ color: character.color }}>{character.name}</span>
                  </div>
                )}
                {!isUser && !showAvatar && <div className="w-8" />}

                <div className={cn('flex flex-col max-w-[75%]', isUser && 'items-end')}>
                  <div
                    className={cn(
                      'px-4 py-3 text-sm leading-relaxed',
                      isUser
                        ? 'rounded-tl-2xl rounded-tr-2xl rounded-bl-2xl rounded-br-sm'
                        : 'rounded-tl-sm rounded-tr-2xl rounded-br-2xl rounded-bl-2xl border'
                    )}
                    style={{
                      backgroundColor: isUser ? 'rgba(212,175,55,0.12)' : '#0F0F14',
                      color: '#F8F8FA',
                      borderColor: isUser ? 'rgba(212,175,55,0.2)' : '#2A2A35',
                    }}
                  >
                    {msg.voice_url ? (
                      <div className="flex items-center gap-3">
                        <button className="flex items-center justify-center w-8 h-8 rounded-full" style={{ backgroundColor: '#22222C' }}>
                          <Volume2 className="w-4 h-4" style={{ color: '#D4AF37' }} />
                        </button>
                        <WaveformBars count={20} active={false} color={character.color} />
                        <span className="text-xs" style={{ color: '#71717A' }}>{formatDuration(recordingTime || 5)}</span>
                      </div>
                    ) : (
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    )}
                  </div>
                  <span className="text-[10px] mt-1 px-1" style={{ color: '#71717A' }}>
                    {formatTime(msg.timestamp)}
                  </span>

                  {/* Action item card */}
                  {msg.action_item && msg.action_item.status === 'pending' && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="mt-2 p-3 rounded-lg border-l-[3px]"
                      style={{ backgroundColor: '#0F0F14', borderLeftColor: '#D4AF37', borderColor: '#2A2A35', borderWidth: 1, borderLeftWidth: 3 }}
                    >
                      <p className="text-sm font-medium mb-2" style={{ color: '#F8F8FA' }}>
                        Tactical Action
                      </p>
                      <p className="text-sm mb-3" style={{ color: '#A1A1AA' }}>{msg.action_item.description}</p>
                      <div className="flex gap-2">
                        <button
                          onClick={() => {
                            setMessages((prev) => prev.map((m) =>
                              m.id === msg.id && m.action_item
                                ? { ...m, action_item: { ...m.action_item, status: 'accepted' } }
                                : m
                            ))
                          }}
                          className="px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1"
                          style={{ backgroundColor: '#10B981', color: '#050507' }}
                        >
                          <Check className="w-3 h-3" /> Lock it in
                        </button>
                        <button
                          onClick={() => {
                            setMessages((prev) => prev.map((m) =>
                              m.id === msg.id && m.action_item
                                ? { ...m, action_item: { ...m.action_item, status: 'passed' } }
                                : m
                            ))
                          }}
                          className="px-3 py-1.5 rounded-md text-xs font-medium"
                          style={{ backgroundColor: '#22222C', color: '#A1A1AA' }}
                        >
                          Pass
                        </button>
                      </div>
                    </motion.div>
                  )}
                  {msg.action_item && msg.action_item.status === 'accepted' && (
                    <div className="mt-1 flex items-center gap-1 text-xs" style={{ color: '#10B981' }}>
                      <Check className="w-3 h-3" /> Tactical Action locked in.
                    </div>
                  )}
                  {msg.action_item && msg.action_item.status === 'passed' && (
                    <div className="mt-1 text-xs" style={{ color: '#A1A1AA' }}>No pressure. Next time.</div>
                  )}

                  {/* Trust delta */}
                  {msg.trust_delta !== undefined && msg.trust_delta !== 0 && (
                    <div
                      className="mt-1 flex items-center gap-1 text-xs"
                      style={{ color: msg.trust_delta > 0 ? '#D4AF37' : '#DC2626' }}
                    >
                      {msg.trust_delta > 0 ? '+' : ''}{msg.trust_delta} trust
                    </div>
                  )}
                </div>
              </motion.div>
            )
          })}

          {/* Thinking indicator */}
          {isThinking && (
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-start gap-3"
            >
              <div className="flex flex-col items-center gap-1 pt-1">
                <HexAvatar color={character.color} src={character.avatar} size={32} pulse />
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px]" style={{ color: '#71717A' }}>
                  {character.name} is listening...
                </span>
                <div
                  className="px-3 py-2 rounded-xl border"
                  style={{ backgroundColor: '#0F0F14', borderColor: '#2A2A35' }}
                >
                  <ThinkingDots />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ─── Input Area ─── */}
      <motion.div
        initial={{ y: 100 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
        className="shrink-0 z-20 px-4 py-3 border-t"
        style={{ backgroundColor: 'rgba(5,5,7,0.85)', backdropFilter: 'blur(8px)', borderColor: '#2A2A35' }}
      >
        <div className="flex items-end gap-2">
          <button
            onMouseDown={startRecording}
            onMouseUp={stopRecording}
            onTouchStart={startRecording}
            onTouchEnd={stopRecording}
            className={cn(
              'flex-shrink-0 w-11 h-11 rounded-full flex items-center justify-center transition-all active:scale-95',
              recording ? 'animate-pulse' : 'hover:scale-105'
            )}
            style={{
              backgroundColor: recording ? '#DC2626' : '#22222C',
              color: recording ? '#fff' : '#A1A1AA',
            }}
          >
            {recording ? <Flame className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
          </button>

          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  sendMessage(input)
                }
              }}
              placeholder="Say what you mean. No filter."
              rows={1}
              className="w-full rounded-full px-4 py-2.5 text-sm resize-none outline-none border focus:border-[#00A8E8] pr-10"
              style={{
                backgroundColor: '#18181F',
                color: '#F8F8FA',
                borderColor: '#2A2A35',
                maxHeight: 120,
              }}
            />
            {input.trim().length > 0 && (
              <motion.button
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                onClick={() => sendMessage(input)}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full flex items-center justify-center"
                style={{ backgroundColor: '#D4AF37', color: '#050507' }}
              >
                <Send className="w-4 h-4" />
              </motion.button>
            )}
          </div>
        </div>
        {recording && (
          <div className="flex items-center justify-center gap-2 mt-2">
            <span className="text-xs font-medium animate-pulse" style={{ color: '#DC2626' }}>Recording...</span>
            <span className="text-xs font-mono" style={{ color: '#F8F8FA' }}>{formatDuration(recordingTime)}</span>
          </div>
        )}
      </motion.div>

      {/* ─── Session Drawer ─── */}
      <AnimatePresence>
        {drawerOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setDrawerOpen(false)}
              className="fixed inset-0 z-40 bg-black/50"
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
              className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-[400px] border-l overflow-y-auto"
              style={{ backgroundColor: '#0F0F14', borderColor: '#2A2A35' }}
            >
              <div className="p-6 space-y-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold tracking-wide" style={{ color: '#F8F8FA' }}>SESSION INFO</h3>
                  <button onClick={() => setDrawerOpen(false)} className="p-2 rounded-full hover:bg-white/5" style={{ color: '#A1A1AA' }}>
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <div className="space-y-4">
                  <div className="p-4 rounded-lg border" style={{ backgroundColor: '#18181F', borderColor: '#2A2A35' }}>
                    <div className="flex items-center gap-3 mb-3">
                      <Hash className="w-4 h-4" style={{ color: '#71717A' }} />
                      <span className="text-xs uppercase tracking-wider" style={{ color: '#71717A' }}>Session ID</span>
                    </div>
                    <p className="text-sm font-mono" style={{ color: '#F8F8FA' }}>{session.id}</p>
                  </div>

                  <div className="p-4 rounded-lg border" style={{ backgroundColor: '#18181F', borderColor: '#2A2A35' }}>
                    <div className="flex items-center gap-3 mb-3">
                      <Flame className="w-4 h-4" style={{ color: VIBE_MAP[session.vibe]?.color || '#A1A1AA' }} />
                      <span className="text-xs uppercase tracking-wider" style={{ color: '#71717A' }}>Vibe</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{session.vibe_emoji}</span>
                      <span className="text-sm font-medium capitalize" style={{ color: '#F8F8FA' }}>{session.vibe}</span>
                    </div>
                  </div>

                  <div className="p-4 rounded-lg border" style={{ backgroundColor: '#18181F', borderColor: '#2A2A35' }}>
                    <div className="flex items-center gap-3 mb-3">
                      <MessageSquare className="w-4 h-4" style={{ color: character.color }} />
                      <span className="text-xs uppercase tracking-wider" style={{ color: '#71717A' }}>Character</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <HexAvatar color={character.color} src={character.avatar} size={40} />
                      <div>
                        <p className="text-sm font-bold" style={{ color: character.color }}>{character.name}</p>
                        <p className="text-xs" style={{ color: '#A1A1AA' }}>{character.role}</p>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 rounded-lg border" style={{ backgroundColor: '#18181F', borderColor: '#2A2A35' }}>
                    <div className="flex items-center gap-3 mb-3">
                      <Shield className="w-4 h-4" style={{ color: session.safe_harbor === 'green' ? '#10B981' : session.safe_harbor === 'yellow' ? '#F59E0B' : '#DC2626' }} />
                      <span className="text-xs uppercase tracking-wider" style={{ color: '#71717A' }}>Safe Harbor</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className="w-3 h-3 rounded-full"
                        style={{
                          backgroundColor: session.safe_harbor === 'green' ? '#10B981' : session.safe_harbor === 'yellow' ? '#F59E0B' : '#DC2626',
                        }}
                      />
                      <span className="text-sm font-medium capitalize" style={{ color: '#F8F8FA' }}>{session.safe_harbor}</span>
                    </div>
                  </div>

                  <div className="p-4 rounded-lg border" style={{ backgroundColor: '#18181F', borderColor: '#2A2A35' }}>
                    <div className="flex items-center gap-3 mb-3">
                      <BarChart3 className="w-4 h-4" style={{ color: '#D4AF37' }} />
                      <span className="text-xs uppercase tracking-wider" style={{ color: '#71717A' }}>Trust Delta</span>
                    </div>
                    <p
                      className="text-2xl font-mono font-medium"
                      style={{ color: session.trust_delta >= 0 ? '#D4AF37' : '#DC2626' }}
                    >
                      {session.trust_delta >= 0 ? '+' : ''}{session.trust_delta}
                    </p>
                  </div>

                  <div className="p-4 rounded-lg border" style={{ backgroundColor: '#18181F', borderColor: '#2A2A35' }}>
                    <div className="flex items-center gap-3 mb-3">
                      <Clock className="w-4 h-4" style={{ color: '#71717A' }} />
                      <span className="text-xs uppercase tracking-wider" style={{ color: '#71717A' }}>Started</span>
                    </div>
                    <p className="text-sm" style={{ color: '#F8F8FA' }}>
                      {new Date(session.started_at).toLocaleString()}
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => { setDrawerOpen(false); setShowEndModal(true) }}
                  className="w-full py-3 rounded-lg text-sm font-medium border transition-colors hover:bg-white/5"
                  style={{ color: '#DC2626', borderColor: 'rgba(220,38,38,0.3)' }}
                >
                  End FlowQuest
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ─── End Session Modal ─── */}
      <AnimatePresence>
        {showEndModal && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowEndModal(false)}
              className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4"
            >
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                onClick={(e: React.MouseEvent) => e.stopPropagation()}
                className="w-full max-w-md rounded-xl border p-6 space-y-4"
                style={{ backgroundColor: '#18181F', borderColor: '#2A2A35' }}
              >
                <h3 className="text-xl font-bold" style={{ color: '#F8F8FA' }}>End this FlowQuest?</h3>
                <p className="text-sm" style={{ color: '#A1A1AA' }}>
                  Wrap it up? Here's how this session went.
                </p>

                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: '#0F0F14', borderColor: '#2A2A35' }}>
                    <p className="text-lg font-mono font-medium" style={{ color: '#D4AF37' }}>{messages.filter(m => m.role === 'user').length}</p>
                    <p className="text-[10px] uppercase tracking-wider" style={{ color: '#71717A' }}>Your dumps</p>
                  </div>
                  <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: '#0F0F14', borderColor: '#2A2A35' }}>
                    <p className="text-lg font-mono font-medium" style={{ color: '#D4AF37' }}>{messages.filter(m => m.role === 'assistant').length}</p>
                    <p className="text-[10px] uppercase tracking-wider" style={{ color: '#71717A' }}>Responses</p>
                  </div>
                  <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: '#0F0F14', borderColor: '#2A2A35' }}>
                    <p className="text-lg font-mono font-medium" style={{ color: session.trust_delta >= 0 ? '#D4AF37' : '#DC2626' }}>
                      {session.trust_delta >= 0 ? '+' : ''}{session.trust_delta}
                    </p>
                    <p className="text-[10px] uppercase tracking-wider" style={{ color: '#71717A' }}>Trust delta</p>
                  </div>
                  <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: '#0F0F14', borderColor: '#2A2A35' }}>
                    <p className="text-lg font-mono font-medium" style={{ color: '#F8F8FA' }}>{character.name}</p>
                    <p className="text-[10px] uppercase tracking-wider" style={{ color: '#71717A' }}>Character</p>
                  </div>
                </div>

                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => setShowEndModal(false)}
                    className="flex-1 py-2.5 rounded-lg text-sm font-medium transition-colors hover:bg-white/5"
                    style={{ color: '#A1A1AA', backgroundColor: '#22222C' }}
                  >
                    Keep going
                  </button>
                  <button
                    onClick={handleEndSession}
                    className="flex-1 py-2.5 rounded-lg text-sm font-medium transition-colors"
                    style={{ backgroundColor: '#D4AF37', color: '#050507' }}
                  >
                    End Session
                  </button>
                </div>
              </motion.div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ─── Click outside to close menu ─── */}
      {menuOpen && (
        <div className="fixed inset-0 z-30" onClick={() => setMenuOpen(false)} />
      )}
    </div>
  )
}
