"""
RAG Retriever
===============
The main retrieval service that searches across all three RAG systems
and returns relevant context for injection into the LLM prompt.

Three retrieval sources:
    1. Global Knowledge Base — therapeutic techniques, legal info, resources, playbooks
    2. Per-User Documents   — court docs, school records, medical records (via metadata)
    3. Cross-User Patterns  — anonymized intervention effectiveness data (from Postgres)

The retriever is called by the chat endpoint's context builder.
It decides WHAT to retrieve based on the RAG classifier, then
assembles the results into a formatted context string.
"""

import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.rag import embedding_service, chroma_store
from app.core.constants import Character
from app.models.pattern import Pattern

logger = logging.getLogger(__name__)

# Maximum tokens to allocate for RAG context in the prompt
MAX_RAG_CONTEXT_TOKENS = 600  # ~2400 characters


async def retrieve_for_message(
    message: str,
    user_id: UUID,
    character: Character,
    db: AsyncSession,
    include_knowledge_base: bool = True,
    include_user_docs: bool = True,
    include_patterns: bool = False,
    knowledge_filter: Optional[dict] = None,
) -> str:
    """
    Main retrieval entry point. Searches relevant sources and returns
    a formatted context string ready for injection into the system prompt.

    Args:
        message: The user's current message (used as the query)
        user_id: Current user's ID
        character: Active character (affects which collections to prioritize)
        db: Database session (for pattern queries)
        include_knowledge_base: Search global knowledge collections
        include_user_docs: Search user's personal document collection
        include_patterns: Search cross-user pattern library
        knowledge_filter: Optional ChromaDB metadata filter for knowledge search

    Returns:
        Formatted context string (empty string if no relevant results)
    """
    query_embedding = embedding_service.embed_text(message)
    context_parts = []

    # ---- 1. Global Knowledge Base ----
    if include_knowledge_base:
        kb_results = _search_knowledge_base(
            query_embedding=query_embedding,
            character=character,
            metadata_filter=knowledge_filter,
        )
        if kb_results:
            context_parts.append("REFERENCE INFORMATION:\n" + "\n---\n".join(kb_results))

    # ---- 2. Per-User Documents ----
    if include_user_docs:
        user_doc_results = _search_user_documents(
            query_embedding=query_embedding,
            user_id=str(user_id),
        )
        if user_doc_results:
            context_parts.append("USER DOCUMENT CONTEXT:\n" + "\n---\n".join(user_doc_results))

    # ---- 3. Cross-User Patterns ----
    if include_patterns:
        pattern_results = await _search_patterns(
            message=message,
            character=character,
            db=db,
        )
        if pattern_results:
            context_parts.append("PATTERN INSIGHTS:\n" + pattern_results)

    # Combine and truncate to token budget
    if not context_parts:
        return ""

    combined = "\n\n".join(context_parts)

    # Rough truncation to stay within token budget
    max_chars = MAX_RAG_CONTEXT_TOKENS * 4
    if len(combined) > max_chars:
        combined = combined[:max_chars] + "\n[...context truncated for token efficiency]"

    return combined


# ============================================================
# KNOWLEDGE BASE SEARCH (System 1)
# ============================================================

def _search_knowledge_base(
    query_embedding: list[float],
    character: Character,
    metadata_filter: Optional[dict] = None,
    n_results: int = 3,
) -> list[str]:
    """
    Search across all four global knowledge collections.
    Prioritizes collections based on the active character.
    """
    # Character → collection priority mapping
    collection_priority = {
        Character.NAVIGATOR: [
            "global_therapeutic", "global_playbooks", "global_resources", "global_legal"
        ],
        Character.CHALLENGER: [
            "global_playbooks", "global_therapeutic", "global_legal", "global_resources"
        ],
        Character.STRAIGHT_SHOOTER: [
            "global_legal", "global_playbooks", "global_resources", "global_therapeutic"
        ],
        Character.STRATEGIST: [
            "global_therapeutic", "global_legal", "global_playbooks", "global_resources"
        ],
    }

    priority_order = collection_priority.get(character, chroma_store.GLOBAL_COLLECTIONS)
    all_results = []

    for collection_name in priority_order:
        if chroma_store.collection_count(collection_name) == 0:
            continue

        # Build filter: character_affinity contains this character
        where_filter = metadata_filter
        if where_filter is None:
            # Try to filter by character affinity
            where_filter = {
                "character_affinity": {"$contains": character.value}
            }

        try:
            results = chroma_store.query_collection(
                collection_name=collection_name,
                query_embedding=query_embedding,
                n_results=n_results,
                where=where_filter,
            )
        except Exception:
            # If filtered query fails (e.g., field doesn't exist), try without filter
            results = chroma_store.query_collection(
                collection_name=collection_name,
                query_embedding=query_embedding,
                n_results=n_results,
            )

        # Extract results
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                if not doc:
                    continue
                distance = results["distances"][0][i] if results["distances"][0] else 1.0
                # Only include results with reasonable similarity (cosine distance < 0.7)
                if distance < 0.7:
                    meta = results["metadatas"][0][i] if results["metadatas"][0] else {}
                    source = meta.get("document_type", collection_name)
                    all_results.append(f"[{source}] {doc[:600]}")

        # Stop after we have enough results
        if len(all_results) >= n_results:
            break

    return all_results[:n_results]


