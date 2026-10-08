"""
chords.py — naming those sounds
STACKED THIRDS
  Chords are built by stacking thirds on a root
    Relative to the root:

        major       0  4  7          (M3 + m3)
        minor       0  3  7          (m3 + M3)
        diminished  0  3  6
        augmented   0  4  8
        dom7        0  4  7  10
        maj7        0  4  7  11
        min7        0  3  7  10
        sus2 / sus4 0  2  7 / 0  5  7   (third replaced)

IDENTIFICATION
  Given a pitch-class set, try every possible root r: subtract r from each
  note (mod 12) and compare against the templates. Real audio is messy 
  extra overtones, a missing third so exact matching is too strict and hard
  Instead each candidate is scored: reward template notes present, penalise
  extras and missing chord tones, and weight the third heavily since it
  decides major vs minor.

INVERSIONS
  C/E is still C major but the bass note changes. Because we
  work on pitch-class sets, inversions are more easily identifiable

In this file
  - chord templates
  - identify(pcs) -> best (root, quality) with a score
  - chord -> pitch classes for display / fingerings
"""
from .notes import name_of

#Intervals above the root for each chord type so it just do the math to find the right notes
CHORD_TYPES = {
    "":     (0, 4, 7),
    "m":    (0, 3, 7),
    "dim":  (0, 3, 6),
    "aug":  (0, 4, 8),
    "sus2": (0, 2, 7),
    "sus4": (0, 5, 7),
    "6":    (0, 4, 7, 9),
    "m6":   (0, 3, 7, 9),
    "7":    (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11),
    "m7":   (0, 3, 7, 10),
    "m7b5": (0, 3, 6, 10),
    "dim7": (0, 3, 6, 9),
    "7sus4": (0, 5, 7, 10),
    "add9": (0, 2, 4, 7),
}


def build(root: int, suffix: str) -> set[int]:
    """build a chord from its root"""
    return {(root + interval) % 12 for interval in CHORD_TYPES[suffix]}


def identify(pcs: list[int], bass: int | None = None) -> tuple[int, str] | None:
    """find the best chord match for a group of pitch classes.
    Bass can be used when the notes are an inversion. It is used
    as a tie-breaker when more than one chord fits the same notes which can happen often
    """
    played = {pitch % 12 for pitch in pcs}

    if len(played) < 3:
        return None

    if bass is not None:
        bass = bass % 12

    best = None
    best_score = float("-inf")

    for root in range(12):
        for suffix, intervals in CHORD_TYPES.items():
            tones = build(root, suffix)

            if not tones <= played:
                continue

            #extra notes are allowed because live audio often contains
            #harmonics or ghost notes
            score = len(tones) * 10 - len(played - tones) * 4

            #exact matches should always beat matches with ghost notes
            if not (played - tones):
                score += 2

            #prefer the root that is actually in the bass
            if bass is not None:
                if root == bass:
                    score += 8
                else:
                    score -= 2

            # Some four-note chords are especially obnoxious prefer the more common seventh-chord
            # when the bass doesnt give enough information
            if bass is None and not (played - tones):
                if suffix == "m7":
                    score += 2
                if suffix == "6":
                    score += 1

            if score > best_score:
                best = (root, suffix)
                best_score = score

    return best


def chord_name(root: int, suffix: str, flats: bool = False) -> str:
    return name_of(root, flats) + suffix


def is_minorish(suffix: str) -> bool:
    """Return true for minor and diminished chords"""
    return (suffix.startswith("m") and not suffix.startswith("maj")) or suffix.startswith("dim")


def slash_name(root: int, suffix: str, bass: int, flats: bool = False) -> str:
    """return a chord name with a slash bass when the bass is different"""
    name = chord_name(root, suffix, flats)
    bass = bass % 12

    if bass != root:
        name += "/" + name_of(bass, flats)

    return name
