import React from 'react';
import type { ConnectionState } from '../../types/health';
import { Wifi, WifiOff, AlertTriangle, RefreshCw } from 'lucide-react';

interface StatusBadgeProps {
  state: ConnectionState;
  latencyMs?: number | null;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  state,
  latencyMs,
  onRefresh,
  isRefreshing = false,
}) => {
  const getBadgeConfig = () => {
    switch (state) {
      case 'online':
        return {
          bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
          dot: 'bg-emerald-400',
          label: 'Backend Online',
          icon: Wifi,
        };
      case 'degraded':
        return {
          bg: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
          dot: 'bg-amber-400',
          label: 'Database Degraded',
          icon: AlertTriangle,
        };
      case 'checking':
        return {
          bg: 'bg-sky-500/10 border-sky-500/30 text-sky-400',
          dot: 'bg-sky-400',
          label: 'Connecting...',
          icon: RefreshCw,
        };
      case 'offline':
      default:
        return {
          bg: 'bg-rose-500/10 border-rose-500/30 text-rose-400',
          dot: 'bg-rose-400',
          label: 'Backend Offline',
          icon: WifiOff,
        };
    }
  };

  const config = getBadgeConfig();
  const Icon = config.icon;

  return (
    <div className="flex items-center gap-2">
      <div
        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-medium tracking-wide shadow-sm backdrop-blur-md transition-all ${config.bg}`}
      >
        <span className="relative flex h-2 w-2">
          {state !== 'offline' && (
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${config.dot}`}
            />
          )}
          <span className={`relative inline-flex rounded-full h-2 w-2 ${config.dot}`} />
        </span>
        <Icon className={`w-3.5 h-3.5 ${state === 'checking' ? 'animate-spin' : ''}`} />
        <span>{config.label}</span>
        {latencyMs !== undefined && latencyMs !== null && state !== 'offline' && (
          <span className="text-[10px] opacity-75 font-mono ml-0.5 border-l border-current/20 pl-1.5">
            {latencyMs}ms
          </span>
        )}
      </div>

      {onRefresh && (
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          title="Refresh health status"
          className="p-1.5 rounded-lg border border-slate-800 bg-slate-900/60 text-slate-400 hover:text-slate-100 hover:border-slate-700 transition disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
        </button>
      )}
    </div>
  );
};
