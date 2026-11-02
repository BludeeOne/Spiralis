""" file made with help from ai
chord_report.py — grade chord detection against real recordings, no browser needed

Each file in tests/audio/ is one chord strummed for a while. The chord it SHOULD
be is the start of the file name, up to the first underscore:

    A_chord.m4a        -> A
    F#m__e-shape.m4a   -> F#m

For every file this script:
  1. splits the recording into strums using the same detector as useMic.ts
     (same constants, same math), so a test strum = what the app would send
  2. sends each strum through the real /api/analyze route function
  3. compares the chord that comes back with the chord in the file name

Run from backend/:
    python -m tests.chord_report               # every file
    python -m tests.chord_report E_Chord       # only files whose name contains "E_Chord"
    python -m tests.chord_report -v            # also list every strum

Grades:
    ok      right root and right quality (enharmonics count: F# == Gb)
    root    right root, wrong quality (A came back as Asus2 / A7 ...)
    wrong   a different chord
    none    no chord at all (usually fewer than 3 notes heard)

Only STRONG strums are graded, because those are the only ones App.tsx commits
to the chord panel. Weak strums (upstrokes) are counted but not graded.
"""
import io
import sys
import wave
from collections import Counter
from pathlib import Path

import numpy as np
import essentia.standard as es
from fastapi import HTTPException, UploadFile

from app.routes.analyze import analyze as analyze_route
from app.theory_bridge import parse_written

AUDIO_DIR = Path(__file__).parent / "audio"
EXTENSIONS = {".wav", ".m4a", ".mp3", ".flac"}
SR = 48000   # the browser's rate, so the strum detector sees what useMic sees
BLOCK = 128  # AudioWorklet block size


# ---- mirror of useMic.ts: change one, change the other ----
GATE_DB = 6
FLOOR_SEC = 15
FLOOR_CAP = 2e-3
ABS_FLOOR = 1e-4
TARGET_PEAK = 0.5
MAX_GAIN = 40
HOP_SEC = 0.5

FAST_MS = 10
SLOW_MS = 300
ONSET_DB = 6
REFRACTORY_MS = 150
SKIP_MS = 40
STRUM_MS = 450
MIN_STRUM_MS = 150
STRONG_DB = 6
LOUD_DECAY_DB = 3


def ms(n):
    return round(n / 1000 * SR)


def rms(x):
    return float(np.sqrt(np.mean(x * x))) if len(x) else 0.0


def to_db(x):
    return 20 * np.log10(max(x, 1e-6))


def split_strums(audio):
    """Walk the audio in 128-sample blocks exactly like the worklet does and
    return [(start, end, db, strong), ...] for every strum window useMic would send."""
    gate = 10 ** (GATE_DB / 20)
    onset_ratio = 10 ** (ONSET_DB / 20)
    fast_a = 1 - np.exp(-BLOCK / ms(FAST_MS))
    slow_a = 1 - np.exp(-BLOCK / ms(SLOW_MS))
    hop = round(SR * HOP_SEC)
    floor_hops = int(np.ceil(FLOOR_SEC / HOP_SEC))

    fast = slow = prev = 0.0
    floor = FLOOR_CAP
    recent = []
    since_hop = 0
    last_onset = -10**9
    capture_from = -1
    strum_peak = 0.0
    loudest, loudest_at = -np.inf, 0.0
    strums = []

    def emit(end):
        nonlocal loudest, loudest_at, capture_from
        db = to_db(strum_peak)
        at = last_onset / SR
        loudest = max(db, loudest - LOUD_DECAY_DB * (at - loudest_at))
        loudest_at = at
        strums.append((capture_from, end, db, db >= loudest - STRONG_DB))
        capture_from = -1

    for start in range(0, len(audio) - BLOCK + 1, BLOCK):
        block = audio[start:start + BLOCK]
        total = start + BLOCK

        # difference signal: the pick click stands out, ringing strings don't
        diff = np.diff(block, prepend=prev)
        prev = block[-1]
        r = float(np.sqrt(np.mean(diff * diff)))
        fast += (r - fast) * fast_a
        slow += (r - slow) * slow_a

        if capture_from >= 0 and total < capture_from:
            strum_peak = max(strum_peak, fast)

        is_onset = (
            fast > slow * onset_ratio
            and rms(block) > max(ABS_FLOOR, floor * gate)
            and total - last_onset > ms(REFRACTORY_MS)
        )

        if is_onset:
            if capture_from >= 0 and total - capture_from >= ms(MIN_STRUM_MS):
                emit(total)
            last_onset = total
            capture_from = total + ms(SKIP_MS)
            strum_peak = fast
        elif capture_from >= 0 and total >= capture_from + ms(STRUM_MS):
            emit(capture_from + ms(STRUM_MS))

        # noise floor, updated every hop like the sliding window does
        since_hop += BLOCK
        if since_hop >= hop:
            since_hop = 0
            recent.append(rms(audio[max(0, total - hop):total]))
            recent = recent[-floor_hops:]
            floor = min(FLOOR_CAP, *recent)

    return strums
