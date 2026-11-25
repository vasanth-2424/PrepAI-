import { Link, useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../../auth/AuthContext';

export function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();

  const activePage =
    location.pathname === '/resume'
      ? 'resume'
      : location.pathname.startsWith('/interview')
        ? 'interview'
        : location.pathname === '/'
          ? 'landing'
          : undefined;

  return (
    <header className="border-b border-slate-800/60 bg-slate-950/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link to="/" className="flex items-center gap-2 text-left">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500 text-sm font-bold text-white">
            PA
          </div>
          <span className="text-lg font-semibold tracking-tight text-white">PrepAI</span>
        </Link>

        <nav className="flex items-center gap-3 text-sm sm:gap-4">
          {activePage === 'landing' ? (
            <>
              <a
                href="#features"
                className="hidden text-slate-400 transition-colors hover:text-white sm:inline"
              >
                Features
              </a>
              <a
                href="#status"
                className="hidden text-slate-400 transition-colors hover:text-white sm:inline"
              >
                Status
              </a>
            </>
          ) : null}

          <Link
            to="/resume"
            className={`rounded-lg px-3 py-1.5 transition-colors ${
              activePage === 'resume'
                ? 'bg-indigo-500/20 text-indigo-200'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Resume Upload
          </Link>

          <Link
            to="/interview"
            className={`rounded-lg px-3 py-1.5 transition-colors ${
              activePage === 'interview'
                ? 'bg-indigo-500/20 text-indigo-200'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Interview
          </Link>

          {isAuthenticated && user ? (
            <div className="flex items-center gap-2 sm:gap-3">
              <span className="hidden max-w-[140px] truncate text-slate-400 sm:inline">
                {user.name}
              </span>
              <button
                type="button"
                onClick={logout}
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-slate-300 transition-colors hover:border-slate-500 hover:text-white"
              >
                Logout
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="rounded-lg px-3 py-1.5 text-slate-400 transition-colors hover:text-white"
              >
                Login
              </button>
              <button
                type="button"
                onClick={() => navigate('/signup')}
                className="rounded-lg bg-indigo-500/20 px-3 py-1.5 text-indigo-200 transition-colors hover:bg-indigo-500/30"
              >
                Sign Up
              </button>
            </div>
          )}
        </nav>
      </div>
    </header>
  );
}
