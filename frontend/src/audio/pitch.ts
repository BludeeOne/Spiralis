/**
 * pitch.ts — frequency -> note name + cents for the Tuner
 *
 *   semitones from A4 = 12 · log2(f / 440)
 *   note  = round(that)            (mod 12 for the pitch class)
 *   cents = 100 · (that − note)    (−50 … +50, 0 = in tune)
 *
 * Fed by peak_hz from the backend; no detection runs in the browser
 */
//
export function yin(buf: Float32Array, sr: number, threshold = 0.15): number | null {
  let energy = 0
  for (let i = 0; i < buf.length; i++) energy += buf[i] * buf[i]
  if (Math.sqrt(energy / buf.length) < 0.01) return null // silence gate

  const W = Math.floor(buf.length / 2)
  const minLag = Math.max(2, Math.floor(sr / 1200))
  const maxLag = Math.min(W - 1, Math.floor(sr / 60))

  // difference function -> cumulative mean normalized difference
  const cmnd = new Float32Array(maxLag + 1)
  cmnd[0] = 1
  let running = 0
  for (let tau = 1; tau <= maxLag; tau++) {
    let d = 0
    for (let i = 0; i < W; i++) { const diff = buf[i] - buf[i + tau]; d += diff * diff }
    running += d
    cmnd[tau] = running ? (d * tau) / running : 1
  }

  let tau = minLag
  for (; tau <= maxLag; tau++) {
    if (cmnd[tau] < threshold) {
      while (tau + 1 <= maxLag && cmnd[tau + 1] < cmnd[tau]) tau++
      break
    }
  }
  if (tau > maxLag) return null

  //parabolic interpolation around the minimum
  const a = cmnd[tau - 1], b = cmnd[tau], c = tau + 1 <= maxLag ? cmnd[tau + 1] : b
  const denom = a - 2 * b + c
  const shift = denom ? (a - c) / (2 * denom) : 0
  return sr / (tau + shift)
}

export const SHARPS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

export interface NoteReading { midi: number; name: string; octave: number; cents: number; hz: number }

export function freqToNote(hz: number): NoteReading {
  const exact = 69 + 12 * Math.log2(hz / 440)
  const midi = Math.round(exact)
  return { midi, name: SHARPS[((midi % 12) + 12) % 12], octave: Math.floor(midi / 12) - 1, cents: Math.round((exact - midi) * 100), hz }
}
