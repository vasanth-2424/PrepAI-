import type { AnalysisStep } from '../../types';

const STEPS: { key: AnalysisStep; label: string }[] = [
  { key: 'upload', label: 'Extracting PDF text' },
  { key: 'analyze', label: 'Analyzing resume' },
  { key: 'generate', label: 'Generating questions' },
];

interface LoadingProgressProps {
  currentStep: AnalysisStep;
}

export function LoadingProgress({ currentStep }: LoadingProgressProps) {
  const currentIndex = STEPS.findIndex((s) => s.key === currentStep);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent" />
        <p className="text-white">Processing your resume...</p>
      </div>

      <div className="space-y-3">
        {STEPS.map((step, index) => {
          const isActive = index === currentIndex;
          const isComplete = index < currentIndex;

          return (
            <div
              key={step.key}
              className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm ${
                isActive
                  ? 'border border-indigo-500/40 bg-indigo-500/10 text-indigo-200'
                  : isComplete
                    ? 'text-emerald-400'
                    : 'text-slate-500'
              }`}
            >
              <span>{isComplete ? '✓' : isActive ? '●' : '○'}</span>
              <span>{step.label}</span>
            </div>
          );
        })}
      </div>

      <div className="animate-pulse space-y-3">
        <div className="h-4 w-3/4 rounded bg-slate-800" />
        <div className="h-4 w-full rounded bg-slate-800" />
        <div className="h-4 w-5/6 rounded bg-slate-800" />
        <div className="h-24 w-full rounded-xl bg-slate-800/80" />
      </div>
    </div>
  );
}
