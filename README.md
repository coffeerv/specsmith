
# SpecSmith

This MVP uses **LangGraph** with **Google Vertex AI (Gemini)**
It supports images via Gemini captioning when `USE_GEMINI_VISION=1`, plus text/audio/video stubs.

## Prereqs
- Python 3.11+
- Auth: `gcloud auth application-default login`
- Env:
  ```env
  GOOGLE_CLOUD_PROJECT=your-project-id
  GOOGLE_CLOUD_LOCATION=us-central1   # or europe-west1
  GEMINI_MODEL=gemini-2.5-flash       # or gemini-2.5-pro
  USE_GEMINI_VISION=1                 # enable image captioning
  ```

## Install & Run
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
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

