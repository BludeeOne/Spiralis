# Spiralis — Peer Review

**October 9, 2026**  
Erik Siemsen

## Project Title and Purpose

### Spiralis: A Musician's Website

Spiralis is a music theory tool for guitar players, songwriters, and anyone who wants to experiment with music. You play your guitar into a microphone, and Spiralis tries to identify the notes, chord, and key you're playing. From there, it shows scales that fit, possible next chords, Roman numerals, and other information to help you understand where a song can go.

The idea came from teaching myself guitar. I kept finding that music theory tools were spread across a bunch of different websites, and it was hard to find one place that connected everything. Spiralis is my attempt at putting all of that together into one tool that is useful for both beginners and people who already write music.

The README explains how the audio moves from the microphone through the backend and back to the screen. I've also added a header to each source file explaining what it does and why it's there.

## Key Features Implemented

The main live microphone pipeline is working end to end. The browser records audio in roughly two-second chunks, sends them to the backend for analysis, and updates the different panels with the results.

| Feature | What it does | Main files |
| --- | --- | --- |

| Live microphone 
| Records audio in roughly two-second WAV chunks without browser audio processing interfering with pitch detection 
| `frontend/src/audio/useMic.ts`, `wav.ts` |

| Tuner | Detects and displays the strongest pitch directly in the browser 
| `audio/pitch.ts`, `components/Tuner.tsx` |

| Audio detection | Uses FFT, spectral peaks, HPCP chroma, and beat tracking to figure out which notes are playing, mostly from the essentia api 
| `backend/app/audio/detection.py` |

| Chord identification | Turns detected notes and the bass note into a chord name, including slash chords 
| `theory/chords.py` |

| Key detection | Compares the chord history against major and minor keys to find the best match 
| `theory/progressions.py` |

| Note spelling | Uses the correct note names for the key, such as Bb instead of A# in F major 
| `theory/notes.py` |

| Chord progression | Displays the chords played so far with Roman numerals like I–V–vi–IV 
| `progressions.py`, `components/Timeline.tsx` |

| Next chord suggestions | Suggests possible chords to play next and labels them with Roman numerals 
| `progressions.py` |

| Scales and modes | Shows scales that fit the detected key 
| `theory/scales.py` |

| Circle of fifths | Finds related keys and their relationships 
| `theory/circle_of_fifths.py` |

| Guitar fingerings | Generates chord voicings and scale positions for a 12-fret guitar neck. The backend is mostly done, and the UI is functional yet i have some bigger ideas
| `theory/fingerings.py` |

| Written chord input | Accepts chord names like C, G7, Am, and F without needing audio 
| `app/main.py`, `theory_bridge.py` |

| Error handling | Tracks unfinished theory functions and tells the UI what's missing instead of crashing 
| `routes/analyze.py`, `components/Panel.tsx` |


## Languages, Libraries, and Frameworks

The backend is written in Python, and the frontend uses TypeScript and React. 

| Layer | Technology | Purpose |
| --- | --- | --- |
| Backend | Python 3.11 | Audio analysis and music theory |

| API | FastAPI, Uvicorn, Pydantic 2 | Handles requests and validates data |

| Audio processing | Essentia 2.1b6 | FFT, spectral peaks, HPCP chroma, beat tracking, BPM, and key cross-checking |

| Numerical processing | NumPy, SciPy | Chroma averaging and detection thresholds |

| Additional audio libraries | librosa, basic-pitch | Installed during the Apple Silicon rebuild, but not currently part of the main pipeline |

| Music theory | Python |implementation of chords, scales, keys, progressions, and fingerings |

| Frontend | TypeScript 5.5 | Typed responses from the backend |

| UI | React 18, Vite 5 | Displays the results and handles the frontend |

| Browser audio | Web Audio API, `getUserMedia` | Microphone access, WAV encoding, and tuner |

There is currently no database or authentication system. The chord history stays in React state and gets sent to the backend with each analysis request.
Im think i should probably add a database for users but im tired

## Challenges and How I Addressed Them

The biggest challenge was getting correct musical information out of a guitar recording. A guitar signal isn't always clean, and just detecting frequencies doesn't automatically tell you which notes or chords someone is playing. A lot of the design choices came from trying to make that process more reliable. I ran into a lot of 
problems with of misidentifying chrods because of frequenices overpower overs and some notes being harmonics of other notes so essentia isnt sure whats happening. I reduced harmonic detection and Im currently playing with the labeling of chords and the strength of my bass logic. Basically right now 

### 1. Noisy and Unreliable Note Detection

At first, analyzing each audio frame independently caused the detected chords to jump around. louder notes and their harmonics could also drown out quieter notes

I added a Blackman-Harris window before the FFT to reduce spectral leakage, then used HPCP to group frequencies into the 12 pitch classes. I also added beat tracking so the system could average chroma between beats instead of making a decision on every frame. A threshold of 0.5 helps decide which notes are actually present when everything is displayed

My research notes for this are in `docs/relevantResearch.md`

### 2. Browser Microphone Processing

Browsers normally apply things like echo cancellation, noise suppression, and automatic gain control to microphone input. Those features are predominately for like voice calls or recording, its supposed to making vox cleaner and more understandable but when it comes to guitar playing and identifying it would only hinder progress

I turned those settings off in `useMic.ts` so the backend receives audio that is closer to what the instrument actually sounds like

### 3. Deciding Where Audio Detection Should Happen

I considered doing the audio processing in the browser using WebAssembly, but ended up using Python on the backend for the first version.

