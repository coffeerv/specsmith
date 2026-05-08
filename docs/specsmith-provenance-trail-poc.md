# SpecSmith — Provenance Trail PoC

> Implementation brief in Spec Kit shape. Single-file handoff with compressed Constitution / Spec / Plan / Tasks structure. This PoC demonstrates inspectable agent orchestration, provenance of user-facing inputs, and separation between deterministic and LLM-generated findings.

---

## Constitution

Non-negotiable principles for this PoC. Every decision below defers to these.

### 1. Scope discipline

This is a Proof of Concept demonstrating an orchestration and provenance pattern.

It is not a production telemetry system, compliance audit log, replay engine, or observability platform.

We add the minimum that makes provenance demoable and credible. We explicitly avoid:

- Persistence.
- Replay tooling.
- OpenTelemetry exporters.
- Trace UIs.
- Retry-with-trace behavior.
- Prompt version registries.
- Redaction policies.
- Multi-tenant trace scoping.
- Tamper-proof or immutable audit storage.

Anything beyond this PoC should become a follow-up issue, not part of this implementation.

### 2. Trace integrity beats trace richness

A small, typed, consistent trace is more valuable than a verbose, inconsistent one.

If we cannot reliably populate a field across the relevant nodes, we omit it or mark it optional.

A successful run must never return without a complete trace for all instrumented nodes.

### 3. Existing patterns are preserved

No refactor of the agent graph topology.

No change to node responsibilities.

No breaking change to the public behavior of `/specify`.

The trace is additive.

Clients that ignore the new `trace` field should continue to work.

### 4. Deterministic and probabilistic findings must remain separate

Auditability requires structural separation between deterministic validator findings and probabilistic LLM critique findings.

They must remain distinguishable end-to-end and must never be collapsed into a single string list.

### 5. Provenance hashes cover user-facing inputs only

Provenance hashes cover the user-facing input payloads consumed by each node.

They do not claim full model execution reproducibility.

System prompts, model-side state, inference settings, tool descriptions, and hidden provider behavior are not included in the hash.

This PoC verifies that the same user-facing inputs produce the same input fingerprints. Full model reproducibility would require prompt versioning, model version pinning, inference parameter capture, tool configuration capture, and replay infrastructure, all of which are out of scope.

### 6. The trace is a first-class artifact

The trace is part of typed state.

It is returned by the API.

It can be serialized as structured JSON.

It is not a side effect hidden in logs.

### 7. Prompt text is recorded once per trace entry

LLM critique findings must reference the prompt used to generate them.

The full prompt text is recorded once on the relevant node trace entry, not duplicated inside every critique finding.

This keeps the output readable while preserving provenance.

---

## Spec

## What we are building

A provenance trail for SpecSmith’s agent graph that records, for every run:

- Per-node execution metadata.
- Stable input hashes for each node’s user-facing input subject.
- Model identifiers for nodes that invoke an LLM.
- Prompt metadata for LLM-invoking nodes.
- Per-finding attribution distinguishing deterministic rule findings from LLM critique findings.
- A run-level identifier that ties trace entries together.

The trail is exposed as part of the API response and can be serialized as a structured JSON artifact.

---

## Outcomes

After this work is complete, the following must be true:

1. Calling `POST /specify` returns the existing `{target, spec}` payload plus a new top-level `trace` field.

2. The `trace` field includes one completed entry per executed graph node, in execution order:

   ```text
   ingest, classify, extract, critique, revise, render
   ```

3. Each trace entry includes stable execution metadata:

   - `entry_id`
   - `run_id`
   - `node`
   - `started_at`
   - `ended_at`
   - `duration_ms`
   - `input_hash`
   - `output_keys`
   - `status`

4. Nodes that invoke an LLM include model metadata. Nodes that do not invoke an LLM have `model: null`.

5. The `critique` node records prompt text once in its trace entry under `prompts`.

6. The `critique` node’s output preserves per-finding provenance. Every finding is either:

   - A `RuleFinding`, produced by deterministic validators.
   - A `CritiqueFinding`, produced by an LLM critique pass.

