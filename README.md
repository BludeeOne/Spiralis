# Spiralis

A one-stop shop for aspiring musicians, accomplished songwriters, and anyone who wants to mess around in a musical playground.

Play your guitar into your mic and **Spiralis** tells you what you're playing -> the notes, the chord, the key, and everything that comes with it: scales, diatonic chords, circle-of-fifths neighbors, where the progression can go next, and even different ways to finger it on a guitar neck

Each source file opens with a header explaining the science behind it. This README focuses on the path through the program. Follow the tree, then open whichever file you are curious about

---

## Running Spiralis Locally

You need **two terminals**: one for the backend and one for the frontend.

### Backend — FastAPI on `:8000`

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The next time you run the project, you can use:

```bash
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload
```

### Frontend — Vite on `:5173`

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Then open:

**http://localhost:5173**

The browser will need microphone access. It doesn't always ask for permission immediately, but pressing the **Play** button will trigger the microphone request if permission has not already been given.

The Vite frontend proxies `/api` requests to the backend, so the backend needs to be running first.

---

# The Pipeline Through Spiralis

At a high level, the program takes the sound from your guitar, turns it into numbers, interprets those numbers as music theory, and sends the results back to the frontend.

```text
Guitar / microphone
        │
        
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND — React + Vite (:5173)                             │
│                                                             │
│  micCapture.tsx                                             │
│      │                                                      │
│      ├── getUserMedia()                                     │
│      │     Microphone input with voice processing OFF       │
│      │     (echo cancellation / noise suppression can       │
│      │      interfere with pitch detection)                 │
│      │                                                      │
│      └── encode ~2 second audio chunk as WAV                │
└─────────────────────────────────────────────────────────────┘
        │
        │ POST /api/analyze
        
┌─────────────────────────────────────────────────────────────┐
│ BACKEND — FastAPI + Uvicorn (:8000)                         │
│                                                             │
│  main.py                                                    │
│  └── app, CORS, and router setup                            │
│                                                             │
│      routes/analyze.py                                      │
│      └── The conductor: sends the audio through             │
│          detection first, then theory                       │
│                                                             │
│          1. audio/detection.py                              │
│             SIGNAL → NUMBERS                                │
│             (all Essentia processing happens here)           │
│                                                             │
│             ├── decode                                       │
│             │   WAV bytes -> mono float32                    │
│             │                                                │
│             ├── frame + window                               │
│             │   Blackman-Harris 62                           │
│             │                                                │
│             ├── spectrum                                     │
│             │   FFT magnitude for each frame                │
│             │                                                │
│             ├── spectral peaks                               │
│             │   strongest partials -> peak_hz                 │
│             │                                                │
│             ├── chroma (HPCP)                                │
│             │   12 pitch-class bins, rolled so C = 0         │
│             │                                                │
│             ├── beats                                        │
│             │   beat grid + BPM                              │
│             │                                                │
│             ├── beat synchronization                         │
│             │   average chroma between beats                 │
│             │                                                │
│             └── pitch-class sets                              │
│                 bins >= 0.5 → {0, 4, 7}, etc.                │
│                                                             │
│             At this point they are still just numbers        │
│             from 0–11. No actual note names yet.             │
│                                                             │
│          2. theory_bridge.py                                 │
│             NUMBERS -> MEANING                                │
│             (the only door into theory/)                     │
│                                                             │
│             └── theory/                                      │
│                 ├── notes.py                                │
│                 │   pitch class ↔ note name + spelling       │
│                 │                                            │
│                 ├── chords.py                               │
│                 │   pitch-class set -> chord name             │
│                 │                                            │
│                 ├── scales.py                               │
│                 │   modes and scales that fit                │
│                 │                                            │
│                 ├── circle_of_fifths.py                     │
│                 │   key + nearby keys                        │
│                 │                                            │
│                 ├── progressions.py                          │
│                 │   Roman numerals + possible next chords    │
│                 │                                            │
│                 └── fingerings.py                            │
│                     guitar chord / scale voicings            │
│                                                             │
│  schemas.py                                                  │
│  └── Shapes the final response:                              │
│      notes, chord, key, roman, scales, suggestions,         │
│      bpm, peak_hz, chroma, pending                           │
└─────────────────────────────────────────────────────────────┘
        │
        │ JSON
        
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND                                                    │
│                                                             │
│  livePanel                                                  │
│  └── notes · chord · key · BPM · chroma bars                │
│                                                             │
│  circleOfFifths                                             │
│  └── current key + nearby keys highlighted                  │
│                                                             │
│  guitarNeck                                                 │
│  └── scale / chord shapes displayed on the fretboard        │
└─────────────────────────────────────────────────────────────┘
```

---

## The Short Version

If you don't want to follow the whole diagram the basic idea is:

```text
Sound
  
Microphone
  
~2 second WAV chunk
  
audio/detection.py
  
FFT -> peaks -> HPCP -> beats -> pitch classes
  
theory_bridge.py
  
notes -> chord -> key -> scales ->progressions -> fingerings
  
JSON response
  
React frontend
  
You see what you're playing
```

The important separation is that `detection.py` does not try to name chords. It turns the audio into frequencies/numbers

Then `theory_bridge.py` takes those numbers and gives them musical names


