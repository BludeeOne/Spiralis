"""schemas file
description: a running list of everything this engine should support"""
from pydantic import BaseModel, Field


class KeyEstimate(BaseModel):
    key: str
    scale: str
    strength: float


class BeatFrame(BaseModel):
    start: float                     # seconds
    end: float
    chroma: list[float]              # 12 values, index 0 = C
    pitch_classes: list[int]         # active notes, 0-11, at most 5 to reduce computation time


class AudioFeatures(BaseModel):
    duration: float
    bpm: float
    frames: list[BeatFrame]
    essentia_key: KeyEstimate        # cross-check


class TheoryResult(BaseModel):
    key: str | None = None
    progression: list[str] = Field(default_factory=list)       # e.g. ["I", "V", "vi", "IV"]
    chords: list[str] = Field(default_factory=list)            # e.g. ["C", "G", "Am", "F"]
    scales: list[str] = Field(default_factory=list)            # e.g. ["Major Pentatonic"]
    related_chords: list[str] = Field(default_factory=list)    # circle-of-fifths neighbors
    next_chords: list[str] = Field(default_factory=list)       # possible song paths


class AnalysisResponse(BaseModel):
    features: AudioFeatures
    theory: TheoryResult | None
    theory_status: str               


class WrittenInput(BaseModel):
    #incase theyd rather just write intheir song without having to play it
    chords: list[list[str]] = Field(min_length=1)