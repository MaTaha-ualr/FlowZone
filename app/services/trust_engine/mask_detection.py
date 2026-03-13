"""
Mask Detection Service
========================
Detects when a user's selected vibe emoji doesn't match their actual text sentiment.

How it works:
    1. User selects vibe emoji (e.g., 💎 Solid)
    2. User submits text (voice or typed)
    3. This service sends the text to an analytical model (Gemini Flash, free)
    4. Model returns detected sentiment + reasoning
    5. If mismatch detected → flag for the character to address

This is NOT a keyword-matching system. The LLM itself does the sentiment analysis,
which handles slang, sarcasm, code-switching, and context that rules-based
approaches would miss.

Cost: $0 — uses free-tier Gemini Flash or Groq Llama for analysis
"""

import json
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Vibe
from app.services.model_router import model_router, LLMMessage

logger = logging.getLogger(__name__)

# The analytical prompt — instructs the model to assess sentiment
MASK_DETECTION_PROMPT = """You are a sentiment analysis system for a youth engagement platform.

Given a user's selected mood emoji and their actual message text, determine if there is a mismatch between their stated mood and their real emotional state.

Mood options:
- solid (💎): Feeling stable, good, in control
- angry (🔥): Frustrated, under pressure, heated
- guarded (🔏): Closed off, resistant, not trusting
- storm (⛈️): Overwhelmed, in crisis, can't cope

Respond ONLY with valid JSON (no markdown, no explanation):
{
    "detected_vibe": "solid|angry|guarded|storm",
    "confidence": 0.0-1.0,
    "mask_detected": true|false,
    "reasoning": "brief explanation",
    "sentiment_score": -1.0 to 1.0,
    "key_indicators": ["list", "of", "indicators"]
}

Rules:
- A mask is detected when the selected vibe clearly contradicts the text sentiment
- Low confidence masks (< 0.6) should NOT be flagged
- Be sensitive to slang, sarcasm, and code-switching
- "I'm good" or "whatever" are often masks but don't always flag — look for deeper signals
- Fatigue words ("tired", "exhausted") in a "solid" context = likely mask
- Anger words in a "solid" context = likely mask
- Overly positive language in every message = possible positive masking
"""


async def detect_mask(
    selected_vibe: Vibe,
    message_text: str,
    db: AsyncSession,
    user_id=None,
    session_id=None,
) -> dict:
    """
    Analyze whether the user's stated vibe matches their message text.

    Args:
        selected_vibe: The emoji/vibe the user selected
        message_text: The actual text they wrote or spoke
        db: Database session (for credit tracking)

    Returns:
        {
            "detected_vibe": Vibe enum value,
            "confidence": float 0-1,
            "mask_detected": bool,
            "reasoning": str,
            "sentiment_score": float -1 to 1,
            "key_indicators": list[str]
        }
    """
    analysis_request = (
        f"Selected mood: {selected_vibe.value}\n"
        f"User message: \"{message_text}\"\n\n"
        f"Analyze the mismatch and respond with JSON only."
    )

    messages = [
        LLMMessage(role="system", content=MASK_DETECTION_PROMPT),
        LLMMessage(role="user", content=analysis_request),
    ]

    try:
        # Route through the analytical pipeline (free models)
        response = await model_router.route_analytical(
            messages=messages,
            db=db,
            user_id=user_id,
            session_id=session_id,
            max_tokens=256,
            temperature=0.1,  # Very low temp for consistent analysis
        )

        # Parse the JSON response
        result = _parse_analysis(response.content, selected_vibe)
        logger.info(
            f"Mask detection: selected={selected_vibe.value}, "
            f"detected={result['detected_vibe']}, "
            f"mask={result['mask_detected']} "
            f"(confidence: {result['confidence']:.2f})"
        )
        return result

    except Exception as e:
        logger.warning(f"Mask detection failed: {e}. Defaulting to no mask.")
        return {
            "detected_vibe": selected_vibe.value,
            "confidence": 0.0,
            "mask_detected": False,
            "reasoning": f"Analysis unavailable: {str(e)[:100]}",
            "sentiment_score": 0.0,
            "key_indicators": [],
        }


def _parse_analysis(raw_response: str, selected_vibe: Vibe) -> dict:
    """
    Parse the LLM's JSON response. Handle malformed responses gracefully.
    """
    # Strip markdown fences if present
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1])

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON in the response
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                result = json.loads(cleaned[start:end])
            except json.JSONDecodeError:
                return _default_result(selected_vibe)
        else:
            return _default_result(selected_vibe)

    # Validate and normalize
    detected = result.get("detected_vibe", selected_vibe.value)
    confidence = min(1.0, max(0.0, float(result.get("confidence", 0.5))))
    mask_flag = result.get("mask_detected", False)

    # Only flag mask if confidence is above threshold
    if confidence < 0.6:
        mask_flag = False

    return {
        "detected_vibe": detected,
        "confidence": confidence,
        "mask_detected": bool(mask_flag),
        "reasoning": result.get("reasoning", ""),
        "sentiment_score": float(result.get("sentiment_score", 0.0)),
        "key_indicators": result.get("key_indicators", []),
    }


def _default_result(selected_vibe: Vibe) -> dict:
    """Fallback when analysis fails — assume no mask."""
    return {
        "detected_vibe": selected_vibe.value,
        "confidence": 0.0,
        "mask_detected": False,
        "reasoning": "Analysis failed — defaulting to no mask",
        "sentiment_score": 0.0,
        "key_indicators": [],
    }


async def extract_session_data(
    message_text: str,
    db: AsyncSession,
    user_id=None,
    session_id=None,
) -> dict:
    """
    Extract structured data from a user's FlowQuest dump.
    This is the JSON extraction pipeline from the architecture:
    raw emotional speech → {traps, moves, goals, emotional_state}

    Used after every voice/text dump to update session logs.
    """
    extraction_prompt = """You are a data extraction system for a youth engagement platform.

Given a user's raw, unfiltered message, extract structured information.

Respond ONLY with valid JSON:
{
    "traps": ["list of risk factors or challenges mentioned"],
    "moves": ["list of positive actions taken or planned"],
    "goals": ["list of stated or implied goals"],
    "emotional_state": "brief description of emotional state",
    "urgency_level": "low|medium|high",
    "topics": ["key topics discussed"]
}

Rules:
- Be specific: "peer_pressure_from_trey" not just "peer_pressure"
- Capture both explicit and implied information
- "Moves" are positive — things they did right
- "Traps" are risks — things that could get them in trouble
- If they mention declining a risky offer, that's both a trap AND a move
"""

    messages = [
        LLMMessage(role="system", content=extraction_prompt),
        LLMMessage(role="user", content=f"User message: \"{message_text}\""),
    ]

    try:
        response = await model_router.route_utility(
            messages=messages,
            db=db,
            user_id=user_id,
            max_tokens=256,
            temperature=0.2,
        )

        # Parse JSON
        cleaned = response.content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])

        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end])

        return {"traps": [], "moves": [], "goals": [], "emotional_state": "unknown",
                "urgency_level": "low", "topics": []}

    except Exception as e:
        logger.warning(f"Session data extraction failed: {e}")
        return {"traps": [], "moves": [], "goals": [], "emotional_state": "unknown",
                "urgency_level": "low", "topics": []}
