
from __future__ import annotations
import os
from typing import Optional
from dotenv import load_dotenv
from langchain_google_vertexai import ChatVertexAI

load_dotenv()

def get_llm():
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION","us-central1")
    model = os.getenv("GEMINI_MODEL","gemini-2.5-flash")
    temperature = float(os.getenv("TEMPERATURE","0.2"))
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is not set. Run `gcloud auth application-default login` and export GOOGLE_CLOUD_PROJECT.")
    return ChatVertexAI(project=project, location=location, model=model, temperature=temperature)

_captioner = None

def get_captioner():
    global _captioner
    if _captioner is not None:
        return _captioner
    from vertexai.generative_models import GenerativeModel  # lazy import
    model = os.getenv("GEMINI_VISION_MODEL", os.getenv("GEMINI_MODEL","gemini-2.5-flash"))
    _captioner = GenerativeModel(model)
    return _captioner