Essentia's Python support was a better fit for the features I needed, and keeping the detection server-side made it easier to develop and debug the pipeline.

### 4. Getting the Development Environment Working

Essentia was the most difficult dependency to install. it just straight up didnt work on my old pc it was outdated. I ran into a problem of do i just amass outdated or
underfunctional apis, or just get a new computer. So i literally got a new computer to have a functioning enviroment After that i had to reinstall every dependency ever, delete vs code and clear its history, just a whole lot of reset. But Once i had my new baby it was bbq chicken

I settled on Python 3.11, pinned the dependencies in `requirements.txt`, and reorganized the backend around Essentia and FastAPI.

### 5. Connecting Audio Data to Music Theory

The audio detection system produces numbers representing pitch classes, but the music theory side works with actual notes, chords, and keys. There was also a mismatch between Essentia's pitch indexing and the convention used by my theory code. Essentia is coded to start at A, which i guess makes sense, but i start at C cause thats what ive always done. Super simple fix. Rotate of 3 for any note. 

I separated the two systems so each has one job. `detection.py` handles audio and doesn't name chords, while the `theory/` directory handles music theory and doesn't process audio. `theory_bridge.py` connects them, and pitch classes are normalized to use C = 0 before they reach the theory engine.

### 6. Getting Note Names Right
this was a tricky one. 
A basic note detector might identify a pitch as A#, even when Bb is the correct spelling for the key. The pitches are technically equivalent, but theres standardized scales and ways of writing notes, like some notes are Always Bb and some notes are always F#. 

I wrote `notes.py` to spell notes based on the key signature. The chord history is also respelled once the key is known, so the names make more sense in context.

### 7. Building the Theory Engine Without Breaking Everything

I've been adding the music theory functions incrementally, so not every feature is finished yet.

Instead of letting a missing function crash the entire application, I wrapped the theory calls so unfinished features get added to a `pending` list. The corresponding panel can then explain what is missing. 

### 8. Handling Audio Requests

The browser sends audio chunks about every two seconds, but the backend can take longer than that to finish analyzing them.

Rather than building up a queue of old audio, the frontend skips a chunk while another request is still running. This keeps the application from falling behind and analyzing audio that is no longer relevant.

## Future Improvements

The second half of the semester will focus on connecting the remaining backend features to the frontend, improving reliability, and cleaning up the code. Along with a hopefulyl beautiful and aesethic frontend. 

### Features I Want to Add

- **Circle of fifths visualization:** Display the circle directly in the UI. The backend already has the information needed.
- **Guitar neck visualization:** Show chord fingerings and scale positions on the fretboard using the existing fingering code.
- **Song uploads:** Add an interface for uploading MP3, M4A, WAV, and FLAC files. The backend already has a file analysis endpoint that accepts files up to 50 MB.
- **Written chord input:** Let users enter a progression manually instead of playing it into the microphone.
- **More progression options:** Show additional possible paths a song could take, building on the existing next-chord suggestions, but with defined terms like pop, jazz, emo, etc
- **Computer vision (stretch goal):** Explore whether a camera could identify hand positions on the fretboard and determine which chord is being played, but thats a long long far stretch goal

### Known Issues

These are things I already know need work, so feedback on them is welcome.

- **No automated tests yet.** The theory engine mostly uses standalone functions and there is no tests for seperate parts, i kinda just threw them all together
- **Overlapping analysis endpoints.** `/api/analyze` handles live microphone analysis through `routes/analyze.py`, while `/analyze` in `main.py` handles file uploads. They currently return different response formats and could use a more consistent structure.
- **Outdated README** Some filenames in the pipeline diagram have changed. For example, `micCapture.tsx` was replaced by `useMic.ts`, and the circle of fifths and guitar neck panels still need to be built.
- **Unused dependencies.** `librosa` and `basic-pitch` are installed but i didnt end up using them, theres some unused functions and stuff hiding around too 
- **Detection sensitivity.** The 0.5 threshold and roughly two-second audio chunks have been tuned by ear using my own guitar. Quiet playing and other instruments may need different settings.

## Running the Project and Where to Look

To run Spiralis, you'll need Python 3.11, Node.js 18 or newer, and two terminal windows. You can test it with a guitar, another instrument, or even a guitar video playing near your microphone. I use garageband piano sometimes, or i even just sing

### Terminal 1: Start the Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The backend runs on port `8000`.

### Terminal 2: Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on port `5173`.

Open [http://localhost:5173](http://localhost:5173) and press Play to grant microphone access.

Essentia provides prebuilt packages for macOS and Linux. If you're on Windows, using WSL is probably the easiest option.

### Suggested Reading Order

1. **`README.md`** — Start here for the project overview and pipeline diagram.
2. **`backend/app/routes/analyze.py`** — Shows how the application connects audio detection to music theory.
3. **`backend/app/audio/detection.py`** — Explains how the raw audio gets turned into pitch-class data.
4. **`backend/app/theory_bridge.py`** — Connects the audio results to the theory engine.
5. **`backend/theory/chords.py` and `progressions.py`** — The main music theory logic, including chord identification and progression suggestions.
6. **`frontend/src/App.tsx` and `frontend/src/audio/useMic.ts`** — Shows how the browser captures audio and displays the results.

The main goal with Spiralis is to make music theory more connected and accessible. Instead of having to look up chords, scales, and progressions separately, I want someone to be able to play something and have the information they need show up in one place. The core pipeline is working, and the next step is making the remaining features easier to use and getting the whole application ready for other people to try. Theres a lot more I think I could do with this all though. 