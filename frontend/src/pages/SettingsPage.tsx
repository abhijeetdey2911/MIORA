import React from 'react';
import { Settings, Database, Globe } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="border-b border-slate-800 pb-4">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <Settings className="w-5 h-5 text-indigo-400" />
          Environment & System Configuration
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Review foundational runtime configurations and service parameters for Project JobHunter.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3">
          <div className="flex items-center gap-2 text-indigo-400 font-semibold text-sm">
            <Globe className="w-4 h-4" />
            <span>Frontend Client Environment</span>
          </div>
          <div className="text-xs space-y-2 text-slate-300 font-mono">
            <div className="flex justify-between py-1 border-b border-slate-800">
              <span className="text-slate-400">VITE_API_URL:</span>
              <span className="text-emerald-400">http://localhost:8000</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800">
              <span className="text-slate-400">DEV SERVER PORT:</span>
              <span>5173</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">ROUTER:</span>
              <span>React Router v7</span>
            </div>
          </div>
        </div>

        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3">
          <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
            <Database className="w-4 h-4" />
            <span>Database Connection Pool</span>
          </div>
          <div className="text-xs space-y-2 text-slate-300 font-mono">
            <div className="flex justify-between py-1 border-b border-slate-800">
              <span className="text-slate-400">POOL SIZE:</span>
              <span>5 connections</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800">
              <span className="text-slate-400">MAX OVERFLOW:</span>
              <span>10 connections</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">POOL PRE-PING:</span>
              <span className="text-emerald-400">Enabled</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
