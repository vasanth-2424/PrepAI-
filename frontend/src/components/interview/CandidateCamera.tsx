import { useEffect, useRef, useState } from 'react';

interface CandidateCameraProps {
  isListening: boolean;
  isSubmitting: boolean;
  elapsedSeconds: number;
}

export function CandidateCamera({
  isListening,
  isSubmitting,
  elapsedSeconds,
}: CandidateCameraProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [hasCameraPermission, setHasCameraPermission] = useState<boolean | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);

  useEffect(() => {
    let stream: MediaStream | null = null;

    async function setupCamera() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 640 }, height: { ideal: 480 } },
          audio: false, // Audio handled by Web Speech API
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setHasCameraPermission(true);
        setCameraError(null);
      } catch (err) {
        console.warn('Webcam permission denied or unavailable:', err);
        setHasCameraPermission(false);
        setCameraError('Webcam unavailable. Interview continues in text/voice mode.');
      }
    }

    setupCamera();

    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const formatTimer = (totalSec: number) => {
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="relative flex flex-col overflow-hidden rounded-xl border border-slate-800 bg-slate-950 p-3">
      {/* Top Overlay Badges */}
      <div className="absolute top-5 left-5 z-10 flex flex-wrap items-center gap-2">
        {/* Camera Status */}
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold backdrop-blur-md ${
            hasCameraPermission
              ? 'border border-emerald-500/40 bg-emerald-950/80 text-emerald-300'
              : 'border border-amber-500/40 bg-amber-950/80 text-amber-300'
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              hasCameraPermission ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
            }`}
          />
          {hasCameraPermission ? 'Camera Active' : 'Camera Off'}
        </span>

        {/* Mic Status */}
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold backdrop-blur-md ${
            isListening
              ? 'border border-red-500/40 bg-red-950/80 text-red-300'
              : isSubmitting
              ? 'border border-amber-500/40 bg-amber-950/80 text-amber-300'
              : 'border border-slate-700 bg-slate-900/80 text-slate-400'
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              isListening
                ? 'bg-red-400 animate-ping'
                : isSubmitting
                ? 'bg-amber-400 animate-spin'
                : 'bg-slate-500'
            }`}
          />
          {isListening ? 'Mic Listening' : isSubmitting ? 'Evaluating' : 'Mic Muted'}
        </span>
      </div>

      {/* Timer Badge Top Right */}
      <div className="absolute top-5 right-5 z-10 rounded-full border border-slate-800 bg-slate-900/80 px-3 py-1 text-xs font-mono text-slate-300 backdrop-blur-md">
        ⏱️ {formatTimer(elapsedSeconds)}
      </div>

      {/* Camera Video Stream Frame */}
      <div className="relative flex aspect-video w-full items-center justify-center overflow-hidden rounded-lg bg-slate-900 border border-slate-800">
        {hasCameraPermission === true ? (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="h-full w-full object-cover transform -scale-x-100"
          />
        ) : (
          <div className="flex flex-col items-center justify-center p-6 text-center">
            <div className="mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-slate-800 text-slate-400">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="h-8 w-8"
              >
                <path d="M4.5 4.5a3 3 0 0 0-3 3v9a3 3 0 0 0 3 3h15a3 3 0 0 0 3-3v-9a3 3 0 0 0-3-3h-15ZM3 7.5a1.5 1.5 0 0 1 1.5-1.5h15A1.5 1.5 0 0 1 21 7.5v9a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 16.5v-9Z" />
              </svg>
            </div>
            <p className="text-sm font-semibold text-slate-200">Candidate Preview</p>
            <p className="mt-1 text-xs text-slate-400">
              {cameraError || 'Requesting camera permissions…'}
            </p>
          </div>
        )}

        {/* Candidate Speaking Overlay Bar */}
        {isListening && (
          <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between rounded-lg border border-emerald-500/30 bg-emerald-950/90 px-3 py-1.5 text-xs text-emerald-200 backdrop-blur-md">
            <span className="flex items-center gap-2">
              <span className="h-2 w-2 animate-ping rounded-full bg-emerald-400" />
              Candidate Speaking…
            </span>
            <span className="text-[10px] font-mono text-emerald-400">LIVE AUDIO CAPTURE</span>
          </div>
        )}
      </div>
    </div>
  );
}
