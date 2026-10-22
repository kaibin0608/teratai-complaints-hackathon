"""Shared types for the LLM layer. Adapters only move requests; LLMClient owns everything else."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Protocol

JsonMode = Literal["json_schema", "json_object", "prompt"]
JSON_MODES: tuple[JsonMode, ...] = ("json_schema", "json_object", "prompt")


class LLMError(Exception):
    """Final failure: bad config, non-retryable provider error, or invalid output after the retry."""


class TransientLLMError(LLMError):
    """Timeout, rate limit or 5xx: worth one retry."""


class ConfigError(LLMError):
    """Unknown provider, malformed provider:model, missing key. Raised at startup."""


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str

    @classmethod
    def parse(cls, value: str) -> ModelSpec:
        provider, sep, model = value.strip().partition(":")
        if not sep or not provider or not model:
            raise ConfigError(f"expected provider:model, got {value!r}")
        return cls(provider, model)

    def __str__(self) -> str:
        return f"{self.provider}:{self.model}"


@dataclass
class LLMRequest:
    model: str
    messages: list[dict[str, str]]
    response_format: dict[str, Any] | None = None
    temperature: float = 0.0
    max_tokens: int = 1024

    def cache_key(self, provider: str) -> str:
        """Hash of everything that shapes the answer, so any prompt or schema edit misses the cache."""
        canonical = json.dumps({"provider": provider, **asdict(self)}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class LLMRaw:
    text: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float | None = None  # as reported by the provider; None when it reports nothing
    latency_ms: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


class Adapter(Protocol):
    name: str

    async def complete(self, request: LLMRequest) -> LLMRaw: ...