7. `CritiqueFinding` references the prompt by `critique_prompt_id`. The corresponding prompt text is available in the `critique` node’s trace entry.

8. Given the same user-facing input payloads, input hashes are identical across runs.

9. Existing example inputs, such as `examples/screenshot_prd.specscript`, continue to work end-to-end with no behavioral change beyond the addition of trace data and typed findings.

---

## Out of scope

Do not build:

- Persistence to disk or database.
- A `/trace/{run_id}` endpoint.
- Replay tooling.
- Diffing tools.
- Trace UI.
- Prompt registry.
- Prompt redaction.
- Secret scrubbing.
- PII handling.
- Async streaming of trace entries.
- OpenTelemetry integration.
- External observability dependencies.
- Production-grade audit storage.
- Tamper-evidence.
- Cryptographic signing.
- A fully pluggable rule engine.

---

## Functional requirements

### FR-1. One completed trace entry per node

Each instrumented node execution produces exactly one completed `TraceEntry`, emitted after the node exits successfully.

No node produces zero entries.

No node produces more than one entry.

### FR-2. Run and entry identifiers

Each trace entry has a unique UUID.

Each run has a unique UUID shared by all entries in that run.

### FR-3. Deterministic input hashes

`TraceEntry.input_hash` is deterministic for identical user-facing input subjects.

Structured payloads use canonical JSON.

Binary payloads use raw bytes.

Mixed payloads use a canonical envelope.

### FR-4. Model metadata

`TraceEntry.model` is populated when and only when the node invoked an LLM.

Nodes that do not call an LLM have:

```json
"model": null
```

### FR-5. Prompt metadata

Nodes that invoke prompts may include prompt metadata in:

```json
"prompts": []
```

For this PoC, the `critique` node must record the full critique prompt text once in its trace entry.

### FR-6. Typed findings

The critique output review list is replaced with typed findings.

Each finding is either a `RuleFinding` or a `CritiqueFinding`, distinguished by a `kind` discriminator.

### FR-7. Rule findings

`RuleFinding` carries:

- `kind`
- `rule_id`
- `severity`
- `target_field`
- `message`

### FR-8. Critique findings

`CritiqueFinding` carries:

- `kind`
- `critique_prompt_id`
- `model`
- `severity`
- `target_field`
- `message`

The full prompt text is not duplicated on each finding. It is recorded once in the corresponding trace entry.

### FR-9. Trace integrity

A successful `/specify` response must include a complete trace.

If instrumentation is misconfigured, missing `run_id`, or unable to emit a trace entry, the run fails loudly during development.

### FR-10. Success-only trace entries for PoC

This PoC records successful node executions only.

Failure traces, exception capture, retry metadata, and partial traces are out of scope.

Each trace entry has:

```json
"status": "success"
```

---

# Plan

## Architecture decisions

---

## AD-1. Trace storage: in-state, sink-mediated writes

Trace entries are stored on the typed `State` as:

```python
state["trace"]: List[TraceEntry]
```

However, the decorator that produces entries does not write directly to `state["trace"]`.

It emits entries through a `TraceSink` interface.

The default implementation appends to in-state trace.

```python
class TraceSink(Protocol):
    def emit(self, state: State, entry: TraceEntry) -> dict: ...


class InStateSink:
    def emit(self, state, entry):
        return {
            "trace": [
                *state.get("trace", []),
                entry,
            ]
        }
```

The sink returns a partial state update, not a fully merged state.

### Rationale

This keeps the PoC simple because the trace flows with graph state.

It also preserves a future swap path to file, queue, database, or observability backend without changing node code.

---

## AD-2. Decorator-based instrumentation

A `@traced_node(...)` decorator wraps each node function.

The decorator is responsible for:

- Generating the entry UUID.
- Reading the existing `run_id`.
- Capturing `started_at`.
- Computing `input_hash`.
- Invoking the wrapped node function.
- Capturing `ended_at`.
- Computing `duration_ms`.
- Extracting `_trace_meta` from the node update.
- Stripping `_trace_meta` before returning state.
- Determining `output_keys`.
- Building a `TraceEntry`.
- Emitting the entry through the configured sink.
- Returning a partial state update containing the original node update plus the updated trace field.

