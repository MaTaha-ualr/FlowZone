"""
Groq Provider (Llama 3.1 + Whisper)
======================================
Used primarily for:
    - Straight Shooter character (Llama 70B — direct, tactical)
    - Utility tasks (Llama 8B — sanitization, summarization)
    - Speech-to-Text (Whisper large-v3)

Why: Free tier is incredibly generous (30 RPM, 14.4K RPD) and
Groq's custom LPU hardware makes inference blazing fast.
This is your safety net — if everything else fails, Groq is there.

Rate limits (free tier):
    - Llama 70B: 30 RPM, 14,400 RPD, 6,000 tokens/min
    - Llama 8B: 30 RPM, 14,400 RPD, 6,000 tokens/min
    - Whisper: 20 RPM, 2,000 RPD
"""

import time
import json
from typing import AsyncGenerator, Optional
import httpx
from app.core.config import settings
from app.services.model_router.base_provider import (
    BaseLLMProvider, LLMRequest, LLMResponse, LLMStreamChunk, ProviderStatus
)


class GroqProvider(BaseLLMProvider):
    """
    Groq provider for Llama models and Whisper STT.
    Uses OpenAI-compatible API format (which makes it easy).
    """
    provider_name = "groq"
    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
    WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

    def __init__(self):
        self.api_key = settings.groq_api_key
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
            raise ValueError("Groq API key not configured")

        client = await self._get_client()
        start_time = time.time()

        # Groq uses OpenAI-compatible format
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
            raise ValueError("Groq API key not configured")

        client = await self._get_client()

        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        payload = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": messages,
            "stream": True,
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

                # Usage data (Groq includes in x-groq headers and final chunks)
                if event.get("x_groq", {}).get("usage"):
                    usage = event["x_groq"]["usage"]
                    tokens_in = usage.get("prompt_tokens", 0)
                    tokens_out = usage.get("completion_tokens", 0)

                choices = event.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    text = delta.get("content", "")
                    if text:
                        yield LLMStreamChunk(content=text)

        yield LLMStreamChunk(
            content="", is_final=True, tokens_in=tokens_in, tokens_out=tokens_out
        )

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.wav") -> dict:
        """
        Transcribe audio using Groq-hosted Whisper large-v3.
        Returns: {"text": "transcribed text", "duration": seconds}

        This is separate from the chat interface because Whisper
        uses a multipart form upload, not JSON.
        """
        if not self.api_key:
            raise ValueError("Groq API key not configured")

        # Need a separate client without the JSON content-type header
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={"Authorization": f"Bearer {self.api_key}"},
        ) as client:
            files = {
                "file": (filename, audio_bytes, "audio/wav"),
            }
            data = {
                "model": "whisper-large-v3",
                "response_format": "verbose_json",
                "language": "en",
            }

            response = await client.post(self.WHISPER_URL, files=files, data=data)
            response.raise_for_status()
            result = response.json()

            return {
                "text": result.get("text", ""),
                "duration": result.get("duration", 0),
                "language": result.get("language", "en"),
            }

    async def check_health(self) -> ProviderStatus:
        if not self.api_key:
            return ProviderStatus.NO_API_KEY
        try:
            client = await self._get_client()
            response = await client.post(
                self.BASE_URL,
                json={
                    "model": "llama-3.1-8b-instant",
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
        # Free tier — no cost
        return 0.0

    async def close(self):
        if self.client and not self.client.is_closed:
            await self.client.aclose()
