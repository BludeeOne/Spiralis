// The contract between the frontend and POST /api/analyze.
// Pitch classes are ints 0-11 with C = 0, same convention as the backend.
export type PitchClass = number

export interface HistoryItem {
  name: string
  pcs: PitchClass[]
}

export interface ChordInfo {
  name: string
  root: PitchClass
  pcs: PitchClass[]
}

export interface KeyInfo {
  name: string // "C major"
  relative: string | null // "A minor"
}

export interface Numbered {
  name: string // "G7"
  numeral: string | null // "V7"
}

export interface AnalyzeResponse {
  notes: string[] // spelled names of what's sounding now
  pcs: PitchClass[]
  chord: ChordInfo | null
  key: KeyInfo | null
  history: HistoryItem[] // server-normalized history incl. current chord
  progression: Numbered[] // aligned 1:1 with history
  suggestions: Numbered[]
  scales: string[]
  bpm: number | null
  pending: string[] // theory_bridge functions not implemented yet
}
