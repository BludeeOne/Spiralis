"""Signal processing layer. 
Where i use essentia to decode live recordings 
take the note it spits out then send to my theory engine
Pipeline: decode -> per-frame HPCP chroma -> beat tracking -> pitch class
output is numbers corresponding to one of 12 notes"""

from pathlib import Path
import numpy as np
import essentia.standard as es

SAMPLE_RATE = 44100
FRAME_SIZE = 4096
HOP_SIZE = 2048

#essentias pcp bin 0 actually is the note a so instead of
# changing my notes and stuff i just rolled essentia over by 3 indicies
HPCP_SHIFT = -3
FALLBACK = 0.5              #when the beat tracker comes empty
SILENCE_THRESHOLD = 1e-3    # if something is too quiet it shouldnt be analyzied

def load_audio(path: str | Path) -> np.ndarray:
    """Decode any ffmpeg-supported file (wav/mp3/m4a/flac/webm...) to mono Float32"""
    return es.MonoLoader(filename=str(path), sampleRate=SAMPLE_RATE)()

def chroma_frames(audio: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (chroma[n, 12] with C at index 0, frame center times[n], frame rms[n])."""
    window = es.Windowing(type = "blackmanharrris62")   #essentia tool for tapering chunks edges to prevent spectral leakage
    spectrum = es.Spectrum()                            #returns the strength of each frequency, 10hz wide
    peaks = es.SpectralPeaks(                           #keeps only local maxima between 40 and 5000hz, 
        orderBy="magnitude", magnitudeThreshold=1e-5,
        minFrequency=40, maxFrequency=5000, maxPeaks=100, sampleRate=SAMPLE_RATE,
    )
    hpcp = es.HPCP(                                     #hpcp folds every peak into one of the 12 pitvh classes, possible problem with harmonics
        size=12, referenceFrequency=440, harmonics=8,
        minFrequency=40, maxFrequency=5000, sampleRate=SAMPLE_RATE,
    )
    rms = es.RMS()          #essentia root mean square(rms) averages the magnitude of a set of valeus, which is espeically important in contexts where the values fluctuate over time
 
    chroma, times, energy = [], [], []
    for i, frame in enumerate(es.FrameGenerator(
        audio, frameSize=FRAME_SIZE, hopSize=HOP_SIZE, startFromZero=True,
    )):
        freqs, mags = peaks(spectrum(window(frame)))
        chroma.append(np.roll(hpcp(freqs, mags), HPCP_SHIFT))
        times.append((i * HOP_SIZE + FRAME_SIZE / 2) / SAMPLE_RATE)
        energy.append(rms(frame))
 
    if not chroma:
        return np.zeros((0, 12)), np.zeros(0), np.zeros(0)
    return np.array(chroma), np.array(times), np.array(energy)
 
 
def beat_boundaries(audio: np.ndarray, duration: float) -> tuple[float, list[float]]:
    bpm, ticks = 0.0, []
    if duration >= 3.0:  # the tracker needs a few seconds to lock on
        bpm, ticks, *_ = es.RhythmExtractor2013(method="multifeature")(audio)
        ticks = [float(t) for t in ticks if 0 < t < duration]
    if len(ticks) < 2:
        ticks = list(np.arange(FALLBACK, duration, FALLBACK))
    return float(bpm), [0.0, *ticks, duration]

 
def active_pitch_classes(chroma: np.ndarray, threshold: float = 0.5, max_notes: int = 5) -> list[int]:
    if chroma.max() <= 0:
        return []
    c = chroma / chroma.max()
    strongest = [int(i) for i in np.argsort(c)[::-1] if c[i] >= threshold][:max_notes]
    return sorted(strongest)
 
 
def extract_features(path: str | Path) -> dict:
    audio = load_audio(path)
    duration = len(audio) / SAMPLE_RATE
 
    chroma, times, energy = chroma_frames(audio)
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
        frames.append({
            "start": round(float(start), 3),
            "end": round(float(end), 3),
            "chroma": [round(float(v), 4) for v in seg],
            "pitch_classes": active_pitch_classes(seg) if loud else [],
        })
 
    key, scale, strength = es.KeyExtractor(sampleRate=SAMPLE_RATE)(audio)
 
    return {
        "duration": round(duration, 3),
        "bpm": round(bpm, 2),
        "frames": frames,
        "essentia_key": {"key": key, "scale": scale, "strength": round(float(strength), 4)},
    }