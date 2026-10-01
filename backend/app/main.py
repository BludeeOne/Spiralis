"""Spiralis API.

Run from backend/:  uvicorn app.main:app --reload
Demo:               http://localhost:8000/
Docs:               http://localhost:8000/docs
"""
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app import theory_bridge
from app.audio.detection import extract_features
from app.schemas import AnalysisResponse, AudioFeatures, TheoryResult, WrittenInput

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Spiralis API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite / CRA dev servers
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def demo_page():
    """Minimal demo UI. Same origin as the API, so no CORS involved."""
    return FileResponse(STATIC_DIR / "demo.html")


@app.get("/health")
def health():
    return {"status": "ok"}


#plain `def`, not `async def`: Essentia is CPU-bound and blocking, so FastAPI
@app.post("/analyze", response_model=AnalysisResponse)
def analyze_audio(file: UploadFile):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}")

    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (50 MB max)")
    if not data:
        raise HTTPException(400, "Empty file")

    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:  # MonoLoader needs a real path
        tmp.write(data)
        tmp.flush()
        try:
            features = AudioFeatures(**extract_features(tmp.name))
        except RuntimeError as e:  # Essentia raises RuntimeError on undecodable audio
            raise HTTPException(422, f"Could not decode audio: {e}") from e

    try:
        theory = theory_bridge.analyze(
            [f.pitch_classes for f in features.frames],
            key_hint=f"{features.essentia_key.key} {features.essentia_key.scale}",
        )
        status = "ok"
    except NotImplementedError as e:
        theory, status = None, f"pending: {e}"

    return AnalysisResponse(features=features, theory=theory, theory_status=status)


@app.post("/analyze/written", response_model=TheoryResult)
def analyze_written(body: WrittenInput):
    try:
        pitch_sets = theory_bridge.parse_written(body.chords)
        return theory_bridge.analyze(pitch_sets)
    except NotImplementedError as e:
        raise HTTPException(501, str(e)) from e
    except (KeyError, ValueError) as e:  # bad note name from pitch_of
        raise HTTPException(422, f"Invalid note: {e}") from e