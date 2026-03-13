"""
Voice Service — STT + TTS Pipeline
=====================================
Speech-to-Text: Groq-hosted Whisper large-v3 (free tier)
Text-to-Speech: Microsoft Edge TTS (free, high quality)

STT Flow:
    User speaks → browser captures audio → POST /api/v1/voice/transcribe
    → Groq Whisper → text returned → feeds into chat endpoint

TTS Flow:
    AI response text → POST /api/v1/voice/synthesize
    → Edge TTS with character-specific voice → audio bytes returned

Character Voice Mapping:
    Challenger:     en-US-GuyNeural     (direct, slightly edgy male voice)
    Navigator:      en-US-JennyNeural   (calm, warm female voice)
    Straight Shooter: en-US-DavisNeural (concise, authoritative male voice)
    Strategist:     en-US-AriaNeural    (thoughtful, measured female voice)
"""

import io
import logging
from typing import Optional
from app.core.config import settings
from app.core.constants import Character
from app.services.model_router.groq_provider import GroqProvider

logger = logging.getLogger(__name__)

# ============================================================
# CHARACTER → VOICE MAPPING (Edge TTS voices)
# ============================================================

CHARACTER_VOICES = {
    Character.CHALLENGER: "en-US-GuyNeural",
    Character.NAVIGATOR: "en-US-JennyNeural",
    Character.STRAIGHT_SHOOTER: "en-US-DavisNeural",
    Character.STRATEGIST: "en-US-AriaNeural",
}

# Voice speaking rates per character personality
CHARACTER_RATE = {
    Character.CHALLENGER: "+5%",       # Slightly fast — energy
    Character.NAVIGATOR: "-10%",       # Slightly slow — calming
    Character.STRAIGHT_SHOOTER: "+10%", # Fast — efficient
    Character.STRATEGIST: "-5%",       # Measured — thoughtful
}


class VoiceService:
    """
    Unified voice pipeline for FlowZone.
    Handles both Speech-to-Text and Text-to-Speech.
    """

    def __init__(self):
        self._groq_provider = GroqProvider()

    # ================================================================
    # SPEECH-TO-TEXT (Groq Whisper)
    # ================================================================

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
    ) -> dict:
        """
        Transcribe audio to text using Groq-hosted Whisper.

        Args:
            audio_bytes: Raw audio bytes (WAV, MP3, M4A, WebM supported)
            filename: Original filename (helps Whisper detect format)

        Returns:
            {"text": "transcribed text", "duration": seconds, "language": "en"}
        """
        if settings.stt_provider.value != "groq_whisper":
            raise ValueError(f"STT provider '{settings.stt_provider}' not supported in backend. "
                             "Use 'groq_whisper' or handle STT in the browser.")

        logger.info(f"Transcribing audio ({len(audio_bytes)} bytes, {filename})")

        result = await self._groq_provider.transcribe(
            audio_bytes=audio_bytes,
            filename=filename,
        )

        logger.info(f"Transcription complete: {len(result['text'])} chars, "
                     f"{result['duration']:.1f}s duration")

        return result

    # ================================================================
    # TEXT-TO-SPEECH (Edge TTS)
    # ================================================================

    async def synthesize(
        self,
        text: str,
        character: Character,
    ) -> bytes:
        """
        Convert text to speech using Edge TTS with character-specific voice.

        Args:
            text: The text to speak
            character: Which character is speaking (determines voice)

        Returns:
            MP3 audio bytes
        """
        if settings.tts_provider.value == "none":
            raise ValueError("TTS is disabled (TTS_PROVIDER=none)")

        try:
            import edge_tts
        except ImportError:
            raise ImportError("edge-tts package not installed. Run: pip install edge-tts")

        voice = CHARACTER_VOICES.get(character, "en-US-JennyNeural")
        rate = CHARACTER_RATE.get(character, "+0%")

        logger.info(f"Synthesizing TTS: voice={voice}, rate={rate}, "
                     f"text_length={len(text)}, character={character.value}")

        # Edge TTS generates audio chunks — collect them all
        communicate = edge_tts.Communicate(text, voice=voice, rate=rate)

        audio_buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer.write(chunk["data"])

        audio_bytes = audio_buffer.getvalue()
        logger.info(f"TTS complete: {len(audio_bytes)} bytes")

        return audio_bytes

    async def get_available_voices(self) -> list[dict]:
        """List available Edge TTS voices (for debugging/configuration)."""
        try:
            import edge_tts
            voices = await edge_tts.list_voices()
            # Filter to English voices
            return [
                {"name": v["ShortName"], "gender": v["Gender"], "locale": v["Locale"]}
                for v in voices
                if v["Locale"].startswith("en-")
            ]
        except ImportError:
            return [{"error": "edge-tts not installed"}]


# Singleton
voice_service = VoiceService()
