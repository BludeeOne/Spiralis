//livePanel.tsx
// Presentational only — takes a reading and renders it. No mic/audio logic
// here, so it can be reused (e.g. later fed by the websocket path instead).

import { NoteReading } from '../lib/pitchMath';
import './livePanel.css';


interface LivePanelProps {
  reading: NoteReading | null;
  isListening: boolean;
}

const ARC_LEN = 408.4; //path length of the gauge arc

function needleOffset(cents: number): number {
  const clamped = Math.max(-50, Math.min(50, cents));
  const fraction = (clamped + 50) / 100;
  return ARC_LEN - fraction * ARC_LEN;
}

function tuningClass(cents: number): string {
  if (cents > 8) return 'sharp';
  if (cents < -8) return 'flat';
  return 'in-tune';
}

export default function LivePanel({ reading, isListening }: LivePanelProps) {
  const cls = reading ? tuningClass(reading.cents) : '';
  const centsRounded = reading ? Math.round(reading.cents) : 0;

  return (
    <div className="live-panel">
      <div className="gauge-wrap">
        <svg className="gauge" viewBox="0 0 320 190">
          <path className="gauge-track" d="M 30 170 A 130 130 0 0 1 290 170" />
          <line className="gauge-tick" x1="160" y1="42" x2="160" y2="58" />
          <line className="gauge-tick" x1="41" y1="170" x2="55" y2="160" />
          <line className="gauge-tick" x1="279" y1="170" x2="265" y2="160" />
          <path
            className={`gauge-needle ${cls}`}
            d="M 30 170 A 130 130 0 0 1 290 170"
            strokeDasharray={ARC_LEN}
            strokeDashoffset={needleOffset(reading?.cents ?? 0)}
          />
        </svg>
        <div className="stage">
          <div className={`note ${cls}`}>
            {reading ? `${reading.name}${reading.octave}` : '–'}
          </div>
          <div className="freq">{reading ? `${reading.frequency.toFixed(1)} Hz` : '\u00A0'}</div>
        </div>
      </div>
      <div className="cents">
        {reading
          ? `${centsRounded > 0 ? '+' : ''}${centsRounded} cents`
          : isListening
            ? 'Play a note'
            : '\u00A0'}
      </div>
    </div>
  );
}