Node functions remain mostly pure with respect to trace concerns.

They do not construct `TraceEntry`.

They may optionally return `_trace_meta` when they invoke an LLM or prompt.

---

## AD-3. Trace metadata via `_trace_meta`

Nodes that need to pass trace-specific metadata to the decorator return a private `_trace_meta` object.

Example:

```python
return {
    "spec": updated_spec,
    "_trace_meta": TraceMeta(
        model="vertex/gemini-1.5-pro",
        token_usage=None,
        prompts=[
            PromptTrace(
                prompt_id="critique.spec.v0",
                prompt_text=critique_prompt,
            )
        ],
    ),
}
```

The decorator consumes `_trace_meta`, copies its public values into the trace entry, and removes `_trace_meta` from the returned state update.

### Rationale

This avoids brittle single-purpose internal keys such as:

```python
"__last_model__"
"__last_prompt__"
"__last_token_usage__"
```

One small structured metadata object is easier to extend and easier to explain.

---

## AD-4. Per-finding provenance in `critique`

`utils/validators.run_all(spec)` is changed to return:

```python
List[RuleFinding]
```

instead of:

```python
List[str]
```

Each validator gets:

- Stable `rule_id`.
- Default severity.
- Best-effort `target_field`.

The LLM critique step wraps each LLM-produced review item in a `CritiqueFinding`.

The merged review output becomes:

```python
List[Finding]
```

where `Finding` is a discriminated union of:

- `RuleFinding`
- `CritiqueFinding`

The findings live on the spec as:

```python
spec["findings"]
```

---

## AD-5. Prompt provenance

The LLM critique prompt is recorded once on the `critique` node’s trace entry:

```json
{
  "node": "critique",
  "model": "vertex/gemini-1.5-pro",
  "prompts": [
    {
      "prompt_id": "critique.spec.v0",
      "prompt_text": "..."
    }
  ]
}
```

Each LLM-produced finding references that prompt:

```json
{
  "kind": "critique",
  "critique_prompt_id": "critique.spec.v0",
  "model": "vertex/gemini-1.5-pro",
  "severity": "warn",
  "target_field": "acceptance_criteria",
  "message": "Acceptance criteria are present but not measurable enough."
}
```

### Rationale

This avoids duplicating the full prompt text across multiple findings.

It also cleanly separates node-level execution provenance from finding-level attribution.

---

## AD-6. Hashing strategy

Structured payloads:

```python
sha256(
    json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
)
```

Binary payloads:

```python
sha256(raw_bytes)
```

Mixed payloads:

```python
{
    "text": [...],
    "binary_hashes": [...]
}
```

Each binary asset contributes its own SHA-256.

The mixed envelope is then hashed using canonical JSON.

### Important limitation

Hash scope is user-facing input payload only.

The hash does not cover:

- System prompts.
- Hidden instructions.
- Tool descriptions.
- Model provider internals.
- Inference parameters.
- Model-side state.

This is intentional for the PoC.

---

## AD-7. Per-node input hash subjects

Each node defines its own meaningful input subject.

| Node | Hash subject |
|---|---|
| `ingest` | User-provided assets |
| `classify` | `state["corpus"]` |
| `extract` | `state["corpus"]` + `state["target"]` |
| `critique` | Spec before findings |
| `revise` | Spec including findings |
| `render` | Revised spec |

The decorator receives a `hash_subject` callable.

Example:

```python
@traced_node(
    name="critique",
    hash_subject=lambda state: state["spec"],
)
def critique_node(state: State) -> dict:
    ...
```

For `ingest`, use a dedicated hash subject helper because assets may include mixed text and binary payloads.

---

## AD-8. API surface

`POST /specify` response changes from:

```json
{
  "target": "PRD",
  "spec": {}
}
```

to:

```json
{
  "target": "PRD",
  "spec": {},
  "trace": {
    "run_id": "uuid",
    "entries": []
  }
}
```

