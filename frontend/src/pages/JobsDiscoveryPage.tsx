import { useEffect, useState } from 'react';
import {
  AlertCircle,
  Briefcase,
  CheckCircle2,
  ExternalLink,
  Filter,
  Globe,
  Layers,
  Mail,
  MapPin,
  Search,
  ShieldAlert,
  Sparkles,
  UserCheck,
} from 'lucide-react';
import {
  getJobsSummary,
  listJobMatches,
  listJobSources,
  toggleJobSource,
  toggleMatchShortlist,
} from '../services/multiAgentService';
import { getPreferences } from '../services/preferenceService';
import type {
  JobDiscoverySummary,
  JobMatchItem,
  JobSourceItem,
} from '../types/multiAgent';
import type { JobPreference } from '../types/preference';

export function JobsDiscoveryPage() {
  const [matches, setMatches] = useState<JobMatchItem[]>([]);
  const [preferences, setPreferences] = useState<JobPreference[]>([]);
  const [sources, setSources] = useState<JobSourceItem[]>([]);
  const [summary, setSummary] = useState<JobDiscoverySummary | null>(null);
  const [loading, setLoading] = useState(true);

  const [selectedPreferenceId, setSelectedPreferenceId] = useState<string>('');
  const [minScore, setMinScore] = useState<number>(0);
  const [shortlistedOnly, setShortlistedOnly] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [workModeFilter, setWorkModeFilter] = useState<string>('');
  const [sourceFilter, setSourceFilter] = useState<string>('');
  const [expandedMatchId, setExpandedMatchId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      listJobMatches({
        preference_id: selectedPreferenceId || undefined,
        shortlisted_only: shortlistedOnly,
        min_score: minScore > 0 ? minScore : undefined,
        search: searchQuery || undefined,
      }),
      getPreferences(),
      listJobSources(),
      getJobsSummary({
        preference_id: selectedPreferenceId || undefined,
      }),
    ])
      .then(([matchRows, prefRows, srcRows, summaryData]) => {
        if (!cancelled) {
          setMatches(matchRows);
          setPreferences(prefRows);
          setSources(srcRows);
          setSummary(summaryData);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedPreferenceId, shortlistedOnly, minScore, searchQuery]);

  const selectedPreference = preferences.find(
    (p) => p.id === selectedPreferenceId,
  );

  const filteredMatches = matches.filter((m) => {
    const job = m.discovered_job;
    if (
      workModeFilter &&
      (job.work_mode || '').toLowerCase() !== workModeFilter.toLowerCase()
    ) {
      return false;
    }
    if (sourceFilter && job.source_name !== sourceFilter) {
      return false;
    }
    return true;
  });

  const handleToggleShortlist = async (match: JobMatchItem) => {
    try {
      const updated = await toggleMatchShortlist(match.id, !match.shortlisted);
      setMatches((prev) =>
        prev.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch {
      // Ignore toggle error
    }
  };

  const handleToggleSource = async (
    sourceId: string,
    currentEnabled: boolean,
  ) => {
    try {
      const updated = await toggleJobSource(sourceId, !currentEnabled);
      setSources((prev) =>
        prev.map((s) => (s.id === updated.id ? updated : s)),
      );
      if (summary) {
        setSummary({
          ...summary,
          sources: summary.sources.map((s) =>
            s.id === updated.id ? updated : s,
          ),
        });
      }
    } catch {
      // Ignore toggle error
    }
  };

  // Metrics calculation
  const totalDiscovered = summary?.total_discovered ?? matches.length;
  const totalEvaluated = summary?.total_evaluated ?? matches.length;
  const matchingCount =
    summary?.matching_count ?? matches.filter((m) => m.is_matching).length;
  const shortlistedCount =
    summary?.shortlisted_count ?? matches.filter((m) => m.shortlisted).length;
  const locIneligibleCount =
    summary?.location_ineligible_count ??
    matches.filter((m) =>
      m.reasons_for_rejection.some((r) => r.includes('Location Ineligible')),
    ).length;
  const expIneligibleCount =
    summary?.experience_ineligible_count ??
    matches.filter((m) =>
      m.reasons_for_rejection.some((r) => r.includes('Experience Ineligible')),
    ).length;

  return (
    <div className="space-y-4">
      {/* Metrics Bar */}
      <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <div className="rounded-2xl border border-line bg-surface p-3 shadow-card">
          <p className="text-[11px] font-medium text-muted">Discovered</p>
          <p className="mt-1 text-xl font-bold text-ink">{totalDiscovered}</p>
          <span className="text-[10px] text-muted">Total scraped listings</span>
        </div>

        <div className="rounded-2xl border border-line bg-surface p-3 shadow-card">
          <p className="text-[11px] font-medium text-muted">Evaluated</p>
          <p className="mt-1 text-xl font-bold text-ink">{totalEvaluated}</p>
          <span className="text-[10px] text-muted">AI & rule analyzed</span>
        </div>

        <div className="rounded-2xl border border-line bg-surface p-3 shadow-card">
          <p className="text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
            Matching / Eligible
          </p>
          <p className="mt-1 text-xl font-bold text-emerald-600 dark:text-emerald-400">
            {matchingCount}
          </p>
          <span className="text-[10px] text-muted">Eligible for role & city</span>
        </div>

        <div className="rounded-2xl border border-line bg-surface p-3 shadow-card">
          <p className="text-[11px] font-medium text-violet-600 dark:text-violet-400">
            Shortlisted
          </p>
          <p className="mt-1 text-xl font-bold text-violet-600 dark:text-violet-400">
            {shortlistedCount}
          </p>
          <span className="text-[10px] text-muted">Ready for route discovery</span>
        </div>

        <div className="rounded-2xl border border-line bg-surface p-3 shadow-card">
          <p className="text-[11px] font-medium text-rose-500">
            Location Ineligible
          </p>
          <p className="mt-1 text-xl font-bold text-rose-500">
            {locIneligibleCount}
          </p>
          <span className="text-[10px] text-muted">Excluded by location mode</span>
        </div>

        <div className="rounded-2xl border border-line bg-surface p-3 shadow-card">
          <p className="text-[11px] font-medium text-amber-500">
            Experience Ineligible
          </p>
          <p className="mt-1 text-xl font-bold text-amber-500">
            {expIneligibleCount}
          </p>
          <span className="text-[10px] text-muted">Seniority level mismatch</span>
        </div>
      </section>

      {/* Source Adapters Status Pills */}
      <section className="rounded-2xl border border-line bg-surface p-3.5 shadow-card">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-ink">
            <Globe className="h-3.5 w-3.5 text-accent" />
            <span>Configured Job Discovery Source Adapters</span>
          </div>
          <span className="text-[11px] text-muted">
            Click any adapter pill to toggle enabled/disabled
          </span>
        </div>

        <div className="mt-2.5 flex flex-wrap gap-2">
          {sources.map((src) => (
            <button
              key={src.id}
              type="button"
              onClick={() => handleToggleSource(src.id, src.is_enabled)}
              className={`inline-flex items-center gap-2 rounded-xl border px-3 py-1.5 text-xs font-medium transition ${
                src.is_enabled
                  ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                  : 'border-line bg-surface-2 text-muted opacity-60 hover:opacity-100'
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  src.is_enabled ? 'bg-emerald-500 animate-pulse' : 'bg-muted'
                }`}
              />
              <span className="font-semibold">{src.name}</span>
              <span className="text-[10px] text-muted">
                ({src.adapter_type})
              </span>
              <span className="rounded-md border border-line/60 bg-surface px-1.5 py-0.2 text-[9px] font-semibold text-ink">
                {src.is_enabled ? 'Active' : 'Disabled'}
              </span>
            </button>
          ))}
        </div>
      </section>

      {/* Filters Bar */}
      <section className="rounded-2xl border border-line bg-surface p-4 shadow-card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-accent" />
            <h2 className="text-sm font-semibold text-ink">
              Job Discovery & AI Matching (Agents 1, 2 & 3)
            </h2>
            <span className="rounded-full bg-surface-2 px-2.5 py-0.5 text-xs font-medium text-muted">
              {filteredMatches.length} evaluated listings
            </span>
          </div>

          <label className="inline-flex cursor-pointer items-center gap-2 text-xs font-medium text-ink">
            <input
              type="checkbox"
              checked={shortlistedOnly}
              onChange={(e) => setShortlistedOnly(e.target.checked)}
              className="rounded border-line text-accent focus:ring-accent"
            />
            Shortlisted only
          </label>
        </div>

        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-3.5 w-3.5 text-subtle" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search title, company, location..."
              className="w-full rounded-xl border border-line bg-surface-2 py-2 pl-8 pr-3 text-xs text-ink placeholder:text-subtle focus:border-accent focus:outline-none"
            />
          </div>

          <select
            value={selectedPreferenceId}
            onChange={(e) => setSelectedPreferenceId(e.target.value)}
            aria-label="Filter by job preference"
            className="rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink focus:border-accent focus:outline-none"
          >
            <option value="">All Job Preferences</option>
            {preferences.map((pref) => (
              <option key={pref.id} value={pref.id}>
                {pref.preference_name} ({pref.is_active ? 'Active' : 'Paused'})
              </option>
            ))}
          </select>

          <select
            value={workModeFilter}
            onChange={(e) => setWorkModeFilter(e.target.value)}
            aria-label="Filter by work mode"
            className="rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink focus:border-accent focus:outline-none"
          >
            <option value="">All Work Modes</option>
            <option value="Remote">Remote</option>
            <option value="Hybrid">Hybrid</option>
            <option value="On-site">On-site</option>
          </select>

          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            aria-label="Filter by job source"
            className="rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink focus:border-accent focus:outline-none"
          >
            <option value="">All Job Sources</option>
            {sources.map((src) => (
              <option key={src.id} value={src.name}>
                {src.name}
              </option>
            ))}
          </select>

          <div className="flex items-center gap-2 rounded-xl border border-line bg-surface-2 px-3 py-1.5">
            <span className="text-[11px] text-muted">Min Score:</span>
            <input
              type="range"
              min={0}
              max={95}
              step={5}
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="w-full accent-[var(--accent)]"
            />
            <span className="w-8 text-right text-xs font-semibold text-ink">
              {minScore}%
            </span>
          </div>
        </div>

        {selectedPreference && (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <MapPin className="h-4 w-4 text-accent shrink-0" />
              <span className="font-medium text-ink">
                Active Location Mode:
              </span>
              <span className="rounded-md bg-accent/10 px-2 py-0.5 font-semibold text-accent-ink">
                {selectedPreference.location_mode === 'SELECTED_LOCATIONS_ONLY'
                  ? 'Selected Locations Only'
                  : selectedPreference.location_mode === 'WORLDWIDE_REMOTE'
                  ? 'Worldwide Remote'
                  : 'India Only (Default)'}
              </span>
              <span className="text-muted">
                Preferred Cities: {selectedPreference.locations.join(', ')}
              </span>
              {selectedPreference.experience_level && (
                <span className="ml-2 rounded-md border border-line bg-surface px-2 py-0.5 text-[11px] font-semibold text-ink">
                  Target Level: {selectedPreference.experience_level}
                </span>
              )}
            </div>
            <span className="text-[11px] text-muted">
              {selectedPreference.location_mode === 'SELECTED_LOCATIONS_ONLY'
                ? 'Only jobs matching your selected cities are eligible.'
                : selectedPreference.location_mode === 'WORLDWIDE_REMOTE'
                ? 'Worldwide remote jobs and Indian locations are eligible.'
                : 'All Indian locations & India-eligible remote roles are eligible.'}
            </span>
          </div>
        )}
      </section>

      {/* Discovered & Matched Jobs List */}
      {loading ? (
        <div className="rounded-2xl border border-line bg-surface p-8 text-center text-xs text-muted">
          Loading discovered jobs and preference match evaluations...
        </div>
      ) : filteredMatches.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-line bg-surface p-8 text-center">
          <p className="text-sm font-semibold text-ink">
            No matching discovered jobs found
          </p>
          <p className="mt-1 text-xs text-muted">
            Press &quot;Start JobHunter&quot; on the Dashboard or Automation
            page to run Agent 1 (Job Discovery) and Agent 2 (Job Matching).
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredMatches.map((match) => {
            const job = match.discovered_job;
            const isExpanded = expandedMatchId === match.id;
            const hasLocationIneligible = match.reasons_for_rejection.some(
              (r) => r.includes('Location Ineligible'),
            );
            const hasExperienceIneligible = match.reasons_for_rejection.some(
              (r) => r.includes('Experience Ineligible'),
            );

            return (
              <article
                key={match.id}
                className="rounded-2xl border border-line bg-surface p-4 shadow-card transition-colors hover:border-subtle/40"
              >
                <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-sm font-semibold text-ink">
                        {job.title}
                      </h3>
                      <span className="text-xs font-medium text-muted">
                        · {job.company}
                      </span>
                      <span className="rounded-md border border-line bg-surface-2 px-2 py-0.5 text-[10px] font-medium text-muted">
                        {match.preference_name || 'Preference'}
                      </span>
                      {job.experience_requirement && (
                        <span className="inline-flex items-center gap-1 rounded-md border border-line bg-surface-2 px-2 py-0.5 text-[10px] font-medium text-ink">
                          <Briefcase className="h-3 w-3 text-subtle" />
                          {job.experience_requirement}
                        </span>
                      )}
                    </div>

                    <div className="mt-1.5 flex flex-wrap items-center gap-3 text-xs text-muted">
                      <span className="inline-flex items-center gap-1">
                        <MapPin className="h-3.5 w-3.5 text-subtle" />
                        {job.location || 'Flexible'} ·{' '}
                        {job.work_mode || 'Remote'}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <Globe className="h-3.5 w-3.5 text-subtle" />
                        {job.source_name}
                      </span>
                      {job.min_salary && (
                        <span>
                          {job.salary_currency || 'INR'}{' '}
                          {job.min_salary.toLocaleString()}
                          {job.max_salary
                            ? ` – ${job.max_salary.toLocaleString()}`
                            : '+'}
                        </span>
                      )}
                    </div>

                    {match.skills_matched.length > 0 && (
                      <div className="mt-2.5 flex flex-wrap gap-1.5">
                        {match.skills_matched.map((sk) => (
                          <span
                            key={sk}
                            className="rounded-md bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-600 dark:text-emerald-300"
                          >
                            {sk}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="flex shrink-0 flex-wrap items-center gap-2 sm:flex-col sm:items-end">
                    <div className="flex flex-wrap items-center gap-2">
                      {hasLocationIneligible && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/10 px-2.5 py-1 text-xs font-semibold text-rose-500">
                          <AlertCircle className="h-3 w-3" />
                          Location Ineligible
                        </span>
                      )}

                      {hasExperienceIneligible && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2.5 py-1 text-xs font-semibold text-amber-600 dark:text-amber-300">
                          <AlertCircle className="h-3 w-3" />
                          Experience Ineligible
                        </span>
                      )}

                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${
                          hasLocationIneligible || hasExperienceIneligible
                            ? 'bg-rose-500/10 text-rose-500'
                            : match.match_score >= match.threshold_used
                            ? 'bg-emerald-500/10 text-emerald-600 dark:bg-emerald-400/15 dark:text-emerald-300'
                            : 'bg-amber-500/10 text-amber-600 dark:bg-amber-400/15 dark:text-amber-300'
                        }`}
                      >
                        <Sparkles className="h-3 w-3" />
                        {match.match_score}% Match
                      </span>

                      <button
                        type="button"
                        onClick={() => handleToggleShortlist(match)}
                        disabled={
                          hasLocationIneligible || hasExperienceIneligible
                        }
                        className={`inline-flex items-center gap-1 rounded-xl border px-2.5 py-1 text-xs font-medium transition ${
                          match.shortlisted
                            ? 'border-violet-500/30 bg-violet-500/10 text-violet-600 dark:text-violet-300'
                            : hasLocationIneligible || hasExperienceIneligible
                            ? 'border-line/40 bg-surface-2 text-subtle opacity-50 cursor-not-allowed'
                            : 'border-line bg-surface-2 text-muted hover:text-ink'
                        }`}
                      >
                        <Layers className="h-3 w-3" />
                        {match.shortlisted ? 'Shortlisted' : 'Shortlist'}
                      </button>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() =>
                          setExpandedMatchId(isExpanded ? null : match.id)
                        }
                        className="text-xs font-medium text-accent-ink hover:underline"
                      >
                        {isExpanded
                          ? 'Hide Match & Route Details'
                          : 'View Match & Routes'}
                      </button>
                      <a
                        href={job.official_job_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 rounded-lg border border-line bg-surface-2 px-2 py-1 text-[11px] font-medium text-ink hover:border-subtle/50"
                      >
                        Official Link
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                </div>

                {isExpanded && (
                  <div className="mt-4 space-y-3 border-t border-line pt-3 text-xs">
                    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                      <div className="rounded-xl border border-line bg-surface-2 p-3">
                        <p className="font-semibold text-ink">
                          Agent 2 — Why This Job Matched (Threshold:{' '}
                          {match.threshold_used}%)
                        </p>
                        {match.reasons_for_matching.length > 0 && (
                          <ul className="mt-1.5 list-disc space-y-1 pl-4 text-muted">
                            {match.reasons_for_matching.map((r, i) => (
                              <li key={i}>{r}</li>
                            ))}
                          </ul>
                        )}
                        {match.reasons_for_rejection.length > 0 && (
                          <ul className="mt-1.5 list-disc space-y-1 pl-4 text-rose-500">
                            {match.reasons_for_rejection.map((r, i) => (
                              <li key={i}>{r}</li>
                            ))}
                          </ul>
                        )}
                        {match.missing_or_unverified_requirements.length >
                          0 && (
                          <div className="mt-2 rounded-lg border border-amber-500/20 bg-amber-500/5 p-2 text-[11px] text-amber-700 dark:text-amber-300">
                            <span className="font-semibold">
                              Unverified in Resume Text:
                            </span>{' '}
                            {match.missing_or_unverified_requirements.join(
                              '; ',
                            )}
                          </div>
                        )}
                      </div>

                      <div className="rounded-xl border border-line bg-surface-2 p-3">
                        <p className="font-semibold text-ink">
                          Agent 3 — Verified Application Routes (
                          {match.routes.length})
                        </p>
                        {match.routes.length === 0 ? (
                          <p className="mt-1.5 text-muted">
                            Routes are discovered automatically for shortlisted
                            jobs.
                          </p>
                        ) : (
                          <ul className="mt-1.5 space-y-2">
                            {match.routes.map((rt) => (
                              <li
                                key={rt.id}
                                className="flex items-start justify-between gap-2 rounded-lg border border-line bg-surface p-2"
                              >
                                <div className="min-w-0">
                                  <div className="flex items-center gap-1.5 font-medium text-ink">
                                    {rt.route_type === 'published_hr_email' ? (
                                      <Mail className="h-3.5 w-3.5 text-sky-500" />
                                    ) : rt.route_type ===
                                      'verified_recruiter_contact' ? (
                                      <UserCheck className="h-3.5 w-3.5 text-violet-500" />
                                    ) : (
                                      <Globe className="h-3.5 w-3.5 text-emerald-500" />
                                    )}
                                    <span className="capitalize">
                                      {rt.route_type.replace(/_/g, ' ')}
                                    </span>
                                  </div>
                                  <p className="mt-0.5 truncate text-[11px] text-muted">
                                    {rt.url_or_contact}
                                  </p>
                                </div>

                                <span
                                  className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                                    rt.requires_manual_review
                                      ? 'bg-amber-500/10 text-amber-600 dark:text-amber-300'
                                      : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-300'
                                  }`}
                                >
                                  {rt.requires_manual_review ? (
                                    <>
                                      <ShieldAlert className="h-3 w-3" />
                                      Manual Review
                                    </>
                                  ) : (
                                    <>
                                      <CheckCircle2 className="h-3 w-3" />
                                      Verified ({rt.confidence_level}%)
                                    </>
                                  )}
                                </span>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
