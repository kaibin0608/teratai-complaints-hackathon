"""One real call through the configured extract model. Skipped unless .env sets LLM_EXTRACT to a real provider and its key.

    pytest -m live -s backend/tests/test_llm_live.py
"""
import asyncio

import pytest

from backend import config
from backend.llm.client import LLMClient
from backend.llm.registry import step_config

pytestmark = pytest.mark.live

spec, _ = step_config("extract")
needs_key = {"openrouter": config.OPENROUTER_API_KEY, "openai_compatible": config.OPENAI_COMPAT_BASE_URL}


@pytest.mark.skipif(not needs_key.get(spec.provider), reason="no real LLM provider configured in .env")
def test_live_text_call_reports_usage_and_cost():
    client = LLMClient(use_cache=False)
    reply, usage = asyncio.run(client.text(spec, [{"role": "user", "content": "Reply with the single word: ok"}],
                                           max_tokens=200))  # some models spend tokens before answering
    print(f"\n{spec}: {reply!r} tokens {usage.tokens_in}/{usage.tokens_out} "
          f"RM{usage.cost_myr:.6f} {usage.latency_ms} ms")
    assert reply and usage.tokens_in > 0
