
# SpecSmith

This MVP uses **LangGraph** with **Gemini**.
It supports images via Gemini captioning when `USE_GEMINI_VISION=1`, plus text/audio/video stubs.

## Prereqs
- Python 3.11+
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