No new endpoints.

No query parameters.

Backward compatibility for clients that ignore `trace` is preserved.

---

# Data model

Create a new file:

```text
models/trace.py
```

---

## `PromptTrace`

```python
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Dict, List, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class PromptTrace(BaseModel):
    prompt_id: str
    prompt_text: str
```

---

## `TraceMeta`

Internal node-to-decorator metadata.

This is not returned directly by the API.

```python
class TraceMeta(BaseModel):
    model: Optional[str] = None
    token_usage: Optional[Dict[str, int]] = None
    prompts: List[PromptTrace] = Field(default_factory=list)
```

---

## `TraceEntry`

```python
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
```

---

## `RuleFinding`

```python
Severity = Literal["info", "warn", "error"]


class RuleFinding(BaseModel):
    kind: Literal["rule"] = "rule"
    rule_id: str
    severity: Severity
    target_field: Optional[str] = None
    message: str
```

---

## `CritiqueFinding`

```python
class CritiqueFinding(BaseModel):
    kind: Literal["critique"] = "critique"
    critique_prompt_id: str
    model: str
    severity: Severity
    target_field: Optional[str] = None
    message: str
```

---

## `Finding`

```python
Finding = Annotated[
    Union[RuleFinding, CritiqueFinding],
    Field(discriminator="kind"),
]
```

---

## State additions

Wherever the graph `State` TypedDict lives:

```python
from typing import List, NotRequired
from uuid import UUID

from models.trace import TraceEntry


class State(TypedDict):
    ...
    run_id: NotRequired[UUID]
    trace: NotRequired[List[TraceEntry]]
```

At graph entry, initialize:

```python
{
    **initial_state,
    "run_id": uuid4(),
    "trace": [],
}
```

---

# Test plan

PoC-level, not exhaustive.

---

## Unit tests

### 1. Hash determinism

Assert:

- Same structured payload produces same hash.
- Dict key order does not affect hash.
- Changed value changes hash.
- Same bytes produce same hash.
- Mixed envelope produces stable hash.

### 2. Finding discriminator

Assert `RuleFinding` and `CritiqueFinding` round-trip through Pydantic validation using the `kind` discriminator.

### 3. Trace decorator

Wrap a stub node.

Assert:

- One trace entry is emitted.
- `run_id` is copied from state.
- `entry_id` is generated.
- `started_at` and `ended_at` are populated.
- `duration_ms` is non-negative.
- `status` is `"success"`.
- `output_keys` excludes `_trace_meta`.
- Returned state update does not contain `_trace_meta`.

### 4. Trace metadata

Wrap a stub node that returns `_trace_meta`.

Assert:

- `model` appears on `TraceEntry`.
- `prompts` appear on `TraceEntry`.
- `_trace_meta` does not appear in returned state.

---

## Integration tests

### 1. Trace order

Run the existing example through `/specify`.

Assert `trace.entries` has exactly six entries in order:

```text
ingest, classify, extract, critique, revise, render
```

### 2. Hash stability

Run the same input twice.

Assert:

- `run_id` differs.
- `entry_id` values differ.
- `input_hash` values match node-by-node.

### 3. Finding provenance

Run an input known to trigger both deterministic and LLM findings.

Assert:

- `spec.findings` contains at least one `RuleFinding`.
- `spec.findings` contains at least one `CritiqueFinding`.
- `CritiqueFinding.critique_prompt_id` matches a prompt in the `critique` trace entry.

---

# Tasks

Ordered, atomic, executable.

---

## T-1. Create `models/trace.py`

Define:

- `PromptTrace`
- `TraceMeta`
- `TraceEntry`
- `RuleFinding`
- `CritiqueFinding`
- `Finding`

Use `from __future__ import annotations`.

Use Pydantic models.

Use a discriminated union for `Finding`.

**Done when:**

- All models import cleanly.
- `RuleFinding` validates.
- `CritiqueFinding` validates.
- The `Finding` discriminator works with both `kind: "rule"` and `kind: "critique"`.

---

## T-2. Add `run_id` and `trace` to graph state

