"""
progressions.py — where the song can go next

DIATONIC HARMONY
  Stack thirds using only notes of a scale and every degree gets its own
  chord. In a major key the qualities are always:

        I    ii   iii   IV   V    vi   vii°
       maj  min  min   maj  maj  min  dim

  In C: C  Dm  Em  F  G  Am  B°. Roman numerals describe a chord's *job*
  in the key, independent of the actual key — which is why I–V–vi–IV sounds
  the same in any key.

FUNCTION
  Chords group by role:
        tonic (rest)        I, vi, iii
        predominant (move)  ii, IV
        dominant (tension)  V, vii°
  Typical motion: tonic -> predominant -> dominant -> tonic Strongest single
  move: V -> I (the root falls a fifth -> one step on the circle).

NEXT-CHORD SUGGESTIONS
  From the current chord's function, suggest chords that continue the
  tonic -> predominant -> dominant flow, plus common moves borrowed from
  neighbouring keys on the circle of fifths

In this file
  - roman numeral of a chord in a key
  - diatonic chords for a key
  - suggested next chords / alternate song paths
"""
from .chords import CHORD_TYPES, identify, is_minorish
from .circle_of_fifths import relative_minor
from .scales import key_scale

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII"]
TAILS = {"dim": "°", "aug": "+", "m7": "7", "m7b5": "ø7", "m": ""}

#where each scale degree tends to go in a major key
NEXT_MAJOR = {
    0: [3, 4, 5],
    1: [4, 6],
    2: [5, 3],
    3: [4, 0, 1],
    4: [0, 5],
    5: [3, 1, 4],
    6: [0, 2],
}

#common progressions and a general mood for each one
NAMED_PROGRESSIONS = {
    ("I", "V", "vi", "IV"): ("Pop", "uplifting and familiar"),
    ("vi", "IV", "I", "V"): ("Pop", "emotional and uplifting"),
    ("I", "vi", "IV", "V"): ("Classic", "bright and nostalgic"),
    ("I", "IV", "V"): ("Rock", "simple and energetic"),
    ("I", "V", "IV"): ("Rock", "driving and energetic"),
    ("ii", "V", "I"): ("Jazz", "strong resolution"),
    ("I", "IV", "I", "V"): ("Classic", "bright and traditional"),
    ("i", "VI", "III", "VII"): ("Minor", "dark and dramatic"),
}


def diatonic_chord(degree: int, tonic: int, mode: str) -> tuple[int, str]:
    """Build the triad for a scale degree."""
    scale = key_scale(tonic, mode)
    notes = [scale[(degree + k) % 7] for k in (0, 2, 4)]

    root, suffix = identify(notes)

    #minor keys commonly use a major V from harmonic minor
    if mode == "minor" and degree == 4:
        return root, ""

    return root, suffix


def roman_numeral(root: int, suffix: str, tonic: int, mode: str) -> str | None:
    """Turn a chord into a Roman numeral, including common chromatic chords."""
    scale = key_scale(tonic, mode)
    root = root % 12

    #look for a secondary dominant such as V/V or V/ii
    for degree, target in enumerate(scale):
        dominant_root = (target + 7) % 12

        if degree != 0 and root == dominant_root and suffix in ("", "7"):
            root_degree = scale.index(root) if root in scale else None
            diatonic_suffix = None

            if root_degree is not None:
                _, diatonic_suffix = diatonic_chord(root_degree, tonic, mode)

            #a major chord where the key normally has a minor chord s a common secondary dominant.
            if suffix == "7" or suffix != diatonic_suffix:
                target_numeral = ROMAN[degree]
                _, target_suffix = diatonic_chord(degree, tonic, mode)

                if is_minorish(target_suffix):
                    target_numeral = target_numeral.lower()

                tail = TAILS.get(suffix, suffix)

                if suffix == "7":
                    return "V7/" + target_numeral

                return "V/" + target_numeral + tail

    if root in scale:
        degree = scale.index(root)
        numeral = ROMAN[degree]

        if is_minorish(suffix):
            numeral = numeral.lower()

        return numeral + TAILS.get(suffix, suffix)

    #prefer flat alterations because they are more common for borrowed chords
    for degree, target in enumerate(scale):
        if root == (target - 1) % 12:
            numeral = "b" + ROMAN[degree]
            return numeral + TAILS.get(suffix, suffix)

    for degree, target in enumerate(scale):
        if root == (target + 1) % 12:
            numeral = "#" + ROMAN[degree]
            return numeral + TAILS.get(suffix, suffix)

    return None


