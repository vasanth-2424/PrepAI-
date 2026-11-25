import { useEffect, useState } from 'react';

interface AiAvatarProps {
  isSpeaking: boolean;
  isListening: boolean;
  isEvaluating: boolean;
  questionText: string;
  questionIndex: number;
  totalQuestions: number;
  onReplayAudio: () => void;
  isTTSSupported: boolean;
}

/**
 * Modular AI Interviewer Avatar Component.
 * Designed to cleanly wrap custom avatar video providers (HeyGen, Tavus, D-ID)
 * while providing an executive studio interview appearance natively.
 */
export function AiAvatar({
  isSpeaking,
  isListening,
  isEvaluating,
  questionText,
  questionIndex,
  totalQuestions,
  onReplayAudio,
  isTTSSupported,
}: AiAvatarProps) {
  // Wave bar animation frame generator
  const [waveHeights, setWaveHeights] = useState([30, 60, 40, 80, 50, 70, 45]);

  useEffect(() => {
    if (!isSpeaking && !isListening) return;
    const interval = setInterval(() => {
      setWaveHeights(
        Array.from({ length: 7 }, () => Math.floor(Math.random() * 60) + 20)
      );
    }, 150);
    return () => clearInterval(interval);
  }, [isSpeaking, isListening]);

  return (
    <div className="flex h-full flex-col justify-between rounded-2xl border border-slate-800 bg-slate-900/90 p-5 shadow-2xl backdrop-blur-md">
      {/* Top Header & Status */}
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="relative flex h-3 w-3">
            <span
              className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${
                isSpeaking
                  ? 'bg-indigo-400'
                  : isListening
                  ? 'bg-emerald-400'
                  : isEvaluating
                  ? 'bg-amber-400'
                  : 'bg-slate-500'
              }`}
            />
            <span
              className={`relative inline-flex h-3 w-3 rounded-full ${
                isSpeaking
                  ? 'bg-indigo-500'
                  : isListening
                  ? 'bg-emerald-500'
                  : isEvaluating
                  ? 'bg-amber-500'
                  : 'bg-slate-400'
              }`}
            />
          </div>
          <span className="text-xs font-bold uppercase tracking-wider text-white">
            AI Interviewer
          </span>
        </div>

        {/* Dynamic Status Badge */}
        <div className="flex items-center gap-2">
          {isSpeaking && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-500/40 bg-indigo-500/10 px-3 py-1 text-xs font-medium text-indigo-300">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-400" />
              Speaking…
            </span>
          )}
          {isListening && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-300">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
              Listening…
            </span>
          )}
          {isEvaluating && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-300">
              <span className="h-1.5 w-1.5 animate-spin rounded-full border border-amber-400 border-t-transparent" />
              Evaluating Answer…
            </span>
          )}
          {!isSpeaking && !isListening && !isEvaluating && (
            <span className="rounded-full border border-slate-700 bg-slate-800/60 px-3 py-1 text-xs text-slate-400">
              Ready
            </span>
          )}
        </div>
      </div>

      {/* Main Studio Avatar Feed Container */}
      <div className="relative my-4 flex flex-1 flex-col items-center justify-center overflow-hidden rounded-xl border border-slate-800 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 p-6 min-h-[260px]">
        {/* Ambient Studio Background Lighting Grid */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-indigo-900/20 via-slate-950/80 to-slate-950 opacity-70" />

        {/* AI Interviewer Avatar Portrait Visual */}
        <div className="relative z-10 flex flex-col items-center">
          <div
            className={`relative flex h-32 w-32 items-center justify-center rounded-full border-2 transition-all duration-300 ${
              isSpeaking
                ? 'border-indigo-500 shadow-lg shadow-indigo-500/30 scale-105'
                : isListening
                ? 'border-emerald-500/70 shadow-md shadow-emerald-500/20'
                : 'border-slate-700 bg-slate-900'
            }`}
          >
            {/* Professional Interviewer Avatar Graphic */}
            <div className="flex h-28 w-28 items-center justify-center rounded-full bg-gradient-to-tr from-slate-900 via-indigo-950 to-slate-800 text-slate-200">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="h-16 w-16 text-indigo-300/90"
              >
                <path fillRule="evenodd" d="M7.5 6a4.5 4.5 0 1 1 9 0 4.5 4.5 0 0 1-9 0ZM3.751 20.105a8.25 8.25 0 0 1 16.498 0 .75.75 0 0 1-.437.695A18.683 18.683 0 0 1 12 22.5c-2.786 0-5.433-.6-7.812-1.7a.75.75 0 0 1-.437-.695Z" clipRule="evenodd" />
              </svg>
            </div>

            {/* Speaking Audio Wave Visualizer */}
            {(isSpeaking || isListening) && (
              <div className="absolute -bottom-2 flex items-end gap-1 rounded-full border border-slate-800 bg-slate-950 px-3 py-1 shadow-md">
                {waveHeights.map((h, idx) => (
                  <span
                    key={idx}
                    className={`w-1 rounded-full transition-all duration-150 ${
                      isSpeaking ? 'bg-indigo-400' : 'bg-emerald-400'
                    }`}
                    style={{ height: `${h}%`, minHeight: '6px' }}
                  />
                ))}
              </div>
            )}
          </div>

          <p className="mt-4 font-semibold text-white tracking-wide">AI Senior Technical Recruiter</p>
          <p className="text-xs text-slate-400">PrepAI Virtual Interview Room</p>
        </div>
      </div>

      {/* Question Card Display */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
        <div className="mb-2 flex items-center justify-between text-xs text-slate-400">
          <span className="font-semibold text-indigo-400">
            Question {questionIndex + 1} of {totalQuestions}
          </span>
          {isTTSSupported && (
            <button
              type="button"
              onClick={onReplayAudio}
              className="flex items-center gap-1 text-slate-400 hover:text-white transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5">
                <path d="M10 3.75a.75.75 0 0 0-1.264-.546L4.703 7H3.167A1.667 1.667 0 0 0 1.5 8.667v2.666C1.5 12.247 2.247 13 3.167 13h1.536l4.033 3.796A.75.75 0 0 0 10 16.25V3.75Z" />
                <path d="M13.854 6.146a.75.75 0 0 0-1.061 1.06 3.5 3.5 0 0 1 0 4.948.75.75 0 0 0 1.06 1.061 5 5 0 0 0 0-7.069Z" />
              </svg>
              <span>Replay Audio</span>
            </button>
          )}
        </div>
        <p className="text-base font-semibold leading-relaxed text-white">
          {questionText}
        </p>
      </div>
    </div>
  );
}
