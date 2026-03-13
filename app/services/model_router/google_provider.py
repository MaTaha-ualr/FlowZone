"""
Google Gemini Provider (Gemini 1.5 Flash)
============================================
Used primarily for: Navigator character, analytical tasks (mask detection, sentiment)
Why: Free tier (15 RPM, 1500 RPD), good empathetic tone, handles structured JSON well.

This is your free-tier workhorse. The Navigator lives here.
Analytical tasks (mask detection, sentiment sync) also run here.

Rate limits (free tier):
    - 15 requests per minute
    - 1,500 requests per day
    - 1,000,000 tokens per minute
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


class GoogleProvider(BaseLLMProvider):
    provider_name = "google"
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self):
        self.api_key = settings.google_ai_api_key
        self.client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=10.0),
            )
        return self.client

    def _build_url(self, model: str, stream: bool = False) -> str:
        action = "streamGenerateContent" if stream else "generateContent"
        return f"{self.BASE_URL}/{model}:{action}?key={self.api_key}"

    def _convert_messages(self, messages: list) -> tuple[Optional[str], list[dict]]:
        """
        Convert standard messages to Gemini format.
        Gemini uses 'user' and 'model' roles, with system instruction separate.
        """
        system_instruction = None
        contents = []

        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
            elif msg.role == "assistant":
                contents.append({
                    "role": "model",
                    "parts": [{"text": msg.content}]
                })
            else:
                contents.append({
                    "role": "user",
                    "parts": [{"text": msg.content}]
                })

        return system_instruction, contents

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise ValueError("Google AI API key not configured")

        client = await self._get_client()
        start_time = time.time()

        system_instruction, contents = self._convert_messages(request.messages)

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": request.max_tokens,
                "temperature": request.temperature,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        url = self._build_url(request.model)
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        elapsed_ms = int((time.time() - start_time) * 1000)

        # Extract content from Gemini response
        content = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for part in parts:
                content += part.get("text", "")

        # Token usage
        usage = data.get("usageMetadata", {})
        tokens_in = usage.get("promptTokenCount", 0)
        tokens_out = usage.get("candidatesTokenCount", 0)

        return LLMResponse(
            content=content,
            model=request.model,
            provider=self.provider_name,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            finish_reason=candidates[0].get("finishReason", "STOP") if candidates else "ERROR",
            response_time_ms=elapsed_ms,
        )

    async def stream(self, request: LLMRequest) -> AsyncGenerator[LLMStreamChunk, None]:
        if not self.api_key:
            raise ValueError("Google AI API key not configured")

        client = await self._get_client()

        system_instruction, contents = self._convert_messages(request.messages)

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": request.max_tokens,
                "temperature": request.temperature,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        url = self._build_url(request.model, stream=True) + "&alt=sse"
        tokens_in = 0
        tokens_out = 0

        async with client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                try:
                    event = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                candidates = event.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for part in parts:
                        text = part.get("text", "")
                        if text:
                            yield LLMStreamChunk(content=text)

                usage = event.get("usageMetadata", {})
                if usage:
                    tokens_in = usage.get("promptTokenCount", tokens_in)
                    tokens_out = usage.get("candidatesTokenCount", tokens_out)

        yield LLMStreamChunk(
            content="", is_final=True, tokens_in=tokens_in, tokens_out=tokens_out
        )

    async def check_health(self) -> ProviderStatus:
        if not self.api_key:
            return ProviderStatus.NO_API_KEY
        try:
            client = await self._get_client()
            url = self._build_url("gemini-1.5-flash")
            response = await client.post(
                url,
                json={"contents": [{"parts": [{"text": "hi"}]}],
                       "generationConfig": {"maxOutputTokens": 1}},
            )
            if response.status_code == 429:
                return ProviderStatus.RATE_LIMITED
            if response.status_code == 200:
                return ProviderStatus.AVAILABLE
            return ProviderStatus.ERROR
        except Exception:
            return ProviderStatus.ERROR

    def estimate_cost(self, tokens_in: int, tokens_out: int, model: str) -> float:
        # Free tier — no cost
        return 0.0

    async def close(self):
        if self.client and not self.client.is_closed:
            await self.client.aclose()
