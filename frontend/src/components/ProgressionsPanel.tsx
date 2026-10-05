import type { Numbered } from '../types'
import { Panel, Pending } from './Panel'

export function ProgressionPanel({ progression, pending }: { progression: Numbered[]; pending: boolean }) {
  const recent = progression.slice(-4)
  const hasNumerals = recent.some((p) => p.numeral)
  return (
    <Panel title="Progression" area="prog">
      {!recent.length ? (
        <p className="empty">Builds as you change chords</p>
      ) : hasNumerals ? (
        <ol className="numerals">
          {recent.map((p, i) => <li key={i} title={p.name}>{p.numeral ?? '?'}</li>)}
        </ol>
      ) : pending ? <Pending fn="roman_numeral" /> : null}
    </Panel>
  )
}
