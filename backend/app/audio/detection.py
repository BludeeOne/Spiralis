"""
detection.py — turning sound into pitch classes.

All Essentia calls live here. Output is deliberately music-theory-free: sets
of integers 0–11 (C = 0), a 12-bin chroma vector, BPM, and the strongest
frequency. Naming chords is theory/'s job.

THE PATH
    WAV ─▶ frames ─▶ window ─▶ FFT ─▶ peaks ─▶ HPCP ─▶ beat-sync ─▶ threshold
                                       │                                   │
                                    peak_hz                         {0, 4, 7}

1. DECODE
   WAV bytes → mono float32 at the browser's sample rate (usually 48 kHz).
   WAV is used because it needs no codec, so it decodes identically on every
   machine.

2. FRAMING + WINDOWING  (Blackman-Harris 62)
   A song isn't one frequency over time, so we analyse short overlapping
   frames, each treated as "frozen" in time. Cutting a frame out of a signal
   creates hard edges, and the FFT reads those edges as fake frequencies
   smeared across the spectrum (spectral leakage). A window tapers each frame
   to zero at both ends. Blackman-Harris trades a slightly wider main peak
   for very low sidelobes (−62 dB), so a loud low E doesn't bleed into the
   bins of the quiet G# next to it.

3. SPECTRUM  (FFT)
   The Fourier transform rewrites a frame as a sum of sine waves and reports
   how much energy sits at each frequency. Frequency resolution is
   sample_rate / frame_size; bigger frames = finer pitch, worse timing.

4. SPECTRAL PEAKS
   We keep only the local maxima — the actual partials of the strings — and
   drop the noise floor between them. The single loudest one is reported as
   `peak_hz` (useful as a tuner).

5. CHROMA  (HPCP — Harmonic Pitch Class Profile)
   Octaves don't matter for harmony: every C sounds like "C". Pitch class of
   a frequency f:
                  pc = round(12 · log2(f / 440)) mod 12      (A = 0 here)
   HPCP folds every peak into one of 12 bins this way, weighting by
   magnitude, and optionally adds credit for harmonics (a note's overtones at
   2f, 3f, 4f … ). Result: a 12-number "fingerprint" of which notes are
   sounding.

   Gotcha: Essentia's HPCP puts its reference (A = 440 Hz) at bin 0. We
   np.roll(hpcp, -3) so bin 0 = C, matching theory/notes.py.

   Tuning matters: bins are a semitone (100 cents) wide. An instrument ~50
   cents off sits on the border between two bins and splits its energy.

6. BEATS + BPM
   Essentia's beat tracker finds onsets (sudden energy rises) and fits a
   steady grid to them, which gives both the beat positions and the tempo.

7. BEAT-SYNCHRONISATION
   Chords tend to change on beats. Averaging the chroma frames *between*
   beats gives one stable vector per beat instead of jittery per-frame noise.

8. THRESHOLDING → PITCH-CLASS SETS
   Normalise each beat's chroma so the loudest bin = 1.0, keep bins ≥ 0.5.
   {0, 4, 7} → "C, E, G are sounding".

   Known weakness: a guitar E major has three E strings and two B strings but
   only one G#. The third can fall below 0.5 while overtones of the doubled
   notes climb above it — so E gets misread as B, Eadd9, Esus. The fix is
   template matching on the full chroma vector instead of a hard threshold.
   scripts/chroma_debug.py exists to experiment with this.
"""

from pathlib import Path

import numpy as np
import essentia.standard as es


SAMPLE_RATE = 44100
FRAME_SIZE = 4096
HOP_SIZE = 2048

# Essentia's PCP bin 0 is A, so roll it over by 3 to make C index 0.
HPCP_SHIFT = -3

FALLBACK = 0.5
SILENCE_THRESHOLD = 1e-3
ACTIVE_THRESHOLD = 0.5
MAX_NOTES = 5


def load_audio(path: str | Path) -> np.ndarray:
    """Decode an ffmpeg-supported file to mono Float32."""
    return es.MonoLoader(
        filename=str(path),
        sampleRate=SAMPLE_RATE,
    )()


