import { useEffect, useState } from 'react';
import { checkBackendHealth } from '../services/api';
import type { HealthCheckResult } from '../types/health';

const INITIAL_STATE: HealthCheckResult = {
  state: 'checking',
  data: null,
  latencyMs: null,
  error: null,
  lastChecked: null,
};

/** Polls the backend health endpoints (Phase 1 API client) and exposes the latest result. */
export function useBackendHealth(intervalMs = 12000): HealthCheckResult {
  const [health, setHealth] = useState<HealthCheckResult>(INITIAL_STATE);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      const result = await checkBackendHealth();
      if (!cancelled) setHealth(result);
    };

    void run();
    const id = window.setInterval(run, intervalMs);

    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [intervalMs]);

  return health;
}

