"""LLMClient: retry, validation, cache, cost, concurrency; registry config errors; the OpenAI-compatible transport."""
import asyncio
import json
from decimal import Decimal

import httpx2
import pytest
from pydantic import BaseModel, ConfigDict

from backend import config
from backend.llm import registry
from backend.llm.cache import LLMCache
from backend.llm.client import LLMClient, parse_json
from backend.llm.fake_adapter import FakeAdapter
from backend.llm.openai_compatible_adapter import OpenAICompatibleAdapter
from backend.llm.types import ConfigError, LLMError, LLMRequest, ModelSpec, TransientLLMError

SPEC = ModelSpec("fake", "m1")
MESSAGES = [{"role": "system", "content": "Extract."}, {"role": "user", "content": "complaint"}]
SCHEMA = {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"], "additionalProperties": False}


class Out(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: int


def make_client(responses, **kwargs):
    fake = FakeAdapter(responses, **{k: kwargs.pop(k) for k in ["cost_usd"] if k in kwargs})
    return LLMClient(adapters={"fake": fake}, **kwargs), fake


def structured(client, json_mode="json_schema", messages=MESSAGES):
    return asyncio.run(client.structured(SPEC, messages, schema=SCHEMA, schema_name="out",
                                         convert=Out.model_validate, json_mode=json_mode))


def test_valid_first_time():
    client, fake = make_client(['{"x": 1}'])
    out, usage = structured(client)
    assert out.x == 1 and usage.retries == 0 and not usage.cached
    assert fake.calls[0].response_format["json_schema"]["strict"] is True


def test_invalid_then_valid_retries_once_with_feedback():
    client, fake = make_client(['{"x": 1, "urgency": "high"}', '{"x": 2}'])
    out, usage = structured(client)
    assert out.x == 2 and usage.retries == 1
    assert "invalid" in fake.calls[1].messages[-1]["content"]


def test_two_invalid_outputs_raise():
    client, _ = make_client(["not json", '{"y": 1}'])
    with pytest.raises(LLMError, match="no valid output"):
        structured(client)


def test_transient_error_then_success():
    client, _ = make_client([TransientLLMError("429"), '{"x": 3}'])
    out, usage = structured(client)
    assert out.x == 3 and usage.retries == 1


def test_non_transient_error_is_not_retried():
    client, fake = make_client([LLMError("HTTP 400"), '{"x": 3}'])
    with pytest.raises(LLMError, match="400"):
        structured(client)
    assert len(fake.calls) == 1


def test_rerun_hits_cache_with_zero_cost():
    client, fake = make_client(['{"x": 1}'], cost_usd=0.001)
    _, first = structured(client)
    out, second = structured(client)
    assert len(fake.calls) == 1
    assert out.x == 1 and second.cached and second.cost_myr == 0 and second.tokens_in == first.tokens_in


def test_prompt_change_misses_cache():
    client, fake = make_client(['{"x": 1}', '{"x": 2}'])
    structured(client)
    out, usage = structured(client, messages=[{"role": "system", "content": "Extract v2."}, MESSAGES[1]])
    assert len(fake.calls) == 2 and out.x == 2 and not usage.cached


def test_invalid_output_is_not_cached():
    client, _ = make_client(["nope", "nope"])
    with pytest.raises(LLMError):
        structured(client)
    assert len(client.cache) == 0


def test_cache_bypass():
    client, fake = make_client(['{"x": 1}', '{"x": 1}'], use_cache=False)
    structured(client)
    structured(client)
    assert len(fake.calls) == 2


def test_cache_survives_restart(tmp_path):
    path = tmp_path / "cache.db"
    first = LLMClient(adapters={"fake": FakeAdapter(['{"x": 7}'])}, cache=LLMCache(path))
    structured(first)
    fresh_fake = FakeAdapter([])
    second = LLMClient(adapters={"fake": fresh_fake}, cache=LLMCache(path))
    out, usage = structured(second)
    assert out.x == 7 and usage.cached and not fresh_fake.calls


def test_cost_converted_to_myr_and_summed_over_retries():
    client, _ = make_client(['{"bad": 1}', '{"x": 1}'], cost_usd=0.0004, usd_to_myr=4.20)
    _, usage = structured(client)
    assert usage.cost_myr == Decimal("0.00336")  # 2 × 0.0004 × 4.20


def test_missing_cost_counts_as_zero():
    client, _ = make_client(['{"x": 1}'], cost_usd=None)
    _, usage = structured(client)
    assert usage.cost_myr == 0


@pytest.mark.parametrize("mode, response_type", [("json_object", "json_object"), ("prompt", None)])
def test_weaker_json_modes_put_schema_in_system_prompt(mode, response_type):
    client, fake = make_client(['```json\n{"x": 1}\n```'])
    out, _ = structured(client, json_mode=mode)
    request = fake.calls[0]
    assert out.x == 1
    assert (request.response_format or {}).get("type") == response_type
    assert '"additionalProperties": false' in request.messages[0]["content"]


def test_concurrency_cap():
    in_flight = peak = 0

    class SlowAdapter:
        name = "fake"

        async def complete(self, request):
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            await asyncio.sleep(0.01)
            in_flight -= 1
            from backend.llm.types import LLMRaw
            return LLMRaw(text='{"x": 1}')

    client = LLMClient(adapters={"fake": SlowAdapter()}, max_concurrency=3, use_cache=False)

    async def many():
        await asyncio.gather(*(client.structured(SPEC, [{"role": "user", "content": str(i)}], schema=SCHEMA,
                                                 schema_name="out", convert=Out.model_validate) for i in range(20)))

    asyncio.run(many())
    assert peak == 3


def test_text_completion():
    client, _ = make_client(["  Dear customer, ...  "])
    reply, usage = asyncio.run(client.text(SPEC, MESSAGES))
    assert reply == "Dear customer, ..." and usage.provider == "fake"


def test_parse_json_strips_fence():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}


# --- registry / config ---


def test_spec_parse():
    assert ModelSpec.parse("openrouter:vendor/model-x") == ModelSpec("openrouter", "vendor/model-x")
    with pytest.raises(ConfigError):
        ModelSpec.parse("no-colon")


def test_unknown_provider_fails_at_startup(monkeypatch):
    monkeypatch.setattr(config, "LLM_EXTRACT", "nosuch:model-x")
    with pytest.raises(ConfigError, match="unknown LLM provider 'nosuch'.*openrouter"):
        registry.check_config()


def test_missing_openrouter_key_fails_at_startup(monkeypatch):
    monkeypatch.setattr(config, "LLM_EXTRACT", "openrouter:some/model")
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    monkeypatch.setattr(registry, "_INSTANCES", {})
    with pytest.raises(ConfigError, match="OPENROUTER_API_KEY"):
        registry.check_config()


def test_default_config_needs_no_key():
    registry.check_config()  # fake:keywords / fake:template


def test_bad_json_mode(monkeypatch):
    monkeypatch.setattr(config, "LLM_EXTRACT_JSON_MODE", "yaml")
    with pytest.raises(ConfigError, match="JSON mode"):
        registry.step_config("extract")


# --- OpenAI-compatible transport ---


def adapter_with(handler, **kwargs):
    return OpenAICompatibleAdapter("openrouter", "https://example.test/api/v1", "sk-test",
                                   transport=httpx2.MockTransport(handler), **kwargs)


def ok_response(content, cost=0.0002):
    return httpx2.Response(200, json={
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 30, "cost": cost,
                  "prompt_tokens_details": {"cached_tokens": 100}},
    })