# ---- end mirror ----


def normalize(win):
    peak = float(np.abs(win).max()) if len(win) else 0.0
    gain = min(MAX_GAIN, TARGET_PEAK / max(peak, 1e-6))
    return win * gain if gain > 1 else win


def to_wav(samples):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes())
    return buf.getvalue()


def analyze(samples):
    """Send one strum through the real route function (no server, no httpx)."""
    upload = UploadFile(file=io.BytesIO(to_wav(samples)), filename="strum.wav")
    try:
        return analyze_route(audio=upload, history="[]")
    except HTTPException as e:
        return {"chord": None, "notes": [], "error": e.detail}


def expected_for(path):
    """'F#m__e-shape.m4a' -> parsed F#m. Uses the theory engine's own parser."""
    name = path.stem.split("_")[0]
    parsed = parse_written([name])
    return parsed[0] if parsed else None


def grade(expected, chord):
    if chord is None:
        return "none"
    if chord["root"] == expected["root"]:
        return "ok" if chord.get("suffix", "") == expected["suffix"] else "root"
    return "wrong"


def run(files, verbose=False):
    totals = Counter()
    rows = []

    for path in files:
        expected = expected_for(path)
        if expected is None:
            print(f"skipping {path.name}: can't read a chord name from it")
            continue

        audio = es.MonoLoader(filename=str(path), sampleRate=SR)()
        strums = split_strums(audio)
        strong = [s for s in strums if s[3]]

        grades = Counter()
        misreads = Counter()
        heard = Counter()

        if verbose:
            print(f"\n{path.name}  (expect {expected['name']})")

        for start, end, db, _ in strong:
            res = analyze(normalize(audio[start:end].copy()))
            chord = res.get("chord")
            g = grade(expected, chord)
            grades[g] += 1
            heard[" ".join(res.get("notes", []))] += 1
            if g != "ok":
                misreads[chord["name"] if chord else "—"] += 1
            if verbose:
                got = chord["name"] if chord else "—"
                print(f"  {start / SR:6.2f}s  {db:6.1f} dB  {g:5s}  {got:8s}  heard: {' '.join(res.get('notes', []))}")

        totals.update(grades)
        n = len(strong)
        top_miss = ", ".join(f"{k} ×{v}" for k, v in misreads.most_common(3)) or "—"
        top_heard = heard.most_common(1)[0][0] if heard else "—"
        rows.append((path.name, expected["name"], len(strums), n, grades["ok"], grades["root"],
                     grades["wrong"], grades["none"], top_miss, top_heard))

    print()
    print(f"{'file':22s} {'want':5s} {'strums':>6s} {'graded':>6s} {'ok':>4s} {'root':>4s} {'wrong':>5s} {'none':>4s}  "
          f"{'most common misreads':28s} most common notes heard")
    for name, want, all_n, n, ok, root, wrong, none, miss, top in rows:
        pct = f"{100 * ok / n:3.0f}%" if n else "  -"
        print(f"{name:22s} {want:5s} {all_n:6d} {n:6d} {ok:4d} {root:4d} {wrong:5d} {none:4d}  {miss:28s} {top}   [{pct}]")

    graded = sum(totals.values())
    if graded:
        print(f"\noverall: {totals['ok']}/{graded} strong strums correct ({100 * totals['ok'] / graded:.0f}%), "
              f"{totals['root']} right root only, {totals['wrong']} wrong, {totals['none']} no chord")


def main(argv):
    verbose = "-v" in argv
    patterns = [a for a in argv if a != "-v"]
    files = sorted(p for p in AUDIO_DIR.iterdir() if p.suffix.lower() in EXTENSIONS)
    if patterns:
        files = [p for p in files if any(pat in p.name for pat in patterns)]
    if not files:
        print(f"no recordings found in {AUDIO_DIR}")
        return
    run(files, verbose)


if __name__ == "__main__":
    main(sys.argv[1:])
