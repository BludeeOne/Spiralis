//pitchMath.ts
// Authro: Erik FLores-Siemsen
// Description: pure signal processing helper for live pitch detection, doesnt connect to react 
//mostly for demo practice

export interface NoteReading {
    frequency: number;
    name: string;
    octave: number;
    cents: number;      //incase a note isnt exactly at teh frequency, slight deivation check

}

const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

export function frequencyToNote(freq: number): NoteReading {
    const noteNum = 12 * Math.log2(freq / 440) + 69; // MIDI note number, A4 = 69
    const rounded = Math.round(noteNum);
    const cents = (noteNum - rounded) * 100;
    const name = NOTE_NAMES[((rounded % 12) + 12) % 12];
    const octave = Math.floor(rounded / 12) - 1;
    return { frequency: freq, name, octave, cents };
  }

  export interface DetectPitchOptions {
    minFreq?: number;       //hz lower bound of the search range
    maxFreq?: number;       //hz upper bound 
    minRms?: number;    
    minConfidence?: number; 
  }


/* Autocorrelation pitch detection over a time domain buffer.
 * Returns the estimated fundamental frequency in Hz, or null if the signal
 * is too quiet or no confident periodicity was found like a chord or noise
 * Monophonic only feed it one note/string at a time(for now)
 */

export function detectPitch(
    buffer: Float32Array,
    sampleRate: number,
    opts: DetectPitchOptions = {}
  ): number | null {
    const { minFreq = 60, maxFreq = 1200, minRms = 0.012, minConfidence = 0.35 } = opts;
    const SIZE = buffer.length;
   
    let energy = 0;
    for (let i = 0; i < SIZE; i++) energy += buffer[i] * buffer[i];
    const rms = Math.sqrt(energy / SIZE);
    if (rms < minRms || energy === 0) return null;
   
    const maxLag = Math.min(Math.floor(sampleRate / minFreq), SIZE - 1);
    const minLag = Math.max(Math.floor(sampleRate / maxFreq), 2);
   
    const corrAt = (lag: number): number => {
      let c = 0;
      const n = SIZE - lag;
      for (let i = 0; i < n; i++) c += buffer[i] * buffer[i + lag];
      return c / n;
    };
   
    let bestLag = -1;
    let bestCorr = 0;
    for (let lag = minLag; lag <= maxLag; lag++) {
      const corr = corrAt(lag);
      if (corr > bestCorr) {
        bestCorr = corr;
        bestLag = lag;
      }
    }
    if (bestLag <= 0) return null;
   
    const confidence = bestCorr / (energy / SIZE);
    if (confidence < minConfidence) return null;
   
    // Parabolic interpolation around the best lag for sub-sample accuracy
    const y0 = corrAt(Math.max(bestLag - 1, minLag));
    const y1 = bestCorr;
    const y2 = corrAt(Math.min(bestLag + 1, maxLag));
    const denom = y0 - 2 * y1 + y2;
    const shift = denom !== 0 ? (0.5 * (y0 - y2)) / denom : 0;
    const refinedLag = bestLag + shift;
   
    return sampleRate / refinedLag;
  }