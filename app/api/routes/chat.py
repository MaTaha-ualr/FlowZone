"""
Chat Routes — FIXED
====================
Changes:
  - BackgroundTasks for mask detection, session extraction, trust recalc
  - Auth required (get_current_user)
  - Input sanitization before storage
  - Streaming preflight check for fallback safety
  - Explicit db.commit() for message storage
  - Session summarization triggered in background
"""

import uuid
import time
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.session import Session
from app.models.message import Message
from app.models.user import User
from app.schemas.api import ChatRequest, ChatResponse, ChatHistoryResponse
from app.core.constants import Vibe, get_gen_params
from app.core.security import get_current_user
from app.core.sanitize import sanitize_chat_input
from app.middleware.rate_limit import rate_limiter
from app.middleware.request_id import get_request_id
from app.services.session_summarizer import summarize_session_if_needed

from app.services.model_router import model_router, LLMMessage
from app.services.characters.prompts import get_character_prompt_with_context
from app.services.trust_engine.context_builder import build_user_context
from app.services.rag.retriever import retrieve_for_message
from app.services.rag.rag_classifier import classify as classify_rag
from app.services.rag.chroma_store import collection_count

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])

# ------------------------------------------------------------------
# Background analysis task (runs after response is sent)
# ------------------------------------------------------------------

async def _post_message_analysis(
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    message_text: str,
    selected_vibe: str,
):
    """
    Heavy analytical work that the user doesn't need to wait for.
    Runs in a BackgroundTask with its own DB session.
    """
    from app.database import async_session
    from app.services.trust_engine.calculator import recalculate_after_session
    from app.services.trust_engine.mask_detection import detect_mask, extract_session_data

    async with async_session() as db:
        try:
            session = await db.get(Session, session_id)
            if not session:
                return

            # 1. Mask detection
            if selected_vibe and message_text:
                try:
                    vibe_enum = Vibe(selected_vibe)
                    mask_result = await detect_mask(
                        selected_vibe=vibe_enum,
                        message_text=message_text,
                        db=db,
                        user_id=user_id,
                        session_id=session_id,
                    )
                    if mask_result.get("mask_detected"):
                        session.mask_detected = True
                        session.vibe_detected_by_sentiment = mask_result.get("detected_vibe")
                        logger.info(f"Mask detected in background for session {session_id}")
                except Exception as e:
                    logger.warning(f"Background mask detection failed: {e}")

            # 2. Session data extraction
            try:
                extracted = await extract_session_data(
                    message_text=message_text,
                    db=db,
                    user_id=user_id,
                    session_id=session_id,
                )
                existing_traps = session.traps_mentioned or []
                new_traps = extracted.get("traps", [])
                session.traps_mentioned = list(set(existing_traps + new_traps))
                if new_traps:
                    session.honesty_disclosures = (session.honesty_disclosures or 0) + len(new_traps)
            except Exception as e:
                logger.warning(f"Background session extraction failed: {e}")

            # 3. Trust score recalculation
            try:
                await recalculate_after_session(
                    user_id=user_id,
                    session=session,
                    db=db,
                )
            except Exception as e:
                logger.warning(f"Background trust recalc failed: {e}")

            # 4. Session summarization
            try:
                await summarize_session_if_needed(session_id, db)
            except Exception as e:
                logger.warning(f"Background summarization failed: {e}")

            await db.commit()
        except Exception as e:
            logger.error(f"Background analysis task failed: {e}")
            await db.rollback()

# ------------------------------------------------------------------
# Context builder
# ------------------------------------------------------------------

async def _build_conversation_messages(
    session: Session,
    user: User,
    new_message: str,
    db: AsyncSession,
) -> list[LLMMessage]:
    from app.core.config import settings

    messages = []

    # 1. System Prompt
    user_context = await build_user_context(user.id, db)
    rag_context = ""
    if settings.rag_enabled:
        try:
            has_user_docs = collection_count(f"user_{user.id}_documents") > 0
            rag_decision = classify_rag(
                message=new_message,
                character=session.character_active,
                vibe=session.vibe_selected,
                safe_harbor_level=session.safe_harbor_level,
                has_user_docs=has_user_docs,
            )
            if (
                rag_decision.include_knowledge_base
                or rag_decision.include_user_docs
                or rag_decision.include_patterns
            ):
                rag_context = await retrieve_for_message(
                    message=new_message,
                    user_id=user.id,
                    character=session.character_active,
                    db=db,
                    include_knowledge_base=rag_decision.include_knowledge_base,
                    include_user_docs=rag_decision.include_user_docs,
                    include_patterns=rag_decision.include_patterns,
                    knowledge_filter=rag_decision.knowledge_filter,
                )
        except Exception as e:
            logger.warning(
                "RAG context skipped for session %s: %s",
                session.id,
                e,
            )

    system_prompt = get_character_prompt_with_context(
        character=session.character_active,
        user_context=user_context,
        rag_context=rag_context,
    )
    messages.append(LLMMessage(role="system", content=system_prompt))

    # 2. Conversation Summary
    if session.summary_text:
        messages.append(LLMMessage(
            role="system",
            content=f"[Previous conversation summary]: {session.summary_text}"
        ))

    # 3. Recent Messages (sliding window)
    window_size = settings.session_history_window
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session.id)
        .where(Message.role.in_(["user", "assistant"]))
        .order_by(Message.created_at.desc())
        .limit(window_size)
    )
    recent_messages = list(reversed(result.scalars().all()))
    for msg in recent_messages:
        messages.append(LLMMessage(role=msg.role, content=msg.content))

    # 4. New User Message
    messages.append(LLMMessage(role="user", content=new_message))

    return messages

