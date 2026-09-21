//usePitchDetector.ts
//works the mic stream audio context and detection loop
//everything here works in browser and doesnt connect to backend
//attempting to replace a websocket round trip fo rsingle note detectioin. 
//Reduce input time

import { useCallback, useEffect, useRef, useState } from 'react';
import { detectPitch, frequencyToNote, NoteReading } from '../lib/pitchMath';
 
interface UsePitchDetectorResult {
  reading: NoteReading | null;
  isListening: boolean;
  error: string | null;
  start: () => Promise<void>;
  stop: () => void;
}

interface UsePitchDetectorResult {
    reading: NoteReading | null;
    isListening: boolean;
    error: string | null;
    start: () => Promise<void>;
    stop: () => void;
  }
   
  export function usePitchDetector(): UsePitchDetectorResult {
    const [reading, setReading] = useState<NoteReading | null>(null);
    const [isListening, setIsListening] = useState(false);
    const [error, setError] = useState<string | null>(null);
   
    const audioCtxRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const rafRef = useRef<number | null>(null);
   
    const loop = useCallback(() => {
      const analyser = analyserRef.current;
      const audioCtx = audioCtxRef.current;
      if (!analyser || !audioCtx) return;
   
      const buf = new Float32Array(analyser.fftSize);
      analyser.getFloatTimeDomainData(buf);
      const freq = detectPitch(buf, audioCtx.sampleRate);
      setReading(freq ? frequencyToNote(freq) : null);
   
      rafRef.current = requestAnimationFrame(loop);
    }, []);
   
    const start = useCallback(async () => {
      setError(null);
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false },
        });
        const AudioCtxClass = window.AudioContext || (window as any).webkitAudioContext;
        const audioCtx: AudioContext = new AudioCtxClass();
        const source = audioCtx.createMediaStreamSource(stream);
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 2048;
        source.connect(analyser);
   
        streamRef.current = stream;
        audioCtxRef.current = audioCtx;
        sourceRef.current = source;
        analyserRef.current = analyser;
   
        setIsListening(true);
        rafRef.current = requestAnimationFrame(loop);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Microphone access failed');
      }
    }, [loop]);
   
    const stop = useCallback(() => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      sourceRef.current?.disconnect();
      streamRef.current?.getTracks().forEach((t) => t.stop());
      audioCtxRef.current?.close();
   
      rafRef.current = null;
      sourceRef.current = null;
      streamRef.current = null;
      audioCtxRef.current = null;
      analyserRef.current = null;
   
      setIsListening(false);
      setReading(null);
    }, []);
   
    //release the mic if the component unmounts while still listening
    useEffect(() => stop, [stop]);
   
    return { reading, isListening, error, start, stop };
  }