"""
theory_bridge.py — the cross from frequencies and science to beautiful harmoic noises

detection.py speaks physics (frequencies, energy per pitch class)
theory/ speaks music (chords, keys, roman numerals)
this is the translator file that converts one to the other

Graceful degradation
  Each theory call is wrapped: if a function raises NotImplementedError, its
  name goes into `pending` and the rest of the response still ships. The app will always run even if i have more to implement]
  or something straight up failed
"""
from app.schemas import TheoryResult
from theory import chords, circle_of_fifths, fingerings, notes, progressions, scales


def _flats(key):
    """decide whether names in a key should normally use flats, as to not confuse normal musicans"""
    return notes.uses_flats(key["tonic"], key["mode"])


def _key(tonic, mode):
    """Build the key dictionary used by the app with spelled names"""
    tonic = tonic % 12

    if mode == "major":
        rel, rel_mode = circle_of_fifths.relative_minor(tonic), "minor"
    else:
        rel, rel_mode = circle_of_fifths.relative_major(tonic), "major"

    return {
        "tonic": tonic,
        "mode": mode,
        "name": f"{notes.name_in_key(tonic, tonic, mode)} {mode}",
        "relative": f"{notes.name_in_key(rel, tonic, mode)} {rel_mode}",
    }


def _root_suffix(chord):
    """root and suffix of a chord dictionary, re-identifying from pcs if they're missing"""
    if "root" in chord:
        return chord["root"], chord.get("suffix", "")

    found = chords.identify(chord.get("pcs", []))
    return found if found else (None, None)


def identify_chord(pcs, bass=None):
    """identify a chord and return an API-friendly dictionary"""
    result = chords.identify(pcs, bass)

    if result is None:
        return None

    root, suffix = result
    return {
        "root": root,
        "suffix": suffix,
        "name": chords.chord_name(root, suffix),
    }


def estimate_key(chord_sets):
    """rstimate the key from the detected chord history"""
    result = progressions.detect_key(chord_sets)

    if result is None:
        return None

    tonic, mode = result
    return _key(tonic, mode)


def roman_numeral(chord, key):
    """translate a chord dictionary into a Roman numeral"""
    if not chord:
        return None

    root, suffix = _root_suffix(chord)

    if root is None:
        return None

    return progressions.roman_numeral(root, suffix, key["tonic"], key["mode"])


def suggest_next(chord, key):
    """return likely next chords for the current chord"""
    if not chord:
        return []

    suggestions = progressions.suggest_next(
        chord["root"],
        key["tonic"],
        key["mode"],
    )

    flats = _flats(key)
    return [
        {
            "root": root,
            "suffix": suffix,
            "name": chords.chord_name(root, suffix, flats),
            "numeral": numeral,
        }
        for root, suffix, numeral in suggestions
    ]


def fitting_scales(key):
    """return scales that fit the current keyr"""
    flats = _flats(key)
    tonic = key["tonic"]
    mode = key["mode"]

    scale_names = scales.scales_for_key(tonic, mode)
    result = []

    for scale_type in scale_names:
        #scales from the other mode start on the relative key
        if scale_type in ("major", "major_pentatonic") and mode == "minor":
            root = circle_of_fifths.relative_major(tonic)
        elif scale_type in ("natural_minor", "minor_pentatonic") and mode == "major":
            root = circle_of_fifths.relative_minor(tonic)
        else:
            root = tonic

        name = notes.name_of(root, flats)

        if scale_type == "major":
            label = f"{name} major (Ionian)"
        elif scale_type == "natural_minor":
            label = f"{name} natural minor (Aeolian)"
        elif scale_type == "major_pentatonic":
            label = f"{name} major pentatonic"
        elif scale_type == "minor_pentatonic":
            label = f"{name} minor pentatonic"
        else:
            label = f"{name} {scale_type.replace('_', ' ')}"

        result.append({
            "root": root,
            "type": scale_type,
            "name": label,
        })

    return result


