import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Mic,
  Square,
  Loader2,
  Volume2,
  VolumeX,
  AlertTriangle,
  RefreshCw,
  Trash2,
} from "lucide-react";
import {
  createSession,
  getCurrentSession,
  sendChatMessage,
  synthesizeVoice,
  transcribeVoice,
  deleteSession,
  startNewSession,
} from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import type { CharacterEnum, SessionResponse } from "@/types";

/* ─── Character display info ─── */

const CHARACTER_DISPLAY: Record<CharacterEnum, { name: string; tagline: string; color: string }> = {
  challenger: { name: "VEX", tagline: "Direct. No filter.", color: "#DC2626" },
  navigator: { name: "YOGI", tagline: "Steady. Here to listen.", color: "#00A8E8" },
  straight_shooter: { name: "ACE", tagline: "Get to the move.", color: "#10B981" },
  strategist: { name: "NOVA", tagline: "Long game.", color: "#6C5CE7" },
  ace: { name: "ACE", tagline: "Get to the move.", color: "#10B981" },
  nova: { name: "NOVA", tagline: "Long game.", color: "#6C5CE7" },
};

/* ─── Status types ─── */

type Status =
  | "idle"
  | "recording"
  | "transcribing"
  | "thinking"
  | "speaking"
  | "error";

interface Turn {
  id: string;
  role: "user" | "ai";
  text: string;
  audioUrl?: string;
}

/* ─── Live waveform during recording ─── */

function Waveform({ stream, active }: { stream: MediaStream | null; active: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    if (!stream || !active) {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      return;
    }
    const audioCtx = new AudioContext();
    ctxRef.current = audioCtx;
    const source = audioCtx.createMediaStreamSource(stream);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    analyserRef.current = analyser;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const draw = () => {
      const ctx = canvas.getContext("2d");
      if (!ctx || !analyserRef.current) return;
      const bufferLength = analyserRef.current.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      analyserRef.current.getByteFrequencyData(dataArray);

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const bars = 48;
      const barW = canvas.width / bars;
      const slice = Math.floor(bufferLength / bars);
      for (let i = 0; i < bars; i++) {
        let sum = 0;
        for (let j = 0; j < slice; j++) sum += dataArray[i * slice + j] || 0;
        const avg = sum / slice;
        const h = Math.max(4, (avg / 255) * canvas.height);
        const x = i * barW;
        const y = (canvas.height - h) / 2;
        const grad = ctx.createLinearGradient(0, y, 0, y + h);
        grad.addColorStop(0, "#D4AF37");
        grad.addColorStop(1, "#00A8E8");
        ctx.fillStyle = grad;
        ctx.fillRect(x + 1, y, barW - 2, h);
      }
      rafRef.current = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      audioCtx.close().catch(() => undefined);
    };
  }, [stream, active]);

  return <canvas ref={canvasRef} width={400} height={80} className="w-full h-20 rounded-xl bg-fz-elevated" />;
}

/* ─── Page ─── */

