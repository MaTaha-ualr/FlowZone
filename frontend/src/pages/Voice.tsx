import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft,
  Mic,
  Check,
  Loader2,
  Play,
  Pause,
  Volume2,
  ChevronRight,
  X,
  SkipBack,
  SkipForward,
  Speaker,
  Clock,
  Languages,
  Send,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { createSession, getVoiceOptions, synthesizeVoice, transcribeVoice } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'

/* ─── Types ─── */

interface VoiceOption {
  id: string
  name: string
  gender: string
  style: string
  description: string
  preview_url?: string
}

interface VoiceDump {
  id: string
  duration_seconds: number
  date: string
  character: string
  transcript: string
  confidence: number
  audio_url?: string
}

/* ─── Inline API helpers ─── */

type VoiceOptionsResponse = VoiceOption[] | {
  character_mapping?: Record<string, string>
}

async function getVoices(): Promise<VoiceOption[]> {
  try {
    const data = await getVoiceOptions() as VoiceOptionsResponse
    if (Array.isArray(data)) return data
    const mapping = data?.character_mapping || {}
    return Object.keys(mapping).map((character) => ({
      id: character,
      name: characterName(character),
      gender: 'Character',
      style: mapping[character],
      description: `${characterName(character)} voice`,
    }))
  } catch {
    return []
  }
}

async function transcribeAudio(audioBlob: Blob): Promise<{ text: string; confidence: number }> {
  const result = await transcribeVoice(audioBlob)
  return { text: result.text, confidence: result.confidence ?? 0 }
}

async function synthesizeSpeech(text: string, voiceId: string): Promise<{ audio_url: string }> {
  const audioBlob = await synthesizeVoice(text, voiceCharacter(voiceId))
  return { audio_url: URL.createObjectURL(audioBlob) }
}

function characterName(character: string): string {
  if (character === 'challenger') return 'Vex'
  if (character === 'navigator') return 'Yogi'
  if (character === 'straight_shooter') return 'Ace'
  if (character === 'strategist') return 'Nova'
  return character
}

function voiceCharacter(voiceId: string): string {
  if (voiceId.includes('vex')) return 'challenger'
  if (voiceId.includes('yogi')) return 'navigator'
  if (voiceId.includes('ace')) return 'straight_shooter'
  if (voiceId.includes('nova')) return 'strategist'
  return voiceId
}

/* ─── Mock voices ─── */

const MOCK_VOICES: VoiceOption[] = [
  { id: 'vex-v1', name: 'Vex', gender: 'Male', style: 'Direct', description: 'Sharp, urban, no filter' },
  { id: 'yogi-v1', name: 'Yogi', gender: 'Male', style: 'Calm', description: 'Steady, reflective, wise' },
  { id: 'ace-v1', name: 'Ace', gender: 'Male', style: 'Straight', description: 'Direct, tactical, no games' },
  { id: 'nova-v1', name: 'Nova', gender: 'Female', style: 'Strategic', description: 'Calculated, composed, sharp' },
]

const MOCK_DUMPS: VoiceDump[] = [
  {
    id: 'vd-001',
    duration_seconds: 42,
    date: '2024-03-12T21:30:00Z',
    character: 'Vex',
    transcript: "Man, Trey kept pushing me and I just... I don't even know why I reacted like that.",
    confidence: 0.94,
  },
  {
    id: 'vd-002',
    duration_seconds: 75,
    date: '2024-03-11T20:15:00Z',
    character: 'Yogi',
    transcript: "I don't even know what I'm doing anymore. Everything feels like it's slipping.",
    confidence: 0.91,
  },
  {
    id: 'vd-003',
    duration_seconds: 28,
    date: '2024-03-10T19:45:00Z',
    character: 'Yogi',
    transcript: "Practice was good today. Coach said my footwork is getting better.",
    confidence: 0.96,
  },
]

/* ─── Utils ─── */

