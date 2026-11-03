import React from 'react';
import { StatusBadge } from './StatusBadge';
import type { ConnectionState } from '../../types/health';
import { Terminal, ExternalLink, Sparkles } from 'lucide-react';

interface HeaderProps {
  connectionState: ConnectionState;
  latencyMs?: number | null;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  connectionState,
  latencyMs,
  onRefresh,
  isRefreshing,
}) => {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-xl">
      <div className="flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        {/* Brand identity */}
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 via-indigo-500 to-fuchsia-500 p-[1px] shadow-lg shadow-indigo-500/20">
            <div className="w-full h-full bg-slate-950 rounded-[11px] flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-indigo-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold tracking-tight text-lg text-white font-mono">
                JOB<span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400">HUNTER</span>
              </span>
              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono">
                PHASE 1
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium tracking-wide hidden sm:block">
              AI-Powered Autonomous Job Hunt Platform
            </p>
          </div>
        </div>

        {/* Right side status indicator & links */}
        <div className="flex items-center gap-3 sm:gap-4">
          <StatusBadge
            state={connectionState}
            latencyMs={latencyMs}
            onRefresh={onRefresh}
            isRefreshing={isRefreshing}
          />

          <a
            href="http://localhost:8000/api/v1/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition"
          >
            <Terminal className="w-3.5 h-3.5 text-cyan-400" />
            <span>API Docs</span>
            <ExternalLink className="w-3 h-3 text-slate-500" />
          </a>
        </div>
      </div>
    </header>
  );
};
