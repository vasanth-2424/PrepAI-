import { useEffect, useState } from 'react';

import { api } from '../../services/api';
import type { HealthResponse } from '../../types';

type Status = 'loading' | 'healthy' | 'error';

export function HealthStatus() {
  const [status, setStatus] = useState<Status>('loading');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function checkHealth() {
      try {
        const data = await api.getHealth();
        if (!cancelled) {
          setHealth(data);
          setStatus('healthy');
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to reach backend');
          setStatus('error');
        }
      }
    }

    checkHealth();

    return () => {
      cancelled = true;
    };
  }, []);

  const statusColor =
    status === 'healthy' ? 'bg-emerald-400' : status === 'error' ? 'bg-red-400' : 'bg-amber-400';

  const statusLabel =
    status === 'healthy' ? 'Connected' : status === 'error' ? 'Disconnected' : 'Checking...';

  return (
    <section id="status" className="mx-auto max-w-6xl px-6 py-16">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-8">
        <div className="mb-6 flex items-center gap-3">
          <span className={`h-3 w-3 rounded-full ${statusColor}`} />
          <h2 className="text-xl font-semibold text-white">Backend Status: {statusLabel}</h2>
        </div>

        {status === 'loading' && (
          <p className="text-slate-400">Checking API health endpoint...</p>
        )}

        {status === 'healthy' && health && (
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <dt className="text-xs uppercase tracking-wider text-slate-500">Service</dt>
              <dd className="mt-1 font-medium text-white">{health.service}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wider text-slate-500">Status</dt>
              <dd className="mt-1 font-medium capitalize text-emerald-400">{health.status}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wider text-slate-500">Environment</dt>
              <dd className="mt-1 font-medium text-white">{health.environment}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wider text-slate-500">Version</dt>
              <dd className="mt-1 font-medium text-white">{health.version}</dd>
            </div>
          </dl>
        )}

        {status === 'error' && (
          <div>
            <p className="text-red-400">{error}</p>
            <p className="mt-2 text-sm text-slate-500">
              Make sure the backend is running on port 8000.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
