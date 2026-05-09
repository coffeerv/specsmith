from __future__ import annotations

import asyncio

from utils import provider


def test_configuration_help_mentions_vertex_for_vision(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "google_genai")

    help_text = provider._configuration_help()

    assert "USE_GEMINI_VISION=1" in help_text
    assert "Vertex AI" in help_text


def test_lazy_llm_initializes_client_once_under_concurrency(monkeypatch):
    build_count = 0

    class StubClient:
        async def ainvoke(self, messages):
            return {"messages": messages}

    def fake_build_llm():
        nonlocal build_count
        build_count += 1
        return StubClient()

    monkeypatch.setattr(provider, "_build_llm", fake_build_llm)

    llm = provider.LazyLLM()

    async def run():
        clients = await asyncio.gather(llm._get_client(), llm._get_client(), llm._get_client())
        assert clients[0] is clients[1] is clients[2]

    asyncio.run(run())

    assert build_count == 1
