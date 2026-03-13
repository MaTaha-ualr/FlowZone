"""Tests for Model Router budget-aware selection and fallback chains."""
import pytest
from app.services.model_router.router import ModelRouter
from app.services.model_router.credit_manager import BudgetTier
from app.core.constants import Character, ModelProvider, ModelID, CHARACTER_MODEL_MAP, MODEL_COSTS


class TestModelChainSelection:
    def setup_method(self):
        self.router = ModelRouter()

    def test_green_challenger_gets_claude(self):
        chain = self.router._get_model_chain(Character.CHALLENGER, BudgetTier.GREEN)
        assert chain[0]["provider"] == ModelProvider.ANTHROPIC

    def test_green_strategist_gets_openai(self):
        chain = self.router._get_model_chain(Character.STRATEGIST, BudgetTier.GREEN)
        assert chain[0]["provider"] == ModelProvider.OPENAI

    def test_green_navigator_gets_gemini(self):
        chain = self.router._get_model_chain(Character.NAVIGATOR, BudgetTier.GREEN)
        assert chain[0]["provider"] == ModelProvider.GOOGLE

    def test_green_straight_shooter_gets_groq(self):
        chain = self.router._get_model_chain(Character.STRAIGHT_SHOOTER, BudgetTier.GREEN)
        assert chain[0]["provider"] == ModelProvider.GROQ

    def test_yellow_challenger_keeps_premium(self):
        chain = self.router._get_model_chain(Character.CHALLENGER, BudgetTier.YELLOW)
        assert chain[0]["provider"] == ModelProvider.ANTHROPIC

    def test_yellow_strategist_downgrades(self):
        chain = self.router._get_model_chain(Character.STRATEGIST, BudgetTier.YELLOW)
        providers = [m["provider"] for m in chain]
        assert ModelProvider.OPENAI not in providers

    def test_red_only_free_models(self):
        for character in Character:
            chain = self.router._get_model_chain(character, BudgetTier.RED)
            for m in chain:
                assert m["provider"] in (ModelProvider.GOOGLE, ModelProvider.GROQ)

    def test_red_always_has_fallback(self):
        for character in Character:
            chain = self.router._get_model_chain(character, BudgetTier.RED)
            assert len(chain) >= 1


class TestModelCosts:
    def test_free_models_zero_cost(self):
        assert MODEL_COSTS[ModelID.GEMINI_FLASH]["input"] == 0
        assert MODEL_COSTS[ModelID.LLAMA_70B]["input"] == 0

    def test_paid_models_have_cost(self):
        assert MODEL_COSTS[ModelID.CLAUDE_SONNET]["output"] > 0
        assert MODEL_COSTS[ModelID.GPT_4O_MINI]["output"] > 0

    def test_all_characters_have_mappings(self):
        for c in Character:
            assert c in CHARACTER_MODEL_MAP
            assert "primary" in CHARACTER_MODEL_MAP[c]
            assert len(CHARACTER_MODEL_MAP[c]["fallbacks"]) >= 1
