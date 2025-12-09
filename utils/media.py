
from __future__ import annotations
import os, io
from PIL import Image
from .provider import get_captioner
def detect_type(filename: str) -> str:
    f = filename.lower()
    if any(f.endswith(x) for x in [".png",".jpg",".jpeg",".gif",".bmp",".webp"]): return "image"
    if any(f.endswith(x) for x in [".mp4",".mov",".mkv",".webm",".avi"]): return "video"
    if any(f.endswith(x) for x in [".mp3",".wav",".m4a",".aac",".flac",".ogg"]): return "audio"
    if any(f.endswith(x) for x in [".pdf"]): return "pdf"
    if any(f.endswith(x) for x in [".txt",".md",".rtf"]): return "text"
    return "binary"

def stub_ocr(image_bytes: bytes) -> str:
    try:
        Image.open(io.BytesIO(image_bytes))
        return "[OCR_STUB] Image detected; enable USE_GEMINI_VISION=1 for captioning."
    except Exception:
        return "[OCR_STUB] Invalid image data."

def gemini_caption(image_bytes: bytes) -> str:
    try:
        from vertexai.generative_models import Part
        cap = get_captioner()
        part = Part.from_data(mime_type="image/png", data=image_bytes)
        prompt = "Describe the UI elements and user intent relevant for a product spec. Be concise and structured."
        resp = cap.generate_content([prompt, part])
        return getattr(resp, "text", None) or "[VISION_EMPTY]"
    except Exception as e:
        return f"[VISION_ERROR] {e}; falling back to OCR stub."

def summarize_image(image_bytes: bytes) -> str:
    if os.getenv("USE_GEMINI_VISION","0") == "1":
        return gemini_caption(image_bytes)
    return stub_ocr(image_bytes)

def stub_asr(audio_bytes: bytes) -> str:
    return "[ASR_STUB] Transcribed text here; replace with WhisperX/Vertex Transcribe."

def stub_video_summary(video_bytes: bytes) -> str:
    return "[VIDEO_STUB] Keyframes + captions summary; replace with scenedetect + Gemini VLM."
