"""
fingerings.py — from pitch classes to the fretboard.

THE NECK IS ARITHMETIC
  Standard tuning, low to high:  E  A  D  G  B  E   ->  {4, 9, 2, 7, 11, 4}
  Each fret raises a string one semitone, so the fret that gives pitch class
  p on a string tuned to s is

                    fret = (p − s) mod 12        (+ 12 for the next octave)

  Every chord tone therefore appears on every string  the question is which
  combination a human hand can actually play
my voicings logic isnt perfect, I think I could really stretch i tout and i lose out by only muting low strings
VOICINGS
  A playable voicing:
    - uses one note (or mute) per string
    - covers every chord tone, root ideally in the bass
    - spans <= ~4 frets (finger stretch)
  Candidates are ranked by span, open strings, and how low the root sits.

In this file
  - fret positions for a pitch class on each string
  - generate and rank chord voicings
  - scale positions on the neck
"""
STANDARD_TUNING = [4, 9, 2, 7, 11, 4]


def neck_positions(pcs, frets=12, tuning=STANDARD_TUNING):
    """find every fret on each string that contains one of the notes"""
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
    """find simple playable chord shapes within a small fret span
    Each string gets one note, or is muted with None/x. The shape is ranked
    by fret span, number of muted strings, and whether the root is in the bass
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

        #mutes can only be on the low strings so the shape can still
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

        #smaller fret spans are easier to play
        if used:
            low = min(used)
            high = max(used)
            score -= (high - low) * 2

            #favor lower positions
            score -= low // 2

            #open strings mixed with high frets are usually a stretch
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
    """Find scale notes across the guitar neck"""
    positions = neck_positions(pcs, frets, tuning)

    return [
        {
            "string": string,
            "frets": string_frets,
        }
        for string, string_frets in enumerate(positions)
    ]
