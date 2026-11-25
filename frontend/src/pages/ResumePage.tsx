import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { Footer } from '../components/layout/Footer';
import { Header } from '../components/layout/Header';
import { AnalysisResults } from '../components/resume/AnalysisResults';
import { LoadingProgress } from '../components/resume/LoadingProgress';
import { QuestionsList } from '../components/resume/QuestionsList';
import { UploadZone } from '../components/resume/UploadZone';
import { api } from '../services/api';
import type { AnalysisStep, StoredResumeItem } from '../types';

type PageMode = 'library' | 'upload' | 'analyzing' | 'error';

const STORAGE_KEY_LIBRARY = 'prepai_resume_library';
const STORAGE_KEY_ACTIVE_ID = 'prepai_active_resume_id';

export function ResumePage() {
  const navigate = useNavigate();
  const [resumes, setResumes] = useState<StoredResumeItem[]>([]);
  const [activeResumeId, setActiveResumeId] = useState<number | null>(null);
  const [pageMode, setPageMode] = useState<PageMode>('library');
  const [currentStep, setCurrentStep] = useState<AnalysisStep>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [inspectingResumeId, setInspectingResumeId] = useState<number | null>(null);

  // CRUD state
  const [deletingResume, setDeletingResume] = useState<StoredResumeItem | null>(null);
  const [editingResumeId, setEditingResumeId] = useState<number | null>(null);
  const [editFilenameText, setEditFilenameText] = useState('');

  // Load persistent library on mount
  useEffect(() => {
    let isMounted = true;

    async function loadLibrary() {
      try {
        const dbResumes = await api.listResumes();
        let savedLibrary: StoredResumeItem[] = [];
        try {
          const raw = localStorage.getItem(STORAGE_KEY_LIBRARY);
          if (raw) savedLibrary = JSON.parse(raw);
        } catch {
          savedLibrary = [];
        }

        const merged: StoredResumeItem[] = dbResumes.map((dbr) => {
          const match = savedLibrary.find((item) => item.id === dbr.id);
          return {
            id: dbr.id,
            filename: dbr.filename,
            uploaded_at: dbr.uploaded_at,
            analysis: match?.analysis ?? {
              name: 'Candidate',
              skills: dbr.skills || [],
              projects: dbr.projects || [],
              education: [],
              experience: [],
              certifications: [],
            },
            questions: match?.questions ?? [],
          };
        });

        // Add any saved library items not yet returned by DB list endpoint
        savedLibrary.forEach((sl) => {
          if (!merged.some((m) => m.id === sl.id)) {
            merged.push(sl);
          }
        });

        if (isMounted) {
          setResumes(merged);
          if (merged.length > 0) {
            const storedActiveId = localStorage.getItem(STORAGE_KEY_ACTIVE_ID);
            const found = merged.find((r) => String(r.id) === storedActiveId);
            const activeId = found ? found.id : merged[0].id;
            setActiveResumeId(activeId);
            setPageMode('library');
          } else {
            setPageMode('upload');
          }
        }
      } catch {
        if (isMounted) {
          try {
            const raw = localStorage.getItem(STORAGE_KEY_LIBRARY);
            if (raw) {
              const parsed: StoredResumeItem[] = JSON.parse(raw);
              if (parsed.length > 0) {
                setResumes(parsed);
                const storedActiveId = localStorage.getItem(STORAGE_KEY_ACTIVE_ID);
                const found = parsed.find((r) => String(r.id) === storedActiveId);
                setActiveResumeId(found ? found.id : parsed[0].id);
                setPageMode('library');
                return;
              }
            }
          } catch {
            // Ignore local storage error
          }
          setPageMode('upload');
        }
      }
    }

    loadLibrary();
    return () => {
      isMounted = false;
    };
  }, []);

  const activeResume = resumes.find((r) => r.id === activeResumeId) ?? resumes[0] ?? null;

  function handleSelectActive(id: number) {
    setActiveResumeId(id);
    localStorage.setItem(STORAGE_KEY_ACTIVE_ID, String(id));
  }

  async function handleStartInterview(targetResume?: StoredResumeItem) {
    const resumeToUse = targetResume ?? activeResume;
    if (!resumeToUse) return;

    setError(null);
    setIsStarting(true);

    try {
      let questionsToPass = resumeToUse.questions;

      if (!questionsToPass || questionsToPass.length === 0) {
        const genRes = await api.generateQuestions(resumeToUse.analysis);
        questionsToPass = genRes.questions;

        const updated = resumes.map((r) =>
          r.id === resumeToUse.id ? { ...r, questions: questionsToPass } : r
        );
        setResumes(updated);
        localStorage.setItem(STORAGE_KEY_LIBRARY, JSON.stringify(updated));
      }

      navigate('/interview', {
        state: {
          questions: questionsToPass,
          projects: resumeToUse.analysis.projects || [],
          skills: resumeToUse.analysis.skills || [],
        },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start mock interview.');
    } finally {
      setIsStarting(false);
    }
  }

  async function handleAnalyzeNewResume() {
    if (!file) {
      setError('Please select a PDF resume file.');
      return;
    }

    setError(null);
    setSuccessMsg(null);
    setPageMode('analyzing');

    try {
      setCurrentStep('upload');
      const upload = await api.uploadResume(file);

      setCurrentStep('analyze');
      const analyzed = await api.analyzeResume(upload.resume_id, upload.text);

      setCurrentStep('generate');
      const questions = await api.generateQuestions(analyzed.analysis);

      const newItem: StoredResumeItem = {
        id: upload.resume_id,
        filename: file.name,
        uploaded_at: new Date().toISOString(),
        analysis: analyzed.analysis,
        questions: questions.questions,
      };

      const updatedResumes = [newItem, ...resumes.filter((r) => r.id !== newItem.id)];
      setResumes(updatedResumes);
      setActiveResumeId(newItem.id);
      localStorage.setItem(STORAGE_KEY_LIBRARY, JSON.stringify(updatedResumes));
      localStorage.setItem(STORAGE_KEY_ACTIVE_ID, String(newItem.id));
      setFile(null);
      setSuccessMsg(`Resume "${file.name}" added to library and set as active.`);
      setPageMode('library');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed. Please try again.');
      setPageMode('error');
    }
  }

  async function handleDeleteResumeConfirm() {
    if (!deletingResume) return;

    const idToDelete = deletingResume.id;
    const nameToDelete = deletingResume.filename;

    try {
      await api.deleteResume(idToDelete);
    } catch {
      // Best-effort delete; update local state safely
    }

    const remaining = resumes.filter((r) => r.id !== idToDelete);
    setResumes(remaining);
    localStorage.setItem(STORAGE_KEY_LIBRARY, JSON.stringify(remaining));

    if (activeResumeId === idToDelete) {
      if (remaining.length > 0) {
        const nextActiveId = remaining[0].id;
        setActiveResumeId(nextActiveId);
        localStorage.setItem(STORAGE_KEY_ACTIVE_ID, String(nextActiveId));
      } else {
        setActiveResumeId(null);
        localStorage.removeItem(STORAGE_KEY_ACTIVE_ID);
        setPageMode('upload');
      }
    }

    setSuccessMsg(`Resume "${nameToDelete}" was permanently removed.`);
    setDeletingResume(null);
  }

  async function handleUpdateFilename(id: number, newName: string) {
    if (!newName.trim()) return;

    try {
      await api.updateResume(id, newName.trim());
      const updated = resumes.map((r) => (r.id === id ? { ...r, filename: newName.trim() } : r));
      setResumes(updated);
      localStorage.setItem(STORAGE_KEY_LIBRARY, JSON.stringify(updated));
      setSuccessMsg(`Resume renamed to "${newName.trim()}".`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update filename.');
    } finally {
      setEditingResumeId(null);
    }
  }

  function handleOpenUploadFlow() {
    setFile(null);
    setError(null);
    setSuccessMsg(null);
    setPageMode('upload');
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
      <Header />
      <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-10">
        <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <Link
              to="/"
              className="mb-2 inline-block text-sm text-slate-400 transition-colors hover:text-white"
            >
              ← Back to Home
            </Link>

            <h1 className="text-3xl font-bold tracking-tight text-white">
              {pageMode === 'library' ? 'Resume Library & Interview Prep' : 'Upload Resume'}
            </h1>
            <p className="mt-1 text-slate-400">
              {pageMode === 'library'
                ? 'Manage your stored resumes, inspect extracted skills, and launch personalized AI Mock Interviews.'
                : 'Upload a PDF resume to extract technical skills and generate AI interview questions.'}
            </p>
          </div>

          {pageMode === 'library' && resumes.length > 0 && (
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                id="add-new-resume-btn"
                onClick={handleOpenUploadFlow}
                className="rounded-xl border border-slate-700 bg-slate-900 px-5 py-2.5 text-sm font-semibold text-slate-200 transition-all hover:border-slate-500 hover:text-white"
              >
                ➕ Add New Resume
              </button>

              <button
                type="button"
                id="start-new-interview-btn"
                disabled={!activeResume || isStarting}
                onClick={() => handleStartInterview()}
                className="rounded-xl bg-gradient-to-r from-indigo-500 to-emerald-500 px-6 py-2.5 text-sm font-bold text-white shadow-lg shadow-indigo-500/25 transition-all hover:from-indigo-400 hover:to-emerald-400 disabled:opacity-50"
              >
                {isStarting ? 'Preparing Session…' : '🚀 Start New Interview'}
              </button>
            </div>
          )}
        </div>

        {error && (
          <div className="mb-6 rounded-xl border border-red-500/30 bg-red-500/10 px-5 py-4 text-red-200 flex items-center justify-between">
            <div>
              <p className="font-semibold">Notice</p>
              <p className="mt-0.5 text-sm">{error}</p>
            </div>
            <button type="button" onClick={() => setError(null)} className="text-xs text-red-300 hover:text-white">✕</button>
          </div>
        )}

        {successMsg && (
          <div className="mb-6 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-5 py-4 text-emerald-200 flex items-center justify-between">
            <p className="text-sm font-medium">✓ {successMsg}</p>
            <button type="button" onClick={() => setSuccessMsg(null)} className="text-xs text-emerald-400 hover:text-white">✕</button>
          </div>
        )}

        {pageMode === 'analyzing' && <LoadingProgress currentStep={currentStep} />}

        {pageMode === 'error' && (
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-8 text-center">
            <h2 className="text-xl font-bold text-red-400">Resume Processing Error</h2>
            <p className="mt-2 text-sm text-slate-400">{error}</p>
            <div className="mt-6 flex justify-center gap-4">
              <button
                type="button"
                onClick={handleAnalyzeNewResume}
                className="rounded-xl bg-indigo-500 px-6 py-2.5 text-sm font-semibold text-white hover:bg-indigo-400"
              >
                Retry
              </button>
              <button
                type="button"
                onClick={() => setPageMode(resumes.length > 0 ? 'library' : 'upload')}
                className="rounded-xl border border-slate-700 px-6 py-2.5 text-sm text-slate-300 hover:border-slate-500"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {pageMode === 'upload' && (
          <div className="space-y-6">
            {resumes.length > 0 && (
              <button
                type="button"
                onClick={() => setPageMode('library')}
                className="text-sm font-medium text-indigo-400 hover:text-indigo-300"
              >
                ← Return to Resume Library
              </button>
            )}

            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur">
              <UploadZone file={file} onFileSelect={setFile} />

              <div className="mt-6 flex justify-end gap-3">
                {resumes.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setPageMode('library')}
                    className="rounded-xl border border-slate-700 px-6 py-2.5 text-sm font-semibold text-slate-300 hover:border-slate-500"
                  >
                    Cancel
                  </button>
                )}
                <button
                  type="button"
                  id="upload-analyze-btn"
                  disabled={!file}
                  onClick={handleAnalyzeNewResume}
                  className="rounded-xl bg-indigo-500 px-8 py-2.5 text-sm font-semibold text-white transition-all hover:bg-indigo-400 disabled:opacity-50"
                >
                  Upload & Analyze Resume
                </button>
              </div>
            </div>
          </div>
        )}

        {pageMode === 'library' && activeResume && (
          <div className="space-y-8">
            {/* Active Resume Card */}
            <div className="relative overflow-hidden rounded-2xl border border-emerald-500/40 bg-slate-900/90 p-6 shadow-xl shadow-emerald-950/20 backdrop-blur">
              <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                <div>
                  <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-400">
                    <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                    ACTIVE RESUME FOR MOCK INTERVIEW
                  </div>

                  <h2 className="mt-3 text-2xl font-bold text-white flex items-center gap-2">
                    📄 {activeResume.filename}
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Uploaded: {new Date(activeResume.uploaded_at).toLocaleDateString()} | Candidate:{' '}
                    {activeResume.analysis.name || 'Engineer'}
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    id="active-card-start-btn"
                    disabled={isStarting}
                    onClick={() => handleStartInterview(activeResume)}
                    className="rounded-xl bg-indigo-500 px-6 py-3 text-sm font-semibold text-white shadow-md hover:bg-indigo-400 disabled:opacity-50"
                  >
                    {isStarting ? 'Initializing Room…' : 'Start Mock Interview Now'}
                  </button>
                </div>
              </div>

              {/* Skills & Projects badges */}
              <div className="mt-6 grid gap-4 border-t border-slate-800/80 pt-5 sm:grid-cols-2">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Extracted Technical Skills
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {activeResume.analysis.skills.length > 0 ? (
                      activeResume.analysis.skills.map((skill) => (
                        <span
                          key={skill}
                          className="rounded-md border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-1 text-xs font-medium text-indigo-300"
                        >
                          {skill}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-slate-500">No skills parsed yet</span>
                    )}
                  </div>
                </div>

                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Extracted Candidate Projects
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {activeResume.analysis.projects.length > 0 ? (
                      activeResume.analysis.projects.map((proj) => (
                        <span
                          key={proj}
                          className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-300"
                        >
                          {proj}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-slate-500">General Technical Projects</span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Resume Library Items Grid */}
            <div>
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-xl font-bold text-white">
                  Your Resume Library ({resumes.length})
                </h3>
                <button
                  type="button"
                  onClick={handleOpenUploadFlow}
                  className="text-xs font-semibold text-indigo-400 hover:text-indigo-300"
                >
                  + Add another resume
                </button>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                {resumes.map((item) => {
                  const isActive = item.id === activeResumeId;
                  const isInspecting = item.id === inspectingResumeId;
                  const isEditing = item.id === editingResumeId;

                  return (
                    <div
                      key={item.id}
                      className={`rounded-2xl border p-5 transition-all ${
                        isActive
                          ? 'border-emerald-500/60 bg-slate-900/90 shadow-md'
                          : 'border-slate-800 bg-slate-900/50 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1">
                          {isEditing ? (
                            <div className="flex items-center gap-2">
                              <input
                                type="text"
                                value={editFilenameText}
                                onChange={(e) => setEditFilenameText(e.target.value)}
                                className="rounded-lg border border-indigo-500 bg-slate-950 px-2 py-1 text-xs text-white"
                              />
                              <button
                                type="button"
                                onClick={() => handleUpdateFilename(item.id, editFilenameText)}
                                className="rounded bg-indigo-500 px-2 py-1 text-xs text-white"
                              >
                                Save
                              </button>
                              <button
                                type="button"
                                onClick={() => setEditingResumeId(null)}
                                className="text-xs text-slate-400"
                              >
                                ✕
                              </button>
                            </div>
                          ) : (
                            <div className="flex items-center gap-2">
                              <p className="font-bold text-white flex items-center gap-2">
                                📄 {item.filename}
                              </p>
                              <button
                                type="button"
                                onClick={() => {
                                  setEditingResumeId(item.id);
                                  setEditFilenameText(item.filename);
                                }}
                                title="Rename Resume"
                                className="text-slate-500 hover:text-slate-300 text-xs"
                              >
                                ✏️
                              </button>
                            </div>
                          )}
                          <p className="text-xs text-slate-500 mt-0.5">
                            Uploaded: {new Date(item.uploaded_at).toLocaleDateString()}
                          </p>
                        </div>

                        {isActive ? (
                          <span className="rounded-full bg-emerald-500/20 px-3 py-1 text-xs font-semibold text-emerald-400">
                            Active
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => handleSelectActive(item.id)}
                            className="rounded-lg border border-slate-700 px-3 py-1 text-xs font-semibold text-slate-300 hover:border-indigo-500 hover:text-indigo-300"
                          >
                            Set Active
                          </button>
                        )}
                      </div>

                      <div className="mt-3 flex flex-wrap gap-1">
                        {item.analysis.skills.slice(0, 4).map((s) => (
                          <span
                            key={s}
                            className="rounded border border-slate-800 bg-slate-950 px-2 py-0.5 text-[11px] text-slate-300"
                          >
                            {s}
                          </span>
                        ))}
                        {item.analysis.skills.length > 4 && (
                          <span className="text-[11px] text-slate-500">
                            +{item.analysis.skills.length - 4} more
                          </span>
                        )}
                      </div>

                      <div className="mt-4 flex items-center justify-between border-t border-slate-800/60 pt-3">
                        <button
                          type="button"
                          onClick={() => setInspectingResumeId(isInspecting ? null : item.id)}
                          className="text-xs font-medium text-slate-400 hover:text-white"
                        >
                          {isInspecting ? 'Hide Details' : 'Inspect Analysis & Questions'}
                        </button>

                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => setDeletingResume(item)}
                            className="rounded-lg border border-red-500/30 bg-red-500/10 px-2.5 py-1 text-xs font-semibold text-red-400 hover:bg-red-500/20"
                          >
                            🗑 Delete
                          </button>

                          <button
                            type="button"
                            onClick={() => {
                              handleSelectActive(item.id);
                              handleStartInterview(item);
                            }}
                            className="rounded-lg bg-indigo-600 px-3 py-1 text-xs font-semibold text-white hover:bg-indigo-500"
                          >
                            Start Interview
                          </button>
                        </div>
                      </div>

                      {isInspecting && (
                        <div className="mt-4 space-y-4 border-t border-slate-800 pt-4">
                          <AnalysisResults analysis={item.analysis} />
                          {item.questions.length > 0 && (
                            <QuestionsList questions={item.questions} />
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {deletingResume && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
            <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
              <h3 className="text-xl font-bold text-white flex items-center gap-2">
                🗑 Delete Resume
              </h3>
              <p className="mt-3 text-sm text-slate-300">
                Are you sure you want to delete <span className="font-semibold text-white">"{deletingResume.filename}"</span>?
              </p>
              <p className="mt-2 text-xs text-slate-400">
                This action will permanently remove this resume from your library. Existing interview session history remains unaffected.
              </p>

              <div className="mt-6 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setDeletingResume(null)}
                  className="rounded-xl border border-slate-700 px-5 py-2 text-sm font-semibold text-slate-300 hover:border-slate-500"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  id="confirm-delete-resume-btn"
                  onClick={handleDeleteResumeConfirm}
                  className="rounded-xl bg-red-600 px-5 py-2 text-sm font-semibold text-white hover:bg-red-500"
                >
                  Delete Resume
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
