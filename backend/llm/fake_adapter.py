"""Offline adapter for tests: scripted responses (or exceptions), records every request it receives."""
from __future__ import annotations

from typing import Callable

from backend.llm.types import LLMRaw, LLMRequest

Script = list["str | Exception"] | Callable[[LLMRequest], str]


class FakeAdapter:
    name = "fake"

    def __init__(self, responses: Script | None = None, *, cost_usd: float | None = 0.0):
        self.responses = responses
        self.cost_usd = cost_usd
        self.calls: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMRaw:
        self.calls.append(request)
        if callable(self.responses):
            text = self.responses(request)
        elif self.responses:
            item = self.responses.pop(0)
            if isinstance(item, Exception):
                raise item
            text = item
        else:  # nothing scripted: echo the last message
            text = request.messages[-1]["content"]
        return LLMRaw(text=text, tokens_in=sum(len(m["content"]) for m in request.messages) // 4,
                      tokens_out=len(text) // 4, cost_usd=self.cost_usd, latency_ms=1)
