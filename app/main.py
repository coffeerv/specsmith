
from __future__ import annotations
from fastapi import FastAPI, HTTPException, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from uuid import uuid4
from agents.graph import build_graph
from utils.provider import is_llm_configuration_error

app = FastAPI(title="SpecSmith (LangGraph + Vertex/Gemini)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

graph = build_graph()

async def _normalize_files(files: List[UploadFile] | None):
    assets = []
    if not files: return assets
    idx = 0
    for f in files:
        b = await f.read()
        assets.append({"id": f"asset_{idx}", "type": None, "filename": f.filename, "bytes": b})
        idx += 1
    return assets

@app.post("/specify")
async def specify(files: List[UploadFile] | None = None,
                  specscript: Optional[str] = Form(default=None),
                  target: Optional[str] = Form(default=None)):
    assets = await _normalize_files(files)
    if specscript:
        assets.append({"id": "specscript_0", "type": "text", "text": specscript, "source": "specscript"})
    state = {"assets": assets, "run_id": uuid4(), "trace": []}
    try:
        result = await graph.ainvoke(state)
    except Exception as exc:
        if is_llm_configuration_error(exc):
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        raise
    return {
        "target": result.get("target","PRD"),
        "spec": result.get("spec",{}),
        "trace": {
            "run_id": str(result["run_id"]),
            "entries": [
                entry.model_dump(mode="json")
                for entry in result.get("trace", [])
            ],
        },
    }
