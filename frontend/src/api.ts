/**
 * api.ts — POSTs each WAV chunk to /api/analyze and returns the typed
 * AnalyzeResponse. The Vite dev server proxies /api to FastAPI on :8000.
 */
import type { AnalyzeResponse, HistoryItem, ScaleResponse } from './types'

export async function analyze(wav: Blob, history: HistoryItem[]): Promise<AnalyzeResponse> {
  const body = new FormData()
  body.append('audio', wav, 'chunk.wav')
  body.append('history', JSON.stringify(history.slice(-32)))
  const res = await fetch('/api/analyze', { method: 'POST', body })
  if (!res.ok) throw new Error(`The backend returned ${res.status}. Check the uvicorn terminal for the traceback.`)
  return res.json()
}

export async function getScale(root: number, mode: string): Promise<ScaleResponse> {
  const res = await fetch(`/api/scale?root=${root}&mode=${mode}`)
  if (!res.ok) throw new Error(`The backend returned ${res.status}. Check the uvicorn terminal for the traceback.`)
  return res.json()
}