function fmtDuration(sec: number) {
  const m = Math.floor(sec / 60)
  const s = String(sec % 60).padStart(2, '0')
  return `${m}:${s}`
}
function fmtDate(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

/* ─── Canvas Waveform Visualizer ─── */

function CanvasWaveform({ active, color = '#DC2626', barCount = 48, height = 60 }: {
  active: boolean
  color?: string
  barCount?: number
  height?: number
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animRef = useRef<number>(0)

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const w = canvas.clientWidth
    const h = height
    canvas.width = w * dpr
    canvas.height = h * dpr
    ctx.scale(dpr, dpr)

    const barW = Math.max(2, (w - (barCount - 1) * 2) / barCount)
    const gap = 2

    ctx.clearRect(0, 0, w, h)

    for (let i = 0; i < barCount; i++) {
      const x = i * (barW + gap)
      let barH: number
      if (active) {
        barH = Math.random() * h * 0.8 + h * 0.1
      } else {
        barH = h * 0.15
      }
      const y = (h - barH) / 2

      const gradient = ctx.createLinearGradient(0, y + barH, 0, y)
      gradient.addColorStop(0, color)
      gradient.addColorStop(1, `${color}40`)

      ctx.fillStyle = gradient
      ctx.beginPath()
      ctx.roundRect(x, y, barW, barH, barW / 2)
      ctx.fill()
    }

    if (active) {
      animRef.current = requestAnimationFrame(draw)
    }
  }, [active, color, barCount, height])

  useEffect(() => {
    if (active) {
      animRef.current = requestAnimationFrame(draw)
    } else {
      cancelAnimationFrame(animRef.current)
      draw()
    }
    return () => cancelAnimationFrame(animRef.current)
  }, [active, draw])

  return (
    <canvas
      ref={canvasRef}
      style={{ width: '100%', height }}
      className="w-full"
    />
  )
}

/* ─── Main Page ─── */

