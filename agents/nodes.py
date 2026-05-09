from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, NotRequired, TypedDict
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage

from agents.instrumentation import traced_node
from models.spec import Spec, TARGET_SPECS
from models.trace import CritiqueFinding, Finding, PromptTrace, TraceEntry, TraceMeta
from parsers.specscript import parse_specscript
from utils.hashing import user_assets_envelope
from utils.media import detect_type, stub_asr, stub_video_summary, summarize_image
from utils.provider import get_llm


def _parse_json(text: str) -> Any:
    text = text.strip()
    if "```" in text:
        pattern = r"```(?:json)?\s*(.*?)\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            text = match.group(1)
    return json.loads(text)


class State(TypedDict, total=False):
    assets: List[Dict[str, Any]]
    corpus: List[Dict[str, Any]]
    classification: Dict[str, Any]
    spec: Dict[str, Any]
    critiques: List[str]
    target: str
    parsed_specscript: Dict[str, Any]
    run_id: NotRequired[UUID]
    trace: NotRequired[List[TraceEntry]]


llm = get_llm()


def _model_id() -> str:
    return (
        getattr(llm, "model_name", None)
        or getattr(llm, "model", None)
        or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    )


def _as_message_text(finding: Any) -> str:
    data = finding.model_dump() if hasattr(finding, "model_dump") else dict(finding)
    prefix = data.get("rule_id") or data.get("critique_prompt_id") or data.get("kind", "finding")
    target = data.get("target_field")
    target_text = f" [{target}]" if target else ""
    return f"{prefix}{target_text}: {data.get('message', '')}"