export default function Voice() {
  const { user } = useAuth();

  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState<string>("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [muted, setMuted] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const turnsEndRef = useRef<HTMLDivElement | null>(null);

  const character: CharacterEnum = user?.current_character ?? "navigator";
  const display = CHARACTER_DISPLAY[character] ?? CHARACTER_DISPLAY.navigator;

  /* ── Session bootstrap ── */
  useEffect(() => {
    if (!user?.id) return;
    let cancelled = false;
    (async () => {
      try {
        const current = (await getCurrentSession(user.id).catch(() => null)) as SessionResponse | null;
        if (current && !cancelled) {
          setSessionId(current.id);
          return;
        }
        const created = (await createSession(user.id)) as SessionResponse;
        if (!cancelled) setSessionId(created.id);
      } catch (err) {
        if (!cancelled) {
          setErrorMsg(err instanceof Error ? err.message : "Couldn't start a session.");
          setStatus("error");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user?.id]);

  /* ── Auto-scroll to latest turn ── */
  useEffect(() => {
    turnsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns.length, status]);

  /* ── Cleanup on unmount ── */
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      stream?.getTracks().forEach((t) => t.stop());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── Record → Transcribe → Chat → Speak round-trip ── */

  const playAi = useCallback(
    async (text: string, turnId: string) => {
      try {
        const audioBlob = await synthesizeVoice(text, character);
        const url = URL.createObjectURL(audioBlob);
        setTurns((prev) => prev.map((t) => (t.id === turnId ? { ...t, audioUrl: url } : t)));

        if (muted) {
          setStatus("idle");
          return;
        }
        const audio = new Audio(url);
        audioRef.current = audio;
        audio.onended = () => setStatus("idle");
        audio.onerror = () => setStatus("idle");
        await audio.play();
      } catch (err) {
        console.warn("TTS failed", err);
        setStatus("idle");
      }
    },
    [character, muted],
  );

  const handleAudio = useCallback(
    async (audioBlob: Blob) => {
      if (!sessionId) {
        setErrorMsg("No active session.");
        setStatus("error");
        return;
      }

      // 1. Transcribe
      setStatus("transcribing");
      let userText = "";
      try {
        const result = await transcribeVoice(audioBlob);
        userText = (result.text || "").trim();
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : "Transcription failed.");
        setStatus("error");
        return;
      }
      if (!userText) {
        setErrorMsg("Didn't catch that. Try again.");
        setStatus("error");
        return;
      }
      const userTurn: Turn = { id: `u-${Date.now()}`, role: "user", text: userText };
      setTurns((prev) => [...prev, userTurn]);

      // 2. Send to chat → get AI reply
      setStatus("thinking");
      let aiText = "";
      try {
        const reply = (await sendChatMessage(sessionId, userText)) as { content: string };
        aiText = reply?.content ?? "";
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : "AI reply failed.");
        setStatus("error");
        return;
      }
      if (!aiText) {
        setErrorMsg("No reply. Try again.");
        setStatus("error");
        return;
      }
      const aiTurnId = `a-${Date.now()}`;
      setTurns((prev) => [...prev, { id: aiTurnId, role: "ai", text: aiText }]);

      // 3. Speak the reply
      setStatus("speaking");
      await playAi(aiText, aiTurnId);
    },
    [sessionId, playAi],
  );

  const startRecording = useCallback(async () => {
    setErrorMsg("");
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setStatus("recording");
    setRecordingTime(0);
    chunksRef.current = [];

    try {
      const ms = await navigator.mediaDevices.getUserMedia({ audio: true });
      setStream(ms);

      const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "";

      const recorder = mime ? new MediaRecorder(ms, { mimeType: mime }) : new MediaRecorder(ms);
      recorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: chunksRef.current[0]?.type || "audio/webm" });
        ms.getTracks().forEach((t) => t.stop());
        setStream(null);
        await handleAudio(blob);
      };

      recorder.start();
      timerRef.current = setInterval(() => setRecordingTime((t) => t + 1), 1000);
    } catch (err) {
      setErrorMsg(
        err instanceof Error && err.name === "NotAllowedError"
          ? "Microphone access denied. Allow it in your browser settings."
          : "Couldn't access the microphone.",
      );
      setStatus("error");
    }
  }, [handleAudio]);

  const stopRecording = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    const r = recorderRef.current;
    if (r && r.state !== "inactive") r.stop();
  }, []);

  const replay = (url?: string) => {
    if (!url) return;
    if (audioRef.current) audioRef.current.pause();
    const audio = new Audio(url);
    audioRef.current = audio;
    audio.play().catch(() => undefined);
  };

  const handleNewConversation = useCallback(async () => {
    if (!user?.id) return;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    try {
      const fresh = (await startNewSession(user.id)) as { id: string };
      setSessionId(fresh.id);
      setTurns([]);
      setStatus("idle");
      setErrorMsg("");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Could not start a new conversation.");
      setStatus("error");
    }
  }, [user?.id]);

  const handleDeleteConversation = useCallback(async () => {
    if (!sessionId || !user?.id) return;
    if (
      !window.confirm(
        "Delete this conversation? The transcript is gone for good. Trust history stays.",
      )
    ) {
      return;
    }
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    try {
      await deleteSession(sessionId);
    } catch (err) {
      console.warn("Could not delete this conversation", err);
    }
    // After deleting, start a brand-new session so the page is usable.
    try {
      const fresh = (await startNewSession(user.id)) as { id: string };
      setSessionId(fresh.id);
    } catch {
      setSessionId(null);
    }
    setTurns([]);
    setStatus("idle");
    setErrorMsg("");
  }, [sessionId, user?.id]);

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`;

  const buttonState =
    status === "recording"
      ? { label: "Tap to stop", color: "bg-safe-red animate-pulse", icon: <Square className="w-7 h-7" /> }
      : status === "transcribing" || status === "thinking" || status === "speaking"
      ? { label: status === "transcribing" ? "Hearing you out…" : status === "thinking" ? `${display.name} is thinking…` : `${display.name} is speaking…`, color: "bg-fz-overlay", icon: <Loader2 className="w-7 h-7 animate-spin" /> }
      : { label: "Tap to talk", color: "bg-fz-gold hover:bg-fz-gold-bright", icon: <Mic className="w-7 h-7 text-text-inverse" /> };

  const canTap = status === "idle" || status === "recording" || status === "error";

  return (
    <div className="min-h-screen bg-fz-base text-text-primary -mx-4 md:-mx-8 -mt-6">
      <div className="max-w-2xl mx-auto px-4 py-6 flex flex-col" style={{ minHeight: "calc(100vh - 4rem)" }}>
        {/* Header */}
        <motion.header
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between mb-4"
        >
          <div>
            <h1 className="font-display text-4xl tracking-wider" style={{ color: display.color }}>
              {display.name} AI
            </h1>
            <p className="text-xs text-text-muted">{display.tagline}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setMuted((m) => !m)}
              className="p-2 rounded-lg border border-fz-border text-text-secondary hover:text-text-primary"
              title={muted ? "Unmute auto-play" : "Mute auto-play"}
            >
              {muted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
            </button>
            <button
              onClick={handleNewConversation}
              disabled={status === "recording" || status === "transcribing" || status === "thinking"}
              className="p-2 rounded-lg border border-fz-border text-text-secondary hover:text-fz-gold disabled:opacity-40 disabled:cursor-not-allowed"
              title="Start new conversation"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
            <button
              onClick={handleDeleteConversation}
              disabled={!sessionId || status === "recording" || status === "transcribing" || status === "thinking"}
              className="p-2 rounded-lg border border-fz-border text-text-secondary hover:text-safe-red disabled:opacity-40 disabled:cursor-not-allowed"
              title="Delete this conversation"
            >
              <Trash2 className="w-5 h-5" />
            </button>
          </div>
        </motion.header>

        {/* Conversation */}
        <div className="flex-1 overflow-y-auto rounded-2xl bg-fz-elevated border border-fz-border p-4 space-y-3 mb-4">
          {turns.length === 0 && status === "idle" && (
            <div className="h-full flex flex-col items-center justify-center text-center text-text-muted py-12">
              <Mic className="w-10 h-10 mb-3 text-fz-gold opacity-60" />
              <p className="text-sm">Tap the mic and just talk.</p>
              <p className="text-xs mt-1">{display.name} listens. {display.name} replies in voice.</p>
            </div>
          )}

          {turns.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${t.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] px-4 py-3 rounded-2xl ${
                  t.role === "user"
                    ? "bg-fz-gold/15 border border-fz-gold/40 text-text-primary"
                    : "bg-fz-overlay border border-fz-border text-text-primary"
                }`}
              >
                {t.role === "ai" && (
                  <div className="flex items-center justify-between mb-1.5 gap-3">
                    <span className="text-[10px] tracking-widest font-display" style={{ color: display.color }}>
                      {display.name}
                    </span>
                    {t.audioUrl && (
                      <button
                        onClick={() => replay(t.audioUrl)}
                        className="text-text-muted hover:text-text-primary"
                        title="Replay"
                      >
                        <Volume2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                )}
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{t.text}</p>
              </div>
            </motion.div>
          ))}

          <AnimatePresence>
            {(status === "transcribing" || status === "thinking" || status === "speaking") && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="flex justify-start"
              >
                <div className="px-4 py-3 rounded-2xl bg-fz-overlay border border-fz-border flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-fz-gold animate-pulse" />
                  <span
                    className="w-1.5 h-1.5 rounded-full bg-fz-gold animate-pulse"
                    style={{ animationDelay: "0.15s" }}
                  />
                  <span
                    className="w-1.5 h-1.5 rounded-full bg-fz-gold animate-pulse"
                    style={{ animationDelay: "0.3s" }}
                  />
                  <span className="text-xs text-text-muted ml-1">
                    {status === "transcribing"
                      ? "transcribing…"
                      : status === "thinking"
                      ? `${display.name} is thinking…`
                      : `${display.name} is speaking…`}
                  </span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <div ref={turnsEndRef} />
        </div>

        {/* Error banner */}
        {status === "error" && errorMsg && (
          <div className="mb-3 flex items-center gap-2 px-3 py-2 rounded-lg bg-safe-red/10 border border-safe-red/30 text-sm text-safe-red">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Live waveform */}
        {status === "recording" && (
          <div className="mb-3">
            <Waveform stream={stream} active />
            <div className="text-center mt-1 font-mono text-xs text-safe-red">
              REC {formatTime(recordingTime)}
            </div>
          </div>
        )}

        {/* Big button */}
        <div className="flex flex-col items-center pb-4">
          <button
            disabled={!canTap || !sessionId}
            onClick={status === "recording" ? stopRecording : startRecording}
            className={`relative w-24 h-24 rounded-full flex items-center justify-center transition-all shadow-glow-gold ${buttonState.color} disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {buttonState.icon}
          </button>
          <p className="text-sm text-text-muted mt-3">{buttonState.label}</p>
          {!sessionId && status !== "error" && (
            <p className="text-xs text-text-muted mt-1">Connecting…</p>
          )}
        </div>
      </div>
    </div>
  );
}
