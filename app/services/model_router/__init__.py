"""
Model Router Package
=====================
The central LLM routing system with multi-provider support,
budget-aware fallback chains, and credit management.
"""

from app.services.model_router.router import model_router, ModelRouter
from app.services.model_router.credit_manager import credit_manager, CreditManager, BudgetTier
from app.services.model_router.base_provider import (
    LLMMessage, LLMRequest, LLMResponse, LLMStreamChunk, ProviderStatus,
)

__all__ = [
    "model_router", "ModelRouter",
    "credit_manager", "CreditManager", "BudgetTier",
    "LLMMessage", "LLMRequest", "LLMResponse", "LLMStreamChunk", "ProviderStatus",
]
