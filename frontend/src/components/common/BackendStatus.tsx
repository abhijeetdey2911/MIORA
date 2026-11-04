import type { ConnectionState, HealthCheckResult } from '../../types/health';

interface BackendStatusProps {
  health: HealthCheckResult;
}

const STATE_STYLES: Record<ConnectionState, { dot: string; label: string }> = {
  online: { dot: 'bg-emerald-500', label: 'Backend online' },
  degraded: { dot: 'bg-amber-500', label: 'Database unreachable' },
  offline: { dot: 'bg-rose-500', label: 'Backend offline' },
  checking: { dot: 'bg-subtle animate-pulse', label: 'Checking backend…' },
};

/** Compact Phase 1 connectivity indicator. */
export function BackendStatus({ health }: BackendStatusProps) {
  const { dot, label } = STATE_STYLES[health.state];
  const showLatency = health.state === 'online' || health.state === 'degraded';

  return (
    <div
      role="status"
      title={health.error ?? label}
      className="flex items-center gap-2.5 rounded-xl border border-line bg-surface-2 px-3 py-2.5 text-xs"
    >
      <span className={`h-2 w-2 shrink-0 rounded-full ${dot}`} />
      <span className="font-medium text-ink">{label}</span>
      {showLatency && health.latencyMs !== null && (
        <span className="ml-auto font-mono text-subtle">{health.latencyMs}ms</span>
      )}
    </div>
  );
}

