import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { Footer } from '../components/layout/Footer';
import { Header } from '../components/layout/Header';
import { AiAvatar } from '../components/interview/AiAvatar';
import { CandidateCamera } from '../components/interview/CandidateCamera';
import { HelpModal } from '../components/interview/HelpModal';
import { useSpeech } from '../hooks/useSpeech';
import { api } from '../services/api';
import type {
  AnswerResult,
  EvaluationResponse,
  HelpType,
  InterviewQuestion,
  SessionQuestion,
  SessionResultResponse,
} from '../types';

// ---------------------------------------------------------------------------
// Types & Constants
// ---------------------------------------------------------------------------

type InterviewPhase = 'loading' | 'question' | 'evaluation' | 'results' | 'error';

interface LocationState {
  questions?: InterviewQuestion[];
  projects?: string[];
  skills?: string[];
}

const TOTAL_MOCK_QUESTIONS = 6;

// ---------------------------------------------------------------------------
// Helper Components
// ---------------------------------------------------------------------------

function ScoreRing({ score, label = '/ 10' }: { score: number; label?: string }) {
  const pct = (score / 10) * 100;
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (pct / 100) * circumference;
  const color =
    score >= 8 ? '#34d399' : score >= 6 ? '#60a5fa' : score >= 4 ? '#fbbf24' : '#f87171';

  return (
    <div className="relative flex h-28 w-28 items-center justify-center">
      <svg className="-rotate-90 h-28 w-28">
        <circle cx="56" cy="56" r={radius} stroke="#1e293b" strokeWidth="10" fill="none" />
        <circle
          cx="56"
          cy="56"
          r={radius}
          stroke={color}
          strokeWidth="10"
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 1s ease' }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-2xl font-bold text-white">{score.toFixed(1)}</span>
        <span className="text-xs text-slate-400">{label}</span>
      </div>
    </div>
  );
}

