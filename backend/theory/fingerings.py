# fingerings.py
# Author: Erik Flores-Siemsen
# Date: September 2026
# Description: Finding playable guitar chord voicings and scale positions

STANDARD_TUNING = [4, 9, 2, 7, 11, 4]


def neck_positions(pcs, frets=12, tuning=STANDARD_TUNING):
    """Find every fret on each string that contains one of the notes"""
    wanted = {p % 12 for p in pcs}

    return [
        [f for f in range(frets + 1) if (open_ + f) % 12 in wanted]
        for open_ in tuning
    ]


def chord_voicings(
    pcs,
    root=None,
    frets=12,
    tuning=STANDARD_TUNING,
    span=4,
):
    """find simple playable chord shapes within a small fret span.
    Each string gets one note, or is muted with None/x. The shape is ranked
    by fret span, number of muted strings, and whether the root is in the bass.
    """
    wanted = {p % 12 for p in pcs}
    root = root % 12 if root is not None else None
    positions = neck_positions(pcs, frets, tuning)
    voicings = []

    def add_voicing(shape):
        played = [f for f in shape if f is not None]

        if not played:
            return

        used = [f for f in played if f > 0]

        if used:
            low = min(used)
            high = max(used)
            if high - low > span:
                return

        # Mutes can only be on the low strings so the shape can still
        # be strummed normally 
        first_played = next(
            (i for i, fret in enumerate(shape) if fret is not None),
            None,
        )

        if first_played is not None and any(
            fret is None for fret in shape[first_played + 1:]
        ):
            return

        notes = []
        for string, fret in enumerate(shape):
            if fret is not None:
                notes.append((tuning[string] + fret) % 12)

        if not wanted.issubset(set(notes)):
            return

        score = 0

        # Smaller fret spans are easier to play
        if used:
            low = min(used)
            high = max(used)
            score -= (high - low) * 2

            # Favor lower positions
            score -= low // 2

            # Open strings mixed with high frets are usually a stretch
            if 0 in shape and high > 5:
                score -= 3

        #open strings are generally easier than fretted notes
        score += shape.count(0)

        #avoid too many muted strings
        score -= shape.count(None) * 2

        #prefer the root on the lowest sounding string
        if root is not None:
            bass = None
            for string, fret in enumerate(shape):
                if fret is not None:
                    bass = (tuning[string] + fret) % 12
                    break

            if bass == root:
                score += 8

        voicings.append({
            "frets": shape,
            "score": score,
        })

    def search(string, shape):
        if string == len(tuning):
            add_voicing(shape)
            return

        #mute the string
        search(string + 1, shape + [None])

        #try every matching fret on the string
        for fret in positions[string]:
            search(string + 1, shape + [fret])

    search(0, [])

    voicings.sort(key=lambda v: v["score"], reverse=True)

    #remove duplicate fret patterns.
    unique = []
    seen = set()

    for voicing in voicings:
        shape = tuple(voicing["frets"])
        if shape not in seen:
            seen.add(shape)
            unique.append(voicing)

    return unique[:5]


def scale_positions(pcs, frets=12, tuning=STANDARD_TUNING):
    """Find scale notes across the guitar neck."""
    positions = neck_positions(pcs, frets, tuning)

    return [
        {
            "string": string,
            "frets": string_frets,
        }
        for string, string_frets in enumerate(positions)
    ]
