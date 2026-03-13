"""
ChromaDB Store
================
Manages all vector storage for the three RAG systems:

    1. Global Knowledge Base — 4 collections (therapeutic, legal, resources, playbooks)
    2. Per-User Documents  — 1 collection per user (user_{id}_documents)
    3. Session Summaries    — embedded session summaries for context search

ChromaDB runs in EMBEDDED MODE — no separate server needed.
At our scale (30 users × ~20 chunks each + ~500 knowledge base chunks),
this handles everything in-process with zero latency overhead.

Collections are persisted to disk so they survive container restarts.
"""

import os
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazy-loaded singleton
_client = None


def _get_client():
    """Get or create the ChromaDB client (persistent storage)."""
    global _client
    if _client is None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        persist_dir = settings.chroma_persist_dir
        os.makedirs(persist_dir, exist_ok=True)

        _client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )
        logger.info(f"ChromaDB initialized at {persist_dir}")
    return _client


# ============================================================
# COLLECTION MANAGEMENT
# ============================================================

# The four global knowledge base collections
GLOBAL_COLLECTIONS = [
    "global_therapeutic",
    "global_legal",
    "global_resources",
    "global_playbooks",
]


def get_or_create_collection(name: str):
    """
    Get an existing collection or create a new one.
    ChromaDB collections are like tables — they hold documents + embeddings.
    """
    client = _get_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},  # Use cosine similarity
    )


def get_user_collection(user_id: str):
    """Get the per-user document collection."""
    return get_or_create_collection(f"user_{user_id}_documents")


def get_session_collection():
    """Get the session summaries collection."""
    return get_or_create_collection("session_summaries")


def delete_collection(name: str):
    """Delete a collection entirely (e.g., when user is removed)."""
    client = _get_client()
    try:
        client.delete_collection(name)
        logger.info(f"Deleted collection: {name}")
    except Exception as e:
        logger.warning(f"Could not delete collection {name}: {e}")


def list_collections() -> list[str]:
    """List all collection names."""
    client = _get_client()
    return [c.name for c in client.list_collections()]


# ============================================================
# DOCUMENT OPERATIONS
# ============================================================

def add_documents(
    collection_name: str,
    ids: list[str],
    texts: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
):
    """
    Add documents to a collection with pre-computed embeddings.

    Args:
        collection_name: Target collection
        ids: Unique IDs for each chunk (e.g., "doc_123_chunk_0")
        texts: The raw text chunks (stored for reference)
        embeddings: Pre-computed embedding vectors
        metadatas: Metadata dicts for filtered retrieval
    """
    collection = get_or_create_collection(collection_name)
    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    logger.info(f"Added {len(ids)} documents to {collection_name}")


def query_collection(
    collection_name: str,
    query_embedding: list[float],
    n_results: int = 5,
    where: Optional[dict] = None,
    where_document: Optional[dict] = None,
) -> dict:
    """
    Query a collection with a vector and optional metadata filters.

    Args:
        collection_name: Which collection to search
        query_embedding: The query vector
        n_results: How many results to return
        where: Metadata filter (e.g., {"category": "crisis"})
        where_document: Full-text filter on document content

    Returns:
        {
            "ids": [["id1", "id2"]],
            "documents": [["text1", "text2"]],
            "metadatas": [[{...}, {...}]],
            "distances": [[0.1, 0.3]],
        }
    """
    collection = get_or_create_collection(collection_name)

    # Check if collection has any documents
    if collection.count() == 0:
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

    query_params = {
        "query_embeddings": [query_embedding],
        "n_results": min(n_results, collection.count()),
    }
    if where:
        query_params["where"] = where
    if where_document:
        query_params["where_document"] = where_document

    try:
        results = collection.query(**query_params)
        return results
    except Exception as e:
        logger.warning(f"ChromaDB query failed on {collection_name}: {e}")
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}


def delete_documents(collection_name: str, ids: list[str]):
    """Delete specific documents from a collection by ID."""
    collection = get_or_create_collection(collection_name)
    collection.delete(ids=ids)
    logger.info(f"Deleted {len(ids)} documents from {collection_name}")


def collection_count(collection_name: str) -> int:
    """Get the number of documents in a collection."""
    try:
        collection = get_or_create_collection(collection_name)
        return collection.count()
    except Exception:
        return 0


# ============================================================
# UTILITIES
# ============================================================

def get_all_collection_stats() -> dict:
    """Get document counts for all collections. Used by admin/health endpoints."""
    stats = {}
    for name in list_collections():
        stats[name] = collection_count(name)
    return stats


def reset_all():
    """Nuclear option — delete all collections. For testing only."""
    client = _get_client()
    client.reset()
    logger.warning("All ChromaDB collections have been reset!")

