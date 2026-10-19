/**
 * useMic.ts — the start of the pipeline
 *
 * Opens the mic with getUserMedia and turns OFF echoCancellation,
 * noiseSuppression and autoGainControl. Those are tuned for voice calls and
 * actively distort sustained musical tones (AGC pumps volume, noise
 * suppression eats the decay of a ringing string).
 *
 * Buffers raw Float32 samples into ~2 s chunks and hands each one to wav.ts.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { encodeWav } from './wav'

//worklet that copies raw mic frames back to the main thread
const TAP = `class PcmTap extends AudioWorkletProcessor {
  process(inputs) { const ch = inputs[0] && inputs[0][0]; if (ch) this.port.postMessage(ch.slice(0)); return true }
}
registerProcessor('pcm-tap', PcmTap)`

function describe(err: unknown): string {
  if (err instanceof DOMException && err.name === 'NotAllowedError')
    return 'Microphone access is blocked. Allow it in your browser’s site settings, then press play again.'
  if (err instanceof DOMException && err.name === 'NotFoundError')
    return 'No microphone found. Plug one in or pick an input in System Settings, then press play again.'
  return err instanceof Error ? err.message : String(err)
}

const GATE_DB = 6         // window must be this many dB above the noise floor
const FLOOR_SEC = 15      // noise floor = quietest moment in this much recent audio
const FLOOR_CAP = 2e-3    // room hiss with AGC off sits well under this (~-54 dBFS)
const ABS_FLOOR = 1e-4    // never treat anything quieter than this (~-80 dBFS) as signal
const TARGET_PEAK = 0.5   // normalize sent windows to this peak
const MAX_GAIN = 40       // don't boost more than +32 dB (would just amplify hiss)

const rmsOf = (x: Float32Array) => {
  let s = 0
  for (let i = 0; i < x.length; i++) s += x[i] * x[i]
  return Math.sqrt(s / x.length)
}

//opens the mic and exposes an AnalyserNode for the tuner, then emits a WAV of the
//last `windowSec` of audio every `hopSec` (when there's something to hear)
export function useMic(onChunk: (wav: Blob) => void, windowSec = 1.5, hopSec = 0.5) {
  const [listening, setListening] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null)
  const [level, setLevel] = useState<{ db: number; open: boolean }>({ db: -Infinity, open: false })
  const ctxRef = useRef<AudioContext | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const onChunkRef = useRef(onChunk)
  onChunkRef.current = onChunk

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    ctxRef.current?.close()
    streamRef.current = null
    ctxRef.current = null
    setAnalyser(null)
    setListening(false)
    setLevel({ db: -Infinity, open: false })
  }, [])

  const start = useCallback(async () => {
    setError(null)
    try {
      //voice processing is off cuase it mangles sustained guitar notes
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false },
      })
      streamRef.current = stream
      const ctx = new AudioContext()
      ctxRef.current = ctx
      const src = ctx.createMediaStreamSource(stream)

      const an = ctx.createAnalyser()
      an.fftSize = 4096
      src.connect(an)

      const url = URL.createObjectURL(new Blob([TAP], { type: 'application/javascript' }))
      await ctx.audioWorklet.addModule(url)
      URL.revokeObjectURL(url)
      const tap = new AudioWorkletNode(ctx, 'pcm-tap')
      const mute = ctx.createGain()
      mute.gain.value = 0 // keeps the worklet pulled by the graph without playing the mic back
      src.connect(tap).connect(mute).connect(ctx.destination)

      //ring buffer holding the most recent `windowSec` of audio
      const size = Math.round(ctx.sampleRate * windowSec)
      const hop = Math.round(ctx.sampleRate * hopSec)
      const ring = new Float32Array(size)
      let write = 0      // next write position in ring
      let filled = 0     // samples written so far (caps at size)
      let sinceHop = 0
      const recent: number[] = []   // per-hop RMS history for the noise floor
      const floorHops = Math.ceil(FLOOR_SEC / hopSec)
      const gate = Math.pow(10, GATE_DB / 20)

      tap.port.onmessage = (e: MessageEvent<Float32Array>) => {
        const block = e.data
        for (let i = 0; i < block.length; i++) {
          ring[write] = block[i]
          write = (write + 1) % size
        }
        filled = Math.min(size, filled + block.length)
        sinceHop += block.length
        if (sinceHop < hop || filled < size) return
        sinceHop = 0

        //unroll ring into chronological order
        const win = new Float32Array(size)
        win.set(ring.subarray(write), 0)
        win.set(ring.subarray(0, write), size - write)

        //noise floor = quietest hop in the last FLOOR_SEC, capped so a song that
        //never pauses can't drag the floor up to the music's own level
        const r = rmsOf(win.subarray(size - hop))
        recent.push(r)
        if (recent.length > floorHops) recent.shift()
        const floor = Math.min(FLOOR_CAP, ...recent)
        const open = rmsOf(win) > Math.max(ABS_FLOOR, floor * gate)
        setLevel({ db: 20 * Math.log10(Math.max(r, 1e-6)), open })
        if (!open) return

        let peak = 0
        for (let i = 0; i < size; i++) peak = Math.max(peak, Math.abs(win[i]))
        const g = Math.min(MAX_GAIN, TARGET_PEAK / Math.max(peak, 1e-6))
        if (g > 1) for (let i = 0; i < size; i++) win[i] *= g
        onChunkRef.current(encodeWav(win, ctx.sampleRate))
      }

      setAnalyser(an)
      setListening(true)
    } catch (err) {
      setError(describe(err))
      stop()
    }
  }, [windowSec, hopSec, stop])

  useEffect(() => stop, [stop])

  return { listening, error, analyser, level, start, stop }
}
