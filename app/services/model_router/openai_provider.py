"""
OpenAI Provider (GPT-4o-mini)
================================
Used primarily for: The Strategist character
Why: Cheap ($0.15/1M input), good at strategic/planning tasks.

This is your "smart but affordable" option.
The Strategist needs reasoning capability but isn't triggered as often.
"""

import time
import json
from typing import AsyncGenerator, Optional
import httpx
from app.core.config import settings
from app.core.constants import MODEL_COSTS, ModelID
from app.services.model_router.base_provider import (
    BaseLLMProvider, LLMRequest, LLMResponse, LLMStreamChunk, ProviderStatus
)


class OpenAIProvider(BaseLLMProvider):
    provider_name = "openai"
    BASE_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self):
        self.api_key = settings.openai_api_key
        self.client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=10.0),
                headers={
                    "Authorization": f"Bearer {self.api_key or ''}",
                    "Content-Type": "application/json",
                },
            )
        return self.client

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")

        client = await self._get_client()
        start_time = time.time()

        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        payload = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": messages,
        }
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.frequency_penalty is not None:
            payload["frequency_penalty"] = request.frequency_penalty
        if request.presence_penalty is not None:
            payload["presence_penalty"] = request.presence_penalty

        response = await client.post(self.BASE_URL, json=payload)
        response.raise_for_status()
        data = response.json()

        elapsed_ms = int((time.time() - start_time) * 1000)

        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})

        return LLMResponse(
            content=content,
            model=request.model,
            provider=self.provider_name,
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
            response_time_ms=elapsed_ms,
        )

    async def stream(self, request: LLMRequest) -> AsyncGenerator[LLMStreamChunk, None]:
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")

        client = await self._get_client()

        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        payload = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.frequency_penalty is not None:
            payload["frequency_penalty"] = request.frequency_penalty
        if request.presence_penalty is not None:
            payload["presence_penalty"] = request.presence_penalty

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

                try:
                    event = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                # Usage in final chunk
                if event.get("usage"):
                    tokens_in = event["usage"].get("prompt_tokens", 0)
                    tokens_out = event["usage"].get("completion_tokens", 0)

                choices = event.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    text = delta.get("content", "")
                    if text:
                        yield LLMStreamChunk(content=text)

        yield LLMStreamChunk(
            content="", is_final=True, tokens_in=tokens_in, tokens_out=tokens_out
        )

    async def check_health(self) -> ProviderStatus:
        if not self.api_key:
            return ProviderStatus.NO_API_KEY
        try:
            client = await self._get_client()
            response = await client.post(
                self.BASE_URL,
                json={
                    "model": "gpt-4o-mini",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
            if response.status_code == 429:
                return ProviderStatus.RATE_LIMITED
            if response.status_code == 200:
                return ProviderStatus.AVAILABLE
            return ProviderStatus.ERROR
        except Exception:
            return ProviderStatus.ERROR

    def estimate_cost(self, tokens_in: int, tokens_out: int, model: str) -> float:
        model_enum = ModelID(model) if model in [m.value for m in ModelID] else None
        if model_enum and model_enum in MODEL_COSTS:
            costs = MODEL_COSTS[model_enum]
            return (tokens_in * costs["input"] / 1_000_000) + \
                   (tokens_out * costs["output"] / 1_000_000)
        return 0.0

    async def close(self):
        if self.client and not self.client.is_closed:
            await self.client.aclose()
