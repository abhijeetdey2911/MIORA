import type { HealthCheckResult, HealthResponse } from '../types/health';

const RAW_URL = import.meta.env.VITE_API_URL;
const BACKEND_BASE_URL = typeof RAW_URL === 'string' ? RAW_URL.replace(/\/+$/, '') : '';

export async function checkBackendHealth(): Promise<HealthCheckResult> {
  const startTime = performance.now();
  const endpoints = BACKEND_BASE_URL
    ? [
        `${BACKEND_BASE_URL}/api/v1/health`,
        '/api/v1/health',
        `${BACKEND_BASE_URL}/health`,
        '/health',
      ]
    : [
        '/api/v1/health',
        '/health',
      ];

  for (const url of endpoints) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4000);

      const response = await fetch(url, {
        headers: {
          Accept: 'application/json',
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        const latencyMs = Math.round(performance.now() - startTime);
        const data: HealthResponse = await response.json();
        
        const state = data.status === 'healthy' 
          ? 'online' 
          : data.status === 'degraded' 
            ? 'degraded' 
            : 'offline';

        return {
          state,
          data,
          latencyMs,
          error: null,
          lastChecked: new Date(),
        };
      }
    } catch {
      // Continue to next fallback endpoint
      continue;
    }
  }

  // All endpoints failed
  const latencyMs = Math.round(performance.now() - startTime);
  return {
    state: 'offline',
    data: null,
    latencyMs,
    error: 'Backend unreachable. Verify the backend service is running.',
    lastChecked: new Date(),
  };
}