export default function Voice() {
  const navigate = useNavigate()
  const { user } = useAuth()

  const [recordState, setRecordState] = useState<'idle' | 'recording' | 'processing' | 'complete'>('idle')
  const [recordingTime, setRecordingTime] = useState(0)
  const [transcript, setTranscript] = useState('')
  const [confidence, setConfidence] = useState(0)
  const [voices, setVoices] = useState<VoiceOption[]>(MOCK_VOICES)
  const [selectedVoice, setSelectedVoice] = useState<VoiceOption>(MOCK_VOICES[0])
  const [showVoicePicker, setShowVoicePicker] = useState(false)
  const [recentDumps, setRecentDumps] = useState<VoiceDump[]>(MOCK_DUMPS)
  const [playingId, setPlayingId] = useState<string | null>(null)
  const [playbackProgress, setPlaybackProgress] = useState(0)
  const [playbackSpeed, setPlaybackSpeed] = useState(1)
  const [autoSend, setAutoSend] = useState(true)
  const [saveTranscripts, setSaveTranscripts] = useState(true)
  const [ttsPlaying, setTtsPlaying] = useState(false)
  const [ttsAudio, setTtsAudio] = useState<HTMLAudioElement | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const playbackTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const canvasContainerRef = useRef<HTMLDivElement>(null)

  // Load voices
  useEffect(() => {
    getVoices().then((v) => { if (v.length > 0) setVoices(v) }).catch(() => {})
  }, [])

  const startRecording = async () => {
    setRecordState('recording')
    setRecordingTime(0)
    setTranscript('')
    setConfidence(0)
    chunksRef.current = []

    timerRef.current = setInterval(() => {
      setRecordingTime((t) => t + 1)
    }, 1000)

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      mediaRecorderRef.current = recorder
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        handleTranscribe(blob)
        stream.getTracks().forEach((t) => t.stop())
      }
      recorder.start()
    } catch {
      // Fallback: simulate recording
      setTimeout(() => {
        stopRecording()
      }, 3000)
    }
  }

  const stopRecording = () => {
    if (timerRef.current) clearInterval(timerRef.current)
    setRecordState('processing')

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    } else {
      // Fallback simulation
      setTimeout(() => {
        const mockTranscript = "Man, I don't even know where to start. Everything's just... a lot right now."
        setTranscript(mockTranscript)
        setConfidence(0.92)
        setRecordState('complete')
        const newDump: VoiceDump = {
          id: crypto.randomUUID(),
          duration_seconds: recordingTime || 5,
          date: new Date().toISOString(),
          character: selectedVoice.name,
          transcript: mockTranscript,
          confidence: 0.92,
        }
        setRecentDumps((prev) => [newDump, ...prev])
      }, 2000)
    }
  }

  const handleTranscribe = async (blob: Blob) => {
    try {
      const result = await transcribeAudio(blob)
      setTranscript(result.text)
      setConfidence(result.confidence)
      setRecordState('complete')
      const newDump: VoiceDump = {
        id: crypto.randomUUID(),
        duration_seconds: recordingTime,
        date: new Date().toISOString(),
        character: selectedVoice.name,
        transcript: result.text,
        confidence: result.confidence,
      }
      setRecentDumps((prev) => [newDump, ...prev])
    } catch {
      const fallback = "Couldn't process that. Try again."
      setTranscript(fallback)
      setConfidence(0)
      setRecordState('complete')
    }
  }

  const playDump = (dump: VoiceDump) => {
    if (playingId === dump.id) {
      // Pause
      setPlayingId(null)
      if (playbackTimerRef.current) clearInterval(playbackTimerRef.current)
      setPlaybackProgress(0)
      return
    }
    setPlayingId(dump.id)
    setPlaybackProgress(0)
    let prog = 0
    playbackTimerRef.current = setInterval(() => {
      prog += 1 / (dump.duration_seconds / playbackSpeed)
      if (prog >= 1) {
        setPlaybackProgress(1)
        setPlayingId(null)
        if (playbackTimerRef.current) clearInterval(playbackTimerRef.current)
      } else {
        setPlaybackProgress(prog)
      }
    }, 1000)
  }

  const playTTS = async (text: string) => {
    if (ttsPlaying && ttsAudio) {
      ttsAudio.pause()
      setTtsPlaying(false)
      return
    }
    try {
      const result = await synthesizeSpeech(text, selectedVoice.id)
      const audio = new Audio(result.audio_url)
      setTtsAudio(audio)
      audio.onended = () => setTtsPlaying(false)
      audio.onerror = () => setTtsPlaying(false)
      await audio.play()
      setTtsPlaying(true)
    } catch {
      // Fallback: use speech synthesis
      if ('speechSynthesis' in window) {
        const utter = new SpeechSynthesisUtterance(text)
        utter.rate = 1
        utter.onend = () => setTtsPlaying(false)
        window.speechSynthesis.speak(utter)
        setTtsPlaying(true)
      }
    }
  }

  const sendToChat = async () => {
    if (!transcript) return
    try {
      if (user?.id) {
        const session = await createSession(user.id) as { id: string }
        navigate(`/flowquest/${session.id}?msg=${encodeURIComponent(transcript)}`)
        return
      }
    } catch {
      // keep the visual prototype path available if the API cannot create a session
    }
    navigate(`/flowquest?msg=${encodeURIComponent(transcript)}`)
  }

  return (
    <div className="min-h-screen pb-24" style={{ backgroundColor: '#050507' }}>
      <div className="max-w-[640px] mx-auto px-4 py-8 space-y-8">
        {/* ─── Header ─── */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-1 text-xs font-medium transition-colors hover:text-white mb-4"
            style={{ color: '#71717A' }}
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Dashboard</span>
          </button>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-wide uppercase" style={{ color: '#F8F8FA', fontFamily: 'Bebas Neue, sans-serif' }}>
            VOICE
          </h1>
          <p className="text-sm mt-1" style={{ color: '#A1A1AA' }}>
            Speak your truth. However it comes out.
          </p>
        </motion.div>

        {/* ─── Voice Recorder Card ─── */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="rounded-xl border p-6 sm:p-10 text-center space-y-6"
          style={{ backgroundColor: '#0F0F14', borderColor: '#2A2A35' }}
        >
          {/* Record Button */}
          <div className="flex justify-center">
            <div className="relative">
              {/* Pulsing rings when recording */}
              {recordState === 'recording' && (
                <>
                  <motion.span
                    className="absolute inset-0 rounded-full"
                    style={{ backgroundColor: 'rgba(220,38,38,0.15)' }}
                    animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  />
                  <motion.span
                    className="absolute inset-0 rounded-full"
                    style={{ backgroundColor: 'rgba(220,38,38,0.1)' }}
                    animate={{ scale: [1, 1.8, 1], opacity: [0.3, 0, 0.3] }}
                    transition={{ duration: 1.5, repeat: Infinity, delay: 0.3 }}
                  />
                </>
              )}

              <button
                onMouseDown={() => recordState === 'idle' && startRecording()}
                onMouseUp={() => recordState === 'recording' && stopRecording()}
                onTouchStart={() => recordState === 'idle' && startRecording()}
                onTouchEnd={() => recordState === 'recording' && stopRecording()}
                className={cn(
                  'relative w-28 h-28 sm:w-32 sm:h-32 rounded-full flex items-center justify-center transition-all active:scale-95',
                  recordState === 'idle' && 'hover:scale-105',
                  recordState === 'recording' && 'animate-pulse'
                )}
                style={{
                  backgroundColor:
                    recordState === 'idle' ? '#22222C'
                    : recordState === 'recording' ? '#DC2626'
                    : recordState === 'processing' ? '#00A8E8'
                    : '#10B981',
                  color: '#fff',
                }}
              >
                {recordState === 'idle' && <Mic className="w-10 h-10 sm:w-12 sm:h-12" style={{ color: '#A1A1AA' }} />}
                {recordState === 'recording' && <Mic className="w-10 h-10 sm:w-12 sm:h-12" />}
                {recordState === 'processing' && <Loader2 className="w-10 h-10 sm:w-12 sm:h-12 animate-spin" />}
                {recordState === 'complete' && <Check className="w-10 h-10 sm:w-12 sm:h-12" />}
              </button>
            </div>
          </div>

          {/* Status label */}
          <div>
            {recordState === 'idle' && (
              <p className="text-sm font-medium" style={{ color: '#A1A1AA' }}>
                Hold to record. Release to send.
              </p>
            )}
            {recordState === 'recording' && (
              <p className="text-lg font-semibold animate-pulse" style={{ color: '#DC2626' }}>
                Recording...
              </p>
            )}
            {recordState === 'processing' && (
              <p className="text-lg font-semibold" style={{ color: '#00A8E8' }}>
                Processing...
              </p>
            )}
            {recordState === 'complete' && (
              <p className="text-lg font-semibold" style={{ color: '#10B981' }}>
                Done
              </p>
            )}
          </div>

          {/* Timer */}
          {recordState !== 'idle' && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-3xl font-mono font-medium"
              style={{ color: '#F8F8FA' }}
            >
              {fmtDuration(recordingTime)}
            </motion.p>
          )}

          {/* Waveform */}
          <div ref={canvasContainerRef} className="w-full">
            <CanvasWaveform
              active={recordState === 'recording'}
              color={recordState === 'recording' ? '#DC2626' : '#00A8E8'}
              barCount={48}
              height={60}
            />
          </div>
        </motion.div>

        {/* ─── Transcription ─── */}
        <AnimatePresence>
          {(transcript || recordState === 'processing') && (
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              className="rounded-xl border p-5 space-y-3"
              style={{ backgroundColor: '#0F0F14', borderColor: '#2A2A35' }}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs uppercase tracking-wider font-semibold" style={{ color: '#71717A' }}>Transcription</span>
                {confidence > 0 && (
                  <span className="text-xs font-mono" style={{ color: confidence > 0.9 ? '#10B981' : '#F59E0B' }}>
                    {Math.round(confidence * 100)}% confidence
                  </span>
                )}
              </div>
              <p className="text-sm leading-relaxed italic" style={{ color: '#F8F8FA' }}>
                {recordState === 'processing' ? 'Transcribing your voice dump...' : `"${transcript}"`}
              </p>
              {recordState === 'complete' && (
                <div className="flex gap-2 pt-1">
                  <button
                    onClick={() => playTTS(transcript)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors hover:bg-white/5"
                    style={{ color: '#D4AF37', borderColor: '#2A2A35' }}
                  >
                    <Volume2 className="w-3 h-3" />
                    {ttsPlaying ? 'Stop' : 'Play Back'}
                  </button>
                  <button
                    onClick={sendToChat}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
                    style={{ backgroundColor: '#D4AF37', color: '#050507' }}
                  >
                    <Send className="w-3 h-3" />
                    Send to FlowQuest
                  </button>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* ─── Voice Settings ─── */}
        <motion.div
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="rounded-xl border p-5 space-y-4"
          style={{ backgroundColor: '#0F0F14', borderColor: '#2A2A35' }}
        >
          <h4 className="text-sm font-semibold" style={{ color: '#F8F8FA' }}>SETTINGS</h4>

          {/* Input Language */}
          <div className="flex items-center justify-between py-2 border-b" style={{ borderColor: '#2A2A35' }}>
            <div className="flex items-center gap-3">
              <Languages className="w-4 h-4" style={{ color: '#A1A1AA' }} />
              <div>
                <p className="text-sm" style={{ color: '#F8F8FA' }}>English (US)</p>
                <p className="text-xs" style={{ color: '#71717A' }}>We detect Memphis accent patterns. No judgment.</p>
              </div>
            </div>
            <ChevronRight className="w-4 h-4" style={{ color: '#71717A' }} />
          </div>

          {/* Character Voice */}
          <button
            onClick={() => setShowVoicePicker(true)}
            className="w-full flex items-center justify-between py-2 border-b group"
            style={{ borderColor: '#2A2A35' }}
          >
            <div className="flex items-center gap-3">
              <Speaker className="w-4 h-4" style={{ color: '#A1A1AA' }} />
              <div className="text-left">
                <p className="text-sm" style={{ color: '#F8F8FA' }}>
                  {selectedVoice.name} — {selectedVoice.gender}, {selectedVoice.style}
                </p>
                <p className="text-xs" style={{ color: '#71717A' }}>{selectedVoice.description}</p>
              </div>
            </div>
            <ChevronRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" style={{ color: '#71717A' }} />
          </button>

          {/* Auto-Send */}
          <div className="flex items-center justify-between py-2 border-b" style={{ borderColor: '#2A2A35' }}>
            <div>
              <p className="text-sm" style={{ color: '#F8F8FA' }}>Auto-Send</p>
              <p className="text-xs" style={{ color: '#71717A' }}>Send voice immediately after recording</p>
            </div>
            <button
              onClick={() => setAutoSend(!autoSend)}
              className={cn(
                'w-11 h-6 rounded-full transition-colors relative',
                autoSend ? 'bg-[#D4AF37]' : 'bg-[#2A2A35]'
              )}
            >
              <span
                className={cn(
                  'absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform',
                  autoSend ? 'left-[22px]' : 'left-0.5'
                )}
              />
            </button>
          </div>

          {/* Save Transcripts */}
          <div className="flex items-center justify-between py-2">
            <div>
              <p className="text-sm" style={{ color: '#F8F8FA' }}>Save Transcripts</p>
              <p className="text-xs" style={{ color: '#71717A' }}>Keep text versions of your voice dumps</p>
            </div>
            <button
              onClick={() => setSaveTranscripts(!saveTranscripts)}
              className={cn(
                'w-11 h-6 rounded-full transition-colors relative',
                saveTranscripts ? 'bg-[#D4AF37]' : 'bg-[#2A2A35]'
              )}
            >
              <span
                className={cn(
                  'absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform',
                  saveTranscripts ? 'left-[22px]' : 'left-0.5'
                )}
              />
            </button>
          </div>
        </motion.div>

        {/* ─── Recent Voice Dumps ─── */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="rounded-xl border p-5 space-y-4"
          style={{ backgroundColor: '#0F0F14', borderColor: '#2A2A35' }}
        >
          <h3 className="text-lg font-bold tracking-wide" style={{ color: '#F8F8FA', fontFamily: 'Bebas Neue, sans-serif' }}>
            RECENT DUMPS
          </h3>

          {recentDumps.length === 0 ? (
            <div className="text-center py-8">
              <Mic className="w-12 h-12 mx-auto mb-3" style={{ color: '#2A2A35' }} />
              <p className="text-sm font-medium" style={{ color: '#F8F8FA' }}>No voice dumps yet.</p>
              <p className="text-xs mt-1" style={{ color: '#A1A1AA' }}>
                Hold the record button and say what you mean.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <AnimatePresence>
                {recentDumps.map((dump, idx) => (
                  <motion.div
                    key={dump.id}
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -15 }}
                    transition={{ delay: idx * 0.08 }}
                    className="flex items-center gap-3 p-3 rounded-lg border transition-colors hover:bg-white/[0.02]"
                    style={{ borderColor: '#2A2A35' }}
                  >
                    {/* Mini waveform */}
                    <div className="w-[60px] shrink-0">
                      <CanvasWaveform active={false} color="#00A8E8" barCount={12} height={24} />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 text-xs" style={{ color: '#71717A' }}>
                        <Clock className="w-3 h-3" />
                        {fmtDuration(dump.duration_seconds)}
                        <span>·</span>
                        <span>{fmtDate(dump.date)}</span>
                        <span>·</span>
                        <span style={{ color: '#6C5CE7' }}>→ {dump.character}</span>
                      </div>
                      <p className="text-sm italic line-clamp-1 mt-0.5" style={{ color: '#A1A1AA' }}>
                        "{dump.transcript}"
                      </p>
                    </div>

                    <button
                      onClick={() => playDump(dump)}
                      className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-colors hover:bg-white/5"
                      style={{ backgroundColor: '#22222C' }}
                    >
                      {playingId === dump.id ? (
                        <Pause className="w-4 h-4" style={{ color: '#D4AF37' }} />
                      ) : (
                        <Play className="w-4 h-4" style={{ color: '#A1A1AA' }} />
                      )}
                    </button>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </motion.div>
      </div>

      {/* ─── Playback Bottom Sheet ─── */}
      <AnimatePresence>
        {playingId && (
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="fixed bottom-0 left-0 right-0 z-50 rounded-t-xl border-t p-5 space-y-4"
            style={{ backgroundColor: '#18181F', borderColor: '#2A2A35' }}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase tracking-wider" style={{ color: '#71717A' }}>Now Playing</span>
              <button
                onClick={() => { setPlayingId(null); setPlaybackProgress(0); if (playbackTimerRef.current) clearInterval(playbackTimerRef.current) }}
                style={{ color: '#A1A1AA' }}
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <CanvasWaveform active={!!playingId} color="#00A8E8" barCount={48} height={48} />

            <div className="flex items-center gap-3">
              <span className="text-xs font-mono" style={{ color: '#71717A' }}>
                {fmtDuration(Math.floor(playbackProgress * (recentDumps.find(d => d.id === playingId)?.duration_seconds || 0)))}
              </span>
              <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ backgroundColor: '#2A2A35' }}>
                <motion.div
                  className="h-full rounded-full"
                  style={{ backgroundColor: '#D4AF37', width: `${playbackProgress * 100}%` }}
                />
              </div>
              <span className="text-xs font-mono" style={{ color: '#71717A' }}>
                {fmtDuration(recentDumps.find(d => d.id === playingId)?.duration_seconds || 0)}
              </span>
            </div>

            <div className="flex items-center justify-center gap-6">
              <button className="p-2 rounded-full transition-colors hover:bg-white/5" style={{ color: '#A1A1AA' }}>
                <SkipBack className="w-5 h-5" />
              </button>
              <button
                onClick={() => {
                  const dump = recentDumps.find(d => d.id === playingId)
                  if (dump) playDump(dump)
                }}
                className="w-14 h-14 rounded-full flex items-center justify-center"
                style={{ backgroundColor: '#D4AF37', color: '#050507' }}
              >
                {playingId ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6" />}
              </button>
              <button className="p-2 rounded-full transition-colors hover:bg-white/5" style={{ color: '#A1A1AA' }}>
                <SkipForward className="w-5 h-5" />
              </button>
            </div>

            <div className="flex justify-center gap-2">
              {[1, 1.5, 2].map((speed) => (
                <button
                  key={speed}
                  onClick={() => setPlaybackSpeed(speed)}
                  className="px-3 py-1 rounded-full text-xs font-medium transition-colors"
                  style={{
                    backgroundColor: playbackSpeed === speed ? '#D4AF37' : '#22222C',
                    color: playbackSpeed === speed ? '#050507' : '#A1A1AA',
                  }}
                >
                  {speed}x
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── Voice Picker Modal ─── */}
      <AnimatePresence>
        {showVoicePicker && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowVoicePicker(false)}
              className="fixed inset-0 z-50 bg-black/60 flex items-end sm:items-center justify-center p-0 sm:p-4"
            >
              <motion.div
                initial={{ y: '100%', scale: 0.95 }}
                animate={{ y: 0, scale: 1 }}
                exit={{ y: '100%', scale: 0.95 }}
                onClick={(e: React.MouseEvent) => e.stopPropagation()}
                className="w-full sm:max-w-md sm:rounded-xl rounded-t-xl border p-5 space-y-4 max-h-[80vh] overflow-y-auto"
                style={{ backgroundColor: '#18181F', borderColor: '#2A2A35' }}
              >
                <h4 className="text-lg font-bold tracking-wide" style={{ color: '#F8F8FA', fontFamily: 'Bebas Neue, sans-serif' }}>
                  PICK A VOICE
                </h4>

                <div className="space-y-2">
                  {voices.map((voice, idx) => (
                    <motion.button
                      key={voice.id}
                      initial={{ opacity: 0, x: 10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.05 }}
                      onClick={() => setSelectedVoice(voice)}
                      className={cn(
                        'w-full flex items-center gap-3 p-3 rounded-lg border transition-colors text-left',
                        selectedVoice.id === voice.id ? 'border-[#D4AF37]' : 'border-[#2A2A35] hover:bg-white/5'
                      )}
                      style={{ backgroundColor: selectedVoice.id === voice.id ? 'rgba(212,175,55,0.06)' : '#0F0F14' }}
                    >
                      <div className="flex-1">
                        <p className="text-sm font-medium" style={{ color: '#F8F8FA' }}>
                          {voice.name} — {voice.gender}, {voice.style}
                        </p>
                        <p className="text-xs" style={{ color: '#71717A' }}>{voice.description}</p>
                      </div>
                      <button
                        onClick={(e) => { e.stopPropagation(); playTTS(`This is ${voice.name}. I'm here to listen.`) }}
                        className="p-2 rounded-full transition-colors hover:bg-white/5"
                        style={{ color: '#A1A1AA' }}
                      >
                        <Speaker className="w-4 h-4" />
                      </button>
                      {selectedVoice.id === voice.id && (
                        <Check className="w-5 h-5" style={{ color: '#D4AF37' }} />
                      )}
                    </motion.button>
                  ))}
                </div>

                <button
                  onClick={() => setShowVoicePicker(false)}
                  className="w-full py-2.5 rounded-lg text-sm font-medium transition-colors"
                  style={{ backgroundColor: '#D4AF37', color: '#050507' }}
                >
                  Done
                </button>
              </motion.div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
