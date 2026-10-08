"""
notes.py — the foundation of it all, pitch classes and letters

PITCH CLASSES
  Western music uses 12-tone equal temperament: the octave is split into 12
  equal steps (semitones), each a frequency about 1.0595 times up
  After 12 steps you're back to the same note an octave up, so notes live on
  a clock:

        C=0  C#/Db=1  D=2  D#/Eb=3  E=4  F=5  F#/Gb=6  G=7  G#/Ab=8
        A=9  A#/Bb=10  B=11

  Every interval is just subtraction mod 12. Transposition is addition mod 12.
  All internal logic in Spiralis works on these integers

SPELLING
  The same key on the piano can have two names (A# vs Bb)
  Which is correct depends on the key, not the pitch: a scale uses each
  letter A-G exactly once, so F major is F G A *Bb* C D E, never A#.
  Names are only produced at the edges (display, user input)

In this file
  - pitch-class <-> name conversion
  - parse_note_name() for the written-input feature
  - spell(pc, key) — choose the correct enharmonic for a key
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Note:
    pitch: int
    sharp_name: str
    flat_name: str


NOTES: list[Note] = [
    Note(0, "C", "C"),
    Note(1, "C#", "Db"),
    Note(2, "D", "D"),
    Note(3, "D#", "Eb"),
    Note(4, "E", "E"),
    Note(5, "F", "F"),
    Note(6, "F#", "Gb"),
    Note(7, "G", "G"),
    Note(8, "G#", "Ab"),
    Note(9, "A", "A"),
    Note(10, "A#", "Bb"),
    Note(11, "B", "B"),
]

LETTERS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# Tonics whose normal key signatures use flats.
FLAT_MAJOR = {5, 10, 3, 8, 1}
FLAT_MINOR = {7, 0, 5, 10, 3, 2}


def note_at(pitch: int) -> Note:
    return NOTES[pitch % 12]


def pitch_of(name: str) -> int:
    """convert a written note name into a pitch class"""
    name = name.strip()

    if not name or name[0].upper() not in LETTERS:
        raise ValueError(f"bad note name: {name!r}")

    pitch = LETTERS[name[0].upper()]

    for char in name[1:]:
        if char in "#♯":
            pitch += 1
        elif char in "b♭":
            pitch -= 1
        else:
            raise ValueError(f"bad note name: {name!r}")

    return pitch % 12


def uses_flats(tonic: int, mode: str = "major") -> bool:
    """return whether the key normally uses flat note names"""
    tonic = tonic % 12

    if mode == "major":
        return tonic in FLAT_MAJOR

    return tonic in FLAT_MINOR


def name_of(pitch: int, flats: bool = False) -> str:
    """return a basic sharp or flat name for a pitch class"""
    note = note_at(pitch)

    if flats:
        return note.flat_name

    return note.sharp_name


def key_spelling(tonic: int, mode: str = "major") -> dict[int, str]:
    """return the correct note name for every pitch in a key"""
    tonic = tonic % 12

    if mode == "major":
        steps = [0, 2, 4, 5, 7, 9, 11]
    else:
        steps = [0, 2, 3, 5, 7, 8, 10]

    tonic_name = name_of(tonic, uses_flats(tonic, mode))
    first_letter = tonic_name[0]

    letter_order = ["C", "D", "E", "F", "G", "A", "B"]
    start = letter_order.index(first_letter)

    result = {}

    for degree, step in enumerate(steps):
        pitch = (tonic + step) % 12
        letter = letter_order[(start + degree) % 7]

        natural_pitch = LETTERS[letter]
        difference = (pitch - natural_pitch + 6) % 12 - 6

        if difference > 0:
            name = letter + ("#" * difference)
        elif difference < 0:
            name = letter + ("b" * abs(difference))
        else:
            name = letter

        result[pitch] = name

    return result


def name_in_key(pitch: int, tonic: int, mode: str = "major") -> str:
    """return a pitch name using the spelling of the given key"""
    pitch = pitch % 12
    spelling = key_spelling(tonic, mode)

    if pitch in spelling:
        return spelling[pitch]

    #keep natural notes natural when they are outside the key
    natural_names = {
        value: letter for letter, value in LETTERS.items()
    }
    if pitch in natural_names:
        return natural_names[pitch]

    scale = key_scale_for_spelling(tonic, mode)

    #ry the scale note above first so flat spellings win
    for note in scale:
        if (note - 1) % 12 == pitch:
            letter = spelling[note][0]
            diff = (pitch - LETTERS[letter] + 6) % 12 - 6

            if abs(diff) <= 1:
                return letter + (
                    "b" if diff < 0 else "#" if diff > 0 else ""
                )

    # then try the scale note below for sharp spellings
    for note in scale:
        if (note + 1) % 12 == pitch:
            letter = spelling[note][0]
            diff = (pitch - LETTERS[letter] + 6) % 12 - 6

            if abs(diff) <= 1:
                return letter + (
                    "b" if diff < 0 else "#" if diff > 0 else ""
                )

    return name_of(pitch, uses_flats(tonic, mode))

def key_scale_for_spelling(tonic: int, mode: str) -> list[int]:
    """return the seven pitch classes used to build key spelling"""
    tonic = tonic % 12

    if mode == "major":
        steps = [0, 2, 4, 5, 7, 9, 11]
    else:
        steps = [0, 2, 3, 5, 7, 8, 10]

    return [(tonic + step) % 12 for step in steps]


# Useful frequency reference:
# A = 440.00 Hz
# Each half step is approximately 1.0595 times the frequency of the previous note
