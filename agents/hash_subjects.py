from __future__ import annotations

from typing import Any, Dict


def spec_hash_subject(spec: Dict[str, Any]) -> Dict[str, Any]:
    subject = dict(spec)
    subject.pop("created_at", None)
    subject.pop("rendered_markdown", None)
    return subject
