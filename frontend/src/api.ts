import type { AnalyzeResponse, HistoryItem } from './types'

export const MOCK = import.meta.env.VITE_MOCK === '1'

export async function analyze(wav: Blob, history: HistoryItem[]): Promise<AnalyzeResponse> {
  if (MOCK) return mockAnalyze(history)
  const body = new FormData()
  body.append('audio', wav, 'chunk.wav')
  body.append('history', JSON.stringify(history.slice(-32)))
  const res = await fetch('/api/analyze', { method: 'POST', body })
  if (!res.ok) throw new Error(`The backend returned ${res.status}. Check the uvicorn terminal for the traceback.`)
  return res.json()
}

// ---- Mock mode (npm run mock): fake responses so the UI runs with no backend ----
const SHARPS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
const MOCK_CHORDS = [
  { name: 'Cadd9', pcs: [0, 2, 4, 7], numeral: 'Iadd9' },
  { name: 'Am7', pcs: [9, 0, 4, 7], numeral: 'vi7' },
  { name: 'Em7', pcs: [4, 7, 11, 2], numeral: 'iii7' },
  { name: 'Fmaj7', pcs: [5, 9, 0, 4], numeral: 'IVmaj7' },
]
let step = 0

function mockAnalyze(history: HistoryItem[]): Promise<AnalyzeResponse> {
  const c = MOCK_CHORDS[step++ % MOCK_CHORDS.length]
  const seq = history.at(-1)?.name === c.name ? history : [...history, { name: c.name, pcs: c.pcs }]
  return Promise.resolve({
    notes: c.pcs.map((p) => SHARPS[p]),
    pcs: c.pcs,
    chord: { name: c.name, root: c.pcs[0], pcs: c.pcs },
    key: { name: 'C major', relative: 'A minor' },
    history: seq,
    progression: seq.map((h) => ({ name: h.name, numeral: MOCK_CHORDS.find((m) => m.name === h.name)?.numeral ?? null })),
    suggestions: [
      { name: 'G7', numeral: 'V7' },
      { name: 'Dm7', numeral: 'ii7' },
      { name: 'D7', numeral: 'V7/V' },
    ],
    scales: ['C major (Ionian)', 'A natural minor (Aeolian)', 'C major pentatonic', 'A minor pentatonic'],
    bpm: 120,
    pending: [],
  })
}
