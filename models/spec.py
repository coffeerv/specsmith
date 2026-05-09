
from __future__ import annotations
from typing import List, Literal, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from models.trace import Finding

class Attachment(BaseModel):
    id: str
    media_type: Literal["image","video","audio","text","pdf","url"]
    uri: str = ""
    derived: Dict[str,str] = {}
    sha256: str = ""

class Persona(BaseModel):
    name: str
    role: str
    goals: List[str] = []
    pains: List[str] = []

class UserStory(BaseModel):
    as_a: str
    i_want: str
    so_that: str
    priority: Literal["must","should","could"] = "should"
    acceptance_criteria: List[str] = []

class Scope(BaseModel):
    in_scope: List[str] = []
    out_of_scope: List[str] = []

class Spec(BaseModel):
    id: str = "spec-0001"
    title: str
    type: Literal["PRD","TechSpec","GitHubSpec"]
    status: Literal["draft","review","final"] = "draft"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    context: str = ""
    problem_statement: str = ""
    objectives: List[str] = []
    personas: List[Persona] = []
    user_stories: List[UserStory] = []
    functional_requirements: List[str] = []
    non_functional_requirements: List[str] = []
    metrics: List[str] = []
    dependencies: List[str] = []
    risks: List[str] = []
    scope: Scope = Field(default_factory=Scope)
    glossary: Dict[str,str] = {}
    open_questions: List[str] = []
    attachments: List[Attachment] = []
    evidence: Dict[str, str] = {}
    change_log: List[str] = []
    findings: List[Finding] = []
    rendered_markdown: Optional[str] = None

ARTIFACT_TYPES = [
    "feature_request","bug_report","ux_observation","competitive_analysis",
    "architecture_diagram","api_behavior","infra_ops","research_note"
]

TARGET_SPECS = {
    "feature_request": "PRD",
    "bug_report": "GitHubSpec",
    "ux_observation": "PRD",
    "api_behavior": "TechSpec",
    "infra_ops": "TechSpec",
}
