import { useState, type FormEvent } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { Footer } from '../components/layout/Footer';
import { Header } from '../components/layout/Header';

export function LoginPage() {
  const { login, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? '/resume';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!isLoading && isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      await login({ email, password });
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-6 py-12">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-8 shadow-xl">
          <h1 className="text-2xl font-bold text-white">Welcome back</h1>
          <p className="mt-2 text-sm text-slate-400">Sign in to continue your interview prep.</p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <div>
              <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-slate-300">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-2.5 text-sm text-white outline-none transition-colors focus:border-indigo-500"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-slate-300">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                minLength={8}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-2.5 text-sm text-white outline-none transition-colors focus:border-indigo-500"
                placeholder="Your password"
              />
            </div>

            {error ? (
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {error}
              </div>
            ) : null}

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-xl bg-indigo-500 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-400">
            Don&apos;t have an account?{' '}
            <Link to="/signup" className="font-medium text-indigo-300 hover:text-indigo-200">
              Create one
            </Link>
          </p>
        </div>
      </main>
      <Footer />
    </div>
  );
}
