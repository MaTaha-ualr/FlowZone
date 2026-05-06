"""
Voice Service — STT + TTS Pipeline
=====================================
Speech-to-Text:
    Primary:  OpenAI Whisper (whisper-1) — paid, highest quality, reliable
    Fallback: Groq-hosted Whisper large-v3 — free tier

Text-to-Speech:
    Primary:  OpenAI TTS (tts-1-hd) — natural, human-quality voices
    Fallback: Microsoft Edge TTS — free, decent quality

STT Flow:
    User speaks -> browser captures audio -> POST /api/v1/voice/transcribe
    -> OpenAI Whisper -> text returned -> feeds into chat endpoint

TTS Flow:
    AI response text -> POST /api/v1/voice/synthesize
    -> OpenAI TTS with character-specific voice -> audio bytes returned

Character Voice Mapping (OpenAI):
    Challenger:       onyx     (deep, authoritative male)
    Navigator:        shimmer  (warm, empathetic female)
    Straight Shooter: echo     (clear, concise male)
    Strategist:       sage     (thoughtful, measured)

Character Voice Mapping (Edge TTS fallback):
    Challenger:       en-US-GuyNeural
    Navigator:        en-US-JennyNeural
    Straight Shooter: en-US-DavisNeural
    Strategist:       en-US-AriaNeural
"""

import io
import logging
import httpx
from typing import Optional

from app.core.config import settings
from app.core.constants import Character
from app.services.model_router.groq_provider import GroqProvider

logger = logging.getLogger(__name__)


# ============================================================
# CHARACTER -> VOICE MAPPING
# ============================================================

# OpenAI TTS voices: alloy, echo, fable, onyx, nova, shimmer, sage, coral
CHARACTER_VOICES_OPENAI = {
    Character.CHALLENGER: "onyx",
    Character.NAVIGATOR: "shimmer",
    Character.STRAIGHT_SHOOTER: "echo",
    Character.STRATEGIST: "sage",
}

# Edge TTS voices (legacy fallback)
CHARACTER_VOICES_EDGE = {
    Character.CHALLENGER: "en-US-GuyNeural",
    Character.NAVIGATOR: "en-US-JennyNeural",
    Character.STRAIGHT_SHOOTER: "en-US-DavisNeural",
    Character.STRATEGIST: "en-US-AriaNeural",
}

CHARACTER_RATE_EDGE = {
    Character.CHALLENGER: "+5%",
    Character.NAVIGATOR: "-10%",
    Character.STRAIGHT_SHOOTER: "+10%",
    Character.STRATEGIST: "-5%",
}

# Backwards-compatible alias used by older callers (api/routes/voice.py).
# Resolves to whichever map matches the configured TTS provider.
def _active_character_voices() -> dict:
    if settings.tts_provider.value == "openai_tts":
        return CHARACTER_VOICES_OPENAI
    return CHARACTER_VOICES_EDGE


# A snapshot at import time for callers that import the dict directly.
CHARACTER_VOICES = (
    CHARACTER_VOICES_OPENAI
    if settings.tts_provider.value == "openai_tts"
    else CHARACTER_VOICES_EDGE
)

# OpenAI TTS speed (0.25 to 4.0; 1.0 is default)
CHARACTER_SPEED_OPENAI = {
    Character.CHALLENGER: 1.05,
    Character.NAVIGATOR: 0.95,
    Character.STRAIGHT_SHOOTER: 1.10,
    Character.STRATEGIST: 0.95,
}


