import type { ChordInfo, HistoryItem } from '../types'
import { Panel, Pending } from './Panel'

interface Props {
  live: ChordInfo | null
  notes: string[]
  selected: HistoryItem | null
  listening: boolean
  pending: boolean
}

export function ChordPanel({ live, notes, selected, listening, pending }: Props) {
  const name = selected?.name ?? live?.name
  return (
    <Panel title={selected ? 'Chord from history' : 'Note / chord'} area="chord" className="chord-panel">
      {name ? (
        <p className="chord-name" key={name}>{name}</p>
      ) : pending && notes.length ? (
        <Pending fn="identify_chord" />
      ) : (
        <p className="empty">{listening ? 'Listening…' : 'Press play and strum'}</p>
      )}
      {!selected && notes.length > 0 && <p className="notes">{notes.join('  ')}</p>}
    </Panel>
  )
}
