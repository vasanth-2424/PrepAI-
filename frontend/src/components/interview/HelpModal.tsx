import { useState } from 'react';

import type { HelpType } from '../../types';

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRequestHelp: (helpType: HelpType) => Promise<string>;
  usedHelpTypes: HelpType[];
}

const HELP_OPTIONS: {
  type: HelpType;
  title: string;
  description: string;
  icon: string;
  penalty: string;
  color: string;
}[] = [
  {
    type: 'small_hint',
    title: 'Small Hint',
    description: 'Get a subtle nudge in the right direction without spoiling the answer.',
    icon: '💡',
    penalty: '-0.5 pts',
    color: 'border-amber-500/30 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20',
  },
  {
    type: 'explain_concept',
    title: 'Explain Concept',
    description: 'Get a concise explanation of the core technical concept or terminology.',
    icon: '📖',
    penalty: '-1.0 pt',
    color: 'border-blue-500/30 bg-blue-500/10 text-blue-300 hover:bg-blue-500/20',
  },
  {
    type: 'show_approach',
    title: 'Show Approach',
    description: 'Learn how to structure your response using a proven framework.',
    icon: '📐',
    penalty: '-1.5 pts',
    color: 'border-violet-500/30 bg-violet-500/10 text-violet-300 hover:bg-violet-500/20',
  },
  {
    type: 'suggested_answer',
    title: 'Suggested Answer',
    description: 'View an exemplary reference answer to understand ideal coverage.',
    icon: '🎯',
    penalty: '-3.0 pts',
    color: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20',
  },
];

export function HelpModal({
  isOpen,
  onClose,
  onRequestHelp,
  usedHelpTypes,
}: HelpModalProps) {
  const [activeTab, setActiveTab] = useState<HelpType | null>(null);
  const [helpContent, setHelpContent] = useState<Record<string, string>>({});
  const [loadingType, setLoadingType] = useState<HelpType | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  async function handleSelectHelp(type: HelpType) {
    setActiveTab(type);
    if (helpContent[type]) return; // Already loaded

    setLoadingType(type);
    setError(null);
    try {
      const content = await onRequestHelp(type);
      setHelpContent((prev) => ({ ...prev, [type]: content }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch help.');
    } finally {
      setLoadingType(null);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl sm:p-8">
        <div className="mb-6 flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h3 className="text-xl font-bold text-white flex items-center gap-2">
              <span>🤖</span> AI Mentor Assistance
            </h3>
            <p className="mt-1 text-xs text-slate-400">
              Request real-time hints or guidance. A small score adjustment will apply to this answer.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            ✕
          </button>
        </div>

        {/* Option Grid */}
        <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {HELP_OPTIONS.map((opt) => {
            const isUsed = usedHelpTypes.includes(opt.type);
            const isActive = activeTab === opt.type;

            return (
              <button
                key={opt.type}
                type="button"
                onClick={() => handleSelectHelp(opt.type)}
                className={`flex flex-col justify-between rounded-xl border p-4 text-left transition-all ${
                  isActive
                    ? 'ring-2 ring-indigo-500 border-indigo-500 bg-slate-800/90'
                    : opt.color
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2 font-semibold">
                    <span>{opt.icon}</span>
                    <span>{opt.title}</span>
                  </div>
                  <span className="rounded-full bg-slate-950/60 px-2 py-0.5 text-[10px] font-bold tracking-wider">
                    {opt.penalty}
                  </span>
                </div>
                <p className="mt-2 text-xs opacity-80">{opt.description}</p>
                {isUsed && (
                  <span className="mt-2 inline-block text-[10px] font-medium text-indigo-400">
                    ✓ Used in this question
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Content Box */}
        {activeTab && (
          <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-5">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400">
                {HELP_OPTIONS.find((o) => o.type === activeTab)?.title}
              </span>
              <span className="text-xs text-amber-400">
                Penalty: {HELP_OPTIONS.find((o) => o.type === activeTab)?.penalty}
              </span>
            </div>

            {loadingType === activeTab ? (
              <div className="flex items-center gap-3 py-4 text-sm text-slate-400">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
                Fetching hint from AI Mentor…
              </div>
            ) : error ? (
              <p className="text-sm text-red-400">{error}</p>
            ) : (
              <p className="text-sm leading-relaxed text-slate-200 whitespace-pre-line">
                {helpContent[activeTab]}
              </p>
            )}
          </div>
        )}

        <div className="mt-6 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl bg-slate-800 px-6 py-2.5 text-sm font-semibold text-white hover:bg-slate-700"
          >
            Close & Back to Answer
          </button>
        </div>
      </div>
    </div>
  );
}
