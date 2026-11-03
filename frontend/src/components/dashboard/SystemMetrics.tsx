import React, { useState } from 'react';
import type { HealthCheckResult } from '../../types/health';
import { Code, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';

interface SystemMetricsProps {
  health: HealthCheckResult;
}

export const SystemMetrics: React.FC<SystemMetricsProps> = ({ health }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (health.data) {
      navigator.clipboard.writeText(JSON.stringify(health.data, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 shadow-lg backdrop-blur-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Code className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-slate-100">System Telemetry & Live Payload</h3>
        </div>

        <div className="flex items-center gap-2">
          {health.data && (
            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium text-slate-300 hover:text-white bg-slate-800/60 border border-slate-700 transition"
            >
              {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              <span>{copied ? 'Copied' : 'Copy JSON'}</span>
            </button>
          )}

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 transition"
          >
            <span>{isExpanded ? 'Collapse' : 'Inspect Payload'}</span>
            {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/80">
          <span className="text-slate-400 block text-[11px]">Runtime Env</span>
          <span className="font-semibold text-slate-200 font-mono mt-0.5 block capitalize">
            {health.data?.environment || 'development'}
          </span>
        </div>

        <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/80">
          <span className="text-slate-400 block text-[11px]">Python Version</span>
          <span className="font-semibold text-slate-200 font-mono mt-0.5 block">
            {health.data?.system.python_version || '3.12 / 3.14'}
          </span>
        </div>

        <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/80">
          <span className="text-slate-400 block text-[11px]">Target Endpoints</span>
          <span className="font-semibold text-slate-200 font-mono mt-0.5 block">
            /api/v1/health, /health
          </span>
        </div>

        <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/80">
          <span className="text-slate-400 block text-[11px]">Last Checked</span>
          <span className="font-semibold text-slate-200 font-mono mt-0.5 block">
            {health.lastChecked ? health.lastChecked.toLocaleTimeString() : 'Never'}
          </span>
        </div>
      </div>

      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-slate-800/80">
          <div className="flex items-center justify-between pb-2 text-[11px] text-slate-400 font-mono">
            <span>GET /api/v1/health RESPONSE</span>
            <span className="text-emerald-400">HTTP 200 OK</span>
          </div>
          <pre className="p-4 rounded-lg bg-slate-950 border border-slate-800 font-mono text-[11px] text-emerald-400/90 overflow-x-auto max-h-64 scrollbar-thin">
            {health.data
              ? JSON.stringify(health.data, null, 2)
              : JSON.stringify({ status: 'offline', error: health.error }, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};
