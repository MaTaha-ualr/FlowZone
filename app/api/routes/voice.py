"""
Voice Routes
==============
POST /api/v1/voice/transcribe   — Upload audio, get text back (STT)
POST /api/v1/voice/synthesize   — Send text + character, get audio back (TTS)
GET  /api/v1/voice/voices       — List available TTS voices

The voice endpoints sit alongside the chat endpoint:
    1. User speaks → frontend captures audio → POST /voice/transcribe → get text
    2. Frontend sends text to POST /chat/{session_id} → get AI response
    3. AI response text → POST /voice/synthesize → audio plays in browser
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.api import TranscriptionResponse, TTSRequest
from app.services.voice.service import voice_service, CHARACTER_VOICES
from app.core.constants import Character
from app.core.config import settings

router = APIRouter(prefix="/api/v1/voice", tags=["Voice"])

# Max audio upload size: 25MB (Whisper limit)
MAX_AUDIO_SIZE = 25 * 1024 * 1024


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file (WAV, MP3, M4A, WebM)"),
):
    """
    Transcribe an audio file to text using Groq Whisper.

    Accepts: WAV, MP3, M4A, WebM, OGG formats
    Returns: Transcribed text + confidence + duration

    Frontend integration:
        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.wav');
        const response = await fetch('/api/v1/voice/transcribe', {
            method: 'POST',
            body: formData,
        });
        const { text } = await response.json();
    """
    # Validate file size
    contents = await file.read()
    if len(contents) > MAX_AUDIO_SIZE:
        raise HTTPException(status_code=413, detail="Audio file too large (max 25MB)")

    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # Validate file type
    allowed_types = [
        "audio/wav", "audio/wave", "audio/x-wav",
        "audio/mp3", "audio/mpeg",
        "audio/m4a", "audio/mp4",
        "audio/webm", "audio/ogg",
    ]
    content_type = file.content_type or ""
    if content_type and content_type not in allowed_types:
        # Be lenient — some browsers report weird content types
        pass  # Allow it through, let Whisper handle format detection

    try:
        result = await voice_service.transcribe(
            audio_bytes=contents,
            filename=file.filename or "audio.wav",
        )

        return TranscriptionResponse(
            text=result["text"],
            confidence=None,  # Whisper doesn't return per-utterance confidence
            duration_seconds=result.get("duration"),
            provider="groq_whisper",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Transcription failed: {type(e).__name__}: {str(e)[:200]}"
        )


@router.post("/synthesize")
async def synthesize_speech(request: TTSRequest):
    """
    Convert text to speech using Edge TTS with character-specific voice.

    Returns: MP3 audio bytes

    Frontend integration:
        const response = await fetch('/api/v1/voice/synthesize', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ text: aiResponse, character: 'challenger' }),
        });
        const audioBlob = await response.blob();
        const audio = new Audio(URL.createObjectURL(audioBlob));
        audio.play();
    """
    if settings.tts_provider.value == "none":
        raise HTTPException(
            status_code=501,
            detail="TTS is disabled. Set TTS_PROVIDER=edge_tts in .env to enable."
        )

    try:
        character = Character(request.character)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown character: {request.character}")

    try:
        audio_bytes = await voice_service.synthesize(
            text=request.text,
            character=character,
        )

        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"inline; filename=flowzone_{character.value}.mp3",
                "Content-Length": str(len(audio_bytes)),
            },
        )
    except ImportError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"TTS failed: {type(e).__name__}: {str(e)[:200]}"
        )


@router.get("/voices")
async def list_voices():
    """List available TTS voices for debugging and configuration."""
    voices = await voice_service.get_available_voices()
    return {
        "character_mapping": {
            c.value: CHARACTER_VOICES.get(c, "unknown")
            for c in Character
        },
        "available_voices": voices[:20],  # Limit to 20 for readability
    }
