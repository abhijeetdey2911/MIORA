import React from 'react';
import { Database, Server, Cpu, Globe } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="w-full border-t border-slate-800/80 bg-slate-950/40 py-6 px-4 sm:px-6 lg:px-8 mt-auto">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-400">Project JobHunter</span>
          <span>•</span>
          <span>Phase 1 Architecture Foundation</span>
        </div>

        <div className="flex items-center gap-4 text-[11px] font-mono">
          <span className="flex items-center gap-1 text-slate-400">
            <Globe className="w-3.5 h-3.5 text-cyan-400" /> React + Vite
          </span>
          <span className="flex items-center gap-1 text-slate-400">
            <Server className="w-3.5 h-3.5 text-indigo-400" /> FastAPI
          </span>
          <span className="flex items-center gap-1 text-slate-400">
            <Database className="w-3.5 h-3.5 text-emerald-400" /> PostgreSQL
          </span>
          <span className="flex items-center gap-1 text-slate-400">
            <Cpu className="w-3.5 h-3.5 text-amber-400" /> Docker
          </span>
        </div>
      </div>
    </footer>
  );
};
