/**
 * App.tsx — layout + the analyze loop: mic chunk -> api.ts -> panels
 *
 * Two feeds come out of useMic and they're kept apart:
 *   committed — strong strums. Drives the chord, key, progression, suggestions,
 *               scales and the timeline. Switches on the very first strum that
 *               reads as a different chord, so fast changes (two chords a bar,
 *               walk-downs) show up immediately.
 *   heard     — the sliding 'listen' window plus weak strums. The "thinking"
 *               feed: shows the notes being heard, never touches history.
 *
 * The backend is stateless: history goes up with every request and comes back
 * with the new chord appended. So "committing" just means keeping that returned
 * history. Listen responses are shown, and their history is thrown away.
 */
import { useCallback, useRef, useState } from 'react'
import { analyze } from './api'
import { useMic, type ChunkInfo } from './audio/useMic'
import type { AnalyzeResponse, HistoryItem } from './types'
import { ChordPanel } from './components/ChordPanel'
import { KeyPanel } from './components/KeyPanel'
import { ProgressionPanel } from './components/ProgressionsPanel'
import { ScalesPanel } from './components/ScalesPanel'
import { SuggestedPanel } from './components/SuggestedPanel'
import { Timeline } from './components/Timeline'
import { Tuner } from './components/Tuner'

// this commit weak is for upstrokes, currently trying to focus on down strokes, will see if turning off upstrokes fucks anything
const COMMIT_WEAK = false

export default function App() {
  const [committed, setCommitted] = useState<AnalyzeResponse | null>(null)
  const [heard, setHeard] = useState<AnalyzeResponse | null>(null)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [backendError, setBackendError] = useState<string | null>(null)

  const historyRef = useRef(history)
  historyRef.current = history

  const listenBusy = useRef(false)
  const strumBusy = useRef(false)
  const queuedStrum = useRef<Blob | null>(null)

  const report = (err: unknown) =>
    setBackendError(err instanceof TypeError
      ? 'Can’t reach the backend. Start it with: uvicorn app.main:app --reload'
      : err instanceof Error ? err.message : String(err))

  // listen chunks: dropped while one is in flight (the next is only 0.5 s away)
  const sendListen = useCallback(async (wav: Blob) => {
    if (listenBusy.current) return
    listenBusy.current = true

    try {
      setHeard(await analyze(wav, historyRef.current))
      setBackendError(null)
    } catch (err) {
      report(err)
    } finally {
      listenBusy.current = false
    }
  }, [])

  // strum chunks: never dropped. If one
  // is queued and sent right after, so quick changes all make it in order
  const sendStrum = useCallback(async (wav: Blob) => {
    if (strumBusy.current) {
      queuedStrum.current = wav
      return
    }
    strumBusy.current = true

    let next: Blob | null = wav
    while (next) {
      try {
        const res = await analyze(next, historyRef.current)
        setHeard(res)

        // a strum that didn't resolve to a chord leaves the last one on screen
        if (res.chord) {
          setCommitted(res)
          setHistory(res.history)
          historyRef.current = res.history // the queued strum must build on this one
        }
        setBackendError(null)
      } catch (err) {
        report(err)
      }

      next = queuedStrum.current
      queuedStrum.current = null
    }

    strumBusy.current = false
  }, [])

  const onChunk = useCallback((wav: Blob, info: ChunkInfo) => {
    if (info.kind === 'strum' && (info.strong || COMMIT_WEAK)) sendStrum(wav)
    else sendListen(wav)
  }, [sendListen, sendStrum])

  const mic = useMic(onChunk)
  const pending = new Set((committed ?? heard)?.pending ?? [])
  const reset = () => { setHistory([]); setCommitted(null); setHeard(null); setSelected(null) }

  return (
    <div className="app">
      <header className="top">
        <h1 className="wordmark">Spiralis</h1>
        <p className="status" aria-live="polite">
          {mic.listening ? <><i className="dot live" /> {mic.level.open ? 'Hearing sound' : 'Listening'}</> : <><i className="dot" /> Not listening</>}
          {mic.listening && (
            //input meter: -80…-20 dBFS. Gold once the noise gate opens, so you can tell
            //"mic hears nothing" apart from "mic hears it but no chord matched"
            <span className={`meter ${mic.level.open ? 'open' : ''}`} aria-hidden="true">
              <i style={{ width: `${Math.max(0, Math.min(100, ((mic.level.db + 80) / 60) * 100))}%` }} />
            </span>
          )}
        </p>
        <button className="ghost" onClick={reset} disabled={!history.length}>Clear session</button>
      </header>

      {(mic.error || backendError) && <p className="alert" role="alert">{mic.error ?? backendError}</p>}

      <main className="board">
        <KeyPanel keyInfo={committed?.key ?? null} pending={pending.has('estimate_key')} />
        {/* big name = last committed chord; small line under it = what's being heard right now */}
        <ChordPanel live={committed?.chord ?? null} notes={heard?.notes ?? []} listening={mic.listening}
          selected={selected !== null ? history[selected] ?? null : null} pending={pending.has('identify_chord')} />
        <ProgressionPanel progression={committed?.progression ?? []} pending={pending.has('roman_numeral')} />
        <Tuner analyser={mic.analyser} />
        <SuggestedPanel suggestions={committed?.suggestions ?? []} pending={pending.has('suggest_next')} />
        {/* BPM now comes from strong-strum spacing in the browser; the backend's is always empty for short chunks */}
        <Timeline history={history} selected={selected} onSelect={setSelected}
          listening={mic.listening} onToggle={mic.listening ? mic.stop : mic.start} bpm={mic.bpm} />
        <ScalesPanel scales={committed?.scales ?? []} pending={pending.has('fitting_scales')} />
      </main>
    </div>
  )
}
