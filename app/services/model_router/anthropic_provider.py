"""
Anthropic Provider (Claude)
=============================
Used primarily for: The Challenger character
Why: Best at maintaining complex personas, nuanced pushback, instruction-following.

Cost: $3/1M input, $15/1M output (Sonnet)
Rate limit: 50 RPM (paid tier)

This is your premium model — the router only sends requests here
when the budget tier is green and the Challenger is active.
"""

import time
from typing import AsyncGenerator, Optional
import httpx
from app.core.config import settings
from app.core.constants import MODEL_COSTS, ModelID
from app.services.model_router.base_provider import (
    BaseLLMProvider, LLMRequest, LLMResponse, LLMStreamChunk, ProviderStatus
)


class AnthropicProvider(BaseLLMProvider):
    provider_name = "anthropic"
    BASE_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    def __init__(self):
        self.api_key = settings.anthropic_api_key
        self.client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=10.0),
                headers={
                    "x-api-key": self.api_key or "",
                    "anthropic-version": self.API_VERSION,
                    "content-type": "application/json",
                },
            )
        return self.client

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Send a request to Claude and get a complete response."""
        if not self.api_key:
            raise ValueError("Anthropic API key not configured")

        client = await self._get_client()
        start_time = time.time()

        # Convert messages to Anthropic format
        # Anthropic uses a separate "system" parameter
        system_msg = None
        messages = []
        for msg in request.messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                messages.append({"role": msg.role, "content": msg.content})

        payload = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": messages,
        }
        if system_msg:
            payload["system"] = system_msg

        response = await client.post(self.BASE_URL, json=payload)
        response.raise_for_status()
        data = response.json()

        elapsed_ms = int((time.time() - start_time) * 1000)

        # Extract content
        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")

        usage = data.get("usage", {})
        tokens_in = usage.get("input_tokens", 0)
        tokens_out = usage.get("output_tokens", 0)

        return LLMResponse(
            content=content,
            model=request.model,
            provider=self.provider_name,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            finish_reason=data.get("stop_reason", "end_turn"),
            response_time_ms=elapsed_ms,
        )

    async def stream(self, request: LLMRequest) -> AsyncGenerator[LLMStreamChunk, None]:
        """Stream a response from Claude using SSE."""
        if not self.api_key:
            raise ValueError("Anthropic API key not configured")

        client = await self._get_client()

        system_msg = None
        messages = []
        for msg in request.messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                messages.append({"role": msg.role, "content": msg.content})

        payload = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": messages,
            "stream": True,
        }
        if system_msg:
            payload["system"] = system_msg

        tokens_in = 0
        tokens_out = 0

        async with client.stream("POST", self.BASE_URL, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break

                import json
                try:
                    event = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type", "")

                if event_type == "content_block_delta":
                    delta = event.get("delta", {})
                    text = delta.get("text", "")
                    if text:
                        yield LLMStreamChunk(content=text)

                elif event_type == "message_delta":
                    usage = event.get("usage", {})
                    tokens_out = usage.get("output_tokens", 0)

                elif event_type == "message_start":
                    msg = event.get("message", {})
                    usage = msg.get("usage", {})
                    tokens_in = usage.get("input_tokens", 0)

        # Final chunk with usage stats
        yield LLMStreamChunk(
            content="",
            is_final=True,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )

    async def check_health(self) -> ProviderStatus:
        """Verify the Anthropic API is reachable."""
        if not self.api_key:
            return ProviderStatus.NO_API_KEY
        try:
            client = await self._get_client()
            # Minimal request to check connectivity
            response = await client.post(
                self.BASE_URL,
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
            if response.status_code == 429:
                return ProviderStatus.RATE_LIMITED
            if response.status_code in (200, 201):
                return ProviderStatus.AVAILABLE
            return ProviderStatus.ERROR
        except Exception:
            return ProviderStatus.ERROR

    def estimate_cost(self, tokens_in: int, tokens_out: int, model: str) -> float:
        """Estimate cost in USD."""
        model_enum = ModelID(model) if model in [m.value for m in ModelID] else None
        if model_enum and model_enum in MODEL_COSTS:
            costs = MODEL_COSTS[model_enum]
            return (tokens_in * costs["input"] / 1_000_000) + \
                   (tokens_out * costs["output"] / 1_000_000)
        return 0.0

    async def close(self):
        if self.client and not self.client.is_closed:
            await self.client.aclose()