def test_adapter_sends_openrouter_body_and_parses_usage():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        return ok_response('{"x": 1}')

    adapter = adapter_with(handler, require_parameters=True)
    raw = asyncio.run(adapter.complete(LLMRequest("m", MESSAGES, {"type": "json_object"})))
    assert seen["url"] == "https://example.test/api/v1/chat/completions"
    assert seen["auth"] == "Bearer sk-test"
    assert seen["body"]["provider"] == {"require_parameters": True}
    assert (raw.text, raw.tokens_in, raw.tokens_out, raw.cost_usd) == ('{"x": 1}', 120, 30, 0.0002)
    assert raw.extra["cached_tokens"] == 100


@pytest.mark.parametrize("status, error", [(429, TransientLLMError), (503, TransientLLMError), (400, LLMError)])
def test_adapter_maps_http_errors(status, error):
    adapter = adapter_with(lambda request: httpx2.Response(status, text="boom"))
    with pytest.raises(error) as info:
        asyncio.run(adapter.complete(LLMRequest("m", MESSAGES)))
    assert (type(info.value) is TransientLLMError) == (error is TransientLLMError)


def test_adapter_timeout_is_transient():
    def handler(request):
        raise httpx2.ReadTimeout("slow", request=request)

    with pytest.raises(TransientLLMError, match="timeout"):
        asyncio.run(adapter_with(handler).complete(LLMRequest("m", MESSAGES)))


def test_adapter_without_response_format_sends_no_provider_block():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return ok_response("hello")

    asyncio.run(adapter_with(handler, require_parameters=True).complete(LLMRequest("m", MESSAGES)))
    assert "provider" not in seen["body"] and "response_format" not in seen["body"]


def test_reasoning_effort_is_sent_and_keys_unchanged_when_unset():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return ok_response("hi")

    asyncio.run(adapter_with(handler).complete(LLMRequest("m", MESSAGES, reasoning_effort="none")))
    assert seen["body"]["reasoning"] == {"effort": "none"}
    import hashlib
    legacy = hashlib.sha256(json.dumps({"provider": "p", "model": "m", "messages": MESSAGES, "response_format": None,
                                        "temperature": 0.0, "max_tokens": 1024}, sort_keys=True,
                                       ensure_ascii=False).encode()).hexdigest()
    assert LLMRequest("m", MESSAGES).cache_key("p") == legacy  # cached extractions stay valid
    assert LLMRequest("m", MESSAGES, reasoning_effort="none").cache_key("p") != legacy


def test_success_after_retry_is_cached_for_the_first_request():
    client, fake = make_client(['{"bad": 1}', '{"x": 5}'])
    structured(client)
    out, usage = structured(client)  # a rerun: same first request, now answered from the cache
    assert out.x == 5 and usage.cached and len(fake.calls) == 2
