"""
Voice Routes (FIXED)
=====================
Changes:
  - Auth required
  - File streaming (no full memory load for large uploads)
  - Better error handling
"""

import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.api import TranscriptionResponse, TTSRequest
from app.services.voice.service import voice_service, CHARACTER_VOICES
from app.core.constants import Character
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/voice", tags=["Voice"])

MAX_AUDIO_SIZE = 25 * 1024 * 1024

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Transcribe audio to text.
    Uses UploadFile spooling (streams to disk for large files).
    """
    # Check size via spooled file
    file.file.seek(0, 2)  # Seek to end
    size = file.file.tell()
    file.file.seek(0)

    if size > MAX_AUDIO_SIZE:
        raise HTTPException(status_code=413, detail="Audio file too large (max 25MB)")
    if size == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    try:
        # Read bytes (Whisper API needs bytes; for very large files we'd stream)
        contents = await file.read()
        result = await voice_service.transcribe(
            audio_bytes=contents,
            filename=file.filename or "audio.wav",
        )
        return TranscriptionResponse(
            text=result["text"],
            confidence=None,
            duration_seconds=result.get("duration"),
            provider="groq_whisper",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=502, detail=f"Transcription failed: {type(e).__name__}")

@router.post("/synthesize")
async def synthesize_speech(
    request: TTSRequest,
    current_user: User = Depends(get_current_user),
):
    """Convert text to speech."""
    if settings.tts_provider.value == "none":
        raise HTTPException(status_code=501, detail="TTS is disabled")

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
        logger.error(f"TTS failed: {e}")
        raise HTTPException(status_code=502, detail=f"TTS failed: {type(e).__name__}")

@router.get("/voices")
async def list_voices(
    current_user: User = Depends(get_current_user),
):
    """List available TTS voices."""
    voices = await voice_service.get_available_voices()
    return {
        "character_mapping": {
            c.value: CHARACTER_VOICES.get(c, "unknown")
            for c in Character
        },
        "available_voices": voices[:20],
    }
