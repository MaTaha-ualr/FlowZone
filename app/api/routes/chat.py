"""
Chat Routes — LIVE with Model Router
=======================================
POST /api/v1/chat/{session_id}           — Send a message, get AI response
GET  /api/v1/chat/{session_id}/history   — Get conversation history
GET  /api/v1/chat/{session_id}/stream    — SSE streaming endpoint

This is the CORE endpoint. Every message flows:
    User message → Context Builder → Character Prompt → Model Router → Response

The Model Router handles:
    - Model selection based on character + budget tier
    - Fallback chains if primary model fails
    - Credit tracking for every API call
"""

import uuid
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.session import Session
from app.models.message import Message
from app.models.user import User
from app.schemas.api import ChatRequest, ChatResponse, ChatHistoryResponse
from app.core.constants import Character, VIBE_EMOJI_MAP, Vibe
from app.middleware.rate_limit import rate_limiter

# The new integrations
from app.services.model_router import model_router, LLMMessage
from app.services.characters.prompts import get_character_prompt_with_context
from app.services.trust_engine.context_builder import build_user_context
from app.services.rag.retriever import retrieve_for_message
from app.services.rag.rag_classifier import classify as classify_rag
from app.services.rag.chroma_store import collection_count
from app.services.trust_engine.mask_detection import detect_mask, extract_session_data
from app.services.trust_engine.calculator import recalculate_after_session

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])


async def _build_conversation_messages(
    session: Session,
    user: User,
    new_message: str,
    db: AsyncSession,
) -> list[LLMMessage]:
    """
    Build the complete message list for the LLM call.

    Structure:
        1. System prompt = character personality + user context + RAG (future)
        2. Conversation summary (if exists — older messages summarized)
        3. Last N messages from DB (the sliding window)
        4. The new user message

    This is the "token-efficient context" strategy from the architecture:
    ~1500-2500 tokens of context before the user's message.
    """
    from app.core.config import settings

    messages = []

    # ---- 1. System Prompt (character + context + RAG) ----
    user_context = await build_user_context(user.id, db)

    # RAG: Classify whether this message needs retrieval
    has_user_docs = collection_count(f"user_{user.id}_documents") > 0
    rag_decision = classify_rag(
        message=new_message,
        character=session.character_active,
        vibe=session.vibe_selected,
        safe_harbor_level=session.safe_harbor_level,
        has_user_docs=has_user_docs,
    )

    # RAG: Retrieve relevant context if needed
    rag_context = ""
    if rag_decision.include_knowledge_base or rag_decision.include_user_docs or rag_decision.include_patterns:
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

    system_prompt = get_character_prompt_with_context(
        character=session.character_active,
        user_context=user_context,
        rag_context=rag_context,
    )
    messages.append(LLMMessage(role="system", content=system_prompt))

    # ---- 2. Conversation Summary (if we have one) ----
    if session.summary_text:
        messages.append(LLMMessage(
            role="system",
            content=f"[Previous conversation summary]: {session.summary_text}"
        ))

    # ---- 3. Recent Messages (sliding window) ----
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

    # ---- 4. New User Message ----
    messages.append(LLMMessage(role="user", content=new_message))

    return messages


