from __future__ import annotations

import asyncio
from uuid import uuid4

from agents.instrumentation import traced_node
from models.trace import PromptTrace, TraceMeta


def test_traced_node_emits_one_entry_and_strips_trace_meta():
    @traced_node("critique", hash_subject=lambda state: {"input": state["input"]})
    async def stub_node(state):
        return {
            "result": "ok",
            "_trace_meta": TraceMeta(
                model="gemini-test",
                prompts=[PromptTrace(prompt_id="critique.spec.v0", prompt_text="prompt")],
            ),
        }

    run_id = uuid4()
    update = asyncio.run(stub_node({"run_id": run_id, "trace": [], "input": "same"}))

    assert "_trace_meta" not in update
    assert update["result"] == "ok"
    assert len(update["trace"]) == 1
    entry = update["trace"][0]
    assert entry.run_id == run_id
    assert entry.node == "critique"
    assert entry.status == "success"
    assert entry.duration_ms >= 0
    assert entry.output_keys == ["result"]
    assert entry.model == "gemini-test"
    assert entry.prompts[0].prompt_id == "critique.spec.v0"
