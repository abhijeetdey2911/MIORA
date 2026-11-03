import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Search,
  FileText,
  Send,
  BarChart3,
  Settings,
  Lock,
  Layers,
  Server,
} from 'lucide-react';

interface NavItem {
  name: string;
  to: string;
  icon: React.ElementType;
  phase?: string;
  disabled?: boolean;
}

const navItems: NavItem[] = [
  { name: 'Infrastructure Shell', to: '/', icon: LayoutDashboard },
  { name: 'Job Discovery', to: '/jobs', icon: Search, phase: 'Phase 3', disabled: true },
  { name: 'Resume Intelligence', to: '/resumes', icon: FileText, phase: 'Phase 4', disabled: true },
  { name: 'Application Engine', to: '/applications', icon: Send, phase: 'Phase 5', disabled: true },
  { name: 'Analytics & Funnel', to: '/analytics', icon: BarChart3, phase: 'Phase 6', disabled: true },
  { name: 'Environment Settings', to: '/settings', icon: Settings },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 border-r border-slate-800/80 bg-slate-950/50 flex flex-col justify-between shrink-0 hidden md:flex">
      <div className="p-4 space-y-6">
        <div>
          <span className="text-[11px] font-semibold tracking-wider text-slate-400 uppercase px-3">
            Navigation
          </span>
          <nav className="mt-2 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;

              if (item.disabled) {
                return (
                  <div
                    key={item.name}
                    className="flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium text-slate-500 cursor-not-allowed select-none bg-transparent hover:bg-slate-900/30"
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon className="w-4 h-4 text-slate-600" />
                      <span>{item.name}</span>
                    </div>
                    {item.phase && (
                      <span className="inline-flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800/50 text-slate-500 border border-slate-800">
                        <Lock className="w-2.5 h-2.5" />
                        {item.phase}
                      </span>
                    )}
                  </div>
                );
              }

              return (
                <NavLink
                  key={item.name}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition ${
                      isActive
                        ? 'bg-indigo-600/10 text-indigo-400 border border-indigo-500/20 shadow-sm'
                        : 'text-slate-300 hover:text-white hover:bg-slate-900/60'
                    }`
                  }
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className="w-4 h-4" />
                    <span>{item.name}</span>
                  </div>
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Phase 1 Status Info */}
        <div className="rounded-xl border border-indigo-500/20 bg-gradient-to-b from-indigo-950/20 to-slate-900/40 p-3.5 space-y-2">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-400" />
            <h4 className="text-xs font-semibold text-slate-200">Current Scope</h4>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Phase 1 is strictly restricted to foundational architecture: React shell, FastAPI endpoints, PostgreSQL connectivity, and Docker.
          </p>
          <div className="pt-1 flex items-center gap-1.5 text-[10px] text-indigo-300 font-mono">
            <Server className="w-3 h-3" />
            <span>FastAPI 0.110+ • React 19 • PG 16</span>
          </div>
        </div>
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-slate-800/80">
        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <span>Release v0.1.0</span>
          <span className="font-mono text-emerald-400">Phase 1 Active</span>
        </div>
      </div>
    </aside>
  );
};
