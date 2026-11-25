import { Link } from 'react-router-dom';

import { useAuth } from '../../auth/AuthContext';

export function Hero() {
  const { isAuthenticated } = useAuth();

  return (
    <section className="mx-auto max-w-6xl px-6 py-20 text-center">
      <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-4 py-1.5 text-sm text-indigo-300">
        <span className="h-2 w-2 rounded-full bg-emerald-400" />
        AI-Powered Interview Preparation
      </div>

      <h1 className="mb-6 text-4xl font-bold tracking-tight text-white sm:text-5xl lg:text-6xl">
        Master Your Next Interview with{' '}
        <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
          PrepAI
        </span>
      </h1>

      <p className="mx-auto mb-10 max-w-2xl text-lg leading-relaxed text-slate-400">
        Upload your resume, get personalized interview questions, and prepare with AI-powered
        analysis tailored to your skills and projects.
      </p>

      <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
        <Link
          to={isAuthenticated ? '/resume' : '/signup'}
          className="rounded-xl bg-indigo-500 px-8 py-3 text-sm font-semibold text-white transition-colors hover:bg-indigo-400"
        >
          {isAuthenticated ? 'Upload Resume' : 'Get Started'}
        </Link>
        <a
          href="#features"
          className="rounded-xl border border-slate-700 px-8 py-3 text-sm font-semibold text-slate-300 transition-colors hover:border-slate-500 hover:text-white"
        >
          Learn More
        </a>
      </div>
    </section>
  );
}
