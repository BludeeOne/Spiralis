import { useEffect, useRef, useState } from 'react'
import { freqToNote, SHARPS, yin, type NoteReading } from '../audio/pitch'
import { Panel } from './Panel'

const STANDARD = [
  { label: 'E2', midi: 40 }, { label: 'A2', midi: 45 }, { label: 'D3', midi: 50 },
  { label: 'G3', midi: 55 }, { label: 'B3', midi: 59 }, { label: 'E4', midi: 64 },
]
const HOLD_MS = 500 // keep the last reading briefly so the needle doesn't flicker between plucks

export function Tuner({ analyser }: { analyser: AnalyserNode | null }) {
  const [reading, setReading] = useState<NoteReading | null>(null)
  const lastSeen = useRef(0)

  useEffect(() => {
    if (!analyser) { setReading(null); return }
    const buf = new Float32Array(analyser.fftSize)
    const sr = analyser.context.sampleRate
    const id = setInterval(() => {
      analyser.getFloatTimeDomainData(buf)
      const hz = yin(buf, sr)
      const now = performance.now()
      if (hz && hz > 60 && hz < 1200) { lastSeen.current = now; setReading(freqToNote(hz)) }
      else if (now - lastSeen.current > HOLD_MS) setReading(null)
    }, 60)
    return () => clearInterval(id)
  }, [analyser])

  const strip = reading ? [-2, -1, 0, 1, 2].map((d) => SHARPS[(((reading.midi + d) % 12) + 12) % 12]) : ['–', '–', '–', '–', '–']
  const inTune = reading && Math.abs(reading.cents) <= 5
  const nearest = reading ? STANDARD.reduce((a, b) => (Math.abs(b.midi - reading.midi) < Math.abs(a.midi - reading.midi) ? b : a)) : null
  // each cell is 20% wide; ±50 cents spans half a cell either side of center
  const needle = 50 + (reading ? reading.cents / 100 : 0) * 20

  return (
    <Panel title="Tuner" area="tuner">
      <p className="sub">Standard tuning, EADGBE</p>
      <div className={`strip ${inTune ? 'in-tune' : ''} ${reading ? '' : 'idle'}`} role="meter"
        aria-valuemin={-50} aria-valuemax={50} aria-valuenow={reading?.cents ?? 0}
        aria-label={reading ? `${reading.name}${reading.octave}, ${reading.cents} cents` : 'No note'}>
        {strip.map((n, i) => <span key={i} className={i === 2 ? 'center' : ''}>{n}</span>)}
        {reading && <i className="needle" style={{ left: `${needle}%` }} />}
      </div>
      <p className="tuner-read">
        {reading
          ? <>{reading.hz.toFixed(1)} Hz · {reading.cents > 0 ? '+' : ''}{reading.cents}¢ · nearest string {nearest?.label}</>
          : 'Pluck one string'}
      </p>
    </Panel>
  )
}
