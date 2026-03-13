"""Tests for RAG classifier and document chunking."""
import pytest
from app.services.rag.document_processor import chunk_text, extract_text
from app.services.rag.rag_classifier import classify
from app.core.constants import Character, Vibe, SafeHarborLevel


class TestChunking:
    def test_empty(self):
        assert chunk_text("") == []

    def test_short_single_chunk(self):
        chunks = chunk_text("Short paragraph about grounding.")
        assert len(chunks) == 1

    def test_paragraphs_split(self):
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunks = chunk_text(text, max_chunk_tokens=10)
        assert len(chunks) >= 2

    def test_indices_sequential(self):
        chunks = chunk_text("Para.\n\n" * 10, max_chunk_tokens=10)
        for i, c in enumerate(chunks):
            assert c["index"] == i

    def test_chunks_have_text(self):
        chunks = chunk_text("Content A.\n\nContent B.")
        for c in chunks:
            assert len(c["text"].strip()) > 0


class TestTextExtraction:
    def test_plain_text(self):
        assert "Hello" in extract_text(b"Hello world", "test.txt")

    def test_markdown(self):
        assert "Title" in extract_text(b"# Title\n\nBody", "test.md")


class TestRagClassifier:
    def test_crisis_always_triggers(self):
        d = classify("I can't take this anymore I want to end it", Character.NAVIGATOR)
        assert d.include_knowledge_base is True
        assert d.reason == "crisis_keywords_detected"

    def test_safe_harbor_red(self):
        d = classify("I feel okay", Character.NAVIGATOR, safe_harbor_level=SafeHarborLevel.RED)
        assert d.include_knowledge_base is True

    def test_navigator_crisis_mode(self):
        d = classify("Everything falling apart", Character.NAVIGATOR, vibe=Vibe.STORM)
        assert d.include_knowledge_base is True

    def test_legal_question(self):
        d = classify("What are my rights if probation officer shows up?", Character.STRAIGHT_SHOOTER, has_user_docs=True)
        assert d.include_knowledge_base is True
        assert d.include_user_docs is True

    def test_resource_question(self):
        d = classify("Where can I find a shelter?", Character.NAVIGATOR)
        assert d.include_knowledge_base is True

    def test_challenger_trap(self):
        d = classify("My boy hit me up about money", Character.CHALLENGER, has_user_docs=True)
        assert d.include_patterns is True

    def test_strategist_always_patterns(self):
        d = classify("Let's plan my next two weeks", Character.STRATEGIST)
        assert d.include_patterns is True

    def test_casual_no_rag(self):
        d = classify("yeah whatever", Character.CHALLENGER)
        assert d.include_knowledge_base is False

    def test_general_question(self):
        d = classify("What should I do about this situation?", Character.NAVIGATOR)
        assert d.include_knowledge_base is True

    def test_personal_reference(self):
        d = classify("What does my court order say about curfew", Character.STRAIGHT_SHOOTER, has_user_docs=True)
        assert d.include_user_docs is True
