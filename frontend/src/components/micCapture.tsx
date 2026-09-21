// micCapture.tsx
// Container: owns the pitch-detection session and renders the mic control
// plus the LivePanel display. Drop <MicCapture /> anywhere in App.tsx.

import { usePitchDetector } from '../hooks/usePitchDetector';
import LivePanel from './livePanel';

export default function MicCapture() {
  const { reading, isListening, error, start, stop } = usePitchDetector();

  return (
    <div className="mic-capture">
      <LivePanel reading={reading} isListening={isListening} />
      <button onClick={isListening ? stop : start}>
        {isListening ? 'Stop listening' : 'Start listening'}
      </button>
      {error && <p className="mic-error">Mic access failed: {error}</p>}
    </div>
  );
}
