import pytest

from app.services.rag.embedding_service import embed_text


def test_embed_text_shape():
    vec = embed_text("hello world")
    assert isinstance(vec, list)
    assert len(vec) > 0

