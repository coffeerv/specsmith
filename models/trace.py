from __future__ import annotations

from datetime import datetime
from typing import Annotated, Dict, List, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class PromptTrace(BaseModel):
    prompt_id: str
    prompt_text: str


class TraceMeta(BaseModel):
    model: Optional[str] = None
    token_usage: Optional[Dict[str, int]] = None
    prompts: List[PromptTrace] = Field(default_factory=list)


NodeName = Literal[
    "ingest",
    "classify",
    "extract",
    "critique",
    "revise",
    "render",
]


class TraceEntry(BaseModel):
    entry_id: UUID
    run_id: UUID
    node: NodeName
    started_at: datetime
    ended_at: datetime
    duration_ms: int
    input_hash: str
    output_keys: List[str]
    model: Optional[str] = None
    token_usage: Optional[Dict[str, int]] = None
    prompts: List[PromptTrace] = Field(default_factory=list)
    status: Literal["success"] = "success"


Severity = Literal["info", "warn", "error"]


class RuleFinding(BaseModel):
    kind: Literal["rule"] = "rule"
    rule_id: str
    severity: Severity
    target_field: Optional[str] = None
    message: str


class CritiqueFinding(BaseModel):
    kind: Literal["critique"] = "critique"
    critique_prompt_id: str
    model: str
    severity: Severity
    target_field: Optional[str] = None
    message: str


Finding = Annotated[
    Union[RuleFinding, CritiqueFinding],
    Field(discriminator="kind"),
]
