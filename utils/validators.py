
from __future__ import annotations
from typing import Dict, Any, List

from models.trace import RuleFinding

def _has_gwt(ac: str) -> bool:
    s = ac.lower()
    return ("given" in s or "as a" in s) and ("when" in s) and ("then" in s)

def validate_acceptance_coverage(spec: Dict[str, Any]) -> List[RuleFinding]:
    notes = []
    stories = spec.get("user_stories", [])
    if not stories:
        notes.append(RuleFinding(
            rule_id="acceptance.coverage",
            severity="error",
            target_field="user_stories",
            message="No user stories found.",
        ))
        return notes
    for i, s in enumerate(stories):
        ac = s.get("acceptance_criteria", [])
        if not ac:
            notes.append(RuleFinding(
                rule_id="acceptance.coverage",
                severity="error",
                target_field=f"user_stories[{i}].acceptance_criteria",
                message=f"Story {i+1} missing acceptance criteria.",
            ))
        elif not _has_gwt("\n".join(str(x) for x in ac)):
            notes.append(RuleFinding(
                rule_id="acceptance.gwt",
                severity="warn",
                target_field=f"user_stories[{i}].acceptance_criteria",
                message=f"Story {i+1} has acceptance criteria, but none in Given/When/Then form.",
            ))
    return notes

def validate_nfr(spec: Dict[str, Any]) -> List[RuleFinding]:
    needed = ["performance","reliability","security","privacy","accessibility"]
    present = ",".join([x.lower() for x in spec.get("non_functional_requirements", [])])
    missing = [n for n in needed if n not in present]
    return [
        RuleFinding(
            rule_id="nfr.presence",
            severity="warn",
            target_field="non_functional_requirements",
            message=f"Add NFR: {m}",
        )
        for m in missing
    ]

def validate_objectives_metrics(spec: Dict[str, Any]) -> List[RuleFinding]:
    if spec.get("objectives") and not spec.get("metrics"):
        return [RuleFinding(
            rule_id="objectives.metrics",
            severity="warn",
            target_field="metrics",
            message="Objectives present but metrics empty. Add measurable success metrics.",
        )]
    return []

def run_all(spec: Dict[str, Any]) -> List[RuleFinding]:
    notes = []
    notes += validate_acceptance_coverage(spec)
    notes += validate_nfr(spec)
    notes += validate_objectives_metrics(spec)
    return notes
