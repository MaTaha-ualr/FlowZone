"""
Embedding Service
==================
Wraps sentence-transformers to generate vector embeddings for RAG.

Model: all-MiniLM-L6-v2
    - 384-dimensional vectors
    - Runs on CPU (fast enough for <10K vectors)
    - ~80MB model size
    - Free, open source

Architecture Note:
    The model is loaded ONCE on first use and cached.
    Embedding a query takes ~10ms on CPU.
    Embedding a full document (20 chunks) takes ~200ms.
"""

import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazy-loaded singleton
_model = None
_model_name = None


def _get_model():
    """Lazy-load the embedding model on first use."""
    global _model, _model_name
    if _model is None:
        logger.info(f"Loading embedding model: {settings.embedding_model}...")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.embedding_model)
        _model_name = settings.embedding_model
        logger.info(f"Embedding model loaded. Dimension: {_model.get_sentence_embedding_dimension()}")
    return _model


def embed_text(text: str) -> list[float]:
    """
    Embed a single text string into a vector.
    Used for queries at retrieval time.
    """
    model = _get_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed multiple texts in a batch (more efficient than one-by-one).
    Used during document ingestion.
    """
    if not texts:
        return []
    model = _get_model()
    embeddings = model.encode(texts, convert_to_numpy=True, batch_size=32)
    return embeddings.tolist()


def get_embedding_dimension() -> int:
    """Get the vector dimension of the current model."""
    model = _get_model()
    return model.get_sentence_embedding_dimension()

