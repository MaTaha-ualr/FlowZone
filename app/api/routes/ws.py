"""
WebSocket Chat Endpoint
========================
Real-time bidirectional chat with character streaming.

Auth: token passed as query parameter ?token=JWT
      (WebSocket headers are limited in browser support)

Protocol:
  Client sends: {"type": "message", "content": "...", "vibe": "solid"}
  Server sends: {"type": "chunk", "content": "..."}
  Server sends: {"type": "done", "message_id": "...", "trust_delta": 0.0}
  Server sends: {"type": "error", "message": "..."}
"""

import uuid
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import async_session
from app.models.session import Session
from app.models.message import Message
from app.models.user import User
from app.core.security import decode_token
from app.core.config import settings
from app.core.constants import Vibe
from app.core.sanitize import sanitize_chat_input
from app.services.model_router import model_router, LLMMessage
from app.services.characters.prompts import get_character_prompt_with_context
from app.services.trust_engine.context_builder import build_user_context
from app.services.rag.retriever import retrieve_for_message
from app.services.rag.rag_classifier import classify as classify_rag
from app.services.rag.chroma_store import collection_count

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])

async def _get_user_from_ws_token(token: str) -> User:
    """Resolve JWT from WebSocket query param."""
    payload = decode_token(token)
    if not payload:
        return None
    user_id_str = payload.get("sub")
    if not user_id_str:
        return None
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        return None
    async with async_session() as db:
        return await db.get(User, user_id)

@router.websocket("/ws/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    """Main WebSocket endpoint for real-time chat."""
    await websocket.accept()

    # Auth via query param
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing auth token")
        return

    user = await _get_user_from_ws_token(token)
    if not user or not user.is_active:
        await websocket.close(code=1008, reason="Invalid token")
        return

    # Validate session
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        await websocket.close(code=1008, reason="Invalid session ID")
        return

    async with async_session() as db:
        session = await db.get(Session, sid)
        if not session or not session.is_active:
            await websocket.close(code=1008, reason="Session not found")
            return
        if str(session.user_id) != str(user.id):
            await websocket.close(code=1008, reason="Not authorized")
            return

    await websocket.send_json({"type": "connected", "character": session.character_active})

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = data.get("type")
            if msg_type != "message":
                await websocket.send_json({"type": "error", "message": "Unknown message type"})
                continue

            content = data.get("content", "")
            vibe = data.get("vibe")

            if not content:
                await websocket.send_json({"type": "error", "message": "Empty content"})
                continue

            # Sanitize
            sanitized, flags = sanitize_chat_input(content)

            # Set vibe
            if vibe and not session.vibe_selected:
                session.vibe_selected = vibe

            # Store user message
            async with async_session() as db:
                user_msg = Message(
                    session_id=sid, role="user", content=sanitized, input_type="text"
                )
                db.add(user_msg)
                await db.commit()

            # Build context and stream response with a live DB session.
            full_content = ""
            ai_msg = None
            async with async_session() as db:
                user_context = await build_user_context(user.id, db)
                rag_context = ""
                if settings.rag_enabled:
                    try:
                        has_user_docs = collection_count(f"user_{user.id}_documents") > 0
                        rag_decision = classify_rag(
                            message=sanitized,
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
                                message=sanitized,
                                user_id=user.id,
                                character=session.character_active,
                                db=db,
                                include_knowledge_base=rag_decision.include_knowledge_base,
                                include_user_docs=rag_decision.include_user_docs,
                                include_patterns=rag_decision.include_patterns,
                                knowledge_filter=rag_decision.knowledge_filter,
                            )
                    except Exception as e:
                        logger.warning("RAG context skipped for WebSocket session %s: %s", sid, e)

                system_prompt = get_character_prompt_with_context(
                    character=session.character_active,
                    user_context=user_context,
                    rag_context=rag_context,
                )
                messages = [LLMMessage(role="system", content=system_prompt)]

                # Recent history
                result = await db.execute(
                    select(Message)
                    .where(Message.session_id == sid)
                    .where(Message.role.in_(["user", "assistant"]))
                    .order_by(Message.created_at.desc())
                    .limit(8)
                )
                for msg in reversed(result.scalars().all()):
                    messages.append(LLMMessage(role=msg.role, content=msg.content))
                messages.append(LLMMessage(role="user", content=sanitized))

                try:
                    stream = await model_router.route(
                        character=session.character_active,
                        messages=messages,
                        db=db,
                        user_id=user.id,
                        session_id=session.id,
                        stream=True,
                    )
                    async for chunk in stream:
                        if chunk.content:
                            full_content += chunk.content
                            await websocket.send_json({"type": "chunk", "content": chunk.content})
                        if chunk.is_final:
                            break
                except Exception as e:
                    logger.error(f"WebSocket streaming error: {e}")
                    await websocket.send_json({"type": "error", "message": "AI response failed. Please retry."})
                    continue

                ai_msg = Message(
                    session_id=sid, role="assistant", content=full_content,
                    input_type="text", model_provider="streamed_ws",
                )
                db.add(ai_msg)
                await db.commit()
                await db.refresh(ai_msg)

            await websocket.send_json({
                "type": "done",
                "message_id": str(ai_msg.id),
                "content": full_content,
                "mask_detected": session.mask_detected or False,
                "trust_delta": session.trust_score_delta or 0.0,
            })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user.id}, session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal error")
        except Exception:
            pass
