
from __future__ import annotations
from typing import Dict, Any, List

def _has_gwt(ac: str) -> bool:
    s = ac.lower()
    return ("as a" in s) and ("when" in s) and ("then" in s)

def validate_acceptance_coverage(spec: Dict[str, Any]) -> List[str]:
    notes = []
    stories = spec.get("user_stories", [])
    if not stories:
        notes.append("No user stories found.")
        return notes
    for i, s in enumerate(stories):
        ac = s.get("acceptance_criteria", [])
        if not ac:
            notes.append(f"Story {i+1} missing acceptance criteria.")
        elif not any(_has_gwt(x) for x in ac):
            notes.append(f"Story {i+1} has acceptance criteria, but none in Given/When/Then form.")
    return notes

def validate_nfr(spec: Dict[str, Any]) -> List[str]:
    needed = ["performance","reliability","security","privacy","accessibility"]
    present = ",".join([x.lower() for x in spec.get("non_functional_requirements", [])])
    missing = [n for n in needed if n not in present]
    return [f"Add NFR: {m}" for m in missing]

def validate_objectives_metrics(spec: Dict[str, Any]) -> List[str]:
    if spec.get("objectives") and not spec.get("metrics"):
        return ["Objectives present but metrics empty. Add measurable success metrics."]
    return []

def run_all(spec: Dict[str, Any]) -> List[str]:
    notes = []
    notes += validate_acceptance_coverage(spec)
    notes += validate_nfr(spec)
    notes += validate_objectives_metrics(spec)
    return notes
