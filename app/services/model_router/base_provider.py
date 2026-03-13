"""
Base LLM Provider
==================
Abstract interface that every LLM provider (Anthropic, OpenAI, Google, Groq) implements.

Architecture Note:
    This abstraction is what makes the Model Router work.
    The router doesn't care which provider it's talking to —
    it calls the same interface and gets the same response format.
    Adding a new provider = implement this interface + register it.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional
from enum import Enum


@dataclass
class LLMMessage:
    """A single message in a conversation."""
    role: str          # "system", "user", "assistant"
    content: str


@dataclass
class LLMRequest:
    """
    Standardized request to any LLM provider.
    The Model Router builds this, the provider adapts it to their API format.
    """
    messages: list[LLMMessage]
    model: str                          # Provider-specific model ID
    max_tokens: int = 1024
    temperature: float = 0.7
    stream: bool = False
    # Metadata for tracking
    task_type: str = "conversational"   # conversational | analytical | utility
    character: Optional[str] = None     # Which character is active


@dataclass
class LLMResponse:
    """
    Standardized response from any LLM provider.
    Includes the content + usage data for credit tracking.
    """
    content: str
    model: str
    provider: str
    tokens_in: int = 0
    tokens_out: int = 0
    finish_reason: str = "stop"
    response_time_ms: int = 0
    # For streaming, this accumulates
    is_complete: bool = True


@dataclass
class LLMStreamChunk:
    """A single chunk in a streaming response."""
    content: str                # The text delta
    is_final: bool = False      # True for the last chunk
    # Final chunk includes full usage stats
    tokens_in: int = 0
    tokens_out: int = 0


class ProviderStatus(str, Enum):
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    NO_API_KEY = "no_api_key"


class BaseLLMProvider(ABC):
    """
    Abstract base class for all LLM providers.
    Each provider must implement:
      - generate(): Single response
      - stream(): Streaming response (for SSE)
      - check_health(): Verify the provider is reachable
    """

    provider_name: str = "base"

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a complete response (non-streaming)."""
        ...

    @abstractmethod
    async def stream(self, request: LLMRequest) -> AsyncGenerator[LLMStreamChunk, None]:
        """Generate a streaming response (for SSE to frontend)."""
        ...

    @abstractmethod
    async def check_health(self) -> ProviderStatus:
        """Check if this provider is available (API key valid, not rate limited)."""
        ...

    @abstractmethod
    def estimate_cost(self, tokens_in: int, tokens_out: int, model: str) -> float:
        """Estimate the cost in USD for a given token count."""
        ...
