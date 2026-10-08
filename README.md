Spiralis

A one-stop shop for aspiring musicians, accomplished song writers, and anyone who wants to play around in a musical playground.
Play your guitar into your mic and Spiralis tells you what you're playing the notes, the chord, the key and then everything that comes with it: scales, diatonic chords, circle-of-fifths neighbours, where the progression can go next, and even different ways of how to finger it on a guitar neck.

  Each source file opens with a header explaining the science behind it. This README only covers the path through the program. Follow the tree, then open the file you're curious about!



HOW TO RUN:
## Running Spiralis locally

You need two terminals, one for the backend and one for the frontend

### Backend (FastAPI on :8000)
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Next time, just `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload`.

### Frontend (Vite on :5173)
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 and allow mic access. Vite proxies `/api` to the backend, so it needs to be running first
it doesnt always ask for mic access but when you press the play button it does and you can start going at it


The Pipeline Through Spiralis
a sound is played
  │
  |
------------------------------------------------------------------------
│ FRONTEND  (React + Vite, :5173)                                      │
│                                                                      │
│  micCapture.tsx -- getUserMedia, voice processing OFF                │
│        │           (no echo-cancel / noise-suppress /                │
│        │            they wreck pitch)                                │
│        |-> encode ~2s chunk as WAV                                   │
------------------------------------------------------------------------
         │  POST /api/analyze   
         |
------------------------------------------------------------------------
│ BACKEND  (FastAPI + uvicorn, :8000)                                  │
│                                                                      │
│  main.py ── app, CORS, mounts routers                                │
│    └── routes/analyze.py ── the conductor: calls 1 then 2            │
│          │                                                           │
│          |-- 1 audio/detection.py -------- SIGNAL → NUMBERS          │
│          │     │                           (all Essentia  here)      │
│          │     |-- decode ........... WAV bytes → mono float32       │
│          │     |-- frame + window ... Blackman-Harris 62             │
│          │     |-- spectrum ......... FFT magnitude per frame        │  
│          │     |-- spectral peaks ... strongest partials → peak_hz   │
│          │     |-- chroma (HPCP) .... 12 bins, rolled so C = 0       │
│          │     |-- beats ............ beat grid + BPM                │
│          │     |-- beat-sync ........ average chroma between beats   │
│          │     |-- pitch-class sets . bins >= 0.5 -> {0,4,7} etc     │
│          │                                                           │
│          │          plain ints 0–11 no actual notes yet              │
│          │                                                           │
│          |-- 2 theory_bridge.py ---------- NUMBERS → MEANING         │
│                │                           (only door into theory/)  │
│                |-- theory/                                           │
│                      |-- notes.py ............ pc ↔ name, spelling   │
│                      |--c hords.py ........... pc set → chord name   │
│                      |-- scales.py ........... modes, scales that fit│
│                      |-- circle_of_fifths.py . key, neighbours       │
│                      |-- progressions.py ..... roman numerals,       │
│                      │                         next-chord paths      │
│                      |-- fingerings.py ....... guitar voicings       │
│                                                                      │
│  schemas.py ── shapes the reply:                                     │
│     { notes, chord, key, roman, scales, suggestions, bpm,            │
│       peak_hz, chroma, pending }                                     │
------------------------------------------------------------------------
         │  JSON
         ▼
------------------------------------------------------------------------
│ FRONTEND                                                             │
│   livePanel ........ notes · chord · key · BPM · chroma bars         │
│   circleOfFifths ... current key + neighbours highlighted            │
│   guitarNeck ....... scale / chord shapes on the fretboard           │
------------------------------------------------------------------------