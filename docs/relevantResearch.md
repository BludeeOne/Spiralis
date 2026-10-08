# Key Ideas / Essentia Tools

## Essentia Tools
file written out by chatgpt
original research done by muau
### BPM / Beat Tracking
Essentia's beat tracking tools are used to find the beat positions in an
audio signal and estimate the BPM (beats per minute). We use this to
synchronize the detected notes/chroma with the beat instead of analyzing
every single audio frame independently.

https://essentia.upf.edu/tutorial_rhythm_beatdetection.html

### Music Extractor
Essentia's Music Extractor is a larger collection of audio analysis tools
that can extract things like rhythm, tonal information, and other features
from an audio file.

https://essentia.upf.edu/streaming_extractor_music.html

### HPCP — Harmonic Pitch Class Profile
HPCP takes the frequencies found in an audio signal and maps them into the
12 different pitch classes. This means that notes in different octaves are
grouped together. It is useful for figuring out which notes are present in
a chord.

https://essentia.upf.edu/reference/streaming_HPCP.html

### Chroma Features
Chroma features represent the energy of an audio signal across the 12
different pitch classes. Unlike a normal frequency spectrum, chroma focuses
on the musical note rather than the exact frequency or octave.

https://en.wikipedia.org/wiki/Chroma_feature

### RMS — Root Mean Square
RMS measures the overall energy or magnitude of an audio signal. In simple
terms, it gives us an idea of how loud or strong the signal is at a given
point.

Essentia's `RMS` algorithm calculates this value from an array of audio
samples and is commonly used when analyzing the strength of an audio
signal.


## Windowing

### Hanning, Hamming, and Blackman Windows
Window functions are used before running the FFT to reduce spectral leakage.
Different windows make different tradeoffs between frequency resolution and
how much energy leaks into nearby frequency bins.

This article compares the Hanning, Hamming, and Blackman windows and shows
how they behave differently.

https://www.numberanalytics.com/blog/comparing-hanning-hamming-blackman-windows#spectral-leakage-overview

### Blackman-Harris Window
The Blackman-Harris window is the window we use in our audio analysis. It
has very low sidelobes, which helps reduce spectral leakage from strong
frequencies into nearby weaker frequencies.

This is especially useful for our chord detection because a loud note or
harmonic shouldn't overpower nearby notes that are actually being played.

https://www.dsprelated.com/freebooks/sasp/Blackman_Harris_Window_Family.html

### Hamming Window
The Hamming window is another common window function used to reduce spectral
leakage. It provides a different tradeoff between the main lobe and
sidelobes compared to Blackman-Harris.

https://www.dsprelated.com/freebooks/sasp/Hamming_Window.html


## Frequency / Equal Temperament

The 12 notes in an octave are spaced using the equal temperament scale. Each
note is approximately 1.0595 times the frequency of the note before it.

More precisely:

    frequency = reference_frequency × 2^(n/12)

where `n` is the number of semitones away from the reference note.

For example, starting from A4 = 440 Hz:

    A4 = 440 Hz
    A#4 = 466.16 Hz
    B4 = 493.88 Hz
    C5 = 523.25 Hz

After 12 semitones, the frequency doubles and you reach the same note one
octave higher.


# Key Word Definitions

### Fourier Transform

The Fourier Transform is a mathematical technique that converts a signal
from the time domain into the frequency domain.

In our project, this lets us take an audio waveform and figure out which
frequencies make up the sound. The FFT (Fast Fourier Transform) is the
efficient algorithm we use to calculate this.


### Spectral Leakage

Spectral leakage happens when the energy from a frequency spreads into
neighboring frequency bins during the Fourier Transform.

This usually happens because we are analyzing a small section of a signal
instead of an infinite signal. Cutting the signal creates sharp edges, and
the FFT interprets those edges as additional frequencies.

This can cause:

- False detections: Extra frequency bins can appear as peaks.
- Reduced resolution: Nearby frequencies become harder to separate.
- Unwanted interference: Strong frequencies can spread into weaker
  frequencies nearby.

This is why we use a window function before running the FFT.


### Magnitude

Magnitude represents the strength or size of a frequency component.

The FFT produces complex numbers, which contain both magnitude and phase.
For our purposes, we are mainly interested in the magnitude because it tells
us how much energy is present at each frequency.

A larger magnitude means that frequency is stronger in the signal.


### Frequency Resolution

Frequency resolution describes how closely we can distinguish between two
different frequencies in the FFT.

It can be calculated as:

    frequency_resolution = sample_rate / frame_size

A larger frame gives better frequency resolution because the FFT has more
samples to work with. However, larger frames also cover more time, which
makes the timing less precise.

This is one of the main tradeoffs when choosing the frame size for audio
analysis.


### Pitch Class

A pitch class represents a musical note without caring about its octave.

For example:

    C2
    C3
    C4
    C5

are all part of the same pitch class: **C**.

There are 12 pitch classes:

    C  C#  D  D#  E  F  F#  G  G#  A  A#  B

This is why chroma and HPCP can reduce a full frequency spectrum down to
12 values.


### Harmonics

Harmonics are additional frequencies that occur naturally above a
fundamental frequency.

If a note has a fundamental frequency `f`, its harmonics can appear around:

    f
    2f
    3f
    4f
    ...

These harmonics are a big reason instruments have different sounds even
when they play the same note. They also matter for our chord detection
because the FFT can detect harmonics in addition to the fundamental note.


### FFT

The Fast Fourier Transform (FFT) is an efficient way to calculate the
Discrete Fourier Transform.

Instead of looking at the audio as a waveform changing over time, the FFT
lets us look at the frequencies that make up that waveform.

In my pipeline:

    audio -> frames -> window -> FFT -> frequency spectrum -> peaks -> HPCP

The FFT is basically the step that lets us go from "what the waveform looks
like" to "what frequencies are actually in the sound.