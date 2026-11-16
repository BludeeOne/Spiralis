/* Fretboard.tsx - shows the user different fingerings of their scales*/

 
import { Panel } from './Panel'
import type { ScaleResponse } from "../types"

export function Fretboard({ data }: { data: ScaleResponse }) {
    return (
        <Panel title="Fretboard" area="fretboard" >
            <svg viewBox="0 0 600 160" className="fretboard">
                {data.strings.map((s) => ( 
                    <line 
                    key={s.string}
                    x1={0}
                    x2={600}
                    y1={20 + s.string * 24}
                    y2={20 + s.string * 24}
                    stroke="currentColor"
                    />
                ))}
            </svg>
        </Panel>
    )
}
       