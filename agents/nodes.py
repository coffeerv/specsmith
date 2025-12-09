
from __future__ import annotations
from typing import Dict, Any, List, TypedDict
from models.spec import Spec, TARGET_SPECS
from utils.provider import get_llm
from utils.media import detect_type, summarize_image, stub_asr, stub_video_summary
from parsers.specscript import parse_specscript
from langchain_core.messages import SystemMessage, HumanMessage
import json
import re

def _parse_json(text: str) -> Any:
    text = text.strip()
    # Remove markdown code blocks
    if "```" in text:
        pattern = r"```(?:json)?\s*(.*?)\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            text = match.group(1)
    return json.loads(text)

class State(TypedDict, total=False):
    assets: List[Dict[str,Any]]
    corpus: List[Dict[str,Any]]
    classification: Dict[str, Any]
    spec: Dict[str, Any]
    critiques: List[str]
    target: str
    parsed_specscript: Dict[str, Any]

llm = get_llm()

async def ingest(state: State) -> State:
    corpus: List[Dict[str, Any]] = []
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
            shard_text = asset.get("text","")
        else:
            shard_text = asset.get("text","[UNSUPPORTED_ASSET]")
        corpus.append({"id": asset.get("id", f"shard_{len(corpus)}"),
                       "type": kind or "unknown",
                       "text": shard_text})
    state["corpus"] = corpus
    for a in state.get("assets", []):
        if a.get("source") == "specscript":
            state["parsed_specscript"] = parse_specscript(a.get("text",""))
    return state

async def classify(state: State) -> State:
    prompt = (
        f"Classify user intent and artifact types from shards: {state.get('corpus', [])}. "
        f"Return JSON with keys intent, artifact_types (list), confidence (0-1)."
    )
    resp = await llm.ainvoke([SystemMessage(content="You are a precise classifier."),
                              HumanMessage(content=prompt)])
    try:
        parsed = _parse_json(getattr(resp, "content", "{}"))
    except Exception:
        parsed = {"intent": "feature_request", "artifact_types": ["feature_request"], "confidence": 0.5}
    state["classification"] = parsed
    state["target"] = TARGET_SPECS.get(parsed.get("intent","feature_request"), "PRD")
    return state

async def extract(state: State) -> State:
    sys = ("You are SpecSmith, an extractor that emits JSON conforming to the Spec schema. "
           "Fill: title, problem_statement, objectives, user_stories (>=3), functional_requirements, "
           "non_functional_requirements, metrics, dependencies, risks, scope, open_questions. "
           "Use concise, testable language. Add acceptance criteria for each story in GWT form. "
           "If a SpecScript parse is available, respect it.")
    user = {"corpus": state.get("corpus", []),
            "target": state.get("target","PRD"),
            "specscript": state.get("parsed_specscript", {})}
    resp = await llm.ainvoke([SystemMessage(content=sys), HumanMessage(content=str(user))])
    try:
        draft = _parse_json(getattr(resp, "content", "{}"))
    except Exception:
        draft = {
            "title": user["specscript"].get("title","Untitled Spec"),
            "type": state.get("target","PRD"),
            "objectives": user["specscript"].get("objectives",[]),
            "user_stories": [{
                "as_a":"user","i_want":"export data","so_that":"I can analyze",
                "priority":"should","acceptance_criteria":["GWT: As a user, when ... then ..."]}],
            "functional_requirements": [],
            "non_functional_requirements": [],
            "metrics": user["specscript"].get("metrics", []),
            "scope": user["specscript"].get("scope", {"in_scope":[],"out_of_scope":[]})
        }
    draft.setdefault("type", state.get("target","PRD"))
    try:
        spec = Spec(**draft).model_dump()
    except Exception:
        spec = draft
        spec["type"] = state.get("target","PRD")
    state["spec"] = spec
    return state

async def critique(state: State) -> State:
    from utils import validators
    sys = "You are a senior PM. List blocking gaps, contradictions, and missing NFRs. Output a JSON list of strings."
    resp = await llm.ainvoke([SystemMessage(content=sys), HumanMessage(content=str(state.get("spec",{})))])
    try:
        notes_llm = _parse_json(getattr(resp,"content","[]"))
        if not isinstance(notes_llm, list): notes_llm = [str(notes_llm)]
    except Exception:
        notes_llm = []
    notes_rules = validators.run_all(state.get("spec", {}))
    state["critiques"] = list(dict.fromkeys(notes_rules + notes_llm))
    return state

async def revise(state: State) -> State:
    if not state.get("critiques"): return state
    prompt = f"Apply these review notes to improve the spec while preserving intent: {state['critiques']}\nSpec:{state['spec']}"
    resp = await llm.ainvoke([HumanMessage(content=prompt)])
    try:
        improved = _parse_json(getattr(resp,"content","{}"))
    except Exception:
        improved = state["spec"]
    state["spec"] = improved
    return state
