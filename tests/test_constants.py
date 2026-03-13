"""Tests for constants, character prompts, and configuration."""
import pytest
from app.core.constants import (
    Character, Vibe, SafeHarborLevel, TrustTier, ModelProvider, ModelID,
    TaskType, CHARACTER_MODEL_MAP, TASK_MODEL_MAP, MODEL_COSTS,
    TRUST_SCORE_WEIGHTS, TRUST_TIER_THRESHOLDS, INTAKE_SCORING,
    VOUCH_CONFIG, PROVIDER_RATE_LIMITS, CHARACTER_ASSIGNMENT_RULES,
    VIBE_EMOJI_MAP,
)
from app.services.characters.prompts import (
    get_character_prompt, get_character_prompt_with_context, SYSTEM_PROMPTS,
)


class TestPrompts:
    def test_all_characters_have_prompts(self):
        for c in Character:
            p = get_character_prompt(c)
            assert isinstance(p, str) and len(p) > 100

    def test_challenger_keywords(self):
        p = get_character_prompt(Character.CHALLENGER).lower()
        assert "mask" in p
        assert "strateg" in p  # strategy or strategic

    def test_navigator_keywords(self):
        p = get_character_prompt(Character.NAVIGATOR).lower()
        assert "crisis" in p or "overwhelm" in p

    def test_straight_shooter_keywords(self):
        p = get_character_prompt(Character.STRAIGHT_SHOOTER).lower()
        assert "tactical" in p or "action" in p

    def test_strategist_keywords(self):
        p = get_character_prompt(Character.STRATEGIST).lower()
        assert "long" in p and "plan" in p

    def test_context_injection(self):
        p = get_character_prompt_with_context(
            Character.CHALLENGER,
            user_context="USER: Marcus, GPA 1.8",
            rag_context="Legal: right to remain silent",
        )
        assert "Marcus" in p
        assert "remain silent" in p
        assert "--- USER CONTEXT ---" in p
        assert "--- RELEVANT INFORMATION ---" in p

    def test_no_context(self):
        p = get_character_prompt_with_context(Character.NAVIGATOR)
        assert "USER CONTEXT" not in p


class TestConstants:
    def test_vibes_have_emojis(self):
        for v in Vibe:
            assert v in VIBE_EMOJI_MAP

    def test_all_characters_in_assignment_rules(self):
        assigned = set(CHARACTER_ASSIGNMENT_RULES.values())
        for c in Character:
            assert c in assigned

    def test_task_types_mapped(self):
        assert TaskType.ANALYTICAL in TASK_MODEL_MAP
        assert TaskType.UTILITY in TASK_MODEL_MAP

    def test_tier_thresholds_ascending(self):
        vals = [TRUST_TIER_THRESHOLDS[t] for t in [TrustTier.THE_WATCH, TrustTier.THE_FLEX, TrustTier.THE_VETTED]]
        assert vals == sorted(vals)

    def test_intake_scoring(self):
        assert INTAKE_SCORING["q1_check_box"] > INTAKE_SCORING["q1_win_freedom"]
        assert INTAKE_SCORING["q3_specific_trap"] > INTAKE_SCORING["q3_dont_know"]

    def test_vouch_config_keys(self):
        assert "expiry_hours" in VOUCH_CONFIG
        assert "curfew_extension_cost" in VOUCH_CONFIG

    def test_all_providers_have_rate_limits(self):
        for p in ModelProvider:
            assert p in PROVIDER_RATE_LIMITS

    def test_trust_weights_sane(self):
        w = TRUST_SCORE_WEIGHTS
        assert w["honesty_bonus"] > 0
        assert w["mask_penalty"] < 0
        assert w["weight_hard_day"] > w["weight_normal_day"]
        assert 0 < w["credit_decay_rate"] < 1