def _dedupe_findings(findings: List[Finding]) -> List[Finding]:
    seen: set[tuple[str, str, str | None]] = set()
    deduped: List[Finding] = []
    for finding in findings:
        data = finding.model_dump() if hasattr(finding, "model_dump") else dict(finding)
        key = (data.get("kind", ""), data.get("message", ""), data.get("target_field"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(finding)
    return deduped


def _spec_hash_subject(spec: Dict[str, Any]) -> Dict[str, Any]:
    subject = dict(spec)
    subject.pop("created_at", None)
    subject.pop("rendered_markdown", None)
    return subject


@traced_node("ingest", hash_subject=lambda state: user_assets_envelope(state.get("assets", [])))
async def ingest(state: State) -> State:
    corpus: List[Dict[str, Any]] = []
    parsed_specscript: Dict[str, Any] | None = None
    for asset in state.get("assets", []):
        kind = asset.get("type")
        if not kind and "filename" in asset:
            kind = detect_type(asset["filename"])
        shard_text = ""
        if kind == "image" and "bytes" in asset:
            shard_text = summarize_image(asset["bytes"])
        elif kind == "audio" and "bytes" in asset:
            shard_text = stub_asr(asset["bytes"])
        elif kind == "video" and "bytes" in asset:
            shard_text = stub_video_summary(asset["bytes"])
        elif kind == "text":
            shard_text = asset.get("text", "")
        else:
            shard_text = asset.get("text", "[UNSUPPORTED_ASSET]")
        corpus.append(
            {
                "id": asset.get("id", f"shard_{len(corpus)}"),
                "type": kind or "unknown",
                "text": shard_text,
            }
        )
    for asset in state.get("assets", []):
        if asset.get("source") == "specscript":
            parsed_specscript = parse_specscript(asset.get("text", ""))
    update: State = {"corpus": corpus}
    if parsed_specscript is not None:
        update["parsed_specscript"] = parsed_specscript
    return update


@traced_node("classify", hash_subject=lambda state: state.get("corpus", []))
async def classify(state: State) -> State:
    prompt = (
        f"Classify user intent and artifact types from shards: {state.get('corpus', [])}. "
        f"Return JSON with keys intent, artifact_types (list), confidence (0-1)."
    )
    resp = await llm.ainvoke(
        [
            SystemMessage(content="You are a precise classifier."),
            HumanMessage(content=prompt),
        ]
    )
    try:
        parsed = _parse_json(getattr(resp, "content", "{}"))
        if not isinstance(parsed, dict):
            raise ValueError("classification response was not a JSON object")
    except Exception:
        parsed = {
            "intent": "feature_request",
            "artifact_types": ["feature_request"],
            "confidence": 0.5,
        }
    return {
        "classification": parsed,
        "target": TARGET_SPECS.get(parsed.get("intent", "feature_request"), "PRD"),
        "_trace_meta": TraceMeta(model=_model_id()),
    }


@traced_node(
    "extract",
    hash_subject=lambda state: {
        "corpus": state.get("corpus", []),
        "target": state.get("target", "PRD"),
    },
)
async def extract(state: State) -> State:
    sys = (
        "You are SpecSmith, an extractor that emits JSON conforming to the Spec schema. "
        "Fill: title, problem_statement, objectives, user_stories (>=3), functional_requirements, "
        "non_functional_requirements, metrics, dependencies, risks, scope, open_questions. "
        "Use concise, testable language. Add acceptance criteria for each story in GWT form. "
        "If a SpecScript parse is available, respect it."
    )
    user = {
        "corpus": state.get("corpus", []),
        "target": state.get("target", "PRD"),
        "specscript": state.get("parsed_specscript", {}),
    }
    resp = await llm.ainvoke([SystemMessage(content=sys), HumanMessage(content=str(user))])
    try:
        draft = _parse_json(getattr(resp, "content", "{}"))
        if not isinstance(draft, dict):
            raise ValueError("extract response was not a JSON object")
    except Exception:
        draft = {
            "title": user["specscript"].get("title", "Untitled Spec"),
            "type": state.get("target", "PRD"),
            "objectives": user["specscript"].get("objectives", []),
            "user_stories": [
                {
                    "as_a": "user",
                    "i_want": "export data",
                    "so_that": "I can analyze",
                    "priority": "should",
                    "acceptance_criteria": ["GWT: As a user, when ... then ..."],
                }
            ],
            "functional_requirements": [],
            "non_functional_requirements": [],
            "metrics": user["specscript"].get("metrics", []),
            "scope": user["specscript"].get(
                "scope",
                {"in_scope": [], "out_of_scope": []},
            ),
        }
    draft.setdefault("type", state.get("target", "PRD"))
    try:
        spec = Spec(**draft).model_dump()
    except Exception:
        spec = draft
        spec["type"] = state.get("target", "PRD")
    return {
        "spec": spec,
        "_trace_meta": TraceMeta(model=_model_id()),
    }


@traced_node("critique", hash_subject=lambda state: _spec_hash_subject(state.get("spec", {})))
async def critique(state: State) -> State:
    from utils import validators

    critique_prompt_id = "critique.spec.v0"
    sys = (
        "You are a senior PM. List blocking gaps, contradictions, and missing NFRs. "
        "Output a JSON list of strings."
    )
    human = str(state.get("spec", {}))
    prompt_text = f"System: {sys}\nHuman: {human}"
    resp = await llm.ainvoke([SystemMessage(content=sys), HumanMessage(content=human)])
    try:
        notes_llm = _parse_json(getattr(resp, "content", "[]"))
        if not isinstance(notes_llm, list):
            notes_llm = [str(notes_llm)]
    except Exception:
        notes_llm = []
    notes_rules = validators.run_all(state.get("spec", {}))
    critique_findings = [
        CritiqueFinding(
            critique_prompt_id=critique_prompt_id,
            model=_model_id(),
            severity="warn",
            target_field=None,
            message=str(note),
        )
        for note in notes_llm
    ]
    findings = _dedupe_findings([*notes_rules, *critique_findings])
    spec = {
        **state.get("spec", {}),
        "findings": [
            finding.model_dump() if hasattr(finding, "model_dump") else finding
            for finding in findings
        ],
    }
    return {
        "spec": spec,
        "_trace_meta": TraceMeta(
            model=_model_id(),
            prompts=[
                PromptTrace(
                    prompt_id=critique_prompt_id,
                    prompt_text=prompt_text,
                )
            ],
        ),
    }


@traced_node("revise", hash_subject=lambda state: _spec_hash_subject(state.get("spec", {})))
async def revise(state: State) -> State:
    findings = state.get("spec", {}).get("findings", [])
    if not findings:
        return {}
    rule_findings = [finding for finding in findings if finding.get("kind") == "rule"]
    critique_findings = [finding for finding in findings if finding.get("kind") == "critique"]
    prompt = (
        "Apply these review notes to improve the spec while preserving intent.\n\n"
        "Deterministic validator findings:\n"
        + "\n".join(f"- {_as_message_text(finding)}" for finding in rule_findings)
        + "\n\nLLM critique findings:\n"
        + "\n".join(f"- {_as_message_text(finding)}" for finding in critique_findings)
        + f"\n\nSpec:{state['spec']}"
    )
    resp = await llm.ainvoke([HumanMessage(content=prompt)])
    try:
        improved = _parse_json(getattr(resp, "content", "{}"))
        if not isinstance(improved, dict):
            raise ValueError("revise response was not a JSON object")
    except Exception:
        improved = state["spec"]
    if isinstance(improved, dict) and "findings" not in improved:
        improved["findings"] = findings
    return {
        "spec": improved,
        "_trace_meta": TraceMeta(model=_model_id()),
    }