class VoiceService:
    """
    Unified voice pipeline for FlowZone.
    Handles both Speech-to-Text and Text-to-Speech with provider fallbacks.
    """

    OPENAI_STT_URL = "https://api.openai.com/v1/audio/transcriptions"
    OPENAI_TTS_URL = "https://api.openai.com/v1/audio/speech"

    def __init__(self):
        self._groq_provider = GroqProvider()
        self._http: Optional[httpx.AsyncClient] = None

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))
        return self._http

    # ================================================================
    # SPEECH-TO-TEXT
    # ================================================================

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.webm",
    ) -> dict:
        """
        Transcribe audio. Tries the configured primary provider, falls back on failure.

        Returns:
            {"text": "...", "duration": seconds, "language": "en", "provider": "..."}
        """
        provider = settings.stt_provider.value
        logger.info(
            f"Transcribing audio ({len(audio_bytes)} bytes, {filename}, "
            f"provider={provider})"
        )

        if provider == "browser":
            raise ValueError(
                "STT provider 'browser' should not call the backend transcribe endpoint."
            )

        chain: list[str]
        if provider == "openai_whisper":
            chain = ["openai_whisper", "groq_whisper"]
        elif provider == "groq_whisper":
            chain = ["groq_whisper", "openai_whisper"]
        else:
            raise ValueError(f"STT provider '{provider}' not supported.")

        last_error: Optional[Exception] = None
        for attempt in chain:
            try:
                if attempt == "openai_whisper":
                    if not settings.openai_api_key:
                        logger.warning("OpenAI key missing; skipping openai_whisper")
                        continue
                    return await self._transcribe_openai(audio_bytes, filename)

                if attempt == "groq_whisper":
                    if not settings.groq_api_key:
                        logger.warning("Groq key missing; skipping groq_whisper")
                        continue
                    return await self._transcribe_groq(audio_bytes, filename)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    f"STT attempt '{attempt}' failed: {type(exc).__name__}: {exc}"
                )
                continue

        raise RuntimeError(f"All STT providers failed. Last error: {last_error}")

    async def _transcribe_openai(self, audio_bytes: bytes, filename: str) -> dict:
        client = await self._client()
        files = {"file": (filename, audio_bytes, _mime_for(filename))}
        data = {
            "model": settings.openai_stt_model,
            "response_format": "verbose_json",
        }
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}

        resp = await client.post(
            self.OPENAI_STT_URL, files=files, data=data, headers=headers
        )
        resp.raise_for_status()
        payload = resp.json()

        text = payload.get("text", "").strip()
        duration = (
            float(payload.get("duration", 0.0))
            if payload.get("duration") is not None
            else 0.0
        )
        language = payload.get("language", "en")

        logger.info(f"OpenAI STT complete: {len(text)} chars, {duration:.1f}s")
        return {
            "text": text,
            "duration": duration,
            "language": language,
            "provider": "openai_whisper",
            "confidence": 1.0,
        }

    async def _transcribe_groq(self, audio_bytes: bytes, filename: str) -> dict:
        result = await self._groq_provider.transcribe(
            audio_bytes=audio_bytes, filename=filename
        )
        result.setdefault("provider", "groq_whisper")
        result.setdefault("confidence", 1.0)
        logger.info(
            f"Groq STT complete: {len(result.get('text', ''))} chars, "
            f"{result.get('duration', 0.0):.1f}s"
        )
        return result

    # ================================================================
    # TEXT-TO-SPEECH
    # ================================================================

    async def synthesize(
        self,
        text: str,
        character: Character,
    ) -> bytes:
        """Convert text to speech, with provider fallback. Returns MP3 bytes."""
        provider = settings.tts_provider.value
        if provider == "none":
            raise ValueError("TTS is disabled (TTS_PROVIDER=none)")

        chain: list[str]
        if provider == "openai_tts":
            chain = ["openai_tts", "edge_tts"]
        elif provider == "edge_tts":
            chain = ["edge_tts", "openai_tts"]
        else:
            raise ValueError(f"TTS provider '{provider}' not supported.")

        last_error: Optional[Exception] = None
        for attempt in chain:
            try:
                if attempt == "openai_tts":
                    if not settings.openai_api_key:
                        logger.warning("OpenAI key missing; skipping openai_tts")
                        continue
                    return await self._synthesize_openai(text, character)

                if attempt == "edge_tts":
                    return await self._synthesize_edge(text, character)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    f"TTS attempt '{attempt}' failed: {type(exc).__name__}: {exc}"
                )
                continue

        raise RuntimeError(f"All TTS providers failed. Last error: {last_error}")

    async def _synthesize_openai(self, text: str, character: Character) -> bytes:
        client = await self._client()
        voice = CHARACTER_VOICES_OPENAI.get(character, "shimmer")
        speed = CHARACTER_SPEED_OPENAI.get(character, 1.0)

        logger.info(
            f"OpenAI TTS: model={settings.openai_tts_model}, voice={voice}, "
            f"speed={speed}, text_length={len(text)}, character={character.value}"
        )

        payload = {
            "model": settings.openai_tts_model,
            "voice": voice,
            "input": text,
            "speed": speed,
            "response_format": "mp3",
        }
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }

        resp = await client.post(self.OPENAI_TTS_URL, json=payload, headers=headers)
        resp.raise_for_status()
        audio_bytes = resp.content
        logger.info(f"OpenAI TTS complete: {len(audio_bytes)} bytes")
        return audio_bytes

    async def _synthesize_edge(self, text: str, character: Character) -> bytes:
        try:
            import edge_tts
        except ImportError:
            raise ImportError(
                "edge-tts package not installed. Run: pip install edge-tts"
            )

        voice = CHARACTER_VOICES_EDGE.get(character, "en-US-JennyNeural")
        rate = CHARACTER_RATE_EDGE.get(character, "+0%")
        logger.info(
            f"Edge TTS: voice={voice}, rate={rate}, text_length={len(text)}, "
            f"character={character.value}"
        )

        communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])

        audio_bytes = buf.getvalue()
        logger.info(f"Edge TTS complete: {len(audio_bytes)} bytes")
        return audio_bytes

    async def get_available_voices(self) -> list[dict]:
        """List available voices for whichever TTS is currently active."""
        provider = settings.tts_provider.value
        if provider == "openai_tts":
            return [
                {"name": "alloy", "description": "Balanced, neutral"},
                {"name": "echo", "description": "Clear, concise"},
                {"name": "fable", "description": "British, expressive"},
                {"name": "onyx", "description": "Deep, authoritative"},
                {"name": "nova", "description": "Bright, energetic"},
                {"name": "shimmer", "description": "Warm, empathetic"},
                {"name": "sage", "description": "Thoughtful, measured"},
                {"name": "coral", "description": "Friendly, upbeat"},
            ]
        if provider == "edge_tts":
            try:
                import edge_tts
                voices = await edge_tts.list_voices()
                return [
                    {
                        "name": v["ShortName"],
                        "gender": v["Gender"],
                        "locale": v["Locale"],
                    }
                    for v in voices
                    if v["Locale"].startswith("en-")
                ]
            except ImportError:
                return [{"error": "edge-tts not installed"}]
        return []


def _mime_for(filename: str) -> str:
    name = filename.lower()
    if name.endswith(".webm"):
        return "audio/webm"
    if name.endswith(".mp3"):
        return "audio/mpeg"
    if name.endswith(".m4a") or name.endswith(".mp4"):
        return "audio/mp4"
    if name.endswith(".ogg") or name.endswith(".oga"):
        return "audio/ogg"
    if name.endswith(".flac"):
        return "audio/flac"
    return "audio/wav"


# Singleton
voice_service = VoiceService()