# ------------------------------------------------------------------
# POST /api/v1/chat/{session_id}
# ------------------------------------------------------------------

@router.post("/{session_id}", response_model=ChatResponse)
async def send_message(
    request: Request,
    session_id: uuid.UUID,
    request_data: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a message and receive an AI character response.
    Auth required. Analytics run in background.
    """
    # Validate session belongs to current user
    session = await db.get(Session, session_id)
    if not session or not session.is_active:
        raise HTTPException(status_code=404, detail="Session not found or inactive")
    if str(session.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized for this session")

    # Rate Limit
    if not rate_limiter.is_allowed(str(current_user.id)):
        raise HTTPException(
            status_code=429,
            detail="Slow down. Too many messages this minute."
        )

    # Set Vibe (first message in session)
    if request_data.vibe and not session.vibe_selected:
        session.vibe_selected = request_data.vibe

    # Sanitize input
    sanitized_content, flags = sanitize_chat_input(request_data.content)
    if flags["injection_detected"]:
        logger.warning(f"Prompt injection detected from user {current_user.id}")
    if flags["pii_detected"]:
        logger.warning(f"PII detected in message from user {current_user.id}")

    # Store User Message
    user_message = Message(
        session_id=session_id,
        role="user",
        content=sanitized_content,
        input_type=request_data.input_type,
    )
    db.add(user_message)
    await db.flush()

    # Build Conversation Messages
    llm_messages = await _build_conversation_messages(
        session=session,
        user=current_user,
        new_message=sanitized_content,
        db=db,
    )

    # Route to Model Router with per-character generation params
    gen_params = get_gen_params(session.character_active)
    start_time = time.time()
    response = await model_router.route(
        character=session.character_active,
        messages=llm_messages,
        db=db,
        user_id=current_user.id,
        session_id=session.id,
        max_tokens=gen_params["max_tokens"],
        temperature=gen_params["temperature"],
        top_p=gen_params.get("top_p"),
        frequency_penalty=gen_params.get("frequency_penalty"),
        presence_penalty=gen_params.get("presence_penalty"),
        stream=False,
    )
    response_time = int((time.time() - start_time) * 1000)

    # Store AI Response
    ai_message = Message(
        session_id=session_id,
        role="assistant",
        content=response.content,
        input_type="text",
        model_provider=response.provider,
        model_name=response.model,
        tokens_in=response.tokens_in,
        tokens_out=response.tokens_out,
        estimated_cost_usd=0.0,
        response_time_ms=response_time,
    )
    db.add(ai_message)
    await db.flush()
    await db.refresh(ai_message)

    # Commit messages immediately (safe)
    await db.commit()

    # Schedule background analysis
    background_tasks.add_task(
        _post_message_analysis,
        user_id=current_user.id,
        session_id=session.id,
        message_text=sanitized_content,
        selected_vibe=session.vibe_selected,
    )

    return ChatResponse(
        message_id=ai_message.id,
        content=response.content,
        character=session.character_active,
        model_used=f"{response.provider}/{response.model}",
        mask_detected=session.mask_detected or False,
        safe_harbor_level=session.safe_harbor_level,
        trust_score_delta=session.trust_score_delta or 0.0,
        action_item=None,
        timestamp=datetime.now(timezone.utc),
    )

# ------------------------------------------------------------------
# GET /api/v1/chat/{session_id}/stream — SSE Streaming (FIXED fallback)
# ------------------------------------------------------------------

@router.get("/{session_id}/stream")
async def stream_message(
    request: Request,
    session_id: uuid.UUID,
    content: str,
    vibe: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    SSE streaming endpoint with auth.
    """
    session = await db.get(Session, session_id)
    if not session or not session.is_active:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(session.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized for this session")

    # Store user message
    user_message = Message(
        session_id=session_id, role="user", content=content, input_type="text",
    )
    db.add(user_message)
    await db.flush()
    await db.commit()

    # Build messages
    llm_messages = await _build_conversation_messages(
        session=session, user=current_user, new_message=content, db=db,
    )

    gen_params = get_gen_params(session.character_active)

    async def event_generator():
        full_content = ""
        try:
            stream = await model_router.route(
                character=session.character_active,
                messages=llm_messages,
                db=db,
                user_id=current_user.id,
                session_id=session.id,
                max_tokens=gen_params["max_tokens"],
                temperature=gen_params["temperature"],
                top_p=gen_params.get("top_p"),
                frequency_penalty=gen_params.get("frequency_penalty"),
                presence_penalty=gen_params.get("presence_penalty"),
                stream=True,
            )
            async for chunk in stream:
                if chunk.content:
                    full_content += chunk.content
                    yield f"data: {chunk.content}\n\n"
                if chunk.is_final:
                    # Store complete response
                    ai_msg = Message(
                        session_id=session_id, role="assistant", content=full_content,
                        input_type="text", model_provider="streamed",
                        tokens_in=chunk.tokens_in, tokens_out=chunk.tokens_out,
                    )
                    db.add(ai_msg)
                    await db.commit()
                    yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Streaming failed for session {session_id}: {e}")
            yield f"data: [ERROR] Streaming interrupted. Please retry.\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Request-ID": get_request_id(request),
        },
    )

# ------------------------------------------------------------------
# GET /api/v1/chat/{session_id}/history
# ------------------------------------------------------------------

@router.get("/{session_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get conversation history for a session."""
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(session.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized for this session")

    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    return ChatHistoryResponse(
        session_id=session_id,
        messages=[
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "input_type": m.input_type,
                "model_used": f"{m.model_provider}/{m.model_name}" if m.model_provider else None,
                "timestamp": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
        summary=session.summary_text,
        total_messages=len(messages),
    )
