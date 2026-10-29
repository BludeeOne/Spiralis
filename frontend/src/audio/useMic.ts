import { useCallback, useEffect, useRef, useState } from 'react'
import { encodeWav } from './wav'

// copies raw mic frames back to the main thread
const TAP = `class PcmTap extends AudioWorkletProcessor {
  process(inputs) {
    const ch = inputs[0] && inputs[0][0]
    if (ch) this.port.postMessage(ch.slice(0))
    return true
  }
}
registerProcessor('pcm-tap', PcmTap)`

function describe(err: unknown): string {
  if (err instanceof DOMException && err.name === 'NotAllowedError')
    return 'Microphone access is blocked. Allow it in your browser’s site settings, then press play again.'

  if (err instanceof DOMException && err.name === 'NotFoundError')
    return 'No microphone found. Plug one in or pick an input in System Settings, then press play again.'

  return err instanceof Error ? err.message : String(err)
}

const GATE_DB = 6       // minimum difference between signal and noise floor
const FLOOR_SEC = 15    // time window used to estimate the noise floor
const FLOOR_CAP = 2e-3  // maximum noise floor so music does not raise it too much
const ABS_FLOOR = 1e-4  // minimum signal level needed to open the gate
const TARGET_PEAK = 0.5 // target peak when normalizing audio
const MAX_GAIN = 40     // maximum gain to avoid boosting too much background noise

// strum (attack) detection
const FAST_MS = 10         // short envelope: reacts to the pick hitting the strings
const SLOW_MS = 300        // long envelope: the "what's been ringing" average
const ONSET_DB = 6         // fast must jump this far above slow to count as a strum
const REFRACTORY_MS = 150  // ignore new strums this soon after one (pick + string rattle)
const SKIP_MS = 40         // pick noise right after the attack; smears every chroma bin
const STRUM_MS = 450       // how much ringing chord to send after skipping the pick noise
const MIN_STRUM_MS = 150   // a strum cut shorter than this by the next one is dropped
const STRONG_DB = 6        // within this of the loudest recent strum = a strong strum
const LOUD_DECAY_DB = 3    // per second; lets "loudest recent" drift down if you play softer
const BPM_STRUMS = 9       // strong strums kept for the tempo estimate

export type ChunkInfo =
  | { kind: 'listen' }
  | { kind: 'strum'; db: number; strong: boolean }

export interface Strum { db: number; strong: boolean; at: number }

// calculates the root mean square of an audio buffer
const rmsOf = (x: Float32Array) => {
  let sum = 0

  for (let i = 0; i < x.length; i++) {
    sum += x[i] * x[i]
  }

  return Math.sqrt(sum / x.length)
}

const toDb = (x: number) => 20 * Math.log10(Math.max(x, 1e-6))

// boosts a quiet window up to TARGET_PEAK (in place), capped at MAX_GAIN
function normalize(win: Float32Array) {
  let peak = 0

  for (let i = 0; i < win.length; i++) {
    peak = Math.max(peak, Math.abs(win[i]))
  }

  const gain = Math.min(MAX_GAIN, TARGET_PEAK / Math.max(peak, 1e-6))

  if (gain > 1) {
    for (let i = 0; i < win.length; i++) {
      win[i] *= gain
    }
  }
}

// median of strong-strum gaps -> BPM, folded into 60–180 so a strum every
// other beat (or every half beat) still lands on a sensible tempo
function tempoFrom(times: number[]): number | null {
  const gaps: number[] = []

  for (let i = 1; i < times.length; i++) {
    const gap = times[i] - times[i - 1]
    if (gap >= 0.2 && gap <= 2.5) gaps.push(gap) // longer = you paused, not a beat
  }

  if (gaps.length < 3) return null

  gaps.sort((a, b) => a - b)
  let bpm = 60 / gaps[Math.floor(gaps.length / 2)]

  while (bpm < 60) bpm *= 2
  while (bpm > 180) bpm /= 2

  return Math.round(bpm)
}

