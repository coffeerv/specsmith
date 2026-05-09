from __future__ import annotations

from pydantic import TypeAdapter

from models.trace import CritiqueFinding, Finding, RuleFinding


def test_finding_discriminator_round_trips_rule_and_critique():
    adapter = TypeAdapter(Finding)

    rule = adapter.validate_python(
        {
            "kind": "rule",
            "rule_id": "nfr.presence",
            "severity": "warn",
            "target_field": "non_functional_requirements",
            "message": "Add NFR: security",
        }
    )
    critique = adapter.validate_python(
        {
            "kind": "critique",
            "critique_prompt_id": "critique.spec.v0",
            "model": "gemini-test",
            "severity": "warn",
            "target_field": None,
            "message": "Clarify risks.",
        }
    )

    assert isinstance(rule, RuleFinding)
    assert isinstance(critique, CritiqueFinding)
