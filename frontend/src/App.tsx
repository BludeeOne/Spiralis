/**
 * App.tsx — layout + the analyze loop: mic chunk -> api.ts -> latest response
 * fanned out to every panel 
 * Keeps chord history for Timeline
 */
import { useCallback, useRef, useState } from 'react'
import { analyze } from './api'
import { useMic } from './audio/useMic'
import type { AnalyzeResponse, HistoryItem } from './types'
import { ChordPanel } from './components/ChordPanel'
import { KeyPanel } from './components/KeyPanel'
import { ProgressionPanel } from './components/ProgressionsPanel'
import { ScalesPanel } from './components/ScalesPanel'
import { SuggestedPanel } from './components/SuggestedPanel'
import { Timeline } from './components/Timeline'
import { Tuner } from './components/Tuner'

export default function App() {
  const [data, setData] = useState<AnalyzeResponse | null>(null)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [backendError, setBackendError] = useState<string | null>(null)
  const busy = useRef(false)
  const historyRef = useRef(history)
  historyRef.current = history

  const onChunk = useCallback(async (wav: Blob) => {
    if (busy.current) return // drop chunks while a request is in flight rather than queueing stale audio
    busy.current = true
    try {
      const res = await analyze(wav, historyRef.current)
      setData(res)
      setHistory(res.history)
      setBackendError(null)
    } catch (err) {
      setBackendError(err instanceof TypeError
        ? 'Can’t reach the backend. Start it with: uvicorn app.main:app --reload'
        : err instanceof Error ? err.message : String(err))
    } finally {
      busy.current = false
    }
  }, [])

  const mic = useMic(onChunk)
  const pending = new Set(data?.pending ?? [])
  const reset = () => { setHistory([]); setData(null); setSelected(null) }

  return (
    <div className="app">
      <header className="top">
        <h1 className="wordmark">Spiralis</h1>
        <p className="status" aria-live="polite">
          {mic.listening ? <><i className="dot live" /> Listening</> : <><i className="dot" /> Not listening</>}
        </p>
        <button className="ghost" onClick={reset} disabled={!history.length}>Clear session</button>
      </header>

      {(mic.error || backendError) && <p className="alert" role="alert">{mic.error ?? backendError}</p>}

      <main className="board">
        <KeyPanel keyInfo={data?.key ?? null} pending={pending.has('estimate_key')} />
        <ChordPanel live={data?.chord ?? null} notes={data?.notes ?? []} listening={mic.listening}
          selected={selected !== null ? history[selected] ?? null : null} pending={pending.has('identify_chord')} />
        <ProgressionPanel progression={data?.progression ?? []} pending={pending.has('roman_numeral')} />
        <Tuner analyser={mic.analyser} />
        <SuggestedPanel suggestions={data?.suggestions ?? []} pending={pending.has('suggest_next')} />
        <Timeline history={history} selected={selected} onSelect={setSelected}
          listening={mic.listening} onToggle={mic.listening ? mic.stop : mic.start} bpm={data?.bpm ?? null} />
        <ScalesPanel scales={data?.scales ?? []} pending={pending.has('fitting_scales')} />
      </main>
    </div>
  )
}
