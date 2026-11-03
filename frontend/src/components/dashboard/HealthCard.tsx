import React from 'react';
import type { HealthCheckResult } from '../../types/health';
import { Server, Database, CheckCircle2, AlertTriangle, XCircle, Clock, Zap } from 'lucide-react';

interface HealthCardProps {
  health: HealthCheckResult;
}

export const HealthCard: React.FC<HealthCardProps> = ({ health }) => {
  const isOnline = health.state === 'online';
  const isDegraded = health.state === 'degraded';
  const isOffline = health.state === 'offline';

  const formatUptime = (seconds?: number) => {
    if (seconds === undefined) return 'N/A';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    if (hrs > 0) return `${hrs}h ${mins}m ${secs}s`;
    if (mins > 0) return `${mins}m ${secs}s`;
    return `${secs}s`;
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Backend API Service Card */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 shadow-lg backdrop-blur-sm relative overflow-hidden">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-xl border ${
              isOffline
                ? 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                : 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400'
            }`}>
              <Server className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-100">FastAPI Backend</h3>
              <p className="text-xs text-slate-400 font-mono">http://localhost:8000</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {isOffline ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
                <XCircle className="w-3.5 h-3.5" /> Offline
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="w-3.5 h-3.5" /> Operational
              </span>
            )}
          </div>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-3 pt-4 border-t border-slate-800/80">
          <div>
            <span className="text-[11px] text-slate-400 flex items-center gap-1">
              <Zap className="w-3 h-3 text-amber-400" /> Ping Latency
            </span>
            <span className="text-sm font-semibold text-slate-200 font-mono mt-0.5 block">
              {health.latencyMs !== null ? `${health.latencyMs} ms` : 'N/A'}
            </span>
          </div>

          <div>
            <span className="text-[11px] text-slate-400 flex items-center gap-1">
              <Clock className="w-3 h-3 text-cyan-400" /> Uptime
            </span>
            <span className="text-sm font-semibold text-slate-200 font-mono mt-0.5 block">
              {formatUptime(health.data?.services.api.uptime_seconds)}
            </span>
          </div>
        </div>

        {health.error && (
          <div className="mt-3 p-2.5 rounded-lg bg-rose-950/20 border border-rose-800/30 text-[11px] text-rose-300">
            {health.error}
          </div>
        )}
      </div>

      {/* Database Service Card */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 shadow-lg backdrop-blur-sm relative overflow-hidden">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-xl border ${
              isOnline
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                : 'bg-amber-500/10 border-amber-500/20 text-amber-400'
            }`}>
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-100">PostgreSQL Database</h3>
              <p className="text-xs text-slate-400 font-mono">localhost:5432 / jobhunter</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {isOnline ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="w-3.5 h-3.5" /> Connected
              </span>
            ) : isDegraded ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <AlertTriangle className="w-3.5 h-3.5" /> Disconnected
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">
                Unknown
              </span>
            )}
          </div>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-3 pt-4 border-t border-slate-800/80">
          <div>
            <span className="text-[11px] text-slate-400">Dialect / Driver</span>
            <span className="text-sm font-semibold text-slate-200 font-mono mt-0.5 block">
              {health.data?.services.database.dialect || 'postgresql'}
            </span>
          </div>

          <div>
            <span className="text-[11px] text-slate-400">Query Ping</span>
            <span className="text-sm font-semibold text-slate-200 font-mono mt-0.5 block">
              {health.data?.services.database.latency_ms !== null &&
              health.data?.services.database.latency_ms !== undefined
                ? `${health.data.services.database.latency_ms} ms`
                : 'Pending'}
            </span>
          </div>
        </div>

        {health.data?.services.database.error && (
          <div className="mt-3 p-2.5 rounded-lg bg-amber-950/20 border border-amber-800/30 text-[11px] text-amber-300 font-mono truncate">
            {health.data.services.database.error}
          </div>
        )}
      </div>
    </div>
  );
};
