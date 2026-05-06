"""Tests for input sanitization helpers."""

from app.core.sanitize import sanitize_chat_input


def test_email_pii_detected():
    _, flags = sanitize_chat_input("reach me at youth@example.org")
    assert flags["pii_detected"] is True
