
```
   ____                  ____                _  _    _
  / ___| _ __   ___  ___/ ___| _ __ ___  (_)| |_ | |__
  \___ \| '_ \ / _ \/ __\___ \| '_ ` _ \ | || __|| '_ \
   ___) | |_) |  __/ (__ ___) | | | | | || || |_ | | | |
  |____/| .__/ \___|\___|____/|_| |_| |_||_| \__||_| |_|
        |_|                                     —⚒—
```

# SpecSmith

SpecSmith turns a lightweight **SpecScript** (a short structured brief, optionally accompanied by screenshots or other assets) into a structured PRD-style spec, by routing it through a small **LangGraph** agent pipeline — `ingest → classify → extract → critique → revise → render` — backed by **Gemini** (Vertex AI or Google GenAI).

The interesting part isn't the spec generation itself; it's everything around it. Each `/specify` call returns the generated artifact *and* a `trace` describing every node that ran: timing, status, the prompt text actually sent to the model, and a stable hash of the user-facing input subject at that step. Validator output (deterministic rules) and critique output (LLM judgments) stay structurally separate in `spec.findings`, so you can tell which findings a machine is sure about and which a model merely thinks.

In short: an opinionated take on **inspectable, provenance-aware multi-step LLM orchestration**, packaged small enough to read end-to-end. Architecture and design rationale live in [`docs/specsmith-provenance-trail-poc.md`](docs/specsmith-provenance-trail-poc.md).

> **Status:** Proof of concept. Not intended for production. The provenance trail
> in particular returns user-supplied content (and the prompts derived from it)
> in the API response. Do not deploy as-is in any setting where requests may
> contain PII, secrets, or otherwise sensitive data — there is no redaction,
> access control, audit storage, or trace scoping. See the
> [Provenance Trail](#provenance-trail) section for the full list of caveats.

This MVP uses **LangGraph** with **Gemini**.
It supports images via Gemini captioning when `USE_GEMINI_VISION=1`, plus text/audio/video stubs.

## Prereqs
- Python 3.14 (matches the Docker image; older 3.11+ interpreters may work but are not exercised in CI)
- Auth:
  - Google GenAI: set `GOOGLE_API_KEY` or `GEMINI_API_KEY`.
  - Vertex AI: run `gcloud auth application-default login` and set `LLM_PROVIDER=vertexai`.
- Env for Google GenAI:
  ```env
  LLM_PROVIDER=google_genai
  GOOGLE_API_KEY=your-api-key
  GEMINI_MODEL=gemini-2.5-flash       # or gemini-2.5-pro
  USE_GEMINI_VISION=0                 # image captioning still requires Vertex AI credentials
  ```
- Env for Vertex AI:
  ```env
  LLM_PROVIDER=vertexai
  GOOGLE_CLOUD_PROJECT=your-project-id
  GOOGLE_CLOUD_LOCATION=us-central1   # or europe-west1
  GEMINI_MODEL=gemini-2.5-flash       # or gemini-2.5-pro
  USE_GEMINI_VISION=1                 # enable image captioning via Vertex AI
  ```

## Install & Run
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Docker Compose
```bash
docker compose up --build
```

Compose defaults to `LLM_PROVIDER=offline` so the text-only smoke test works without cloud credentials. To use a real model, set `LLM_PROVIDER=google_genai` with `GOOGLE_API_KEY`, or use the Vertex override below after running `gcloud auth application-default login`.

If your `.env` sets `LLM_PROVIDER=vertexai`, the base Compose file is not enough; use the Vertex override so the container can see your Application Default Credentials.

`USE_GEMINI_VISION=1` currently routes image captioning through Vertex AI, even when text generation uses `LLM_PROVIDER=google_genai`. API-key-only setups should leave `USE_GEMINI_VISION=0`.

For Vertex AI in Docker, use the override file (docker-compose.vertex.yml) and point `GOOGLE_ADC_DIR` at your local gcloud config directory:

```bash
# macOS/Linux
export GOOGLE_ADC_DIR="$HOME/.config/gcloud"
docker compose -f docker-compose.yml -f docker-compose.vertex.yml up --build

# Windows PowerShell
$env:GOOGLE_ADC_DIR="$env:APPDATA\gcloud"
docker compose -f docker-compose.yml -f docker-compose.vertex.yml up --build
```

## Test (text-only)
```bash
curl -X POST "http://localhost:8000/specify"   -F 'specscript=#spec
Title: One-click export
Type: PRD
goals:
- reduce support tickets
accept:
- GWT: As an Ops Analyst, when I click Export, I receive a CSV.'
```

## Test with images
```bash
# Single image
curl -X POST "http://localhost:8000/specify"   -F files=@/path/to/screenshot_1.png   -F 'specscript=#spec
Title: Screenshot-driven spec
Type: PRD
accept:
- GWT: As a user, when I click Save, I see a toast.'

# Multiple images
curl -X POST "http://localhost:8000/specify"   -F files=@/path/to/screenshot_1.png   -F files=@/path/to/screenshot_2.jpg   -F 'specscript=#spec
Title: Multi-screenshot PRD
Type: PRD
metrics:
- p95 save < 2s
accept:
- GWT: As an editor, when I press Publish, the article becomes live.'
```

## Provenance Trail
`POST /specify` returns the generated `{target, spec}` plus a top-level `trace` artifact. The trace contains one entry per graph node (`ingest`, `classify`, `extract`, `critique`, `revise`, `render`) with execution timing, status, output keys, a run ID, and a stable hash of that node’s user-facing input subject.

This is a proof-of-concept provenance trail, not a production audit log. Hashes cover user-facing inputs only; they do not include system prompts, model provider internals, inference settings, hidden state, or replay metadata.

Deterministic validator findings and LLM critique findings are structurally separate in `spec.findings`. `RuleFinding` entries use `kind: "rule"`, while `CritiqueFinding` entries use `kind: "critique"` and reference the critique prompt by ID.

The full critique prompt text is recorded once on the `critique` trace entry under `prompts`. Individual critique findings reference that prompt ID instead of duplicating prompt text. Trace writes currently use an in-state `TraceSink`, which keeps the API artifact simple while leaving a future swap path for external sinks.

### Production / PII warning

The `trace.entries[].prompts[].prompt_text` field embeds the spec dict that was
sent to the LLM, which in turn embeds the original user-supplied corpus
(SpecScript text, image OCR, etc.). Any caller of `/specify` receives this
back. Before exposing this service beyond a local demo you must add at least:

- prompt-text redaction or omission for non-trusted callers,
- request-level authentication and per-tenant trace scoping,
- a real audit storage backend instead of `InStateSink`,
- a policy decision about logging PII and secrets that may appear in user input.

This PoC explicitly does not implement any of the above — see
`docs/specsmith-provenance-trail-poc.md` for the full out-of-scope list.
