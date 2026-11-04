import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowUpRight,
  Award,
  Briefcase,
  CalendarCheck,
  ExternalLink,
  Layers,
  MapPin,
  Send,
  SlidersHorizontal,
  Sparkles,
  X,
} from 'lucide-react';
import type { DashboardPreferenceCard } from '../../types/multiAgent';

interface PreferencePerformanceProps {
  items: readonly DashboardPreferenceCard[];
}

export function PreferencePerformance({ items }: PreferencePerformanceProps) {
  const [selectedPreference, setSelectedPreference] =
    useState<DashboardPreferenceCard | null>(null);

  useEffect(() => {
    if (!selectedPreference) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setSelectedPreference(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedPreference]);

  return (
    <section
      aria-labelledby="preference-performance-heading"
      className="rounded-2xl border border-line bg-surface p-5 shadow-card"
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2
              id="preference-performance-heading"
              className="text-sm font-semibold text-ink"
            >
              Preference Performance
            </h2>
            <span className="rounded-full border border-line bg-surface-2 px-2 py-0.5 text-[10px] font-medium text-muted">
              PostgreSQL Live
            </span>
          </div>
          <p className="mt-0.5 text-xs text-muted">
            Independent discovery, matching, and application metrics tracked
            separately for each job preference.
          </p>
        </div>

        <Link
          to="/preferences"
          className="inline-flex items-center gap-1 self-start rounded-xl border border-line bg-surface-2 px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:border-subtle/50 sm:self-auto"
        >
          <SlidersHorizontal
            className="h-3.5 w-3.5 text-accent"
            strokeWidth={1.9}
          />
          Manage Preferences
        </Link>
      </div>

      {items.length === 0 ? (
        <div className="mt-4 rounded-xl border border-dashed border-line bg-surface-2 p-6 text-center">
          <p className="text-sm font-medium text-ink">
            No job preferences created yet
          </p>
          <p className="mt-1 text-xs text-muted">
            Create one or more job preferences to run independent multi-agent
            workflows.
          </p>
          <Link
            to="/preferences"
            className="mt-3 inline-flex items-center gap-1.5 rounded-xl bg-accent px-3.5 py-2 text-xs font-semibold text-white"
          >
            + Create Preference
          </Link>
        </div>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
          {items.map((item) => (
            <article
              key={item.preference_id}
              className="flex flex-col justify-between rounded-2xl border border-line bg-surface-2 p-4 transition-colors hover:border-subtle/40"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="inline-flex h-6 items-center justify-center rounded-lg bg-accent-soft px-2 text-xs font-semibold text-accent-ink">
                        {item.code}
                      </span>
                      <h3 className="truncate text-sm font-semibold text-ink">
                        {item.preference_name}
                      </h3>
                    </div>

                    <p className="mt-1.5 flex items-center gap-1.5 text-xs text-muted">
                      <MapPin
                        className="h-3.5 w-3.5 shrink-0 text-subtle"
                        strokeWidth={1.9}
                      />
                      <span className="truncate">
                        {item.locations.join(', ')} · {item.work_mode}
                      </span>
                    </p>
                  </div>

                  <div className="flex shrink-0 items-center gap-1.5">
                    <span className="rounded-full border border-line bg-surface px-2 py-0.5 text-[10px] font-medium capitalize text-muted">
                      {item.workflow_status}
                    </span>
                    <span
                      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium ${
                        item.is_active
                          ? 'bg-emerald-500/10 text-emerald-600 dark:bg-emerald-400/15 dark:text-emerald-300'
                          : 'bg-surface text-muted'
                      }`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          item.is_active ? 'bg-emerald-500' : 'bg-subtle'
                        }`}
                      />
                      {item.is_active ? 'Active' : 'Paused'}
                    </span>
                  </div>
                </div>

                {/* 6 Independent Preference Metrics */}
                <div className="mt-3.5 grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
                  <div className="flex flex-col justify-between rounded-xl border border-line bg-surface px-2.5 py-2">
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-sm font-semibold leading-none text-ink">
                        {item.jobs_discovered}
                      </p>
                      <Briefcase
                        className="h-3 w-3 shrink-0 text-accent"
                        strokeWidth={1.9}
                      />
                    </div>
                    <p className="mt-1 text-[10px] font-medium leading-tight text-muted">
                      Discovered
                    </p>
                  </div>

                  <div className="flex flex-col justify-between rounded-xl border border-line bg-surface px-2.5 py-2">
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-sm font-semibold leading-none text-ink">
                        {item.matching_jobs}
                      </p>
                      <Sparkles
                        className="h-3 w-3 shrink-0 text-amber-500"
                        strokeWidth={1.9}
                      />
                    </div>
                    <p className="mt-1 text-[10px] font-medium leading-tight text-muted">
                      Matching
                    </p>
                  </div>

                  <div className="flex flex-col justify-between rounded-xl border border-line bg-surface px-2.5 py-2">
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-sm font-semibold leading-none text-ink">
                        {item.shortlisted_jobs}
                      </p>
                      <Layers
                        className="h-3 w-3 shrink-0 text-violet-500"
                        strokeWidth={1.9}
                      />
                    </div>
                    <p className="mt-1 text-[10px] font-medium leading-tight text-muted">
                      Shortlisted
                    </p>
                  </div>

                  <div className="flex flex-col justify-between rounded-xl border border-line bg-surface px-2.5 py-2">
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-sm font-semibold leading-none text-ink">
                        {item.applications_submitted}
                      </p>
                      <Send
                        className="h-3 w-3 shrink-0 text-sky-500"
                        strokeWidth={1.9}
                      />
                    </div>
                    <p className="mt-1 text-[10px] font-medium leading-tight text-muted">
                      Applications
                    </p>
                  </div>

                  <div className="flex flex-col justify-between rounded-xl border border-line bg-surface px-2.5 py-2">
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-sm font-semibold leading-none text-ink">
                        {item.interviews}
                      </p>
                      <CalendarCheck
                        className="h-3 w-3 shrink-0 text-emerald-500"
                        strokeWidth={1.9}
                      />
                    </div>
                    <p className="mt-1 text-[10px] font-medium leading-tight text-muted">
                      Interviews
                    </p>
                  </div>

                  <div className="flex flex-col justify-between rounded-xl border border-line bg-surface px-2.5 py-2">
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-sm font-semibold leading-none text-ink">
                        {item.offers}
                      </p>
                      <Award
                        className="h-3 w-3 shrink-0 text-amber-500"
                        strokeWidth={1.9}
                      />
                    </div>
                    <p className="mt-1 text-[10px] font-medium leading-tight text-muted">
                      Offers
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-4 flex items-center justify-between gap-2 border-t border-line pt-3">
                <div className="flex flex-wrap gap-1">
                  {item.target_roles.slice(0, 2).map((role) => (
                    <span
                      key={role}
                      className="rounded-md border border-line bg-surface px-2 py-0.5 text-[11px] text-muted"
                    >
                      {role}
                    </span>
                  ))}
                  {item.target_roles.length > 2 && (
                    <span className="px-1 text-[11px] text-subtle">
                      +{item.target_roles.length - 2}
                    </span>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => setSelectedPreference(item)}
                  className="inline-flex shrink-0 items-center gap-1 rounded-xl bg-accent-soft px-3 py-1.5 text-xs font-semibold text-accent-ink transition-colors hover:bg-accent hover:text-white"
                >
                  View Results
                  <ArrowUpRight className="h-3.5 w-3.5" strokeWidth={2.1} />
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      {selectedPreference && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="preference-results-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
        >
          <div
            aria-hidden="true"
            onClick={() => setSelectedPreference(null)}
            className="fixed inset-0 bg-black/50 backdrop-blur-[2px]"
          />

          <div className="relative z-10 w-full max-w-xl rounded-2xl border border-line bg-surface p-6 shadow-card">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="rounded-lg bg-accent-soft px-2 py-0.5 text-xs font-semibold text-accent-ink">
                    {selectedPreference.code}
                  </span>
                  <h3
                    id="preference-results-title"
                    className="text-base font-semibold text-ink"
                  >
                    {selectedPreference.preference_name} — Results Breakdown
                  </h3>
                </div>
                <p className="mt-1 text-xs text-muted">
                  Workflow Status:{' '}
                  <span className="font-medium capitalize text-ink">
                    {selectedPreference.workflow_status}
                  </span>{' '}
                  ·{' '}
                  {selectedPreference.has_approved_resume
                    ? 'Approved Resume Linked'
                    : 'No Approved Resume Yet'}
                </p>
              </div>

              <button
                type="button"
                onClick={() => setSelectedPreference(null)}
                aria-label="Close preference results"
                className="rounded-xl p-1.5 text-muted transition-colors hover:bg-surface-2 hover:text-ink"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="mt-4 grid grid-cols-6 gap-2 rounded-xl border border-line bg-surface-2 p-3 text-center">
              <div>
                <p className="text-sm font-semibold text-ink">
                  {selectedPreference.jobs_discovered}
                </p>
                <p className="text-[10px] text-muted">Discovered</p>
              </div>
              <div>
                <p className="text-sm font-semibold text-ink">
                  {selectedPreference.matching_jobs}
                </p>
                <p className="text-[10px] text-muted">Matching</p>
              </div>
              <div>
                <p className="text-sm font-semibold text-ink">
                  {selectedPreference.shortlisted_jobs}
                </p>
                <p className="text-[10px] text-muted">Shortlisted</p>
              </div>
              <div>
                <p className="text-sm font-semibold text-ink">
                  {selectedPreference.applications_submitted}
                </p>
                <p className="text-[10px] text-muted">Applications</p>
              </div>
              <div>
                <p className="text-sm font-semibold text-ink">
                  {selectedPreference.interviews}
                </p>
                <p className="text-[10px] text-muted">Interviews</p>
              </div>
              <div>
                <p className="text-sm font-semibold text-ink">
                  {selectedPreference.offers}
                </p>
                <p className="text-[10px] text-muted">Offers</p>
              </div>
            </div>

            <div className="mt-4">
              <p className="text-xs font-semibold text-ink">
                Matched Opportunities for {selectedPreference.preference_name}
              </p>
              {selectedPreference.recent_matches.length === 0 ? (
                <p className="mt-2 rounded-xl border border-line bg-surface-2 p-4 text-xs text-muted">
                  No jobs have been evaluated for this preference yet. Press
                  &quot;Start JobHunter&quot; to run Agent 1 (Discovery) and
                  Agent 2 (Matching).
                </p>
              ) : (
                <ul className="mt-2 max-h-64 divide-y divide-line overflow-y-auto rounded-xl border border-line bg-surface-2 px-3.5">
                  {selectedPreference.recent_matches.map((job) => (
                    <li
                      key={job.match_id}
                      className="flex items-center justify-between gap-3 py-2.5 text-xs"
                    >
                      <div className="min-w-0">
                        <p className="truncate font-semibold text-ink">
                          {job.title}
                        </p>
                        <p className="text-[11px] text-muted">
                          {job.company} · {job.location || job.work_mode || 'Remote'}
                        </p>
                      </div>

                      <div className="flex shrink-0 items-center gap-2">
                        <span className="rounded-md bg-accent-soft px-2 py-0.5 text-[11px] font-semibold text-accent-ink">
                          {job.match_score}% match
                        </span>
                        {job.shortlisted && (
                          <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-600 dark:text-emerald-300">
                            Shortlisted
                          </span>
                        )}
                        {job.official_job_url && (
                          <a
                            href={job.official_job_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-muted hover:text-ink"
                            title="Open official job listing"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="mt-5 flex items-center justify-between gap-2">
              <Link
                to={`/applications?preference_id=${selectedPreference.preference_id}`}
                onClick={() => setSelectedPreference(null)}
                className="text-xs font-medium text-accent-ink hover:underline"
              >
                Open in Applications & Discovery →
              </Link>
              <button
                type="button"
                onClick={() => setSelectedPreference(null)}
                className="rounded-xl bg-accent px-4 py-2 text-xs font-semibold text-white shadow-card transition hover:brightness-105"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
