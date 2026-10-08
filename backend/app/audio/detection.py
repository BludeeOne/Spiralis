"""
detection.py — turning sound into pitch classes

This file handles all of the Essentia stuff. The goal is to take an audio
file and turn it into useful information about what notes are being played.

The output is kept simple: pitch classes as integers from 0–11 (C = 0),
a 12-bin chroma vector, BPM, and the strongest frequency found in the audio.
The actual chord naming is handled somewhere else.

THE PATH

    WAV -> frames -> window -> FFT -> peaks -> HPCP -> beat-sync -> threshold
                                      │                         │
                                   peak_hz                  {0, 4, 7}


1. DECODE

The WAV file is decoded into mono float32 audio using the browser's sample
rate, which is usually 48 kHz.

WAV is used because it doesn't need an extra codec, so the audio should
decode the same way on different machines.


2. FRAMING + WINDOWING (Blackman-Harris 62)

A song isn't just one frequency. The frequencies change constantly, so we
break the audio into small overlapping frames and treat each frame like a
snapshot of the sound at that moment

The problem is that cutting the audio into frames creates sharp edges. The
FFT can interpret those edges as extra frequencies, which is called spectral
leakage

To reduce this, each frame is passed through a window that gradually brings
the signal down to zero at both ends. We use a Blackman-Harris window because
it has very low sidelobes (-62 dB). This helps stop a loud note, like a low E,
from bleeding into nearby frequencies and making quieter notes harder to
detect


3. SPECTRUM (FFT)

The FFT takes each frame and breaks it down into the different frequencies
that make up the sound. Basically, it tells us how much energy exists at
each frequency.

The frequency resolution is:

    sample_rate / frame_size

Using a larger frame gives us better frequency resolution, which helps with
pitch detection, but it also means we lose some timing information.


4. SPECTRAL PEAKS

Instead of using every frequency in the spectrum, we look for the local
peaks. These peaks are usually the actual notes and harmonics produced by
the instrument.

The strongest peak is saved as `peak_hz`. This can also be useful for things
like basic tuning since it gives us the strongest frequency in the signal.


5. CHROMA (HPCP — Harmonic Pitch Class Profile)

For chords, the exact octave isn't as important as the note itself. For
example, a C played low and a C played high are still both C.

The pitch class of a frequency can be thought of as:

    pc = round(12 · log2(f / 440)) mod 12

with A = 0 for this calculation.

HPCP takes the frequencies we found and folds them into 12 pitch classes.
It also considers the strength of each frequency and can give extra weight
to harmonics, such as 2f, 3f, 4f, etc.

The result is basically a 12-number fingerprint showing which notes are
present in the audio.

One important detail is that Essentia's HPCP uses A as bin 0. Our program
uses C as bin 0 instead, so we do:

    np.roll(hpcp, -3)

This keeps the chroma format consistent with theory/notes.py.

Tuning can also cause problems here
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
