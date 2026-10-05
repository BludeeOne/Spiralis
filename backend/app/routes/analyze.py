"""POST /api/analyze: the contract the React dashboard expects (frontend/src/types.ts).

Detection comes from app.audio.detection. ALL theory comes from app.theory_bridge.
Any bridge function that's missing or raises NotImplementedError is listed in
`pending`, and its panel shows which function it's waiting on.

Bridge functions this route calls:
    identify_chord(pcs: list[int])               -> {"name": str, "root": int} | None
    estimate_key(chords: list[list[int]])        -> {"name": str, "relative": str | None} | None
    roman_numeral(chord: {"name","pcs"}, key)    -> str | None
    suggest_next(chord, key)                     -> [{"name": str, "numeral": str | None}]
    fitting_scales(key)                          -> [str]
    spell(pcs: list[int], key | None)            -> [str]
"""
import json
import tempfile

import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app import theory_bridge
from app.audio.detection import active_pitch_classes, extract_features

router = APIRouter(prefix="/api")

BRIDGE = ["identify_chord", "estimate_key", "roman_numeral", "suggest_next", "fitting_scales", "spell"]
SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]  # display fallback only
MAX_HISTORY = 32


def _call(name: str, pending: list[str], *args):
    """Call a bridge function; on missing/unimplemented, record it in pending and return None."""
    fn = getattr(theory_bridge, name, None)
    if fn is None:
        return None  # already listed up front
    try:
        return fn(*args)
    except NotImplementedError:
        if name not in pending:
            pending.append(name)
        return None


def _parse_history(raw: str) -> list[dict]:
    try:
        hist = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(400, "history must be JSON") from e
    if not isinstance(hist, list) or not all(
        isinstance(h, dict) and isinstance(h.get("name"), str) and isinstance(h.get("pcs"), list) for h in hist
    ):
        raise HTTPException(400, "history must be a list of {name, pcs}")
    return hist[-MAX_HISTORY:]


# plain def: Essentia is blocking, so FastAPI runs this in a threadpool
@router.post("/analyze")
def analyze(audio: UploadFile = File(...), history: str = Form("[]")):
    hist = _parse_history(history)

    data = audio.file.read()
    if not data:
        raise HTTPException(400, "Empty audio")
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:  # MonoLoader needs a real path
        tmp.write(data)
        tmp.flush()
        try:
            feats = extract_features(tmp.name)
        except RuntimeError as e:
            raise HTTPException(400, f"Could not decode audio: {e}") from e

    # One pitch-class set for the whole 2 s chunk: average the chroma of the loud beat frames.
    sounding = [f for f in feats["frames"] if f["pitch_classes"]]
    pcs = active_pitch_classes(np.mean([f["chroma"] for f in sounding], axis=0)) if sounding else []

    pending = [n for n in BRIDGE if not hasattr(theory_bridge, n)]

    chord = None
    if pcs:
        found = _call("identify_chord", pending, pcs)
        if found:
            chord = {"name": found["name"], "root": found["root"], "pcs": pcs}
            if not hist or hist[-1]["name"] != chord["name"]:
                hist = [*hist, {"name": chord["name"], "pcs": pcs}][-MAX_HISTORY:]

    key = _call("estimate_key", pending, [h["pcs"] for h in hist]) if hist else None

    progression = [
        {"name": h["name"], "numeral": _call("roman_numeral", pending, h, key) if key else None}
        for h in hist
    ]
    suggestions = (_call("suggest_next", pending, chord, key) or []) if chord and key else []
    scales = (_call("fitting_scales", pending, key) or []) if key else []
    notes = (_call("spell", pending, pcs, key) if pcs else None) or [SHARPS[p] for p in pcs]

    return {
        "notes": notes,
        "pcs": pcs,
        "chord": chord,
        "key": {"name": key["name"], "relative": key.get("relative")} if key else None,
        "history": hist,
        "progression": progression,
        "suggestions": suggestions,
        "scales": scales,
        "bpm": feats["bpm"] or None,  # 2 s chunks are too short for the beat tracker, so usually None
        "pending": pending,
    }