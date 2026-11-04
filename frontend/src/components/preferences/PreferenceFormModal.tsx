import { useEffect, useState, type FormEvent, type KeyboardEvent } from 'react';
import { AlertCircle, Plus, X } from 'lucide-react';
import {
  CURRENCIES,
  EMPLOYMENT_TYPES,
  EXPERIENCE_LEVELS,
  JOB_CATEGORIES,
  JOB_ROLES_BY_CATEGORY,
  PREDEFINED_LOCATIONS,
  WORK_MODES,
  inferJobCategory,
  type EmploymentType,
  type ExperienceLevel,
  type JobCategory,
  type JobPreference,
  type JobPreferencePayload,
  type WorkMode,
} from '../../types/preference';
import { PreferenceStatusToggle } from './PreferenceStatusToggle';
import { SearchableMultiSelectDropdown } from './SearchableMultiSelectDropdown';

interface PreferenceFormModalProps {
  isOpen: boolean;
  initialPreference: JobPreference | null;
  isSubmitting: boolean;
  apiError: string | null;
  onClose: () => void;
  onSubmit: (payload: JobPreferencePayload) => Promise<void>;
}

function mergeTags(existing: string[], rawInput: string): string[] {
  const parts = rawInput
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
  if (parts.length === 0) return existing;

  const seen = new Set(existing.map((item) => item.toLowerCase()));
  const next = [...existing];
  for (const part of parts) {
    const key = part.toLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      next.push(part);
    }
  }
  return next;
}

interface TagInputFieldProps {
  id: string;
  label: string;
  placeholder: string;
  items: string[];
  draftValue: string;
  error?: string;
  onDraftChange: (value: string) => void;
  onAddItems: (raw: string) => void;
  onRemoveItem: (item: string) => void;
}

function TagInputField({
  id,
  label,
  placeholder,
  items,
  draftValue,
  error,
  onDraftChange,
  onAddItems,
  onRemoveItem,
}: TagInputFieldProps) {
  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault();
      if (draftValue.trim()) {
        onAddItems(draftValue);
      }
    } else if (event.key === 'Backspace' && !draftValue && items.length > 0) {
      onRemoveItem(items[items.length - 1]);
    }
  };

  return (
    <div>
      <label htmlFor={id} className="block text-xs font-medium text-ink">
        {label} <span className="text-accent">*</span>
      </label>

      <div className="mt-1.5 flex gap-2">
        <input
          id={id}
          type="text"
          value={draftValue}
          onChange={(e) => onDraftChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="min-w-0 flex-1 rounded-xl border border-line bg-surface-2 px-3.5 py-2 text-sm text-ink placeholder:text-subtle focus:border-accent focus:outline-none"
        />
        <button
          type="button"
          onClick={() => {
            if (draftValue.trim()) {
              onAddItems(draftValue);
            }
          }}
          className="inline-flex shrink-0 items-center gap-1 rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs font-medium text-ink transition-colors hover:border-subtle/60"
        >
          <Plus className="h-3.5 w-3.5 text-accent" strokeWidth={2.2} />
          Add
        </button>
      </div>

      {items.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {items.map((item) => (
            <span
              key={item}
              className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface-2 px-2.5 py-1 text-xs font-medium text-ink"
            >
              {item}
              <button
                type="button"
                onClick={() => onRemoveItem(item)}
                aria-label={`Remove ${item}`}
                className="rounded text-muted transition-colors hover:text-rose-500"
              >
                <X className="h-3 w-3" strokeWidth={2.2} />
              </button>
            </span>
          ))}
        </div>
      )}

      {error && <p className="mt-1 text-xs text-rose-500">{error}</p>}
    </div>
  );
}

