import type { InterviewQuestion } from '../../types';

const TYPE_LABELS: Record<InterviewQuestion['question_type'], string> = {
  technical: 'Technical',
  project: 'Project',
  problem_solving: 'Problem Solving',
  hr: 'HR',
};

interface QuestionsListProps {
  questions: InterviewQuestion[];
  onStartInterview?: () => void;
}

export function QuestionsList({ questions, onStartInterview }: QuestionsListProps) {
  if (questions.length === 0) {
    return (
      <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
        <h2 className="mb-2 text-xl font-bold text-white">Personalized Interview Prep</h2>
        <p className="text-sm text-slate-500">No questions generated yet.</p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 sm:p-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <h2 className="text-xl font-bold text-white">Personalized Interview Questions</h2>
          <p className="mt-1 text-xs text-slate-400">
            Tailored technical and project questions generated from your resume.
          </p>
        </div>

        {onStartInterview && (
          <button
            type="button"
            id="start-mock-interview-btn"
            onClick={onStartInterview}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition-all hover:brightness-110 active:scale-95"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-5 w-5"
            >
              <path fillRule="evenodd" d="M2 10a8 8 0 1 1 16 0 8 8 0 0 1-16 0Zm6.39-2.908a.75.75 0 0 1 .766.027l5 3.25a.75.75 0 0 1 0 1.262l-5 3.25A.75.75 0 0 1 6 14.25v-6.5a.75.75 0 0 1 .39-.658Z" clipRule="evenodd" />
            </svg>
            Start Mock Interview
          </button>
        )}
      </div>

      <div className="space-y-4">
        {questions.map((q, index) => (
          <article
            key={`${q.question_type}-${index}`}
            className="rounded-xl border border-slate-800 bg-slate-950/40 p-5"
          >
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-indigo-300">
                Question {index + 1}
              </span>
              <span className="text-xs text-slate-500">·</span>
              <span className="text-xs text-slate-400">
                {TYPE_LABELS[q.question_type]} • {q.category}
              </span>
              <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-300">
                {q.difficulty}
              </span>
            </div>
            <p className="leading-relaxed text-slate-200">{q.question}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
