"""LLMClient: the one place that owns cache, concurrency, JSON mode, retry, validation and usage/cost.

Adapters only send a request and return raw text plus provider-reported usage (see types.Adapter).
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from decimal import Decimal
from typing import Any, Callable, TypeVar

from pydantic import ValidationError

from backend import config
from backend.contracts import LLMUsage
from backend.llm import registry
from backend.llm.cache import LLMCache
from backend.llm.types import Adapter, JsonMode, LLMError, LLMRaw, LLMRequest, ModelSpec, TransientLLMError

log = logging.getLogger(__name__)

T = TypeVar("T")
MAX_ATTEMPTS = 2  # one retry
FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def parse_json(text: str) -> Any:
    """Model text → JSON, tolerating a ```json fence that prompt-only models sometimes add."""
    text = text.strip()
    if m := FENCE_RE.match(text):
        text = m.group(1)
    return json.loads(text)


def with_schema_instruction(messages: list[dict[str, str]], schema: dict[str, Any]) -> list[dict[str, str]]:
    """For json_object / prompt modes the schema goes into the system message (kept in the cacheable prefix)."""
    note = ("\n\nReturn only one JSON object, with no other text, that matches this JSON schema:\n"
            + json.dumps(schema, ensure_ascii=False))
    if messages and messages[0]["role"] == "system":
        return [{"role": "system", "content": messages[0]["content"] + note}, *messages[1:]]
    return [{"role": "system", "content": note.strip()}, *messages]


class LLMClient:
    def __init__(
        self,
        *,
        cache: LLMCache | None = None,
        adapters: dict[str, Adapter] | None = None,
        max_concurrency: int = config.LLM_MAX_CONCURRENCY,
        usd_to_myr: float = config.USD_TO_MYR,
        use_cache: bool = True,
    ):
        self.cache = cache if cache is not None else LLMCache()
        self.adapters = adapters or {}  # overrides for tests; otherwise the registry builds them
        self.max_concurrency = max_concurrency
        self.usd_to_myr = Decimal(str(usd_to_myr))
        self.use_cache = use_cache
        self._gate_loop: asyncio.AbstractEventLoop | None = None
        self._gate: asyncio.Semaphore | None = None

    def adapter(self, provider: str) -> Adapter:
        return self.adapters.get(provider) or registry.get_adapter(provider)

    def _semaphore(self) -> asyncio.Semaphore:
        """One gate per event loop, so the client survives repeated asyncio.run() calls (tests, CLIs)."""
        loop = asyncio.get_running_loop()
        if self._gate is None or self._gate_loop is not loop:
            self._gate_loop, self._gate = loop, asyncio.Semaphore(self.max_concurrency)
        return self._gate

    async def _send(self, spec: ModelSpec, request: LLMRequest, usage: LLMUsage) -> tuple[LLMRaw, bool]:
        """(raw, cached). Network calls add to usage; cache hits add tokens only (zero cost)."""
        key = request.cache_key(spec.provider)
        if self.use_cache and (hit := self.cache.get(key)) is not None:
            usage.tokens_in += hit.tokens_in
            usage.tokens_out += hit.tokens_out
            return hit, True
        async with self._semaphore():
            raw = await self.adapter(spec.provider).complete(request)
        usage.tokens_in += raw.tokens_in
        usage.tokens_out += raw.tokens_out
        usage.latency_ms += raw.latency_ms
        if raw.cost_usd is None:
            log.warning("%s reported no cost; cost_myr counts it as 0", spec)
        else:
            usage.cost_myr += Decimal(str(raw.cost_usd)) * self.usd_to_myr
        return raw, False

    def _remember(self, spec: ModelSpec, request: LLMRequest, raw: LLMRaw) -> None:
        if self.use_cache:
            self.cache.put(request.cache_key(spec.provider), spec.provider, spec.model, raw)

    async def structured(
        self,
        spec: ModelSpec,
        messages: list[dict[str, str]],
        *,
        schema: dict[str, Any],
        schema_name: str,
        convert: Callable[[dict[str, Any]], T],
        json_mode: JsonMode = "json_schema",
        temperature: float = 0.0,
        max_tokens: int = 800,
    ) -> tuple[T, LLMUsage]:
        """Ask for JSON in the strongest mode the model supports; always validate with convert().

        One retry on a transient error or invalid output (with the validation error fed back), then LLMError.
        """
        if json_mode == "json_schema":
            response_format = {"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema}}
        else:
            messages = with_schema_instruction(messages, schema)
            response_format = {"type": "json_object"} if json_mode == "json_object" else None

        usage = LLMUsage(provider=spec.provider, model=spec.model)
        last_error: Exception | None = None
        for attempt in range(MAX_ATTEMPTS):
            usage.retries = attempt
            request = LLMRequest(spec.model, messages, response_format, temperature, max_tokens)
            try:
                raw, cached = await self._send(spec, request, usage)
            except TransientLLMError as exc:
                last_error = exc
                continue
            try:
                result = convert(parse_json(raw.text))
            except (ValueError, TypeError, ValidationError) as exc:  # JSONDecodeError is a ValueError
                last_error = exc
                messages = [*messages, {"role": "assistant", "content": raw.text},
                            {"role": "user", "content": f"That output was invalid: {exc}. Return only the corrected JSON object."}]
                continue
            if not cached:
                self._remember(spec, request, raw)
            usage.cached = cached and attempt == 0
            return result, usage
        raise LLMError(f"{spec}: no valid output after {MAX_ATTEMPTS} attempts: {last_error}")

    async def text(
        self,
        spec: ModelSpec,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 600,
    ) -> tuple[str, LLMUsage]:
        """Plain text completion (replies). One retry on a transient error or an empty answer."""
        usage = LLMUsage(provider=spec.provider, model=spec.model)
        request = LLMRequest(spec.model, messages, None, temperature, max_tokens)
        last_error: Exception | None = None
        for attempt in range(MAX_ATTEMPTS):
            usage.retries = attempt
            try:
                raw, cached = await self._send(spec, request, usage)
            except TransientLLMError as exc:
                last_error = exc
                continue
            if not raw.text.strip():
                last_error = LLMError("empty reply")
                continue
            if not cached:
                self._remember(spec, request, raw)
            usage.cached = cached and attempt == 0
            return raw.text.strip(), usage
        raise LLMError(f"{spec}: no reply after {MAX_ATTEMPTS} attempts: {last_error}")


_default: LLMClient | None = None


def get_client() -> LLMClient:
    """The process-wide client: one cache file and one concurrency gate shared by every step."""
    global _default
    if _default is None:
        _default = LLMClient(cache=LLMCache(config.LLM_CACHE_PATH))
    return _default