Locate the `State` TypedDict.

Add:

```python
run_id: NotRequired[UUID]
trace: NotRequired[List[TraceEntry]]
```

Update the graph entry path to initialize both before the first node runs:

```python
"run_id": uuid4()
"trace": []
```

**Done when:**

- `state["run_id"]` exists before `ingest`.
- `state["trace"]` exists as an empty list before `ingest`.

---

## T-3. Implement hashing utilities

Create:

```text
utils/hashing.py
```

With:

```python
def hash_structured(payload: Any) -> str:
    ...


def hash_bytes(data: bytes) -> str:
    ...


def hash_envelope(text_parts: List[str], binary_parts: List[bytes]) -> str:
    ...
```

Rules:

- Structured payloads use canonical JSON.
- Binary payloads use raw SHA-256.
- Mixed payloads hash binary parts individually, then hash the canonical envelope.

**Done when:**

- Same structured input hashes identically across calls.
- Dict key ordering does not affect hash.
- Changed value changes hash.
- Same binary input hashes identically.
- Mixed text/binary envelopes hash deterministically.

---

## T-4. Implement `TraceSink` and `InStateSink`

Create:

```text
utils/trace_sink.py
```

With:

```python
class TraceSink(Protocol):
    def emit(self, state: State, entry: TraceEntry) -> dict:
        ...


class InStateSink:
    def emit(self, state: State, entry: TraceEntry) -> dict:
        return {
            "trace": [
                *state.get("trace", []),
                entry,
            ]
        }
```

The sink returns a partial update.

It does not mutate the original state.

**Done when:**

- `InStateSink().emit(state, entry)` returns a dict containing the appended trace.
- The original `state` object is unchanged.

---

## T-5. Implement `@traced_node`

Create:

```text
agents/instrumentation.py
```

Signature:

```python
def traced_node(
    name: NodeName,
    hash_subject: Callable[[State], Any],
    sink: Optional[TraceSink] = None,
):
    ...
```

Behavior:

1. Ensure `state["run_id"]` exists.
2. Capture `started_at`.
3. Compute `input_hash` from `hash_subject(state)`.
4. Invoke wrapped node.
5. Capture `ended_at`.
6. Compute `duration_ms`.
7. Extract `_trace_meta` from node update, if present.
8. Strip `_trace_meta`.
9. Determine `output_keys` from the cleaned node update.
10. Build `TraceEntry`.
11. Emit via sink.
12. Return a partial state update:

```python
{
    **cleaned_node_update,
    **trace_update,
}
```

**Done when:**

- Stub node instrumentation works.
- `_trace_meta` is consumed and stripped.
- Trace entry contains model and prompt metadata when provided.
- Trace entry contains `status: "success"`.
- Returned update is partial state, not a full merged state.

---

## T-6. Define per-node input hash subjects

Decorate every node with `@traced_node`.

Hash subjects:

| Node | Hash subject |
|---|---|
| `ingest` | User-provided assets |
| `classify` | `state["corpus"]` |
| `extract` | `{"corpus": state["corpus"], "target": state["target"]}` |
| `critique` | Spec before findings |
| `revise` | Spec including findings |
| `render` | Revised spec |

Example:

```python
@traced_node(
    name="extract",
    hash_subject=lambda state: {
        "corpus": state["corpus"],
        "target": state["target"],
    },
)
def extract_node(state: State) -> dict:
    ...
```

**Done when:**

- Every graph node is decorated.
- Existing example produces exactly six trace entries.
- Hashes match across identical-input runs.

---

## T-7. Refactor validators to return `RuleFinding`

Update:

```text
utils/validators.py
```

Each validator returns:

```python
List[RuleFinding]
```

instead of:

```python
List[str]
```

Assign stable rule IDs, for example:

```text
acceptance.coverage
nfr.presence
objectives.metrics
```

Each finding includes:

- `rule_id`
- `severity`
- `target_field`
- `message`

**Done when:**

- No validator returns plain strings.
- `run_all()` returns `List[RuleFinding]`.
- Existing validation behavior remains semantically the same.

