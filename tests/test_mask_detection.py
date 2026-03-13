"""Tests for mask detection response parsing."""
import pytest
from app.services.trust_engine.mask_detection import _parse_analysis, _default_result
from app.core.constants import Vibe


class TestMaskParsing:
    def test_valid_json(self):
        raw = '{"detected_vibe": "angry", "confidence": 0.8, "mask_detected": true, "reasoning": "test", "sentiment_score": -0.5, "key_indicators": ["fatigue"]}'
        r = _parse_analysis(raw, Vibe.SOLID)
        assert r["detected_vibe"] == "angry"
        assert r["mask_detected"] is True

    def test_markdown_fences(self):
        raw = '```json\n{"detected_vibe": "angry", "confidence": 0.7, "mask_detected": true, "reasoning": "t", "sentiment_score": -0.3, "key_indicators": []}\n```'
        r = _parse_analysis(raw, Vibe.SOLID)
        assert r["mask_detected"] is True

    def test_preamble_before_json(self):
        raw = 'Analysis:\n{"detected_vibe": "solid", "confidence": 0.4, "mask_detected": false, "reasoning": "ok", "sentiment_score": 0.2, "key_indicators": []}'
        r = _parse_analysis(raw, Vibe.SOLID)
        assert r["mask_detected"] is False

    def test_low_confidence_not_flagged(self):
        raw = '{"detected_vibe": "angry", "confidence": 0.4, "mask_detected": true, "reasoning": "low", "sentiment_score": -0.2, "key_indicators": []}'
        r = _parse_analysis(raw, Vibe.SOLID)
        assert r["mask_detected"] is False  # Below 0.6 threshold

    def test_high_confidence_flagged(self):
        raw = '{"detected_vibe": "angry", "confidence": 0.85, "mask_detected": true, "reasoning": "clear", "sentiment_score": -0.7, "key_indicators": ["anger"]}'
        r = _parse_analysis(raw, Vibe.SOLID)
        assert r["mask_detected"] is True

    def test_malformed_returns_default(self):
        r = _parse_analysis("not json at all", Vibe.SOLID)
        assert r["mask_detected"] is False
        assert r["detected_vibe"] == "solid"

    def test_confidence_clamped(self):
        raw = '{"detected_vibe": "angry", "confidence": 1.5, "mask_detected": true, "reasoning": "t", "sentiment_score": 0, "key_indicators": []}'
        r = _parse_analysis(raw, Vibe.SOLID)
        assert r["confidence"] == 1.0

    def test_default_result(self):
        r = _default_result(Vibe.ANGRY)
        assert r["mask_detected"] is False
        assert r["detected_vibe"] == "angry"
