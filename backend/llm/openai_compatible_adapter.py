"""Transport for any OpenAI-compatible /chat/completions endpoint: OpenRouter (default) or a custom base_url."""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx2

from backend import config
from backend.llm.types import ConfigError, LLMError, LLMRaw, LLMRequest, TransientLLMError


class OpenAICompatibleAdapter:
    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: str = "",
        *,
        timeout_s: float = config.LLM_TIMEOUT_S,
        headers: dict[str, str] | None = None,
        require_parameters: bool = False,
        transport: httpx2.AsyncBaseTransport | None = None,
    ):
        self.name = name
        self.base_url = base_url.rstrip("/") + "/"
        self.headers = {"Content-Type": "application/json", **(headers or {})}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        self.timeout_s = timeout_s
        self.require_parameters = require_parameters  # OpenRouter: only route to endpoints honouring response_format
        self.transport = transport  # httpx2.MockTransport in tests
        self._http_loop: asyncio.AbstractEventLoop | None = None
        self._http: httpx2.AsyncClient | None = None

    @classmethod
    def openrouter(cls) -> OpenAICompatibleAdapter:
        if not config.OPENROUTER_API_KEY:
            raise ConfigError("OPENROUTER_API_KEY is not set; add it to .env")
        return cls("openrouter", config.OPENROUTER_BASE_URL, config.OPENROUTER_API_KEY,
                   headers={"X-Title": "Teratai Complaints Agent"}, require_parameters=True)

    @classmethod
    def generic(cls) -> OpenAICompatibleAdapter:
        if not config.OPENAI_COMPAT_BASE_URL:
            raise ConfigError("OPENAI_COMPAT_BASE_URL is not set; add it to .env")
        return cls("openai_compatible", config.OPENAI_COMPAT_BASE_URL, config.OPENAI_COMPAT_API_KEY)

    def _client(self) -> httpx2.AsyncClient:
        """One connection pool per event loop (pools can't cross loops)."""
        loop = asyncio.get_running_loop()
        if self._http is None or self._http_loop is not loop:
            self._http_loop = loop
            self._http = httpx2.AsyncClient(base_url=self.base_url, headers=self.headers,
                                            timeout=self.timeout_s, transport=self.transport)
        return self._http

    def body(self, request: LLMRequest) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.reasoning_effort:
            body["reasoning"] = {"effort": request.reasoning_effort}
        if request.response_format:
            body["response_format"] = request.response_format
            if self.require_parameters:
                body["provider"] = {"require_parameters": True}
        return body

    async def complete(self, request: LLMRequest) -> LLMRaw:
        start = time.perf_counter()
        try:
            response = await self._client().post("chat/completions", json=self.body(request))
        except httpx2.TimeoutException as exc:
            raise TransientLLMError(f"{self.name}: timeout after {self.timeout_s}s") from exc
        except httpx2.TransportError as exc:
            raise TransientLLMError(f"{self.name}: {type(exc).__name__}: {exc}") from exc
        latency_ms = int((time.perf_counter() - start) * 1000)

        if response.status_code == 429 or response.status_code >= 500:
            raise TransientLLMError(f"{self.name}: HTTP {response.status_code}: {response.text[:300]}")
        if response.status_code >= 400:  # bad request, auth, no endpoint for these parameters: retrying won't help
            raise LLMError(f"{self.name}: HTTP {response.status_code}: {response.text[:300]}")

        data = response.json()
        if not data.get("choices"):
            error = data.get("error") or {}
            code = error.get("code") if isinstance(error, dict) else None
            kind = TransientLLMError if code in (429, 502, 503) else LLMError
            raise kind(f"{self.name}: no choices in response: {str(error or data)[:300]}")
        usage = data.get("usage") or {}
        return LLMRaw(
            text=data["choices"][0]["message"].get("content") or "",
            tokens_in=int(usage.get("prompt_tokens") or 0),
            tokens_out=int(usage.get("completion_tokens") or 0),
            cost_usd=usage.get("cost"),
            latency_ms=latency_ms,
            extra={"cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)},
        )
