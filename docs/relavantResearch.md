Key Ideas / Essentia Tools


#BPM - beat tracking and audio waveforms
https://essentia.upf.edu/tutorial_rhythm_beatdetection.html

music extractor 
https://essentia.upf.edu/streaming_extractor_music.html

HPCP - harmonic pitch class profile 
https://essentia.upf.edu/reference/streaming_HPCP.html

chroma features 
https://en.wikipedia.org/wiki/Chroma_feature

Comparing Hanning, Hamming & Blackman Windows article
https://www.numberanalytics.com/blog/comparing-hanning-hamming-blackman-windows#spectral-leakage-overview

blackmanharris algorithm -
https://www.dsprelated.com/freebooks/sasp/Blackman_Harris_Window_Family.html

Hamming Window algorithm - 
https://www.dsprelated.com/freebooks/sasp/Hamming_Window.html

Frequency Algorithm: 
The 12 note frequencies in the equal temperament scale represent the notes in one octave, each note is approximately 1.0595 times the frequency of the previous note

Key Word definitions:
Fourier transform: 
The Fourier transform is a mathematical technique that transforms a function of time into a function of frequency. It allows for the analysis of signals by decomposing them into their constituent frequencies.

Spectral Leakage:
Spectral leakage occurs when the energy of a sinusoidal component “leaks” into adjacent frequency bins during the Fourier Transform
- False Detections: Unwanted frequency bins may exhibit artificial peaks.
-Reduced Resolution: Overlapping energy distributions make it challenging to distinguish between nearby frequencies.
-Design Compromises: In filter design, leakage influences the stopband and passband characteristics, often trading off precision for practicality.

Magnitude:
In signal audio processing, magnitude refers to the absolute size or strength of a signal's frequency component, always expressed as a positive value, and is derived from the complex values produced by the Fourier Transform.

Essentia RMS:
Essentia.rms computes the root mean square (RMS) of an array of values, which is a statistical measure used to quantify the magnitude of a varying quantity. It is particularly useful in audio processing and signal analysis.


