/** KeyPanel.tsx — detected key and its relative major/minor */

import type { KeyInfo } from '../types'
import { Panel, Pending } from './Panel'

export function KeyPanel({ keyInfo, pending }: { keyInfo: KeyInfo | null; pending: boolean }) {
  return (
    <Panel title="Key" area="key">
      {keyInfo ? (
        <>
          <p className="key-name">{keyInfo.name}</p>
          {keyInfo.relative && <p className="sub">Relative {keyInfo.relative}</p>}
        </>
      ) : pending ? <Pending fn="estimate_key" /> : <p className="empty">Play a few chords to find the key</p>}
    </Panel>
  )
}