@router.post("/{session_id}", response_model=ChatResponse)
async def send_message(
    session_id: uuid.UUID,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message and receive an AI character response.

    Full pipeline:
    1. Validate session
    2. Rate limit check
    3. Store user message
    4. Build context (character prompt + user data + history)
    5. Route to Model Router (selects model, handles fallbacks)
    6. Store AI response with usage metadata
    7. Return response
    """
    # ---- Load Session + User ----
    session = await db.get(Session, session_id)
    if not session or not session.is_active:
        raise HTTPException(status_code=404, detail="Session not found or inactive")

    user = await db.get(User, session.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # ---- Rate Limit ----
    if not rate_limiter.is_allowed(str(user.id)):
        raise HTTPException(
            status_code=429,
            detail="Slow down. Too many messages this minute."
        )

    # ---- Set Vibe (first message in session) ----
    if request.vibe and not session.vibe_selected:
        session.vibe_selected = request.vibe

    # ---- Store User Message ----
    user_message = Message(
        session_id=session_id,
        role="user",
        content=request.content,
        input_type=request.input_type,
    )
    db.add(user_message)
    await db.flush()

    # ---- Build Conversation Messages ----
    llm_messages = await _build_conversation_messages(
        session=session,
        user=user,
        new_message=request.content,
        db=db,
    )

    # ---- Route to Model Router ----
    start_time = time.time()

    response = await model_router.route(
        character=session.character_active,
        messages=llm_messages,
        db=db,
        user_id=user.id,
        session_id=session.id,
        max_tokens=1024,
        temperature=0.7,
        stream=False,
    )

    response_time = int((time.time() - start_time) * 1000)

    # ---- Store AI Response ----
    ai_message = Message(
        session_id=session_id,
        role="assistant",
        content=response.content,
        input_type="text",
        model_provider=response.provider,
        model_name=response.model,
        tokens_in=response.tokens_in,
        tokens_out=response.tokens_out,
        estimated_cost_usd=0.0,  # Calculated by credit manager
        response_time_ms=response_time,
    )
    db.add(ai_message)
    await db.flush()
    await db.refresh(ai_message)

    # ---- Mask Detection (runs in background, free model) ----
    trust_delta = 0.0
    if session.vibe_selected and request.content:
        try:
            mask_result = await detect_mask(
                selected_vibe=Vibe(session.vibe_selected),
                message_text=request.content,
                db=db,
                user_id=user.id,
                session_id=session.id,
            )
            if mask_result["mask_detected"]:
                session.mask_detected = True
                session.vibe_detected_by_sentiment = mask_result["detected_vibe"]
        except Exception:
            pass  # Mask detection failure should never block the response

    # ---- Extract Session Data (traps, moves, goals) ----
    try:
        extracted = await extract_session_data(
            message_text=request.content,
            db=db,
            user_id=user.id,
            session_id=session.id,
        )
        # Accumulate traps/interventions in session
        existing_traps = session.traps_mentioned or []
        new_traps = extracted.get("traps", [])
        session.traps_mentioned = list(set(existing_traps + new_traps))

        # Count honesty disclosures (proactive trap mentions)
        if new_traps:
            session.honesty_disclosures = (session.honesty_disclosures or 0) + len(new_traps)
    except Exception:
        pass  # Extraction failure should never block the response

    # ---- Trust Score Recalculation ----
    try:
        score_result = await recalculate_after_session(
            user_id=user.id,
            session=session,
            db=db,
        )
        trust_delta = score_result.get("delta", 0.0)
    except Exception:
        pass  # Trust score failure should never block the response

    await db.flush()

    return ChatResponse(
        message_id=ai_message.id,
        content=response.content,
        character=session.character_active,
        model_used=f"{response.provider}/{response.model}",
        mask_detected=session.mask_detected,
        safe_harbor_level=session.safe_harbor_level,
        trust_score_delta=trust_delta,
        action_item=None,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/{session_id}/stream")
async def stream_message(
    session_id: uuid.UUID,
    content: str,
    vibe: str = None,
    db: AsyncSession = Depends(get_db),
):
    """
    SSE streaming endpoint for real-time character responses.
    The frontend connects to this and receives text chunks as they generate.

    Usage (frontend):
        const evtSource = new EventSource(
            `/api/v1/chat/${sessionId}/stream?content=${encodeURIComponent(msg)}`
        );
        evtSource.onmessage = (e) => { appendToChat(e.data); };
    """
    session = await db.get(Session, session_id)
    if not session or not session.is_active:
        raise HTTPException(status_code=404, detail="Session not found")

    user = await db.get(User, session.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Store user message
    user_message = Message(
        session_id=session_id, role="user", content=content, input_type="text",
    )
    db.add(user_message)
    await db.flush()

    # Build messages
    llm_messages = await _build_conversation_messages(
        session=session, user=user, new_message=content, db=db,
    )

    # Stream from model router
    async def event_generator():
        full_content = ""
        stream = await model_router.route(
            character=session.character_active,
            messages=llm_messages,
            db=db,
            user_id=user.id,
            session_id=session.id,
            stream=True,
        )
        async for chunk in stream:
            if chunk.content:
                full_content += chunk.content
                yield f"data: {chunk.content}\n\n"
            if chunk.is_final:
                # Store the complete response
                ai_msg = Message(
                    session_id=session_id, role="assistant", content=full_content,
                    input_type="text", model_provider="streamed",
                    tokens_in=chunk.tokens_in, tokens_out=chunk.tokens_out,
                )
                db.add(ai_msg)
                await db.flush()
                yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{session_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get conversation history for a session."""
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

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
