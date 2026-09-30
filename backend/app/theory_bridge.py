# theory bridge file
# takes a list of pitch-class sets and returns a theory result.

from app.schemas import TheoryResult
 
 
def parse_written(chords: list[list[str]]) -> list[list[int]]:
    try:
        from theory.notes import pitch_of  # TODO(theory): implement pitch_of("Bb") -> 10
    except ImportError as e:
        raise NotImplementedError("theory.notes.pitch_of not implemented yet") from e
    return [[pitch_of(name) for name in group] for group in chords]
 
 
def analyze(frames: list[list[int]], key_hint: str | None = None) -> TheoryResult:
    """Pitch-class sets in, MVP answers out.
 
    Rough shape once the engine exists:
        chords      = [identify_chord(set(f)) for f in frames if f]
        chords      = collapse consecutive duplicates (beats -> chord changes)
        key         = detect_key(chords)          # key_hint = Essentia's guess, cross-check only
        progression = to_roman_numerals(chords, key)
        scales      = scales_for_key(key)
        related     = circle_neighbors(key)
        next_chords = suggest_next(progression, key)
    """
