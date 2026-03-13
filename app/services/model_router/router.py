"""
Model Router — The Brain of FlowZone
========================================
This is the single most important service in the backend.

Every LLM interaction in the system flows through here:
    Character conversation → route()
    Mask detection → route_analytical()
    Note sanitization → route_utility()

The router:
    1. Checks the budget tier (green/yellow/red)
    2. Looks up the character-to-model mapping
    3. Checks if the primary model's provider is available
    4. If not, walks the fallback chain
    5. Sends the request to the selected provider
    6. Logs usage to the credit manager
    7. Returns the response

Architecture Note:
    The router is STATELESS — it reads character mappings from constants
    and budget state from the credit manager. This means you can change
    model assignments in constants.py without touching router code.
"""

import logging
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    Character, TaskType, ModelProvider, ModelID,
    CHARACTER_MODEL_MAP, TASK_MODEL_MAP,
)
from app.services.model_router.base_provider import (
    BaseLLMProvider, LLMRequest, LLMResponse, LLMStreamChunk,
    LLMMessage, ProviderStatus,
)
from app.services.model_router.credit_manager import (
    credit_manager, BudgetTier,
)
from app.services.model_router.anthropic_provider import AnthropicProvider
from app.services.model_router.openai_provider import OpenAIProvider
from app.services.model_router.google_provider import GoogleProvider
from app.services.model_router.groq_provider import GroqProvider

logger = logging.getLogger(__name__)


