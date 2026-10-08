"""
schemas.py The tal between front and backend

Pydantic models for everything that crosses the wire. The frontend panels read
these field names directly, so renaming a field here is a breaking change for
the components in frontend/src/components/ (and types.ts mirrors them).

Conventions
  - Pitch classes are ints 0–11 with C = 0. essentia starts with A = 0, but it was no issue
  - `pending` lists theory functions that raised NotImplementedError, so the UI
    can say "waiting on chords.identify" instead of showing blank boxes.
"""
from pydantic import BaseModel, Field


class KeyEstimate(BaseModel):
    key: str
    scale: str
    strength: float


class BeatFrame(BaseModel):
    start: float                    # seconds
    end: float                      # also seconds
    chroma: list[float]             # 12 values index 0 = C
    pitch_classes: list[int]        # active notes, 0-11, at most 5 to reduce computation time ;P
    bass: int | None = None         # lowest strong pitch class, if detected


class AudioFeatures(BaseModel):
    duration: float
    bpm: float
    frames: list[BeatFrame]
    essentia_key: KeyEstimate        # cross-check


class KeyInfo(BaseModel):
    tonic: int
    mode: str                        # "major" | "minor"
    name: str                        # i.e "Bb major"
    relative: str                    # i.e. "G minor" relative is the same key 3 semitones down major


class TheoryResult(BaseModel):
    key: KeyInfo | None = None
    history: list[dict] = Field(default_factory=list)          # [{root, suffix, name, ...}] chord changes
    progression: list[str | None] = Field(default_factory=list)  # e.g. ["I", "V", "vi", "IV"]
    suggestions: list[dict] = Field(default_factory=list)      # [{root, suffix, name, numeral}]
    scales: list[dict] = Field(default_factory=list)           # [{root, type, name}]


class AnalysisResponse(BaseModel):
    features: AudioFeatures
    theory: TheoryResult | None
    theory_status: str               


class WrittenInput(BaseModel):
    #incase theyd rather just write intheir song without having to play it
    chords: list[str] = Field(min_length=1)   # chord names, e.g. ["C", "G7", "Am", "F"]