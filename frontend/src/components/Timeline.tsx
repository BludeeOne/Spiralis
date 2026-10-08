/** Timeline.tsx — chord history over time */

import type { HistoryItem } from '../types'

interface Props {
  history: HistoryItem[]
  selected: number | null
  onSelect: (i: number | null) => void
  listening: boolean
  onToggle: () => void
  bpm: number | null
}

export function Timeline({ history, selected, onSelect, listening, onToggle, bpm }: Props) {
  const last = history.length - 1
  const prev = () => onSelect(selected === null ? (last >= 0 ? last : null) : Math.max(0, selected - 1))
  const next = () => onSelect(selected === null || selected >= last ? null : selected + 1)

  return (
    <section className="timeline" style={{ gridArea: 'timeline' }} aria-label="Previously played">
      <div className="transport">
        <button onClick={prev} disabled={!history.length} aria-label="Step back through history">⏮</button>
        <button className="play" onClick={onToggle} aria-label={listening ? 'Stop listening' : 'Start listening'}>
          {listening ? '■' : '▶'}
        </button>
        <button onClick={next} disabled={selected === null} aria-label="Step forward, back to live">⏭</button>
        <span className="bpm">{bpm ? `${Math.round(bpm)} BPM` : '— BPM'}</span>
      </div>
      <ol className="chips">
        {history.length === 0 && <li className="empty">Chords you play land here</li>}
        {history.map((h, i) => (
          <li key={i}>
            <button className={i === selected ? 'chip selected' : 'chip'} onClick={() => onSelect(i === selected ? null : i)}>
              {h.name}
            </button>
          </li>
        ))}
      </ol>
    </section>
  )
}