def suggest_next(root: int, tonic: int, mode: str) -> list[tuple[int, str, str]]:
    """Return common next chords for the current chord"""
    scale = key_scale(tonic, mode)
    current_degree = scale.index(root) if root in scale else 0

    if mode == "major":
        next_degrees = NEXT_MAJOR[current_degree]
    else:
        next_degrees = [
            (degree - 5) % 7
            for degree in NEXT_MAJOR[(current_degree + 5) % 7]
        ]

    out = []

    for next_degree in next_degrees:
        chord_root, suffix = diatonic_chord(next_degree, tonic, mode)
        numeral = roman_numeral(chord_root, suffix, tonic, mode)
        out.append((chord_root, suffix, numeral))

    return out


def progression_name(numerals: list[str]) -> tuple[str, str] | None:
    """Return a name and mood for a common progression"""
    clean = []

    for numeral in numerals:
        if numeral.endswith("ø7"):
            numeral = numeral[:-2]
        elif numeral.endswith("maj7"):
            numeral = numeral[:-4]
        elif numeral.endswith("7"):
            numeral = numeral[:-1]

        clean.append(numeral)

    for length in (4, 3):
        if len(clean) < length:
            continue

        ending = tuple(clean[-length:])

        if ending in NAMED_PROGRESSIONS:
            return NAMED_PROGRESSIONS[ending]

    return None


def detect_key(chord_sets: list[list[int]]) -> tuple[int, str] | None:
    """Find the key that best matches a chord progression"""
    played = [set(chord) for chord in chord_sets if chord]

    if not played:
        return None

    first = identify(list(played[0]))
    first_root = first[0] if first else None

    chord_counts = {}

    for chord in played:
        found = identify(list(chord))

        if found:
            chord_counts[found] = chord_counts.get(found, 0) + 1

    last = identify(list(played[-1]))
    last_root = last[0] if last else None

    def score(tonic, mode):
        scale = set(key_scale(tonic, mode))

        #harmonic minor raises the seventh
        #  which is often used in the dominant chord of a minor-key progression.
        if mode == "minor":
            scale.add((tonic + 11) % 12)

        total = 0

        for (root, suffix), count in chord_counts.items():
            chord_notes = {
                (root + interval) % 12
                for interval in CHORD_TYPES.get(suffix, (0, 4, 7))
            }

            fit = len(chord_notes & scale) - len(chord_notes - scale)
            total += fit * count

            # Give the final chord one extra vote
            if last and (root, suffix) == last:
                total += fit

        # A V -> I ending is a strong clue in both major and minor keys
        if len(played) >= 2:
            previous = identify(list(played[-2]))

            if previous:
                previous_root = previous[0]

                if previous_root == (tonic + 7) % 12 and last_root == tonic:
                    total += 10

        #give the first chord a smaller weight.
        if first:
            if first_root == tonic:
                total += 2

            #do not let simply starting on a minor chord force a minor key.
            if mode == "major" and first_root == relative_minor(tonic):
                total += 3

        return total

    candidates = [
        (score(tonic, mode), tonic, mode)
        for tonic in range(12)
        for mode in ("major", "minor")
    ]

    _, tonic, mode = max(candidates, key=lambda candidate: candidate[0])

    return tonic, mode