function ScoreBar({ label, text }: { label: string; text: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-4">
      <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">{label}</p>
      <p className="text-sm leading-relaxed text-slate-200">{text}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main AI Interview Room Page
// ---------------------------------------------------------------------------

export function InterviewPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as LocationState | null;

  const initialQuestions: InterviewQuestion[] = state?.questions ?? [];
  const projects: string[] = state?.projects ?? [];
  const skills: string[] = state?.skills ?? [];

  const [phase, setPhase] = useState<InterviewPhase>('loading');
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [activeQuestions, setActiveQuestions] = useState<SessionQuestion[]>([]);
  const [answer, setAnswer] = useState('');
  const [usedHelpTypes, setUsedHelpTypes] = useState<HelpType[]>([]);
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [evaluation, setEvaluation] = useState<EvaluationResponse | null>(null);
  const [results, setResults] = useState<SessionResultResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const {
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
  } = useSpeech();

  // Session timer
  useEffect(() => {
    if (phase !== 'question' && phase !== 'evaluation') return;
    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [phase]);

  // Initialize session on mount
  useEffect(() => {
    if (initialQuestions.length === 0 && projects.length === 0 && skills.length === 0) {
      navigate('/resume', { replace: true });
      return;
    }

    api
      .createInterviewSession(
        initialQuestions.length > 0 ? initialQuestions : undefined,
        'adaptive',
      )
      .then(async (resp) => {
        setSessionId(resp.session_id);
        if (resp.questions && resp.questions.length > 0) {
          // For adaptive sessions, display only the first initial question as Q1
          setActiveQuestions([resp.questions[0]]);
          setPhase('question');
        } else {
          try {
            const firstQ = await api.getNextQuestion(resp.session_id, 0, projects, skills);
            setActiveQuestions([firstQ]);
            setPhase('question');
          } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to initialize AI Interviewer.');
            setPhase('error');
          }
        }
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Failed to connect to AI Interview Room.');
        setPhase('error');
      });
    // Only run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const currentQuestion = activeQuestions[currentIndex];
  const isLastQuestion = currentIndex === TOTAL_MOCK_QUESTIONS - 1;

  // AI speaks question -> Mic automatically activates after AI finishes speaking
  useEffect(() => {
    if (phase === 'question' && currentQuestion) {
      speak(currentQuestion.question, () => {
        if (isSTTSupported) {
          startListening((text) => {
            setAnswer(text);
          });
        }
      });
    } else {
      stopSpeaking();
      stopListening();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, currentIndex, currentQuestion?.question]);

  // Focus textarea when a new question appears
  useEffect(() => {
    if (phase === 'question') {
      textareaRef.current?.focus();
    }
  }, [phase, currentIndex]);

  function handleToggleMic() {
    if (isListening) {
      stopListening();
    } else {
      stopSpeaking();
      startListening((text) => {
        setAnswer(text);
      });
    }
  }

  function handleReplayQuestion() {
    if (!currentQuestion) return;
    stopListening();
    speak(currentQuestion.question, () => {
      if (isSTTSupported) {
        startListening((text) => {
          setAnswer(text);
        });
      }
    });
  }

  async function handleRequestHelp(helpType: HelpType): Promise<string> {
    if (!sessionId || !currentQuestion) throw new Error('Session not ready');
    const res = await api.getInterviewHelp(sessionId, {
      question_text: currentQuestion.question,
      question_category: currentQuestion.category,
      question_difficulty: currentQuestion.difficulty,
      question_type: currentQuestion.question_type,
      help_type: helpType,
    });

    if (!usedHelpTypes.includes(helpType)) {
      setUsedHelpTypes((prev) => [...prev, helpType]);
    }

    return res.content;
  }

  async function handleSubmitAnswer() {
    if (!sessionId || !currentQuestion || !answer.trim() || isSubmitting) return;

    stopSpeaking();
    stopListening();
    setIsSubmitting(true);
    setError(null);

    try {
      const eval_ = await api.submitAnswer(sessionId, {
        question_text: currentQuestion.question,
        question_category: currentQuestion.category,
        question_difficulty: currentQuestion.difficulty,
        question_type: currentQuestion.question_type,
        answer_text: answer.trim(),
        assistance_used: usedHelpTypes,
      });
      setEvaluation(eval_);
      setPhase('evaluation');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Evaluation failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSkip() {
    if (!sessionId || !currentQuestion || isSubmitting) return;

    stopSpeaking();
    stopListening();
    setIsSubmitting(true);
    setError(null);

    try {
      const eval_ = await api.submitAnswer(sessionId, {
        question_text: currentQuestion.question,
        question_category: currentQuestion.category,
        question_difficulty: currentQuestion.difficulty,
        question_type: currentQuestion.question_type,
        answer_text: '[Skipped]',
        assistance_used: usedHelpTypes,
      });
      setEvaluation(eval_);
      setPhase('evaluation');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to skip question.');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleNextQuestion() {
    stopSpeaking();
    stopListening();

    if (isLastQuestion) {
      setPhase('loading');
      try {
        if (sessionId) {
          await api.completeSession(sessionId);
          const res = await api.getSessionResults(sessionId);
          setResults(res);
        }
        setPhase('results');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load results.');
        setPhase('error');
      }
    } else {
      const nextIdx = currentIndex + 1;
      setAnswer('');
      setUsedHelpTypes([]);
      setEvaluation(null);
      setError(null);

      setPhase('loading');
      try {
        const nextQ = await api.getNextQuestion(sessionId!, nextIdx, projects, skills);
        setActiveQuestions((prev) => [...prev.slice(0, nextIdx), nextQ]);
        setCurrentIndex(nextIdx);
        setPhase('question');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to generate next dynamic question.');
        setPhase('error');
      }
    }
  }

  function handleExitInterview() {
    stopSpeaking();
    stopListening();
    setElapsedSeconds(0);
    navigate('/resume', { replace: true });
  }

  // ---------------------------------------------------------------------------
  // Render helpers
  // ---------------------------------------------------------------------------

  if (phase === 'loading') {
    return (
      <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
        <Header />
        <main className="flex flex-1 items-center justify-center">
          <div className="text-center">
            <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent" />
            <p className="text-slate-300 font-medium">Entering AI Virtual Interview Room…</p>
            <p className="mt-1 text-xs text-slate-500">Connecting video feed and initializing adaptive question engine</p>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  if (phase === 'error') {
    return (
      <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
        <Header />
        <main className="mx-auto w-full max-w-2xl flex-1 px-6 py-10">
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6">
            <p className="font-semibold text-red-200">Interview Room Exception</p>
            <p className="mt-1 text-sm text-red-300">{error}</p>
          </div>
          <button
            type="button"
            onClick={handleExitInterview}
            className="mt-6 inline-block text-sm text-slate-400 hover:text-white"
          >
            ← Exit Interview
          </button>
        </main>
        <Footer />
      </div>
    );
  }

  if (phase === 'results' && results) {
    return <ResultsView results={results} elapsedSeconds={elapsedSeconds} />;
  }

  // ---------------------------------------------------------------------------
  // Split-Screen AI Interview Room
  // ---------------------------------------------------------------------------
  if ((phase === 'question' || phase === 'evaluation') && currentQuestion) {
    return (
      <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
        <Header />

        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 sm:py-8">
          {/* Help Modal */}
          <HelpModal
            isOpen={isHelpOpen}
            onClose={() => setIsHelpOpen(false)}
            onRequestHelp={handleRequestHelp}
            usedHelpTypes={usedHelpTypes}
          />

          {/* Top Room Header Navigation */}
          <div className="mb-6 flex items-center justify-between border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <button
                type="button"
                id="exit-interview-btn"
                onClick={handleExitInterview}
                className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-300 transition-colors hover:border-slate-700 hover:bg-slate-800 hover:text-white"
              >
                🚪 Exit Interview
              </button>
              <span className="text-slate-700">|</span>
              <span className="text-sm font-semibold text-white">PrepAI Virtual Interview Room</span>
            </div>

            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-300">
                <span className="h-2 w-2 animate-ping rounded-full bg-indigo-400" />
                Live Interview Session
              </span>
            </div>
          </div>

          {/* Split-Screen Main Grid Layout */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            {/* LEFT COLUMN: AI Interviewer (lg:col-span-7) */}
            <div className="lg:col-span-7 flex flex-col min-h-[460px]">
              <AiAvatar
                isSpeaking={isSpeaking}
                isListening={isListening}
                isEvaluating={isSubmitting || phase === 'evaluation'}
                questionText={currentQuestion.question}
                questionIndex={currentIndex}
                totalQuestions={TOTAL_MOCK_QUESTIONS}
                onReplayAudio={handleReplayQuestion}
                isTTSSupported={isTTSSupported}
              />
            </div>

            {/* RIGHT COLUMN: Candidate Studio & Answering Controls (lg:col-span-5) */}
            <div className="lg:col-span-5 flex flex-col space-y-4">
              {/* Live Webcam Preview */}
              <CandidateCamera
                isListening={isListening}
                isSubmitting={isSubmitting}
                elapsedSeconds={elapsedSeconds}
              />

              {/* Answering & Evaluation Workspace Card */}
              <div className="flex flex-1 flex-col justify-between rounded-2xl border border-slate-800 bg-slate-900/90 p-5 shadow-2xl backdrop-blur-md">
                {phase === 'question' && (
                  <>
                    <div className="mb-2 flex items-center justify-between">
                      <label htmlFor="candidate-answer" className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                        Candidate Answer (Spoken / Typed)
                      </label>

                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => setIsHelpOpen(true)}
                          className="flex items-center gap-1 rounded-lg border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs font-semibold text-amber-300 transition-colors hover:bg-amber-500/20"
                        >
                          💡 Need Help?
                        </button>

                        {isSTTSupported && (
                          <button
                            type="button"
                            onClick={handleToggleMic}
                            className={`flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium transition-all ${
                              isListening
                                ? 'bg-red-500/20 text-red-300 border border-red-500/30 hover:bg-red-500/30'
                                : 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-500/30'
                            }`}
                          >
                            {isListening ? 'Pause Mic' : 'Start Mic'}
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Notice / Warning Alerts */}
                    {(error || sttError) && (
                      <div className="mb-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
                        <p className="font-semibold">Notice</p>
                        <p className="mt-0.5">{error || sttError}</p>
                      </div>
                    )}

                    {/* Assistance Used Indicator */}
                    {usedHelpTypes.length > 0 && (
                      <div className="mb-3 flex flex-wrap items-center gap-1.5 rounded-lg border border-amber-500/20 bg-amber-500/5 p-2 text-xs text-amber-300">
                        <span className="font-semibold">Assistance Requested:</span>
                        {usedHelpTypes.map((ht) => (
                          <span
                            key={ht}
                            className="rounded-md border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium"
                          >
                            {ht.replace('_', ' ')}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Speech Transcript Text Area */}
                    <textarea
                      id="candidate-answer"
                      ref={textareaRef}
                      value={answer}
                      onChange={(e) => {
                        setAnswer(e.target.value);
                        if (sttError) setSttError(null);
                      }}
                      placeholder={
                        isSpeaking
                          ? 'AI Interviewer is asking the question… Microphone will activate automatically when AI finishes.'
                          : isListening
                          ? 'Listening… Speak your answer. Your speech is transcribed here in real-time. You can edit text manually if needed.'
                          : 'Type your answer here or click "Start Mic" to speak…'
                      }
                      rows={5}
                      className="w-full resize-none rounded-xl border border-slate-700 bg-slate-950/80 px-4 py-3 text-sm text-slate-100 placeholder-slate-600 outline-none transition-colors focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
                    />

                    {/* Actions */}
                    <div className="mt-4 flex items-center justify-between">
                      <button
                        type="button"
                        onClick={handleSkip}
                        disabled={isSubmitting}
                        className="text-xs text-slate-500 underline-offset-4 hover:text-slate-300 disabled:opacity-50"
                      >
                        Skip question
                      </button>
                      <button
                        type="button"
                        id="submit-answer-btn"
                        onClick={handleSubmitAnswer}
                        disabled={isSubmitting || !answer.trim()}
                        className="flex items-center justify-center gap-2 rounded-xl bg-indigo-500 px-6 py-2.5 text-sm font-semibold text-white transition-all hover:bg-indigo-400 hover:shadow-lg hover:shadow-indigo-500/25 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {isSubmitting ? (
                          <>
                            <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                            Evaluating…
                          </>
                        ) : (
                          'Submit Answer'
                        )}
                      </button>
                    </div>
                  </>
                )}

                {/* Evaluation Card View */}
                {phase === 'evaluation' && evaluation && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <h3 className="font-semibold text-white">Answer Evaluation</h3>
                      <span className="text-xs text-indigo-400 font-medium">Turn Complete</span>
                    </div>

                    <div className="flex items-center gap-4">
                      <ScoreRing score={evaluation.score} />
                      <div className="flex-1 space-y-2">
                        {evaluation.total_penalty > 0 && (
                          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-2.5 text-xs text-amber-200">
                            <span className="font-semibold">Assistance Penalty: </span>
                            Raw {evaluation.raw_score.toFixed(1)} - Penalty {evaluation.total_penalty.toFixed(1)} = <span className="font-bold text-emerald-400">{evaluation.adjusted_score.toFixed(1)}/10</span>
                          </div>
                        )}
                        <ScoreBar label="Technical Accuracy" text={evaluation.technical_accuracy} />
                      </div>
                    </div>

                    <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4">
                      <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-indigo-400">
                        Feedback
                      </p>
                      <p className="text-xs leading-relaxed text-slate-200">{evaluation.feedback}</p>
                    </div>

                    <div className="flex justify-end pt-2">
                      <button
                        type="button"
                        id="next-question-btn"
                        onClick={handleNextQuestion}
                        className="flex items-center gap-2 rounded-xl bg-indigo-500 px-6 py-2.5 text-sm font-semibold text-white transition-all hover:bg-indigo-400 hover:shadow-lg hover:shadow-indigo-500/25 active:scale-95"
                      >
                        {isLastQuestion ? 'View Final Report' : 'Next Question'}
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                          <path fillRule="evenodd" d="M3 10a.75.75 0 0 1 .75-.75h10.638L10.23 5.29a.75.75 0 1 1 1.04-1.08l5.5 5.25a.75.75 0 0 1 0 1.08l-5.5 5.25a.75.75 0 1 1-1.04-1.08l4.158-3.96H3.75A.75.75 0 0 1 3 10Z" clipRule="evenodd" />
                        </svg>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return null;
}

// ---------------------------------------------------------------------------
// Results View & Comprehensive Final Evaluation Dashboard
// ---------------------------------------------------------------------------

function ResultsView({
  results,
  elapsedSeconds,
}: {
  results: SessionResultResponse;
  elapsedSeconds: number;
}) {
  const navigate = useNavigate();
  const report = results.final_report;

  const formatTimer = (totalSec: number) => {
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${mins}m ${secs}s`;
  };

  const scoreColor = (s: number | null) => {
    if (s === null) return 'text-slate-400';
    if (s >= 8) return 'text-emerald-400';
    if (s >= 6) return 'text-blue-400';
    if (s >= 4) return 'text-amber-400';
    return 'text-red-400';
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
      <Header />
      <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-10">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <h1 className="text-3xl font-bold text-white">Mock Interview Complete 🎉</h1>
            <p className="mt-1 text-slate-400">
              AI Interview Room Performance Evaluation & Competency Breakdown.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-mono text-slate-300">
              ⏱️ Duration: {formatTimer(elapsedSeconds)}
            </span>
          </div>
        </div>

        {/* Overall & Independent Score Overview */}
        {results.average_score !== null && (
          <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex items-center gap-6 rounded-2xl border border-indigo-500/20 bg-indigo-500/5 p-6">
              <ScoreRing score={results.average_score} />
              <div>
                <p className="text-xs uppercase font-semibold text-slate-400">Overall Score</p>
                <p className={`mt-1 text-2xl font-bold ${scoreColor(results.average_score)}`}>
                  {results.average_score.toFixed(1)} / 10
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  Across {results.total_questions} interview questions
                </p>
              </div>
            </div>

            {report && (
              <div className="flex items-center gap-6 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-6">
                <ScoreRing score={report.independent_score} label="Unassisted" />
                <div>
                  <p className="text-xs uppercase font-semibold text-slate-400">Independent Answering</p>
                  <p className="mt-1 text-2xl font-bold text-emerald-400">
                    {report.independent_ratio.toFixed(0)}%
                  </p>
                  <p className="mt-1 text-xs text-slate-400">
                    Unassisted average: {report.independent_score.toFixed(1)}/10
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* AI Mentor Synthesis Report */}
        {report && (
          <div className="mb-8 space-y-6">
            {/* 5-Dimension Assessment */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
              <h2 className="mb-4 text-lg font-bold text-white flex items-center gap-2">
                <span>📊</span> Competency Breakdown
              </h2>
              <div className="space-y-4">
                {report.dimensions.map((dim) => (
                  <div key={dim.dimension} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className="font-semibold text-slate-200">{dim.dimension}</span>
                      <span className={`font-bold ${scoreColor(dim.score)}`}>
                        {dim.score.toFixed(1)} / 10
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
                      <div
                        className="h-full rounded-full bg-indigo-500 transition-all duration-500"
                        style={{ width: `${(dim.score / 10) * 100}%` }}
                      />
                    </div>
                    <p className="text-xs text-slate-400">{dim.details}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Strengths & Areas to Improve */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-6">
                <h3 className="mb-3 text-sm font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-2">
                  <span>✅</span> Key Strengths
                </h3>
                <ul className="space-y-2 text-sm text-slate-200">
                  {report.strengths.map((s, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-emerald-400">•</span>
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-6">
                <h3 className="mb-3 text-sm font-bold uppercase tracking-wider text-amber-400 flex items-center gap-2">
                  <span>⚠️</span> Areas to Improve
                </h3>
                <ul className="space-y-2 text-sm text-slate-200">
                  {report.weaknesses.map((w, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-amber-400">•</span>
                      <span>{w}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Mentor Narrative */}
            <div className="rounded-2xl border border-indigo-500/20 bg-indigo-500/5 p-6">
              <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-indigo-400 flex items-center gap-2">
                <span>🤖</span> AI Mentor Summary
              </h3>
              <p className="text-sm leading-relaxed text-slate-200">{report.mentor_feedback}</p>
            </div>

            {/* Recommended Learning Roadmap */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
              <h3 className="mb-3 text-sm font-bold uppercase tracking-wider text-teal-400 flex items-center gap-2">
                <span>🎯</span> Technical Topics to Study Next
              </h3>
              <div className="flex flex-wrap gap-2">
                {report.next_topics_to_practice.map((topic, i) => (
                  <span
                    key={i}
                    className="rounded-xl border border-teal-500/30 bg-teal-500/10 px-4 py-2 text-xs font-semibold text-teal-300"
                  >
                    📚 {topic}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Detailed Question History */}
        <h2 className="mb-4 text-lg font-bold text-white">Interview Questions History</h2>
        <div className="space-y-4">
          {results.answers.map((ans: AnswerResult, i: number) => (
            <details
              key={ans.answer_id}
              className="group rounded-2xl border border-slate-800 bg-slate-900/50"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between px-6 py-4">
                <div className="flex items-center gap-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-indigo-300">
                    Q{i + 1}
                  </span>
                  <span className="text-sm text-slate-300 line-clamp-1">
                    {ans.question_text}
                  </span>
                </div>
                <div className="flex shrink-0 items-center gap-3 pl-4">
                  <span className={`text-sm font-bold ${scoreColor(ans.score)}`}>
                    {ans.score !== null ? `${ans.score.toFixed(1)} / 10` : 'Skipped'}
                  </span>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="h-4 w-4 text-slate-500 transition-transform group-open:rotate-180"
                  >
                    <path
                      fillRule="evenodd"
                      d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
              </summary>

              <div className="border-t border-slate-800 px-6 pb-6 pt-4 space-y-3">
                <div>
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Your Answer
                  </p>
                  <p className="text-sm leading-relaxed text-slate-300">{ans.answer_text}</p>
                </div>

                {ans.assistance_used && ans.assistance_used.length > 0 && (
                  <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-xs text-amber-300">
                    <span className="font-semibold">Assistance Requested: </span>
                    {ans.assistance_used.join(', ')} (Raw Score: {ans.raw_score?.toFixed(1)} → Adjusted Score: {ans.adjusted_score?.toFixed(1)})
                  </div>
                )}

                {ans.score !== null && (
                  <>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                      <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
                        <p className="mb-1 text-xs text-slate-500">Technical Accuracy</p>
                        <p className="text-xs text-slate-300">{ans.technical_accuracy}</p>
                      </div>
                      <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
                        <p className="mb-1 text-xs text-slate-500">Clarity</p>
                        <p className="text-xs text-slate-300">{ans.clarity}</p>
                      </div>
                      <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
                        <p className="mb-1 text-xs text-slate-500">Completeness</p>
                        <p className="text-xs text-slate-300">{ans.completeness}</p>
                      </div>
                    </div>

                    <div className="rounded-lg border border-indigo-500/20 bg-indigo-500/5 p-4">
                      <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-indigo-400">
                        Feedback
                      </p>
                      <p className="text-sm text-slate-200">{ans.feedback}</p>
                    </div>

                    <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4">
                      <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-emerald-400">
                        Suggested Answer
                      </p>
                      <p className="text-sm text-slate-200">{ans.suggested_answer}</p>
                    </div>
                  </>
                )}
              </div>
            </details>
          ))}
        </div>

        {/* Action Buttons */}
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            id="new-interview-btn"
            onClick={() => navigate('/resume')}
            className="rounded-xl bg-indigo-500 px-6 py-3 text-sm font-semibold text-white transition-all hover:bg-indigo-400 hover:shadow-lg hover:shadow-indigo-500/25"
          >
            Start New Interview
          </button>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="rounded-xl border border-slate-600 px-6 py-3 text-sm text-slate-300 transition-colors hover:border-slate-400 hover:text-white"
          >
            Go to Home
          </button>
        </div>
      </main>
      <Footer />
    </div>
  );
}
