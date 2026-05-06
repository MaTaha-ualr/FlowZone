"""
Session Summarizer
===================
Background task that summarizes conversation history every N messages
to keep the sliding window token-efficient.

Uses the utility model (cheap/free) for summarization.
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.session import Session
from app.models.message import Message
from app.services.model_router import model_router, LLMMessage

logger = logging.getLogger(__name__)

SUMMARY_INTERVAL = 10  # Summarize every 10 messages
MAX_SUMMARY_TOKENS = 256

SUMMARY_PROMPT = """You are a conversation summarizer for a youth mentoring app.

Summarize the following conversation segment into 2-3 sentences.
Focus on:
- Key emotional themes
- Any traps or risks mentioned
- Goals or moves the user discussed
- The character's advice

Be concise. Use plain language."""

async def summarize_session_if_needed(
    session_id,
    db: AsyncSession,
):
    """
    Check if a session needs summarization and run it.
    Called as a BackgroundTask after chat messages.
    """
    session = await db.get(Session, session_id)
    if not session or not session.is_active:
        return

    # Count messages since last summary
    result = await db.execute(
        select(func.count(Message.id))
        .where(Message.session_id == session_id)
        .where(Message.role.in_(["user", "assistant"]))
    )
    total_messages = result.scalar() or 0

    last_summary_msg = session.summary_last_updated_at_msg or 0
    if total_messages - last_summary_msg < SUMMARY_INTERVAL:
        return

    # Fetch the messages to summarize
    messages_to_summarize = total_messages - last_summary_msg
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .where(Message.role.in_(["user", "assistant"]))
        .order_by(Message.created_at.desc())
        .limit(messages_to_summarize)
    )
    msgs = list(reversed(result.scalars().all()))

    if len(msgs) < 3:
        return  # Not enough to summarize

    # Build summarization input
    conversation_text = "\n\n".join([
        f"{m.role.upper()}: {m.content[:300]}"
        for m in msgs
    ])

    llm_messages = [
        LLMMessage(role="system", content=SUMMARY_PROMPT),
        LLMMessage(role="user", content=conversation_text),
    ]

    try:
        response = await model_router.route_utility(
            messages=llm_messages,
            db=db,
            max_tokens=MAX_SUMMARY_TOKENS,
            temperature=0.3,
        )

        new_summary = response.content.strip()
        if not new_summary:
            return

        # Append to existing summary (or replace if too long)
        if session.summary_text:
            combined = f"{session.summary_text}\n\n[New segment]: {new_summary}"
            # Keep summaries under ~2000 chars
            if len(combined) > 2000:
                combined = combined[-1800:]  # Truncate oldest
                combined = "[Earlier context truncated]...\n\n" + combined
            session.summary_text = combined
        else:
            session.summary_text = new_summary

        session.summary_last_updated_at_msg = total_messages
        await db.flush()

        logger.info(f"Session {session_id} summarized ({len(msgs)} messages)")

    except Exception as e:
        logger.warning(f"Session summarization failed for {session_id}: {e}")
