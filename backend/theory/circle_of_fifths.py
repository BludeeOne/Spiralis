"""
circle_of_fifths.py — the map of keys

THE CIRCLE
  Go up a perfect fifth (7 semitones) twelve times and you visit every pitch
  class exactly once before returning home, because gcd(7, 12) = 1:

        C -> G -> D -> A -> E -> B -> F# -> C#/Db -> Ab -> Eb -> Bb -> F -> C

  Each step clockwise adds one sharp to the key signature; each step
  counter-clockwise adds one flat.

WHY NEIGHBOURS MATTER
  Adjacent keys share 6 of their 7 (haha 67) notes (C and G differ only by F vs F#)
  That's why moves around the circle sound smooth and why "chords from the
  neighbouring keys" are the safest borrowed chords to suggest

RELATIVE MINOR
  Each major key shares all seven notes with the minor key 3 semitones
  below its root (C major ↔ A minor) so they sit on the same spoke of the
  wheel

In this file
  - circle order, position of a key
  - neighbours (+- 1 step) and relative minor/major
  - key detection: which major/minor scale best contains the notes heard
"""
CIRCLE = [(i * 7) % 12 for i in range(12)]

#number of sharps/flats in each major key signature
#negative values mean flats, positive values mean sharps
KEY_SIGNATURES_SHARPS = {
    0: 0,    # C
    7: 1,    # G
    2: 2,    # D
    9: 3,    # A
    4: 4,    # E
    11: 5,   # B
    6: 6,    # F#
    1: 7,    # C#
}

KEY_SIGNATURES_FLATS = {
    0: 0,    # C
    5: -1,   # F
    10: -2,  # Bb
    3: -3,   # Eb
    8: -4,   # Ab
    1: -5,   # Db
    6: -6,   # Gb
    11: -7,  # Cb
}

#use the common enharmonic spelling for the seven-sharp/seven-flat keys
KEY_SIGNATURE_NAMES = {
    0: "C",
    1: "C#",
    2: "D",
    3: "Eb",
    4: "E",
    5: "F",
    6: "F#",
    7: "G",
    8: "Ab",
    9: "A",
    10: "Bb",
    11: "B",
}


def neighbors(tonic):
    """return the keys a fourth and fifth away"""
    return (tonic + 5) % 12, (tonic + 7) % 12


def relative_minor(tonic):
    """Return the relative minor of a major key"""
    return (tonic + 9) % 12


def relative_major(tonic):
    """return the relative major of a minor key"""
    return (tonic + 3) % 12


def key_signature(tonic, flats=None):
    """return the number of sharps or flats in a major key signature"""
    tonic = tonic % 12

    if flats is None:
        flats = tonic in KEY_SIGNATURES_FLATS and tonic not in {
            0, 1, 6, 7, 11
        }

    if flats:
        return KEY_SIGNATURES_FLATS[tonic]

    return KEY_SIGNATURES_SHARPS[tonic]


def closely_related_keys(tonic):
    """return the five closely related major keys around a tonic
    These are the tonic, its fourth, its fifth, and the relative minors
    of those two neighboring major keys
    """
    tonic = tonic % 12
    fourth = (tonic + 5) % 12
    fifth = (tonic + 7) % 12

    return {
        "tonic": tonic,
        "dominant": fifth,
        "subdominant": fourth,
        "relative_minor": relative_minor(tonic),
        "dominant_relative_minor": relative_minor(fifth),
        "subdominant_relative_minor": relative_minor(fourth),
    }


def circle_position(tonic):
    """return the position of a key on the circle, from 0 to 11"""
    tonic = tonic % 12

    return CIRCLE.index(tonic)
