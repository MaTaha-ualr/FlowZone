"""
Mentor Note Sanitization Service
===================================
When a mentor submits a note, it may contain emotional language, insults,
or labels ("he's just lazy", "she never listens"). The AI sanitization
pass strips these, keeping only tactical facts for the characters.

Flow:
    1. Mentor writes raw note via dashboard
    2. This service sends it through a utility model (Llama 8B, free)
    3. Returns sanitized version with only factual observations
    4. Both raw and sanitized are stored (RLS ensures characters only see sanitized)

Cost: $0 — uses free-tier Groq Llama 8B
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.model_router import model_router, LLMMessage

logger = logging.getLogger(__name__)

SANITIZATION_PROMPT = """You are a content sanitization system for a youth engagement platform.

Your job: Take a mentor's raw observation note and produce a sanitized version that:
1. KEEPS all factual observations (behavior, actions, events, attendance)
2. REMOVES all subjective judgments, insults, labels, and emotional language
3. REMOVES identifying information about third parties (other than the youth)
4. CONVERTS opinions into observable behaviors
5. Maintains the same information density — don't lose important facts

Examples:
- "He's just lazy and doesn't care" → "Youth showed reduced engagement and did not complete assigned tasks"
- "His mother is a mess and keeps messing him up" → "Home environment appears to be a source of stress; recent family interactions correlated with behavioral changes"
- "Marcus was quiet today. I wish his mama would get her act together" → "Marcus appeared subdued and less communicative than usual. Referenced unspecified home difficulties"

Respond with ONLY the sanitized text. No preamble, no explanation.
"""


async def sanitize_mentor_note(
    raw_content: str,
    db: AsyncSession,
    user_id=None,
) -> str:
    """
    Sanitize a mentor's raw note, removing judgments and keeping facts.

    Args:
        raw_content: The raw mentor note text
        db: Database session (for credit tracking)

    Returns:
        Sanitized text string
    """
    messages = [
        LLMMessage(role="system", content=SANITIZATION_PROMPT),
        LLMMessage(role="user", content=f"Raw mentor note:\n\"{raw_content}\"\n\nSanitized version:"),
    ]

    try:
        response = await model_router.route_utility(
            messages=messages,
            db=db,
            user_id=user_id,
            max_tokens=512,
            temperature=0.2,
        )

        sanitized = response.content.strip()

        # Remove any quotation marks the model might have added
        if sanitized.startswith('"') and sanitized.endswith('"'):
            sanitized = sanitized[1:-1]

        logger.info(f"Note sanitized: {len(raw_content)} chars → {len(sanitized)} chars")
        return sanitized

    except Exception as e:
        logger.warning(f"Sanitization failed: {e}. Using raw content with disclaimer.")
        return f"[Auto-sanitization unavailable] {raw_content}"
