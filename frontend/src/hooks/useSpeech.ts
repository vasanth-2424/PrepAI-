import { useCallback, useEffect, useRef, useState } from 'react';

interface SpeechRecognitionEvent {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: {
      isFinal: boolean;
      [index: number]: {
        transcript: string;
        confidence: number;
      };
    };
  };
}

interface SpeechRecognitionErrorEvent {
  error: string;
  message?: string;
}

interface SpeechRecognitionInstance {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onstart: (() => void) | null;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
}

declare global {
  interface Window {
    SpeechRecognition?: new () => SpeechRecognitionInstance;
    webkitSpeechRecognition?: new () => SpeechRecognitionInstance;
  }
}

export function useSpeech() {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [sttError, setSttError] = useState<string | null>(null);

  // Check support
  const isTTSSupported = typeof window !== 'undefined' && 'speechSynthesis' in window;
  const isSTTSupported =
    typeof window !== 'undefined' &&
    Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const onTranscriptRef = useRef<((text: string) => void) | null>(null);

  // ---------------------------------------------------------------------------
  // Text-To-Speech (TTS)
  // ---------------------------------------------------------------------------

  const stopSpeaking = useCallback(() => {
    if (isTTSSupported && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setIsSpeaking(false);
  }, [isTTSSupported]);

  const speak = useCallback(
    (text: string, onEnd?: () => void) => {
      if (!isTTSSupported) {
        onEnd?.();
        return;
      }

      stopSpeaking();

      const utterance = new SpeechSynthesisUtterance(text);
      utteranceRef.current = utterance;
      utterance.lang = 'en-US';
      utterance.rate = 0.95; // Slightly slower for clear interview questions

      // Pick a clean voice if available
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        const voices = window.speechSynthesis.getVoices();
        const preferredVoice = voices.find(
          (v) =>
            v.lang.startsWith('en') &&
            (v.name.includes('Google') ||
              v.name.includes('Natural') ||
              v.name.includes('Samantha') ||
              v.name.includes('Daniel') ||
              v.name.includes('Karen'))
        );
        if (preferredVoice) {
          utterance.voice = preferredVoice;
        }
      }

      utterance.onstart = () => {
        setIsSpeaking(true);
      };

      utterance.onend = () => {
        setIsSpeaking(false);
        onEnd?.();
      };

      utterance.onerror = (e) => {
        console.warn('SpeechSynthesis error:', e);
        setIsSpeaking(false);
        onEnd?.();
      };

      window.speechSynthesis.speak(utterance);
    },
    [isTTSSupported, stopSpeaking]
  );

  // ---------------------------------------------------------------------------
  // Speech-To-Text (STT)
  // ---------------------------------------------------------------------------

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // Ignored if already stopped
      }
      recognitionRef.current = null;
    }
    setIsListening(false);
  }, []);

  const startListening = useCallback(
    (onTranscript: (text: string) => void) => {
      if (!isSTTSupported) {
        setSttError('Speech recognition is not supported in this browser.');
        return;
      }

      // Stop any existing speaking or listening
      stopSpeaking();
      stopListening();
      setSttError(null);

      onTranscriptRef.current = onTranscript;

      const SpeechRecognitionClass =
        window.SpeechRecognition || window.webkitSpeechRecognition;

      if (!SpeechRecognitionClass) {
        setSttError('Speech recognition unavailable.');
        return;
      }

      const recognition = new SpeechRecognitionClass();
      recognitionRef.current = recognition;

      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      let accumulatedFinal = '';

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        let interimText = '';
        let currentFinal = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcriptChunk = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            currentFinal += transcriptChunk + ' ';
          } else {
            interimText += transcriptChunk;
          }
        }

        if (currentFinal) {
          accumulatedFinal += currentFinal;
        }

        const fullText = (accumulatedFinal + interimText).trim();
        onTranscriptRef.current?.(fullText);
      };

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        console.warn('SpeechRecognition error:', event.error);
        setIsListening(false);

        if (event.error === 'not-allowed') {
          setSttError(
            'Microphone access was denied. Please allow microphone permissions or type your answer.'
          );
        } else if (event.error === 'no-speech') {
          // Ignored (user just didn't speak yet)
        } else if (event.error === 'network') {
          setSttError(
            'Network error during speech recognition. You can type your answer instead.'
          );
        } else {
          setSttError(`Speech recognition error: ${event.error}`);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      try {
        recognition.start();
      } catch (err) {
        console.warn('Failed to start recognition:', err);
        setSttError('Could not start microphone.');
        setIsListening(false);
      }
    },
    [isSTTSupported, stopSpeaking, stopListening]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopSpeaking();
      stopListening();
    };
  }, [stopSpeaking, stopListening]);

  return {
    isTTSSupported,
    isSTTSupported,
    isSpeaking,
    isListening,
    sttError,
    speak,
    stopSpeaking,
    startListening,
    stopListening,
    setSttError,
  };
}
