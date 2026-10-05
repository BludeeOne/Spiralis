import { useCallback, useEffect, useRef, useState } from 'react'
import { encodeWav } from './wav'

// Worklet that copies raw mic frames back to the main thread.
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

/** Opens the mic, exposes an AnalyserNode for the tuner, and emits WAV chunks every `chunkSec`. */
export function useMic(onChunk: (wav: Blob) => void, chunkSec = 2) {
  const [listening, setListening] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null)
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
  }, [])

  const start = useCallback(async () => {
    setError(null)
    try {
      // Voice processing off: it mangles sustained guitar notes.
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

      let parts: Float32Array[] = []
      let len = 0
      const target = Math.round(ctx.sampleRate * chunkSec)
      tap.port.onmessage = (e: MessageEvent<Float32Array>) => {
        parts.push(e.data)
        len += e.data.length
        if (len < target) return
        const all = new Float32Array(len)
        let o = 0
        for (const p of parts) { all.set(p, o); o += p.length }
        parts = []
        len = 0
        onChunkRef.current(encodeWav(all, ctx.sampleRate))
      }

      setAnalyser(an)
      setListening(true)
    } catch (err) {
      setError(describe(err))
      stop()
    }
  }, [chunkSec, stop])

  useEffect(() => stop, [stop])

  return { listening, error, analyser, start, stop }
}