export function PreferenceFormModal({
  isOpen,
  initialPreference,
  isSubmitting,
  apiError,
  onClose,
  onSubmit,
}: PreferenceFormModalProps) {
  const isEditMode = Boolean(initialPreference);

  const [preferenceName, setPreferenceName] = useState(
    () => initialPreference?.preference_name ?? '',
  );
  const [jobCategory, setJobCategory] = useState<JobCategory>(() =>
    inferJobCategory(initialPreference?.job_roles ?? []),
  );
  const [jobRoles, setJobRoles] = useState<string[]>(
    () => initialPreference?.job_roles ?? [],
  );

  const [locations, setLocations] = useState<string[]>(
    () => initialPreference?.locations ?? [],
  );

  const [workMode, setWorkMode] = useState<WorkMode>(
    () => initialPreference?.work_mode ?? 'Remote',
  );
  const [employmentType, setEmploymentType] = useState<EmploymentType>(
    () => initialPreference?.employment_type ?? 'Full-time',
  );
  const [experienceLevel, setExperienceLevel] = useState<ExperienceLevel>(
    () => initialPreference?.experience_level ?? 'Entry-level',
  );

  const [minSalary, setMinSalary] = useState(() =>
    initialPreference?.min_salary !== null && initialPreference?.min_salary !== undefined
      ? String(initialPreference.min_salary)
      : '',
  );
  const [maxSalary, setMaxSalary] = useState(() =>
    initialPreference?.max_salary !== null && initialPreference?.max_salary !== undefined
      ? String(initialPreference.max_salary)
      : '',
  );
  const [currency, setCurrency] = useState(() => initialPreference?.currency || 'INR');

  const [skills, setSkills] = useState<string[]>(() => initialPreference?.skills ?? []);
  const [skillDraft, setSkillDraft] = useState('');

  const [minimumMatchScore, setMinimumMatchScore] = useState(
    () => initialPreference?.minimum_match_score ?? 75,
  );
  const [isActive, setIsActive] = useState(() => initialPreference?.is_active ?? true);

  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (event: KeyboardEvent | globalThis.KeyboardEvent) => {
      if (event.key === 'Escape' && !isSubmitting) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isSubmitting, onClose]);

  if (!isOpen) return null;

  const handleFormSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const finalRoles = jobRoles;
    const finalLocations = locations;
    const finalSkills = mergeTags(skills, skillDraft);

    if (skillDraft.trim()) {
      setSkills(finalSkills);
      setSkillDraft('');
    }

    const nextErrors: Record<string, string> = {};

    if (!preferenceName.trim()) {
      nextErrors.preferenceName = 'Preference name is required.';
    }
    if (finalRoles.length === 0) {
      nextErrors.jobRoles = 'Select or add at least one target job role.';
    }
    if (finalLocations.length === 0) {
      nextErrors.locations = 'Select or add at least one preferred location.';
    }
    if (finalSkills.length === 0) {
      nextErrors.skills = 'Add at least one required skill.';
    }

    const parsedMin = minSalary.trim() === '' ? null : Number(minSalary);
    const parsedMax = maxSalary.trim() === '' ? null : Number(maxSalary);

    if (parsedMin !== null && (Number.isNaN(parsedMin) || parsedMin < 0)) {
      nextErrors.salary = 'Minimum salary must be a non-negative number.';
    } else if (parsedMax !== null && (Number.isNaN(parsedMax) || parsedMax < 0)) {
      nextErrors.salary = 'Maximum salary must be a non-negative number.';
    } else if (parsedMin !== null && parsedMax !== null && parsedMax < parsedMin) {
      nextErrors.salary = 'Maximum salary must be greater than or equal to minimum salary.';
    }

    if (
      Number.isNaN(minimumMatchScore) ||
      minimumMatchScore < 0 ||
      minimumMatchScore > 100
    ) {
      nextErrors.minimumMatchScore = 'Minimum match score must be between 0 and 100.';
    }

    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    const payload: JobPreferencePayload = {
      preference_name: preferenceName.trim(),
      job_roles: finalRoles,
      locations: finalLocations,
      work_mode: workMode,
      employment_type: employmentType,
      experience_level: experienceLevel,
      min_salary: parsedMin !== null ? Math.round(parsedMin) : null,
      max_salary: parsedMax !== null ? Math.round(parsedMax) : null,
      currency: currency.trim().toUpperCase() || 'INR',
      skills: finalSkills,
      minimum_match_score: Math.round(minimumMatchScore),
      is_active: isActive,
    };

    await onSubmit(payload);
  };

  const categoryRoleOptions = JOB_ROLES_BY_CATEGORY[jobCategory];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="preference-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
    >
      <div
        aria-hidden="true"
        onClick={() => {
          if (!isSubmitting) onClose();
        }}
        className="fixed inset-0 bg-black/50 backdrop-blur-[2px]"
      />

      <div className="relative z-10 flex max-h-[90vh] w-full max-w-2xl flex-col rounded-2xl border border-line bg-surface shadow-card">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-line px-6 py-4">
          <div>
            <h2 id="preference-modal-title" className="text-lg font-semibold text-ink">
              {isEditMode ? 'Edit Job Preference' : 'Create Job Preference'}
            </h2>
            <p className="mt-0.5 text-xs text-muted">
              Configure the criteria JobHunter uses to discover and score opportunities.
            </p>
          </div>

          <button
            type="button"
            disabled={isSubmitting}
            onClick={onClose}
            aria-label="Close modal"
            className="rounded-xl p-1.5 text-muted transition-colors hover:bg-surface-2 hover:text-ink"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Form Body */}
        <form onSubmit={handleFormSubmit} noValidate className="overflow-y-auto px-6 py-5">
          {apiError && (
            <div
              role="alert"
              className="mb-4 flex items-start gap-2.5 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-600 dark:text-rose-300"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{apiError}</span>
            </div>
          )}

          <div className="space-y-4">
            {/* Preference Name */}
            <div>
              <label
                htmlFor="preference-name"
                className="block text-xs font-medium text-ink"
              >
                Preference Name <span className="text-accent">*</span>
              </label>
              <input
                id="preference-name"
                type="text"
                value={preferenceName}
                onChange={(e) => {
                  setPreferenceName(e.target.value);
                  if (errors.preferenceName) {
                    setErrors((prev) => ({ ...prev, preferenceName: '' }));
                  }
                }}
                placeholder="e.g., Data Analytics — India & Remote"
                className="mt-1.5 w-full rounded-xl border border-line bg-surface-2 px-3.5 py-2 text-sm text-ink placeholder:text-subtle focus:border-accent focus:outline-none"
              />
              {errors.preferenceName && (
                <p className="mt-1 text-xs text-rose-500">{errors.preferenceName}</p>
              )}
            </div>

            {/* Job Category + Searchable Multi-Select Target Job Roles */}
            <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-3">
              <div>
                <label
                  htmlFor="preference-job-category"
                  className="block text-xs font-medium text-ink"
                >
                  Job Category
                </label>
                <select
                  id="preference-job-category"
                  value={jobCategory}
                  onChange={(e) => setJobCategory(e.target.value as JobCategory)}
                  className="mt-1.5 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-sm text-ink focus:border-accent focus:outline-none"
                >
                  {JOB_CATEGORIES.map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                </select>
              </div>

              <div className="sm:col-span-2">
                <SearchableMultiSelectDropdown
                  id="preference-job-roles"
                  label="Target Job Roles"
                  placeholder={`Select roles in ${jobCategory}…`}
                  searchPlaceholder={`Search ${jobCategory} roles or type custom…`}
                  options={categoryRoleOptions}
                  selectedValues={jobRoles}
                  customActionLabel="Add Custom Role"
                  customInputPlaceholder="Enter custom job role…"
                  error={errors.jobRoles}
                  onChange={(nextRoles) => {
                    setJobRoles(nextRoles);
                    if (errors.jobRoles && nextRoles.length > 0) {
                      setErrors((prev) => ({ ...prev, jobRoles: '' }));
                    }
                  }}
                />
              </div>
            </div>

            {/* Searchable Multi-Select Preferred Locations */}
            <SearchableMultiSelectDropdown
              id="preference-locations"
              label="Preferred Locations"
              placeholder="Select preferred locations…"
              searchPlaceholder="Search locations (e.g., Bangalore, Hyderabad, Remote)…"
              options={PREDEFINED_LOCATIONS}
              selectedValues={locations}
              customActionLabel="Add Custom Location"
              customInputPlaceholder="Enter custom location…"
              error={errors.locations}
              onChange={(nextLocations) => {
                setLocations(nextLocations);
                if (errors.locations && nextLocations.length > 0) {
                  setErrors((prev) => ({ ...prev, locations: '' }));
                }
              }}
            />

            {/* Work Mode, Employment Type, Experience Level */}
            <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-3">
              <div>
                <label
                  htmlFor="preference-work-mode"
                  className="block text-xs font-medium text-ink"
                >
                  Work Mode
                </label>
                <select
                  id="preference-work-mode"
                  value={workMode}
                  onChange={(e) => setWorkMode(e.target.value as WorkMode)}
                  className="mt-1.5 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-sm text-ink focus:border-accent focus:outline-none"
                >
                  {WORK_MODES.map((mode) => (
                    <option key={mode} value={mode}>
                      {mode}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label
                  htmlFor="preference-employment-type"
                  className="block text-xs font-medium text-ink"
                >
                  Employment Type
                </label>
                <select
                  id="preference-employment-type"
                  value={employmentType}
                  onChange={(e) => setEmploymentType(e.target.value as EmploymentType)}
                  className="mt-1.5 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-sm text-ink focus:border-accent focus:outline-none"
                >
                  {EMPLOYMENT_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label
                  htmlFor="preference-experience-level"
                  className="block text-xs font-medium text-ink"
                >
                  Experience Level
                </label>
                <select
                  id="preference-experience-level"
                  value={experienceLevel}
                  onChange={(e) => setExperienceLevel(e.target.value as ExperienceLevel)}
                  className="mt-1.5 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-sm text-ink focus:border-accent focus:outline-none"
                >
                  {EXPERIENCE_LEVELS.map((level) => (
                    <option key={level} value={level}>
                      {level}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Salary Range + Currency */}
            <div>
              <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-3">
                <div>
                  <label
                    htmlFor="preference-currency"
                    className="block text-xs font-medium text-ink"
                  >
                    Currency
                  </label>
                  <select
                    id="preference-currency"
                    value={currency}
                    onChange={(e) => setCurrency(e.target.value)}
                    className="mt-1.5 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-sm text-ink focus:border-accent focus:outline-none"
                  >
                    {CURRENCIES.map((curr) => (
                      <option key={curr} value={curr}>
                        {curr}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label
                    htmlFor="preference-min-salary"
                    className="block text-xs font-medium text-ink"
                  >
                    Minimum Salary (Annual)
                  </label>
                  <input
                    id="preference-min-salary"
                    type="number"
                    min={0}
                    step={50000}
                    value={minSalary}
                    onChange={(e) => {
                      setMinSalary(e.target.value);
                      if (errors.salary) {
                        setErrors((prev) => ({ ...prev, salary: '' }));
                      }
                    }}
                    placeholder="e.g., 1200000"
                    className="mt-1.5 w-full rounded-xl border border-line bg-surface-2 px-3.5 py-2 text-sm text-ink placeholder:text-subtle focus:border-accent focus:outline-none"
                  />
                </div>

                <div>
                  <label
                    htmlFor="preference-max-salary"
                    className="block text-xs font-medium text-ink"
                  >
                    Maximum Salary (Annual)
                  </label>
                  <input
                    id="preference-max-salary"
                    type="number"
                    min={0}
                    step={50000}
                    value={maxSalary}
                    onChange={(e) => {
                      setMaxSalary(e.target.value);
                      if (errors.salary) {
                        setErrors((prev) => ({ ...prev, salary: '' }));
                      }
                    }}
                    placeholder="e.g., 2400000"
                    className="mt-1.5 w-full rounded-xl border border-line bg-surface-2 px-3.5 py-2 text-sm text-ink placeholder:text-subtle focus:border-accent focus:outline-none"
                  />
                </div>
              </div>
              {errors.salary && (
                <p className="mt-1 text-xs text-rose-500">{errors.salary}</p>
              )}
            </div>

            {/* Required Skills */}
            <TagInputField
              id="preference-skills"
              label="Required Skills"
              placeholder="e.g., Python, TypeScript, React, FastAPI (press Enter or Add)"
              items={skills}
              draftValue={skillDraft}
              error={errors.skills}
              onDraftChange={setSkillDraft}
              onAddItems={(raw) => {
                setSkills((prev) => mergeTags(prev, raw));
                setSkillDraft('');
                if (errors.skills) {
                  setErrors((prev) => ({ ...prev, skills: '' }));
                }
              }}
              onRemoveItem={(item) =>
                setSkills((prev) => prev.filter((entry) => entry !== item))
              }
            />

            {/* Minimum Job Match Score + Active Status */}
            <div className="grid grid-cols-1 gap-4 pt-1 sm:grid-cols-2">
              <div className="rounded-xl border border-line bg-surface-2 p-3.5">
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="preference-match-score"
                    className="text-xs font-medium text-ink"
                  >
                    Minimum Job Match Score
                  </label>
                  <span className="rounded-md bg-accent-soft px-2 py-0.5 text-xs font-semibold text-accent-ink">
                    {minimumMatchScore}%
                  </span>
                </div>
                <input
                  id="preference-match-score"
                  type="range"
                  min={0}
                  max={100}
                  step={5}
                  value={minimumMatchScore}
                  onChange={(e) => setMinimumMatchScore(Number(e.target.value))}
                  className="mt-2.5 w-full accent-[#f7821b]"
                />
                <div className="mt-1 flex justify-between text-[10px] text-subtle">
                  <span>0% (Broad)</span>
                  <span>50%</span>
                  <span>100% (Strict)</span>
                </div>
                {errors.minimumMatchScore && (
                  <p className="mt-1 text-xs text-rose-500">
                    {errors.minimumMatchScore}
                  </p>
                )}
              </div>

              <div className="flex flex-col justify-between rounded-xl border border-line bg-surface-2 p-3.5">
                <div>
                  <p className="text-xs font-medium text-ink">Preference Status</p>
                  <p className="mt-0.5 text-[11px] text-muted">
                    Each preference has an independent discovery status.
                  </p>
                </div>

                <div className="mt-3">
                  <PreferenceStatusToggle
                    id="preference-status-switch"
                    isActive={isActive}
                    showHelperText={true}
                    label="Toggle preference active or paused status"
                    onChange={setIsActive}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Modal Footer */}
          <div className="mt-6 flex items-center justify-end gap-2.5 border-t border-line pt-4">
            <button
              type="button"
              disabled={isSubmitting}
              onClick={onClose}
              className="rounded-xl border border-line bg-surface-2 px-4 py-2 text-xs font-medium text-ink transition-colors hover:border-subtle/50 disabled:opacity-60"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-xl bg-accent px-4 py-2 text-xs font-semibold text-white shadow-card transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting
                ? isEditMode
                  ? 'Saving…'
                  : 'Creating…'
                : isEditMode
                  ? 'Save Changes'
                  : 'Create Preference'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