// opens the mic, feeds the tuner, and sends two kinds of chunks:
//   'listen' — sliding window every hopSec (the "thinking" feed)
//   'strum'  — the ringing chord right after each detected attack
export function useMic(
  onChunk: (wav: Blob, info: ChunkInfo) => void,
  windowSec = 1.5,
  hopSec = 0.5
) {
  const [listening, setListening] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null)
  const [level, setLevel] = useState<{ db: number; open: boolean }>({
    db: -Infinity,
    open: false,
  })
  const [lastStrum, setLastStrum] = useState<Strum | null>(null)
  const [bpm, setBpm] = useState<number | null>(null)

  const ctxRef = useRef<AudioContext | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const onChunkRef = useRef(onChunk)

  onChunkRef.current = onChunk

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    ctxRef.current?.close()

    streamRef.current = null
    ctxRef.current = null

    setAnalyser(null)
    setListening(false)
    setLevel({ db: -Infinity, open: false })
    setLastStrum(null)
    setBpm(null)
  }, [])

  const start = useCallback(async () => {
    setError(null)

    try {
      // disables voice processing that can distort sustained guitar notes
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        },
      })

      streamRef.current = stream

      const ctx = new AudioContext()
      ctxRef.current = ctx

      const src = ctx.createMediaStreamSource(stream)

      // connects the mic to the analyser for the tuner
      const an = ctx.createAnalyser()
      an.fftSize = 4096
      src.connect(an)

      // sends raw audio samples from the worklet
      const url = URL.createObjectURL(
        new Blob([TAP], { type: 'application/javascript' })
      )

      await ctx.audioWorklet.addModule(url)
      URL.revokeObjectURL(url)

      const tap = new AudioWorkletNode(ctx, 'pcm-tap')
      const mute = ctx.createGain()

      mute.gain.value = 0
      src.connect(tap).connect(mute).connect(ctx.destination)

      // stores the most recent window of audio samples
      const size = Math.round(ctx.sampleRate * windowSec)
      const hop = Math.round(ctx.sampleRate * hopSec)
      const ring = new Float32Array(size)

      let write = 0
      let filled = 0
      let sinceHop = 0
      let total = 0 // samples received since start; write === total % size

      // keeps recent audio levels to estimate background noise
      const recent: number[] = []
      const floorHops = Math.ceil(FLOOR_SEC / hopSec)
      const gate = Math.pow(10, GATE_DB / 20)
      let floor = FLOOR_CAP // updated every hop; strums must clear it too

      // strum detection state
      const sr = ctx.sampleRate
      const ms = (n: number) => Math.round((n / 1000) * sr)
      const onsetRatio = Math.pow(10, ONSET_DB / 20)
      let fast = 0
      let slow = 0
      let prev = 0 // last sample of the previous block, for the difference signal
      let lastOnset = -Infinity  // sample position of the last strum
      let captureFrom = -1       // where the pending strum window starts (-1 = none)
      let strumPeak = 0          // loudest fast-envelope value during this strum's attack
      let loudest = -Infinity    // loudest recent strum, in dB
      let loudestAt = 0
      const strongTimes: number[] = []

      // copies samples [from, to) out of the ring buffer, chronologically
      const slice = (from: number, to: number) => {
        const out = new Float32Array(to - from)
        for (let i = 0; i < out.length; i++) out[i] = ring[(from + i) % size]
        return out
      }

      // sends the pending strum window (ending at `end`) and decides if it was strong
      const emitStrum = (end: number) => {
        const win = slice(captureFrom, end)
        const db = toDb(strumPeak)
        const at = lastOnset / sr

        loudest = Math.max(db, loudest - LOUD_DECAY_DB * (at - loudestAt))
        loudestAt = at
        const strong = db >= loudest - STRONG_DB

        if (strong) {
          strongTimes.push(at)
          if (strongTimes.length > BPM_STRUMS) strongTimes.shift()
          setBpm(tempoFrom(strongTimes))
        }

        captureFrom = -1
        normalize(win)
        setLastStrum({ db, strong, at })
        onChunkRef.current(encodeWav(win, sr), { kind: 'strum', db, strong })
      }

      tap.port.onmessage = (e: MessageEvent<Float32Array>) => {
        const block = e.data

        // writes new samples into the ring buffer
        for (let i = 0; i < block.length; i++) {
          ring[write] = block[i]
          write = (write + 1) % size
        }

        filled = Math.min(size, filled + block.length)
        sinceHop += block.length
        total += block.length

        // ---- strum detection, every block (~3 ms) ----
        // works on the sample-to-sample difference, not the raw signal: the pick's
        // click is broadband and jumps a lot, while strings still ringing from the
        // last strum are low and smooth and barely register. Raw loudness only
        // rises a few dB when you strum over ringing strings; the difference rises far more
        let d = 0
        for (let i = 0; i < block.length; i++) {
          const diff = block[i] - prev
          d += diff * diff
          prev = block[i]
        }
        const r = Math.sqrt(d / block.length)

        // two envelopes of that signal: fast jumps on the attack, slow lags
        // behind, so fast/slow spikes exactly when a new strum hits
        fast += (r - fast) * (1 - Math.exp(-block.length / ms(FAST_MS)))
        slow += (r - slow) * (1 - Math.exp(-block.length / ms(SLOW_MS)))

        // strum loudness = peak of the attack (the pick click), measured
        // during the skipped pick-noise window. Relative only: used to compare strums
        if (captureFrom >= 0 && total < captureFrom) strumPeak = Math.max(strumPeak, fast)

        const isOnset =
          fast > slow * onsetRatio &&
          rmsOf(block) > Math.max(ABS_FLOOR, floor * gate) && // real sound, not hiss
          total - lastOnset > ms(REFRACTORY_MS)

        if (isOnset) {
          // a new strum cut the previous one short: send it if it's long enough
          if (captureFrom >= 0 && total - captureFrom >= ms(MIN_STRUM_MS)) emitStrum(total)

          lastOnset = total
          captureFrom = total + ms(SKIP_MS)
          strumPeak = fast
        } else if (captureFrom >= 0 && total >= captureFrom + ms(STRUM_MS)) {
          emitStrum(captureFrom + ms(STRUM_MS))
        }

        // ---- sliding 'listen' window, every hopSec ----
        if (sinceHop < hop || filled < size) return

        sinceHop = 0

        // puts the samples in chronological order
        const win = new Float32Array(size)
        win.set(ring.subarray(write), 0)
        win.set(ring.subarray(0, write), size - write)

        // estimates the noise floor using the quietest recent audio
        const hopRms = rmsOf(win.subarray(size - hop))

        recent.push(hopRms)
        if (recent.length > floorHops) recent.shift()

        floor = Math.min(FLOOR_CAP, ...recent)
        const open = rmsOf(win) > Math.max(ABS_FLOOR, floor * gate)

        setLevel({ db: toDb(hopRms), open })

        if (!open) return

        // boosts quiet audio, encodes it, and sends it as a 'listen' chunk
        normalize(win)
        onChunkRef.current(encodeWav(win, sr), { kind: 'listen' })
      }

      setAnalyser(an)
      setListening(true)
    } catch (err) {
      setError(describe(err))
      stop()
    }
  }, [windowSec, hopSec, stop])

  useEffect(() => stop, [stop])

  return { listening, error, analyser, level, lastStrum, bpm, start, stop }
}