---

## T-8. Refactor LLM critique to emit `CritiqueFinding`

In the `critique` node:

1. Assign prompt ID:

```python
critique_prompt_id = "critique.spec.v0"
```

2. Build the critique prompt.

3. Invoke the LLM.

4. Wrap every LLM-produced review item as `CritiqueFinding`.

5. Store the merged findings at:

```python
spec["findings"]
```

6. Return `_trace_meta` with:

```python
TraceMeta(
    model=model_id,
    token_usage=token_usage_or_none,
    prompts=[
        PromptTrace(
            prompt_id=critique_prompt_id,
            prompt_text=critique_prompt,
        )
    ],
)
```

**Done when:**

- LLM critique findings are typed.
- Each `CritiqueFinding` references `critique_prompt_id`.
- The full prompt text appears once in the `critique` trace entry.
- The prompt text is not duplicated inside each finding.

---

## T-9. Update `revise` to consume typed findings

Update the `revise` node to read:

```python
state["spec"]["findings"]
```

Instead of:

```python
state["spec"]["review"]
```

Adjust the revision prompt to format findings grouped by kind:

```text
Deterministic validator findings:
- ...

LLM critique findings:
- ...
```

The revision behavior should remain minimal and PoC-friendly.

**Done when:**

- `revise` runs with mixed `RuleFinding` and `CritiqueFinding` items.
- Revised spec is produced.
- `render` continues to work.

---

## T-10. Wire trace into API response

Update `/specify` in:

```text
app/main.py
```

Return:

```python
{
    "target": result["target"],
    "spec": result["spec"],
    "trace": {
        "run_id": str(result["run_id"]),
        "entries": [
            entry.model_dump(mode="json")
            for entry in result["trace"]
        ],
    },
}
```

**Done when:**

- `POST /specify` returns `{target, spec, trace}`.
- `trace.run_id` matches the run ID.
- `trace.entries` contains six entries for the standard example.

---

## T-11. Add minimal tests

Create:

```text
tests/provenance/
```

Add tests for:

- Hash determinism.
- Finding discriminator.
- Trace decorator.
- Trace metadata.
- Trace order integration.
- Hash stability integration.
- Finding provenance.

**Done when:**

```bash
pytest tests/provenance/
```

passes locally.

At minimum, the non-negotiable tests are:

- Hash determinism.
- Trace order integration.
- Prompt reference integrity.

---

## T-12. Update README

Add a short section:

```text
Provenance Trail
```

It should explain:

- What the trace contains.
- That this is not a production audit log.
- That hashes cover user-facing input provenance only.
- That `RuleFinding` and `CritiqueFinding` are distinguishable by `kind`.
- That LLM critique prompts are recorded once on the node trace entry.
- That findings reference prompt IDs.
- That `TraceSink` provides a future swap path without promising external observability support.

**Done when:**

An outside reader can understand the purpose and limits of the provenance trail in under two minutes.

---

# Acceptance check

The work is complete when, for the existing:

```text
examples/screenshot_prd.specscript
```

input:

1. `POST /specify` returns:

   ```json
   {
     "target": "...",
     "spec": {},
     "trace": {}
   }
   ```

2. `trace.entries` has exactly six entries, in this order:

   ```text
   ingest, classify, extract, critique, revise, render
   ```

3. Each entry has required fields populated.

4. Each entry has:

   ```json
   "status": "success"
   ```

5. `model` is populated exactly on LLM-invoking nodes.

6. The `critique` trace entry contains:

   ```json
   "prompts": [
     {
       "prompt_id": "critique.spec.v0",
       "prompt_text": "..."
     }
   ]
   ```

7. `spec.findings` contains both:

   - `RuleFinding`
   - `CritiqueFinding`

8. Each `CritiqueFinding.critique_prompt_id` matches a prompt ID in the `critique` trace entry.

9. Running the same input twice produces identical `input_hash` values for every node.

10. All tests under `tests/provenance/` pass.

11. README reflects the new behavior and its limits.

Anything beyond this is out of scope for this PoC and should be opened as a follow-up issue.
