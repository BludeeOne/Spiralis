"""
analyze.py — takes the detection results and runs them through the pipeline

This file is basically the middle step of the whole process. It takes one
~2 second WAV chunk, sends it through the audio detection code, and then
passes those results to the music theory side of the program.

The basic flow is:

    WAV bytes
      
    audio.detection
      
    pitch classes, chroma, BPM, peak_hz
      
    theory_bridge
      
    chord, key, scales, suggestions
      
    AnalyzeResponse (schemas.py)


1. AUDIO DETECTION

The WAV chunk is first sent to `audio.detection`, which handles all of the
actual audio processing.

This gives us things like the detected pitch classes, the chroma vector,
the BPM, and the strongest frequency (`peak_hz`).


2. THEORY BRIDGE

Once we have the raw detection results, they are passed to `theory_bridge`.

This is where the program starts interpreting the notes as music. It uses
the detected pitch classes to figure out the most likely chord, key, scales,
and other suggestions.


3. RESPONSE

The final results are put into an `AnalyzeResponse`, which follows the
schemas defined in `schemas.py`.

The important thing about this file is that it connects the audio detection
side to the music theory side without doing all of that work itself.


ERROR HANDLING

If Essentia can't decode or process the audio, the error is caught and
returned as a 400 response with a readable `detail` message.

This keeps one bad audio chunk from crashing the entire server

"""
import json
import tempfile

import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app import theory_bridge
from app.audio.detection import active_pitch_classes, extract_features

router = APIRouter(prefix="/api")

BRIDGE = [
    "identify_chord",
    "estimate_key",
    "roman_numeral",
    "suggest_next",
    "fitting_scales",
    "spell",
    "respell",
]

SHARPS = [
    "C", "C#", "D", "D#", "E", "F",
    "F#", "G", "G#", "A", "A#", "B",
]

MAX_HISTORY = 32


def _call(name: str, pending: list[str], *args):
    """Call a theory bridge function and record missing or broken theory functions"""
    fn = getattr(theory_bridge, name, None)

    if fn is None:
        return None

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
        isinstance(h, dict)
        and isinstance(h.get("name"), str)
        and isinstance(h.get("pcs"), list)
        for h in hist
    ):
        raise HTTPException(400, "history must be a list of {name, pcs}")

    return hist[-MAX_HISTORY:]


def _key_response(key):
    """Frontend key format. The bridge already spells name and relative"""
    if not key:
        return None

    return {"name": key["name"], "relative": key["relative"]}


def _scale_names(scales):
    """Keep the frontend scales as a list of strings"""
    return [
        scale["name"] if isinstance(scale, dict) else scale
        for scale in scales
    ]


@router.post("/analyze")
def analyze(audio: UploadFile = File(...), history: str = Form("[]")):
    hist = _parse_history(history)

    data = audio.file.read()

    if not data:
        raise HTTPException(400, "Empty audio")

    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        #monoLoader needs a real path
        tmp.write(data)
        tmp.flush()

        try:
            feats = extract_features(tmp.name)
        except RuntimeError as e:
            raise HTTPException(400, f"Could not decode audio: {e}") from e

    #one pitch-class set for the whole chunk: average the chroma of
    #the frames where the detector found active pitch classes
    sounding = [
        frame for frame in feats["frames"]
        if frame["pitch_classes"]
    ]

    pcs = (
        active_pitch_classes(
            np.mean([frame["chroma"] for frame in sounding], axis=0)
        )
        if sounding
        else []
    )

    basses = [frame["bass"] for frame in sounding if frame.get("bass") is not None]
    bass = max(set(basses), key=basses.count) if basses else None

    pending = [
        name for name in BRIDGE
        if not hasattr(theory_bridge, name)
    ]

    chord = None

    if pcs:
        found = _call("identify_chord", pending, pcs, bass)

        if found:
            chord = {
                "name": found["name"],
                "root": found["root"],
                "suffix": found.get("suffix", ""),
                "pcs": pcs,
            }

            last = hist[-1] if hist else None
            same = last is not None and (
                (last.get("root"), last.get("suffix", "")) == (chord["root"], chord["suffix"])
                if "root" in last
                else last["name"] == chord["name"]
            )

            if not same:
                hist = [
                    *hist,
                    {
                        "name": chord["name"],
                        "pcs": pcs,
                        "root": chord["root"],
                        "suffix": chord.get("suffix", ""),
                    },
                ][-MAX_HISTORY:]

    key = (
        _call(
            "estimate_key",
            pending,
            [h["pcs"] for h in hist],
        )
        if hist
        else None
    )

    if key:
        respelled = _call("respell", pending, hist, key) or hist

        for old, new in zip(hist, respelled):
            old.update(new)

        if chord:
            current = _call("respell", pending, [chord], key)
            if current:
                chord["name"] = current[0]["name"]

    progression = [
        {
            "name": h["name"],
            "numeral": (
                _call("roman_numeral", pending, h, key)
                if key
                else None
            ),
        }
        for h in hist
    ]

    suggestions = (
        _call("suggest_next", pending, chord, key) or []
    ) if chord and key else []

    scales = (
        _call("fitting_scales", pending, key) or []
    ) if key else []

    notes = (
        _call("spell", pending, pcs, key)
        if pcs
        else None
    ) or [SHARPS[p] for p in pcs]

    return {
        "notes": notes,
        "pcs": pcs,
        "chord": chord,
        "key": _key_response(key),
        "history": hist,
        "progression": progression,
        "suggestions": suggestions,
        "scales": _scale_names(scales),
        "bpm": feats["bpm"] or None,
        "pending": pending,
    }