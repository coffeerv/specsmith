from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class FakeResponse:
    content: str


class FakeLLM:
    model_name = "gemini-test"

    async def ainvoke(self, messages):
        content = "\n".join(str(getattr(message, "content", "")) for message in messages)
        if "precise classifier" in content:
            return FakeResponse(
                json.dumps(
                    {
                        "intent": "feature_request",
                        "artifact_types": ["feature_request"],
                        "confidence": 0.91,
                    }
                )
            )
        if "extractor that emits JSON" in content:
            return FakeResponse(json.dumps(_base_spec()))
        if "senior PM" in content:
            return FakeResponse(json.dumps(["Clarify rollout risk mitigation."]))
        return FakeResponse(json.dumps(_base_spec()))


def _base_spec():
    return {
        "title": "Demo",
        "type": "PRD",
        "status": "draft",
        "context": "A deterministic test spec.",
        "problem_statement": "Users need a predictable workflow.",
        "objectives": ["Reduce manual work"],
        "user_stories": [
            {
                "as_a": "user",
                "i_want": "export data",
                "so_that": "I can analyze it",
                "priority": "should",
                "acceptance_criteria": ["GWT: As a user, when I export, then I receive a CSV."],
            }
        ],
        "functional_requirements": ["Export data as CSV"],
        "non_functional_requirements": [],
        "metrics": [],
        "dependencies": [],
        "risks": [],
        "scope": {"in_scope": ["CSV export"], "out_of_scope": []},
        "open_questions": [],
    }
