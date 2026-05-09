from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.fakes import FakeLLM


client = TestClient(app)


def test_specify_returns_ordered_trace_and_prompt_references(monkeypatch):
    import agents.nodes as nodes

    monkeypatch.setattr(nodes, "llm", FakeLLM())

    response = client.post("/specify", data={"specscript": _specscript()})

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"target", "spec", "trace"}
    entries = body["trace"]["entries"]
    assert [entry["node"] for entry in entries] == [
        "ingest",
        "classify",
        "extract",
        "critique",
        "revise",
        "render",
    ]
    assert all(entry["status"] == "success" for entry in entries)

    models_by_node = {entry["node"]: entry["model"] for entry in entries}
    assert models_by_node["ingest"] is None
    assert models_by_node["render"] is None
    assert models_by_node["classify"] == "gemini-test"
    assert models_by_node["extract"] == "gemini-test"
    assert models_by_node["critique"] == "gemini-test"
    assert models_by_node["revise"] == "gemini-test"

    for entry in entries:
        if entry["model"] is None:
            assert entry["token_usage"] is None
        else:
            assert entry["token_usage"] == {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
            }

    critique_entry = next(entry for entry in entries if entry["node"] == "critique")
    prompt_ids = {prompt["prompt_id"] for prompt in critique_entry["prompts"]}
    findings = body["spec"]["findings"]
    assert {finding["kind"] for finding in findings} == {"rule", "critique"}
    for finding in findings:
        if finding["kind"] == "critique":
            assert finding["critique_prompt_id"] in prompt_ids


def test_specify_input_hashes_are_stable_across_runs(monkeypatch):
    import agents.nodes as nodes

    monkeypatch.setattr(nodes, "llm", FakeLLM())

    first = client.post("/specify", data={"specscript": _specscript()}).json()
    second = client.post("/specify", data={"specscript": _specscript()}).json()

    assert first["trace"]["run_id"] != second["trace"]["run_id"]
    first_entries = first["trace"]["entries"]
    second_entries = second["trace"]["entries"]
    assert [entry["entry_id"] for entry in first_entries] != [
        entry["entry_id"] for entry in second_entries
    ]
    assert [entry["input_hash"] for entry in first_entries] == [
        entry["input_hash"] for entry in second_entries
    ]


def _specscript():
    return """#spec
Title: Demo
Type: PRD
goals:
- Reduce manual work
accept:
- GWT: As a user, when I export, then I receive a CSV.
"""
