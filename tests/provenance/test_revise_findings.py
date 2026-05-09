from __future__ import annotations

import asyncio
from uuid import UUID

from agents.nodes import revise
from tests.fakes import FakeLLM


def test_revise_refreshes_rule_findings_against_revised_spec(monkeypatch):
    import agents.nodes as nodes

    llm = FakeLLM()
    llm.revised_spec = {
        **_spec_with_gaps(),
        "non_functional_requirements": [
            "Performance: Exports complete within 5 seconds.",
            "Reliability: Export succeeds 99.9% of the time.",
            "Security: Exports respect access permissions.",
            "Privacy: Exports follow applicable privacy policy.",
            "Accessibility: Export controls comply with WCAG 2.1 AA.",
        ],
    }
    monkeypatch.setattr(nodes, "llm", llm)

    result = asyncio.run(
        revise(
            {
                "target": "PRD",
                "spec": {
                    **_spec_with_gaps(),
                    "findings": [
                        {
                            "kind": "rule",
                            "rule_id": "nfr.presence",
                            "severity": "warn",
                            "target_field": "non_functional_requirements",
                            "message": "Add NFR: privacy",
                        },
                        {
                            "kind": "critique",
                            "critique_prompt_id": "critique.spec.v0",
                            "model": "gemini-test",
                            "severity": "warn",
                            "target_field": None,
                            "message": "Clarify rollout risk mitigation.",
                        },
                    ],
                },
                "run_id": UUID("00000000-0000-0000-0000-000000000001"),
                "trace": [],
            }
        )
    )

    findings = result["spec"]["findings"]
    assert not any(
        finding.get("kind") == "rule" and finding.get("message") == "Add NFR: privacy"
        for finding in findings
    )
    assert any(finding.get("kind") == "critique" for finding in findings)


def _spec_with_gaps():
    return {
        "title": "One-click export",
        "type": "PRD",
        "objectives": ["Reduce support tickets"],
        "user_stories": [
            {
                "as_a": "Ops Analyst",
                "i_want": "export data",
                "so_that": "I can analyze it",
                "priority": "should",
                "acceptance_criteria": [
                    "GWT: Given I am an Ops Analyst, When I click Export, Then I receive a CSV."
                ],
            }
        ],
        "functional_requirements": ["Export data as CSV."],
        "non_functional_requirements": [
            "Performance: Exports complete within 5 seconds.",
            "Reliability: Export succeeds 99.9% of the time.",
            "Security: Exports respect access permissions.",
        ],
        "metrics": ["Support ticket reduction."],
        "dependencies": [],
        "risks": [],
        "scope": {"in_scope": [], "out_of_scope": []},
        "open_questions": [],
    }
