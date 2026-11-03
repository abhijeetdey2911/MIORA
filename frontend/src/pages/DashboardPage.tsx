import React from 'react';
import { useOutletContext } from 'react-router-dom';
import { HealthCard } from '../components/dashboard/HealthCard';
import { SystemMetrics } from '../components/dashboard/SystemMetrics';
import { PhaseRoadmap } from '../components/dashboard/PhaseRoadmap';
import type { HealthCheckResult } from '../types/health';
import { ArrowUpRight, Terminal, Layers, RefreshCw } from 'lucide-react';

interface LayoutContext {
  health: HealthCheckResult;
  runHealthCheck: () => Promise<void>;
  isRefreshing: boolean;
}

export const DashboardPage: React.FC = () => {
  const { health, runHealthCheck, isRefreshing } = useOutletContext<LayoutContext>();

  return (
    <div className="space-y-6">
      {/* Hero Welcome Banner */}
      <div className="relative rounded-2xl border border-indigo-500/20 bg-gradient-to-r from-indigo-950/30 via-slate-900/60 to-slate-900/30 p-6 sm:p-8 overflow-hidden backdrop-blur-xl">
        <div className="relative z-10 max-w-2xl space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Layers className="w-3.5 h-3.5" />
            <span>Phase 1 Architecture Foundation</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
            Welcome to <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-cyan-400 to-teal-300">JOBHUNTER</span>
          </h1>

          <p className="text-sm text-slate-300 leading-relaxed">
            The personal AI-powered job hunting automation platform. Phase 1 establishes the rock-solid full-stack foundation: React 19 + Vite frontend shell, FastAPI asynchronous backend, PostgreSQL database engine with connection pooling, and Docker containerization.
          </p>

          <div className="pt-2 flex flex-wrap items-center gap-3">
            <button
              onClick={runHealthCheck}
              disabled={isRefreshing}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-600/25 transition disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span>Ping All Systems</span>
            </button>

            <a
              href="http://localhost:8000/api/v1/health"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 transition"
            >
              <Terminal className="w-3.5 h-3.5 text-cyan-400" />
              <span>Direct GET /api/v1/health</span>
              <ArrowUpRight className="w-3.5 h-3.5 text-slate-400" />
            </a>
          </div>
        </div>
      </div>

      {/* Backend & Database Health Cards */}
      <HealthCard health={health} />

      {/* System Telemetry & Live Payload Inspector */}
      <SystemMetrics health={health} />

      {/* 8-Phase Architectural Roadmap */}
      <PhaseRoadmap />
    </div>
  );
};