def chroma_frames(
    audio: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return chroma, frame times, frame RMS, and bass pitch classes."""
    window = es.Windowing(type="blackmanharris62")
    spectrum = es.Spectrum()

    peaks = es.SpectralPeaks(
        orderBy="magnitude",
        magnitudeThreshold=1e-5,
        minFrequency=40,
        maxFrequency=5000,
        maxPeaks=100,
        sampleRate=SAMPLE_RATE,
    )

    hpcp = es.HPCP(
        size=12,
        referenceFrequency=440,
        harmonics=0,
        minFrequency=40,
        maxFrequency=5000,
        sampleRate=SAMPLE_RATE,
    )

    rms = es.RMS()

    chroma = []
    times = []
    energy = []
    bass = []

    for i, frame in enumerate(
        es.FrameGenerator(
            audio,
            frameSize=FRAME_SIZE,
            hopSize=HOP_SIZE,
            startFromZero=True,
        )
    ):
        freqs, mags = peaks(spectrum(window(frame)))
        chroma.append(np.roll(hpcp(freqs, mags), HPCP_SHIFT))

        times.append(
            (i * HOP_SIZE + FRAME_SIZE / 2) / SAMPLE_RATE
        )
        energy.append(rms(frame))
        bass.append(_lowest_strong_pitch(freqs, mags))

    if not chroma:
        return (
            np.zeros((0, 12)),
            np.zeros(0),
            np.zeros(0),
            np.zeros(0, dtype=int),
        )

    return (
        np.array(chroma),
        np.array(times),
        np.array(energy),
        np.array(bass, dtype=int),
    )


def _lowest_strong_pitch(freqs, mags):
    """Find the lowest reasonably strong spectral peak."""
    if len(freqs) == 0:
        return -1

    strongest = float(np.max(mags))
    if strongest <= 0:
        return -1

    # Ignore very weak peaks so guitar harmonics do not become the bass.
    cutoff = strongest * 0.25

    for frequency, magnitude in sorted(
        zip(freqs, mags),
        key=lambda x: x[0],
    ):
        if magnitude >= cutoff and frequency >= 40:
            midi = int(round(69 + 12 * np.log2(frequency / 440.0)))
            return midi % 12

    return -1


def beat_boundaries(
    audio: np.ndarray,
    duration: float,
) -> tuple[float, list[float]]:
    """Find beat boundaries, falling back to half-second chunks."""
    bpm = 0.0
    ticks = []

    if duration >= 3.0:
        bpm, ticks, *_ = es.RhythmExtractor2013(
            method="multifeature"
        )(audio)

        ticks = [
            float(t)
            for t in ticks
            if 0 < t < duration
        ]

    if len(ticks) < 2:
        ticks = list(np.arange(FALLBACK, duration, FALLBACK))

    return float(bpm), [0.0, *ticks, duration]


def active_pitch_classes(
    chroma: np.ndarray,
    threshold: float = ACTIVE_THRESHOLD,
    max_notes: int = MAX_NOTES,
) -> list[int]:
    """Return the strongest pitch classes in a chroma vector."""
    if len(chroma) == 0 or chroma.max() <= 0:
        return []

    c = chroma / chroma.max()

    strongest = [
        int(i)
        for i in np.argsort(c)[::-1]
        if c[i] >= threshold
    ][:max_notes]

    return sorted(strongest)


def extract_features(path: str | Path) -> dict:
    """Decode audio and return chroma, beats, pitch classes, and bass."""
    audio = load_audio(path)
    duration = len(audio) / SAMPLE_RATE

    chroma, times, energy, bass = chroma_frames(audio)
    bpm, bounds = beat_boundaries(audio, duration)

    frames = []

    for start, end in zip(bounds[:-1], bounds[1:]):
        mask = (times >= start) & (times < end)

        if not mask.any():
            continue

        seg = chroma[mask].mean(axis=0)
        loud = energy[mask].mean() >= SILENCE_THRESHOLD

        if seg.max() > 0:
            seg = seg / seg.max()

        bass_values = bass[mask]
        bass_values = bass_values[bass_values >= 0]

        frame_bass = (
            int(np.bincount(bass_values).argmax())
            if len(bass_values)
            else None
        )

        frames.append({
            "start": round(float(start), 3),
            "end": round(float(end), 3),
            "chroma": [round(float(v), 4) for v in seg],
            "pitch_classes": (
                active_pitch_classes(seg)
                if loud
                else []
            ),
            "bass": frame_bass,
        })

    key, scale, strength = es.KeyExtractor(
        sampleRate=SAMPLE_RATE
    )(audio)

    return {
        "duration": round(duration, 3),
        "bpm": round(bpm, 2),
        "frames": frames,
        "essentia_key": {
            "key": key,
            "scale": scale,
            "strength": round(float(strength), 4),
        },
    }
