"""Provider registry. Adding a provider = one adapter + one register() call; callers never change."""
from __future__ import annotations

from typing import Callable

from backend import config
from backend.llm.types import JSON_MODES, Adapter, ConfigError, JsonMode, ModelSpec


def _openrouter() -> Adapter:
    from backend.llm.openai_compatible_adapter import OpenAICompatibleAdapter

    return OpenAICompatibleAdapter.openrouter()


def _openai_compatible() -> Adapter:
    from backend.llm.openai_compatible_adapter import OpenAICompatibleAdapter

    return OpenAICompatibleAdapter.generic()


def _fake() -> Adapter:
    from backend.llm.fake_adapter import FakeAdapter

    return FakeAdapter()


_FACTORIES: dict[str, Callable[[], Adapter]] = {
    "openrouter": _openrouter,
    "openai_compatible": _openai_compatible,
    "fake": _fake,
}
_INSTANCES: dict[str, Adapter] = {}


def register(name: str, factory: Callable[[], Adapter]) -> None:
    _FACTORIES[name] = factory
    _INSTANCES.pop(name, None)


def get_adapter(provider: str) -> Adapter:
    """Build (once) the adapter for a provider. Raises ConfigError for unknown names or missing keys."""
    if provider not in _FACTORIES:
        raise ConfigError(f"unknown LLM provider {provider!r}; registered: {', '.join(sorted(_FACTORIES))}")
    if provider not in _INSTANCES:
        _INSTANCES[provider] = _FACTORIES[provider]()
    return _INSTANCES[provider]


STEPS = {
    "extract": lambda: (config.LLM_EXTRACT, config.LLM_EXTRACT_JSON_MODE),
    "draft": lambda: (config.LLM_DRAFT, config.LLM_DRAFT_JSON_MODE),
    # the second-issue check: empty LLM_ISSUES follows the extraction model and its JSON mode
    "issues": lambda: (config.LLM_ISSUES or config.LLM_EXTRACT, config.LLM_EXTRACT_JSON_MODE),
}


def issues_enabled() -> bool:
    """LLM_ISSUES=off is the Day 2 kill switch for the second-issue check."""
    return config.LLM_ISSUES.lower() != "off"


def step_config(step: str) -> tuple[ModelSpec, JsonMode]:
    """(provider:model, json mode) for an LLM step, read from config at call time."""
    value, mode = STEPS[step]()
    if mode not in JSON_MODES:
        raise ConfigError(f"{step}: JSON mode {mode!r} is not one of {', '.join(JSON_MODES)}")
    return ModelSpec.parse(value), mode


def step_reasoning(step: str) -> str | None:
    """Reasoning effort for a step, or None to leave the model's default."""
    value = {"extract": config.LLM_EXTRACT_REASONING, "draft": config.LLM_DRAFT_REASONING,
             "issues": config.LLM_ISSUES_REASONING}[step].strip()
    return value or None


def check_config() -> None:
    """Fail at startup, before any complaint is processed: every step's provider must exist and have its key."""
    for step in STEPS:
        if step == "issues" and not issues_enabled():
            continue
        spec, _ = step_config(step)
        get_adapter(spec.provider)
