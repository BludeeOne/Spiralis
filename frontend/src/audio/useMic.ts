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

// calculates the root mean square of an audio buffer
const rmsOf = (x: Float32Array) => {
  let sum = 0

  for (let i = 0; i < x.length; i++) {
    sum += x[i] * x[i]
  }

  return Math.sqrt(sum / x.length)
}

// opens the mic and sends audio windows to the tuner
export function useMic(
  onChunk: (wav: Blob) => void,
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

      // keeps recent audio levels to estimate background noise
      const recent: number[] = []
      const floorHops = Math.ceil(FLOOR_SEC / hopSec)
      const gate = Math.pow(10, GATE_DB / 20)

      tap.port.onmessage = (e: MessageEvent<Float32Array>) => {
        const block = e.data

        // writes new samples into the ring buffer
        for (let i = 0; i < block.length; i++) {
          ring[write] = block[i]
          write = (write + 1) % size
        }

        filled = Math.min(size, filled + block.length)
        sinceHop += block.length

        if (sinceHop < hop || filled < size) return

        sinceHop = 0

        // puts the samples in chronological order
        const win = new Float32Array(size)
        win.set(ring.subarray(write), 0)
        win.set(ring.subarray(0, write), size - write)

        // estimates the noise floor using the quietest recent audio
        const r = rmsOf(win.subarray(size - hop))

        recent.push(r)
        if (recent.length > floorHops) recent.shift()

        const floor = Math.min(FLOOR_CAP, ...recent)
        const open = rmsOf(win) > Math.max(ABS_FLOOR, floor * gate)

        setLevel({
          db: 20 * Math.log10(Math.max(r, 1e-6)),
          open,
        })

        if (!open) return

        // finds the loudest sample and calculates the needed gain
        let peak = 0

        for (let i = 0; i < size; i++) {
          peak = Math.max(peak, Math.abs(win[i]))
        }

        const gain = Math.min(
          MAX_GAIN,
          TARGET_PEAK / Math.max(peak, 1e-6)
        )

        // boosts quiet audio without exceeding the gain limit
        if (gain > 1) {
          for (let i = 0; i < size; i++) {
            win[i] *= gain
          }
        }

        // encodes the audio window and sends it to the callback
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
