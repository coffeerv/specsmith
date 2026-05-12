from __future__ import annotations

import ast
import json
import os
import re
from typing import Any, Dict, List, NotRequired, TypedDict
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage

from agents.hash_subjects import spec_hash_subject
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


def _token_usage(resp: Any) -> Dict[str, int] | None:
    raw_usage = getattr(resp, "usage_metadata", None)
    if not raw_usage:
        response_metadata = getattr(resp, "response_metadata", None) or {}
        raw_usage = (
            response_metadata.get("token_usage")
            or response_metadata.get("usage")
            or response_metadata.get("usage_metadata")
        )
    if not isinstance(raw_usage, dict):
        return None

    usage: Dict[str, int] = {}
    key_map = {
        "input_tokens": "input_tokens",
        "prompt_tokens": "input_tokens",
        "output_tokens": "output_tokens",
        "completion_tokens": "output_tokens",
        "candidate_tokens": "output_tokens",
        "total_tokens": "total_tokens",
    }
    # First-writer-wins so the canonical key (input_tokens/output_tokens/total_tokens)
    # cannot be overwritten by a subsequent alias (prompt_tokens, completion_tokens, ...)
    # that providers sometimes report alongside it with a slightly different value.
    for source_key, target_key in key_map.items():
        value = raw_usage.get(source_key)
        if isinstance(value, int):
            usage.setdefault(target_key, value)

    # Thinking-model reasoning tokens (Gemini 2.5, etc.) are not included in
    # output_tokens but do count toward total_tokens. Surface them so the trace
    # arithmetic is auditable.
    output_details = raw_usage.get("output_token_details")
    if isinstance(output_details, dict):
        reasoning = output_details.get("reasoning")
        if isinstance(reasoning, int) and reasoning > 0:
            usage["reasoning_tokens"] = reasoning

    if usage and "total_tokens" not in usage:
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        if input_tokens is not None and output_tokens is not None:
            usage["total_tokens"] = input_tokens + output_tokens + usage.get("reasoning_tokens", 0)
    return usage or None


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


def _ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _format_list_item(item: Any) -> str:
    if isinstance(item, str):
        stripped = item.strip()
        if stripped.startswith(("{", "[")):
            try:
                parsed = ast.literal_eval(stripped)
            except (SyntaxError, ValueError):
                return item
            if parsed is not item:
                return _format_list_item(parsed)
        return item
    if isinstance(item, dict):
        label = (
            item.get("type")
            or item.get("name")
            or item.get("title")
            or item.get("category")
            or item.get("id")
        )
        text = (
            item.get("description")
            or item.get("requirement")
            or item.get("metric")
            or item.get("dependency")
            or item.get("question")
            or item.get("value")
            or item.get("text")
        )
        if label and text:
            return f"{label}: {text}"
        if text:
            return str(text)
        if label:
            extras = {
                key: value
                for key, value in item.items()
                if key not in {"type", "name", "title", "category", "id"}
                and value not in (None, "", [], {})
            }
            if extras:
                return f"{label}: " + "; ".join(
                    f"{key}: {_format_list_item(value)}" for key, value in extras.items()
                )
            return str(label)
        return "; ".join(
            f"{key}: {_format_list_item(value)}"
            for key, value in item.items()
            if value not in (None, "", [], {})
        )
    if isinstance(item, list):
        return "; ".join(_format_list_item(value) for value in item)
    return str(item)


def _string_list(value: Any) -> list[str]:
    return [_format_list_item(item) for item in _ensure_list(value)]


def _coerce_story(story: Any) -> Dict[str, Any]:
    if isinstance(story, str):
        story = {"story": story}
    elif not isinstance(story, dict):
        story = {}

    text = str(story.get("story") or "")
    parsed = re.search(
        r"as an?\s+(?P<as_a>.*?),\s*i want\s+(?P<i_want>.*?),\s*so that\s+(?P<so_that>.*?)[\.\s]*$",
        text,
        re.IGNORECASE,
    )
    if parsed:
        parsed_story = {key: value.strip() for key, value in parsed.groupdict().items()}
    else:
        parsed_story = {}

    return {
        "as_a": story.get("as_a") or parsed_story.get("as_a") or "user",
        "i_want": story.get("i_want") or parsed_story.get("i_want") or text or "complete the workflow",
        "so_that": story.get("so_that") or parsed_story.get("so_that") or "I can achieve my goal",
        "priority": story.get("priority") if story.get("priority") in {"must", "should", "could"} else "should",
        "acceptance_criteria": _string_list(story.get("acceptance_criteria")),
    }


def _coerce_risk(risk: Any) -> str:
    if isinstance(risk, dict):
        risk_text = risk.get("risk") or risk.get("description") or risk.get("title")
        mitigation = risk.get("mitigation")
        if risk_text and mitigation:
            return f"{risk_text} Mitigation: {mitigation}"
        if risk_text:
            return str(risk_text)
    return str(risk)


