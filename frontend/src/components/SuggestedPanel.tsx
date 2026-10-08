/** SuggestedPanel.tsx — next-chord suggestions from progressions.py */

import type { Numbered } from '../types'
import { Panel, Pending } from './Panel'

export function SuggestedPanel({ suggestions, pending }: { suggestions: Numbered[]; pending: boolean }) {
  return (
    <Panel title="Try next" area="suggest">
      {suggestions.length ? (
        <ul className="suggestions">
          {suggestions.map((s) => (
            <li key={s.name}><span className="s-name">{s.name}</span><span className="s-num">{s.numeral}</span></li>
          ))}
        </ul>
      ) : pending ? <Pending fn="suggest_next" /> : <p className="empty">Suggestions follow the key</p>}
    </Panel>
  )
}
