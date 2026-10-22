"""Keep unit tests offline whatever .env says: only tests marked `live` may reach a real provider."""
import pytest

from backend import config


@pytest.fixture(autouse=True)
def offline_llm(request, monkeypatch):
    if request.node.get_closest_marker("live"):
        return
    monkeypatch.setattr(config, "LLM_EXTRACT", "fake:keywords")
    monkeypatch.setattr(config, "LLM_DRAFT", "fake:template")
