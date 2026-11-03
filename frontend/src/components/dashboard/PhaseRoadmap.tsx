import React from 'react';
import { CircleDot, Clock } from 'lucide-react';

interface Phase {
  number: number;
  title: string;
  desc: string;
  status: 'active' | 'pending';
}

const phases: Phase[] = [
  {
    number: 1,
    title: 'Foundational Infrastructure',
    desc: 'React, Vite, Tailwind, FastAPI, SQLAlchemy, PostgreSQL, Docker Compose, Health endpoints.',
    status: 'active',
  },
  {
    number: 2,
    title: 'Database Schema & Core Models',
    desc: 'User entities, Job postings, Resumes, Applications, Status transitions, and Alembic migrations.',
    status: 'pending',
  },
  {
    number: 3,
    title: 'Job Discovery & Scraping Layer',
    desc: 'Multi-board job aggregators, company career page parsers, and deduplication pipeline.',
    status: 'pending',
  },
  {
    number: 4,
    title: 'Resume & Document Intelligence',
    desc: 'PDF parsing, skill taxonomy extraction, and JD-to-Resume semantic alignment.',
    status: 'pending',
  },
  {
    number: 5,
    title: 'Multi-Agent Job Hunting Swarm',
    desc: 'Scout Agent, Tailoring Agent, Application Agent, and orchestrator workflow.',
    status: 'pending',
  },
  {
    number: 6,
    title: 'Automated Application Engine',
    desc: 'Form automation, cover letter drafting, and submission tracking.',
    status: 'pending',
  },
  {
    number: 7,
    title: 'Analytics & Notification Funnel',
    desc: 'Interview conversion rate metrics, email triggers, and telemetry dashboard.',
    status: 'pending',
  },
  {
    number: 8,
    title: 'Hardening & Production Deployment',
    desc: 'CI/CD pipelines, rate limiting, security auditing, and cloud deployment.',
    status: 'pending',
  },
];

export const PhaseRoadmap: React.FC = () => {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 shadow-lg backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">8-Phase Development Roadmap</h3>
          <p className="text-xs text-slate-400">Current Phase: Phase 1 (Foundational Infrastructure)</p>
        </div>
        <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          Phase 1 in progress
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {phases.map((p) => {
          const isActive = p.status === 'active';

          return (
            <div
              key={p.number}
              className={`p-3 rounded-lg border transition ${
                isActive
                  ? 'bg-indigo-950/20 border-indigo-500/40 shadow-sm shadow-indigo-500/10'
                  : 'bg-slate-950/30 border-slate-800/80 opacity-70'
              }`}
            >
              <div className="flex items-center justify-between">
                <span
                  className={`text-xs font-bold font-mono ${
                    isActive ? 'text-indigo-400' : 'text-slate-500'
                  }`}
                >
                  PHASE 0{p.number}
                </span>

                {isActive ? (
                  <span className="flex items-center gap-1 text-[10px] font-medium text-emerald-400">
                    <CircleDot className="w-3 h-3 animate-pulse text-emerald-400" /> Current
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-[10px] font-medium text-slate-400">
                    <Clock className="w-2.5 h-2.5" /> Queued
                  </span>
                )}
              </div>

              <h4
                className={`text-xs font-semibold mt-2 ${
                  isActive ? 'text-slate-100' : 'text-slate-300'
                }`}
              >
                {p.title}
              </h4>
              <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                {p.desc}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
};