def fitting_chord_scales(chord, key=None):
    """return scales that work over a specific chord"""
    if not chord:
        return []

    flats = _flats(key) if key else False
    scale_names = scales.scales_for_chord(
        chord["root"],
        chord["suffix"],
    )

    result = []

    for scale_type in scale_names:
        root = chord["root"]
        name = notes.name_of(root, flats)

        if scale_type == "major":
            label = f"{name} major (Ionian)"
        elif scale_type == "natural_minor":
            label = f"{name} natural minor (Aeolian)"
        elif scale_type == "major_pentatonic":
            label = f"{name} major pentatonic"
        elif scale_type == "minor_pentatonic":
            label = f"{name} minor pentatonic"
        else:
            label = f"{name} {scale_type.replace('_', ' ')}"

        result.append({
            "root": root,
            "type": scale_type,
            "name": label,
        })

    return result


def respell(history, key):
    """respell chord history so note names follow the current key"""
    flats = _flats(key)
    result = []

    for chord in history:
        if not chord:
            continue

        root, suffix = _root_suffix(chord)

        if root is None:
            result.append(chord)
            continue

        result.append({
            **chord,
            "root": root,
            "suffix": suffix,
            "root_name": notes.name_in_key(root, key["tonic"], key["mode"]),
            "name": chords.chord_name(root, suffix, flats),
        })

    return result


def spell(pcs, key):
    """spell a group of pitch classes using the current key"""
    if not key:
        return [notes.name_of(pitch) for pitch in pcs]

    return [
        notes.name_in_key(pitch, key["tonic"], key["mode"])
        for pitch in pcs
    ]


def chord_voicings(chord, key=None):
    """return playable guitar voicings for a chord"""
    if not chord:
        return []

    voicings = fingerings.chord_voicings(
        chords.build(chord["root"], chord["suffix"]),
        root=chord["root"],
    )

    return voicings


def scale_positions(scale_root, scale_type):
    """return guitar-neck positions for a scale"""
    pcs = scales.get_scale(scale_root, scale_type)
    return fingerings.scale_positions(pcs)


def parse_written(chords_in):
    """convert written chord names into the same format as detected chords"""
    result = []

    for name in chords_in:
        name = name.strip()
        if not name:
            continue

        root_name = name[0]

        if len(name) > 1 and name[1] in ("#", "b", "♯", "♭"):
            root_name += name[1]
            suffix = name[2:]
        else:
            suffix = name[1:]

        root = notes.pitch_of(root_name)

        if root is None:
            continue

        identified = chords.identify(chords.build(root, suffix))

        if identified:
            identified_root, identified_suffix = identified
            result.append({
                "root": identified_root,
                "suffix": identified_suffix,
                "name": chords.chord_name(identified_root, identified_suffix),
            })

    return result


def analyze(frames, key_hint=None):
    """analyze detected frames (pcs lists or {"pcs", "bass"} dicts) into a TheoryResult"""
    history = []

    for frame in frames:
        if isinstance(frame, dict):
            pcs, bass = frame.get("pcs", []), frame.get("bass")
        else:
            pcs, bass = frame, None

        chord = identify_chord(pcs, bass) if pcs else None

        # Beats -> chord changes: skip repeats of the same chord.
        if chord and not (history and (history[-1]["root"], history[-1]["suffix"]) == (chord["root"], chord["suffix"])):
            history.append({**chord, "pcs": sorted(chords.build(chord["root"], chord["suffix"]))})

    if not history:
        return TheoryResult()

    # Only accept a hint that's already a key dict (the Essentia string isn't).
    key = key_hint if isinstance(key_hint, dict) else estimate_key([h["pcs"] for h in history])

    if not key:
        return TheoryResult(history=history)

    history = respell(history, key)

    return TheoryResult(
        key=key,
        history=history,
        progression=[roman_numeral(h, key) for h in history],
        suggestions=suggest_next(history[-1], key),
        scales=fitting_scales(key),
    )


def analyze_written(names):
    """Chord names in (["C", "G7", "Am"]), same TheoryResult out as live audio"""
    parsed = parse_written(names)
    frames = [sorted(chords.build(c["root"], c["suffix"])) for c in parsed]

    return analyze(frames)