class ModelRouter:
    """
    Central routing service for all LLM requests.

    Usage:
        router = ModelRouter()

        # Character conversation
        response = await router.route(
            character=Character.CHALLENGER,
            messages=[LLMMessage("system", "..."), LLMMessage("user", "...")],
            db=db_session,
            user_id=user_id,
            session_id=session_id,
        )

        # Analytical task (mask detection)
        response = await router.route_analytical(
            messages=[...],
            db=db_session,
        )

        # Utility task (sanitization)
        response = await router.route_utility(
            messages=[...],
            db=db_session,
        )
    """

    def __init__(self):
        # Initialize all providers
        self._providers: dict[ModelProvider, BaseLLMProvider] = {
            ModelProvider.ANTHROPIC: AnthropicProvider(),
            ModelProvider.OPENAI: OpenAIProvider(),
            ModelProvider.GOOGLE: GoogleProvider(),
            ModelProvider.GROQ: GroqProvider(),
        }

    def get_provider(self, provider_name: ModelProvider) -> BaseLLMProvider:
        """Get a provider instance by name."""
        return self._providers[provider_name]

    # ================================================================
    # PRIMARY ROUTING METHODS
    # ================================================================

    async def route(
        self,
        character: Character,
        messages: list[LLMMessage],
        db: AsyncSession,
        user_id=None,
        session_id=None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[LLMStreamChunk, None]:
        """
        Route a character conversation to the right model.

        This is the main entry point for all chat interactions.
        It selects the model based on character mapping + budget tier,
        tries the primary model, falls back on failure.
        """
        # 1. Get budget tier
        budget_tier = await credit_manager.get_budget_tier(db)
        logger.info(f"Budget tier: {budget_tier.value} | Character: {character.value}")

        # 2. Get the model chain for this character
        # Override budget behavior: always treat as GREEN (use best models first)
        model_chain = self._get_model_chain(character, BudgetTier.GREEN)
        logger.info(f"Model chain: {[f'{m['provider'].value}/{m['model'].value}' for m in model_chain]}")

        # 3. Try each model in the chain
        return await self._execute_with_fallback(
            model_chain=model_chain,
            messages=messages,
            task_type=TaskType.CONVERSATIONAL,
            db=db,
            user_id=user_id,
            session_id=session_id,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=stream,
            character=character.value,
        )

    async def route_analytical(
        self,
        messages: list[LLMMessage],
        db: AsyncSession,
        user_id=None,
        session_id=None,
        max_tokens: int = 512,
        temperature: float = 0.2,  # Low temp for analytical precision
    ) -> LLMResponse:
        """
        Route an analytical task (mask detection, sentiment, JSON extraction).
        Always uses free models — no budget concerns.
        """
        config = TASK_MODEL_MAP[TaskType.ANALYTICAL]
        model_chain = [config["primary"]] + config["fallbacks"]

        result = await self._execute_with_fallback(
            model_chain=model_chain,
            messages=messages,
            task_type=TaskType.ANALYTICAL,
            db=db,
            user_id=user_id,
            session_id=session_id,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=False,
        )
        return result

    async def route_utility(
        self,
        messages: list[LLMMessage],
        db: AsyncSession,
        user_id=None,
        max_tokens: int = 512,
        temperature: float = 0.3,
    ) -> LLMResponse:
        """
        Route a utility task (sanitization, summarization).
        Always uses the cheapest free model.
        """
        config = TASK_MODEL_MAP[TaskType.UTILITY]
        model_chain = [config["primary"]] + config["fallbacks"]

        result = await self._execute_with_fallback(
            model_chain=model_chain,
            messages=messages,
            task_type=TaskType.UTILITY,
            db=db,
            user_id=user_id,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=False,
        )
        return result

    # ================================================================
    # MODEL SELECTION LOGIC
    # ================================================================

    def _get_model_chain(
        self,
        character: Character,
        budget_tier: BudgetTier,
    ) -> list[dict]:
        """
        Build the ordered list of models to try for a given character + budget tier.

        Budget tier affects which models are in the chain:
            GREEN  — primary + all fallbacks
            YELLOW — if primary is paid, skip it for non-critical characters
            RED    — only free models
        """
        config = CHARACTER_MODEL_MAP[character]
        primary = config["primary"]
        fallbacks = config["fallbacks"]

        if budget_tier == BudgetTier.GREEN:
            # All models available
            return [primary] + fallbacks

        elif budget_tier == BudgetTier.YELLOW:
            # Only the Challenger keeps its premium model
            # Everyone else downgrades to free
            primary_provider = primary["provider"]
            if character == Character.CHALLENGER:
                return [primary] + fallbacks
            elif primary_provider in (ModelProvider.ANTHROPIC, ModelProvider.OPENAI):
                # Skip the paid primary, go straight to fallbacks
                logger.info(f"Budget YELLOW: Skipping paid model for {character.value}")
                return fallbacks
            else:
                return [primary] + fallbacks

        else:  # RED
            # Only free models
            free_models = [
                m for m in [primary] + fallbacks
                if m["provider"] in (ModelProvider.GOOGLE, ModelProvider.GROQ)
            ]
            if not free_models:
                # Ultimate fallback — Groq Llama 8B
                free_models = [{"provider": ModelProvider.GROQ, "model": ModelID.LLAMA_8B}]
            logger.warning(f"Budget RED: Free models only for {character.value}")
            return free_models

    # ================================================================
    # EXECUTION WITH FALLBACK
    # ================================================================

    async def _execute_with_fallback(
        self,
        model_chain: list[dict],
        messages: list[LLMMessage],
        task_type: TaskType | str,
        db: AsyncSession,
        user_id=None,
        session_id=None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stream: bool = False,
        character: str = None,
    ) -> LLMResponse | AsyncGenerator[LLMStreamChunk, None]:
        """
        Try each model in the chain. On failure, fall back to the next one.

        Failure modes handled:
            - Provider API key not configured → skip
            - Provider returns rate limit (429) → skip
            - Provider returns error → skip
            - Provider times out → skip
            - All models fail → return error response
        """
        task_type_str = task_type.value if hasattr(task_type, 'value') else str(task_type)
        last_error = None

        for model_config in model_chain:
            provider_enum = model_config["provider"]
            model_enum = model_config["model"]
            provider = self._providers[provider_enum]
            model_id = model_enum.value

            logger.info(
                f"Trying {provider_enum.value}/{model_id} "
                f"for {task_type_str} (character: {character})"
            )

            try:
                # Build request
                request = LLMRequest(
                    messages=messages,
                    model=model_id,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=stream,
                    task_type=task_type_str,
                    character=character,
                )

                if stream:
                    # For streaming, return the generator directly
                    # (can't easily wrap with fallback mid-stream)
                    return self._stream_with_logging(
                        provider=provider,
                        request=request,
                        task_type_str=task_type_str,
                        db=db,
                        user_id=user_id,
                        session_id=session_id,
                    )
                else:
                    # Non-streaming: execute and log
                    response = await provider.generate(request)

                    # Log usage
                    cost = provider.estimate_cost(
                        response.tokens_in, response.tokens_out, model_id
                    )
                    await credit_manager.log_usage(
                        db=db,
                        provider=provider_enum.value,
                        model=model_id,
                        task_type=task_type_str,
                        tokens_in=response.tokens_in,
                        tokens_out=response.tokens_out,
                        cost=cost,
                        user_id=user_id,
                        session_id=session_id,
                        response_time_ms=response.response_time_ms,
                    )

                    logger.info(
                        f"Success: {provider_enum.value}/{model_id} | "
                        f"Tokens: {response.tokens_in}→{response.tokens_out} | "
                        f"Cost: ${cost:.4f} | Time: {response.response_time_ms}ms"
                    )

                    return response

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Failed: {provider_enum.value}/{model_id} — {type(e).__name__}: {str(e)[:200]}"
                )

                # Log the failure
                await credit_manager.log_usage(
                    db=db,
                    provider=provider_enum.value,
                    model=model_id,
                    task_type=task_type_str,
                    tokens_in=0,
                    tokens_out=0,
                    cost=0,
                    user_id=user_id,
                    session_id=session_id,
                    success=False,
                    error_message=f"{type(e).__name__}: {str(e)[:200]}",
                )

                continue  # Try next model in chain

        # All models failed
        error_msg = f"All models in chain failed. Last error: {last_error}"
        logger.error(error_msg)

        return LLMResponse(
            content=(
                "I'm having trouble connecting right now. "
                "This is a temporary issue — please try again in a moment. "
                "If this keeps happening, let your mentor know."
            ),
            model="error",
            provider="none",
            finish_reason="error",
        )

    async def _stream_with_logging(
        self,
        provider: BaseLLMProvider,
        request: LLMRequest,
        task_type_str: str,
        db: AsyncSession,
        user_id=None,
        session_id=None,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Wrap streaming with usage logging on completion."""
        async for chunk in provider.stream(request):
            yield chunk
            if chunk.is_final:
                cost = provider.estimate_cost(
                    chunk.tokens_in, chunk.tokens_out, request.model
                )
                await credit_manager.log_usage(
                    db=db,
                    provider=provider.provider_name,
                    model=request.model,
                    task_type=task_type_str,
                    tokens_in=chunk.tokens_in,
                    tokens_out=chunk.tokens_out,
                    cost=cost,
                    user_id=user_id,
                    session_id=session_id,
                )

    # ================================================================
    # HEALTH & STATUS
    # ================================================================

    async def check_all_providers(self) -> dict[str, str]:
        """Check health of all providers. Used by /health/detailed."""
        statuses = {}
        for provider_name, provider in self._providers.items():
            status = await provider.check_health()
            statuses[provider_name.value] = status.value
        return statuses

    async def close_all(self):
        """Graceful shutdown — close all HTTP clients."""
        for provider in self._providers.values():
            if hasattr(provider, 'close'):
                await provider.close()


# Singleton instance
model_router = ModelRouter()
