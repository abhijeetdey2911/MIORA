import {
  Briefcase,
  Code2,
  GraduationCap,
  Laptop,
  MapPin,
  Pencil,
  Sparkles,
  Trash2,
  Wallet,
} from 'lucide-react';
import type { JobPreference } from '../../types/preference';
import { PreferenceStatusToggle } from './PreferenceStatusToggle';

interface PreferenceCardProps {
  preference: JobPreference;
  isTogglingStatus: boolean;
  onEdit: (preference: JobPreference) => void;
  onToggleStatus: (preference: JobPreference) => void;
  onRequestDelete: (preference: JobPreference) => void;
}

function formatSalaryRange(
  minSalary: number | null,
  maxSalary: number | null,
  currency: string,
): string | null {
  if (minSalary === null && maxSalary === null) {
    return null;
  }
  const fmt = (value: number) => value.toLocaleString('en-IN');
  if (minSalary !== null && maxSalary !== null) {
    return `${currency} ${fmt(minSalary)} – ${fmt(maxSalary)}`;
  }
  if (minSalary !== null) {
    return `From ${currency} ${fmt(minSalary)}`;
  }
  return `Up to ${currency} ${fmt(maxSalary!)}`;
}

export function PreferenceCard({
  preference,
  isTogglingStatus,
  onEdit,
  onToggleStatus,
  onRequestDelete,
}: PreferenceCardProps) {
  const {
    preference_name,
    job_roles,
    locations,
    work_mode,
    employment_type,
    experience_level,
    min_salary,
    max_salary,
    currency,
    skills,
    minimum_match_score,
    is_active,
  } = preference;

  const salaryLabel = formatSalaryRange(min_salary, max_salary, currency);

  return (
    <article className="flex flex-col justify-between rounded-2xl border border-line bg-surface p-5 shadow-card transition-colors hover:border-subtle/40">
      <div>
        {/* Top Row: Preference Name + Independent Status Toggle Switch */}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold text-ink">
              {preference_name}
            </h2>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted">
              <span className="flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5 shrink-0 text-subtle" strokeWidth={1.9} />
                <span className="truncate">{locations.join(', ')}</span>
              </span>
              <span className="rounded-md border border-line bg-surface-2 px-1.5 py-0.5 text-[10px] font-medium text-ink">
                {preference.location_mode === 'SELECTED_LOCATIONS_ONLY'
                  ? 'Selected Cities Only'
                  : preference.location_mode === 'WORLDWIDE_REMOTE'
                  ? 'Worldwide Remote'
                  : 'India Only'}
              </span>
            </div>
          </div>

          <div className="shrink-0">
            <PreferenceStatusToggle
              isActive={is_active}
              disabled={isTogglingStatus}
              showHelperText={false}
              label={`Toggle status for ${preference_name}`}
              onChange={() => onToggleStatus(preference)}
            />
          </div>
        </div>

        {/* Helper text explaining paused preference behavior */}
        <p className="mt-2 text-[11px] text-muted">
          Paused preferences are excluded from future job discovery runs.
        </p>

        {/* Target Job Roles */}
        <div className="mt-4">
          <p className="text-[11px] font-medium uppercase tracking-wider text-subtle">
            Target Job Roles
          </p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {job_roles.map((role) => (
              <span
                key={role}
                className="inline-flex items-center rounded-lg bg-accent-soft px-2.5 py-1 text-xs font-medium text-accent-ink"
              >
                {role}
              </span>
            ))}
          </div>
        </div>

        {/* Metadata Grid: Work mode, Employment type, Experience level, Number of skills */}
        <div className="mt-4 grid grid-cols-2 gap-2.5 rounded-xl border border-line bg-surface-2 p-3 text-xs">
          <div className="flex items-center gap-2 text-ink">
            <Laptop className="h-3.5 w-3.5 shrink-0 text-muted" strokeWidth={1.9} />
            <div className="min-w-0">
              <p className="text-[10px] text-subtle">Work Mode</p>
              <p className="truncate font-medium">{work_mode}</p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-ink">
            <Briefcase className="h-3.5 w-3.5 shrink-0 text-muted" strokeWidth={1.9} />
            <div className="min-w-0">
              <p className="text-[10px] text-subtle">Employment</p>
              <p className="truncate font-medium">{employment_type}</p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-ink">
            <GraduationCap className="h-3.5 w-3.5 shrink-0 text-muted" strokeWidth={1.9} />
            <div className="min-w-0">
              <p className="text-[10px] text-subtle">Experience</p>
              <p className="truncate font-medium">{experience_level}</p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-ink">
            <Code2 className="h-3.5 w-3.5 shrink-0 text-muted" strokeWidth={1.9} />
            <div className="min-w-0">
              <p className="text-[10px] text-subtle">Required Skills</p>
              <p className="truncate font-medium">
                {skills.length} {skills.length === 1 ? 'skill' : 'skills'}
              </p>
            </div>
          </div>
        </div>

        {/* Skills preview + Match score & Salary */}
        <div className="mt-3.5 flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
          <div className="flex flex-wrap items-center gap-1">
            {skills.slice(0, 4).map((skill) => (
              <span
                key={skill}
                className="rounded-md border border-line bg-surface-2 px-2 py-0.5 text-[11px] text-muted"
              >
                {skill}
              </span>
            ))}
            {skills.length > 4 && (
              <span className="px-1 text-[11px] font-medium text-subtle">
                +{skills.length - 4} more
              </span>
            )}
          </div>

          <div className="flex items-center gap-3 text-[11px] font-medium text-muted">
            {salaryLabel && (
              <span className="inline-flex items-center gap-1">
                <Wallet className="h-3 w-3 text-subtle" strokeWidth={1.9} />
                {salaryLabel}
              </span>
            )}
            <span className="inline-flex items-center gap-1 text-ink">
              <Sparkles className="h-3 w-3 text-accent" strokeWidth={2} />
              {minimum_match_score}% match
            </span>
          </div>
        </div>
      </div>

      {/* Card Footer Actions */}
      <div className="mt-5 flex items-center justify-between gap-2 border-t border-line pt-3.5">
        <button
          type="button"
          onClick={() => onEdit(preference)}
          className="inline-flex items-center gap-1.5 rounded-xl border border-line bg-surface-2 px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:border-subtle/50"
        >
          <Pencil className="h-3.5 w-3.5 text-muted" strokeWidth={1.9} />
          Edit
        </button>

        <button
          type="button"
          onClick={() => onRequestDelete(preference)}
          aria-label={`Delete ${preference_name}`}
          className="inline-flex items-center gap-1.5 rounded-xl border border-line bg-surface-2 px-3 py-1.5 text-xs font-medium text-rose-600 transition-colors hover:border-rose-500/30 hover:bg-rose-500/10 dark:text-rose-400"
        >
          <Trash2 className="h-3.5 w-3.5" strokeWidth={1.9} />
          Delete
        </button>
      </div>
    </article>
  );
}