# ============================================================
# USER DOCUMENT SEARCH (System 2)
# ============================================================

def _search_user_documents(
    query_embedding: list[float],
    user_id: str,
    n_results: int = 2,
) -> list[str]:
    """
    Search the user's personal document collection.
    Returns metadata summaries (NOT raw document text — governance).
    """
    collection_name = f"user_{user_id}_documents"

    if chroma_store.collection_count(collection_name) == 0:
        return []

    results = chroma_store.query_collection(
        collection_name=collection_name,
        query_embedding=query_embedding,
        n_results=n_results,
    )

    formatted = []
    if results["metadatas"] and results["metadatas"][0]:
        for meta in results["metadatas"][0]:
            # Build context from metadata (not raw text)
            parts = []
            if meta.get("source_filename"):
                parts.append(f"From: {meta['source_filename']}")
            if meta.get("document_type"):
                parts.append(f"Type: {meta['document_type']}")
            if meta.get("summary"):
                parts.append(f"Summary: {meta['summary']}")
            if parts:
                formatted.append(" | ".join(parts))

    # Also include the stored document text if available (knowledge base docs)
    if results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            if doc and len(doc) > 10:  # Non-empty stored text
                distance = results["distances"][0][i] if results["distances"][0] else 1.0
                if distance < 0.6:  # Stricter threshold for user docs
                    formatted.append(doc[:400])

    return formatted[:n_results]


# ============================================================
# CROSS-USER PATTERN SEARCH (System 3)
# ============================================================

async def _search_patterns(
    message: str,
    character: Character,
    db: AsyncSession,
    limit: int = 2,
) -> Optional[str]:
    """
    Query the pattern library for relevant intervention insights.
    This is a SQL query, not vector search — patterns are structured data.
    """
    # Extract potential trap types from the message using simple keyword matching
    trap_keywords = {
        "peer_pressure": ["friend", "boy", "homie", "crew", "hang", "peer"],
        "financial_stress": ["money", "broke", "cash", "afford", "bills", "rent"],
        "home_instability": ["home", "mom", "dad", "parent", "family", "house"],
        "anger": ["angry", "mad", "pissed", "fight", "hit", "rage"],
        "substance_use": ["drink", "smoke", "high", "weed", "drug"],
        "academic_failure": ["school", "grade", "failing", "homework", "class"],
    }

    detected_traps = []
    message_lower = message.lower()
    for trap, keywords in trap_keywords.items():
        if any(kw in message_lower for kw in keywords):
            detected_traps.append(trap)

    if not detected_traps:
        return None

    # Query patterns matching detected traps
    result = await db.execute(
        select(Pattern)
        .where(Pattern.trap_type.in_(detected_traps))
        .where(Pattern.outcome == "positive")
        .order_by(Pattern.confidence.desc())
        .limit(limit)
    )
    patterns = result.scalars().all()

    if not patterns:
        return None

    # Format pattern insights
    insights = []
    for p in patterns:
        insights.append(
            f"For {p.trap_type} situations, the {p.intervention_used} technique "
            f"has shown positive outcomes (confidence: {p.confidence:.0%}). "
            f"Source: {p.source}."
        )

    return " ".join(insights)