def _coerce_scope(scope: Any) -> Dict[str, list[str]]:
    if not isinstance(scope, dict):
        return {"in_scope": [], "out_of_scope": []}
    return {
        "in_scope": _string_list(scope.get("in_scope")),
        "out_of_scope": _string_list(scope.get("out_of_scope")),
    }


def _normalize_spec(raw: Dict[str, Any], target: str, findings: list[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    draft = dict(raw)
    draft["type"] = draft.get("type") or target
    draft["glossary"] = draft.get("glossary") or draft.get("definitions") or {}
    draft["user_stories"] = [_coerce_story(story) for story in _ensure_list(draft.get("user_stories"))]
    draft["risks"] = [_coerce_risk(risk) for risk in _ensure_list(draft.get("risks"))]
    draft["scope"] = _coerce_scope(draft.get("scope"))
    for key in (
        "objectives",
        "functional_requirements",
        "non_functional_requirements",
        "metrics",
        "dependencies",
        "open_questions",
    ):
        draft[key] = _string_list(draft.get(key))

    try:
        spec = Spec(**draft).model_dump()
    except Exception:
        # WARNING: this fallback silently drops any field not in the allow-list
        # below (e.g. context, attachments, evidence, change_log, glossary,
        # rendered_markdown). It exists so a single bad subfield from the LLM
        # cannot fail the whole run, but the cost is hidden data loss with no
        # diagnostic.
        #
        # Concretely, if the LLM returns:
        #   {"title": "...", "context": "important framing", "user_stories": [...bad shape...]}
        # and Spec(**draft) raises on user_stories, the fallback rebuilds the
        # spec without `context` — the user never sees the framing text and
        # there is no log line saying it was discarded.
        #
        # Similarly, an LLM that emits `attachments=[{"id": "x", "uri": ...}]`
        # alongside one invalid `metrics` entry will lose `attachments`
        # entirely on the fallback path, even though attachments was valid.
        #
        # Follow-up: capture the original ValidationError and either log it
        # with the offending field path, or narrow the fallback to repair only
        # the field that failed instead of rebuilding the whole spec from a
        # fixed allow-list. Until then, treat any field outside this list as
        # best-effort.
        fallback = {
            "title": str(draft.get("title") or "Untitled Spec"),
            "type": target,
            "status": "draft",
            "problem_statement": str(draft.get("problem_statement") or ""),
            "objectives": draft.get("objectives", []),
            "user_stories": draft.get("user_stories", []),
            "functional_requirements": draft.get("functional_requirements", []),
            "non_functional_requirements": draft.get("non_functional_requirements", []),
            "metrics": draft.get("metrics", []),
            "dependencies": draft.get("dependencies", []),
            "risks": draft.get("risks", []),
            "scope": draft.get("scope", {"in_scope": [], "out_of_scope": []}),
            "open_questions": draft.get("open_questions", []),
        }
        spec = Spec(**fallback).model_dump()
    if findings is not None:
        spec["findings"] = findings
    return spec


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
        "_trace_meta": TraceMeta(model=_model_id(), token_usage=_token_usage(resp)),
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
    spec = _normalize_spec(draft, state.get("target", "PRD"))
    return {
        "spec": spec,
        "_trace_meta": TraceMeta(model=_model_id(), token_usage=_token_usage(resp)),
    }


@traced_node("critique", hash_subject=lambda state: spec_hash_subject(state.get("spec", {})))
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
    notes_rules = validators.run_all(state.get("spec", {}), produced_by_node="critique")
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
            token_usage=_token_usage(resp),
            prompts=[
                PromptTrace(
                    prompt_id=critique_prompt_id,
                    prompt_text=prompt_text,
                )
            ],
        ),
    }


@traced_node("revise", hash_subject=lambda state: spec_hash_subject(state.get("spec", {})))
async def revise(state: State) -> State:
    findings = state.get("spec", {}).get("findings", [])
    if not findings:
        return {}
    rule_findings = [finding for finding in findings if finding.get("kind") == "rule"]
    # Critique findings are preserved verbatim across the revise step. Rule findings
    # are deterministic and re-derivable, so we re-run validators against the revised
    # spec below. Critique findings are probabilistic and not reproducible without
    # another LLM call; preserving them keeps the prompt-id provenance chain intact
    # at the cost of potentially carrying notes that no longer apply post-revision.
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
    if isinstance(improved, dict):
        improved = _normalize_spec(improved, state.get("target", "PRD"))
        from utils import validators

        refreshed_rule_findings = [
            finding.model_dump() if hasattr(finding, "model_dump") else finding
            for finding in validators.run_all(improved, produced_by_node="revise")
        ]
        improved["findings"] = [
            *refreshed_rule_findings,
            *critique_findings,
        ]
    return {
        "spec": improved,
        "_trace_meta": TraceMeta(model=_model_id(), token_usage=_token_usage(resp)),
    }
