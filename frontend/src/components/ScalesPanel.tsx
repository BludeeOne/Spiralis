/** ScalesPanel.tsx — every scale that contains the notes played */

import { Panel, Pending } from './Panel'

export function ScalesPanel({ scales, pending }: { scales: string[]; pending: boolean }) {
  return (
    <Panel title="Scales that fit" area="scales">
      {scales.length ? (
        <ul className="scales">{scales.map((s) => <li key={s}>{s}</li>)}</ul>
      ) : pending ? <Pending fn="fitting_scales" /> : <p className="empty">Appears once a key is found</p>}
    </Panel>
  )
}
