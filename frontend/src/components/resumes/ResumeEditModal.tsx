import { useEffect, useState, type FormEvent } from 'react';
import { AlertCircle, Check, X } from 'lucide-react';
import type { JobPreference } from '../../types/preference';
import type { ResumeItem, ResumeUpdatePayload } from '../../types/resume';

interface ResumeEditModalProps {
  resume: ResumeItem | null;
  preferences: JobPreference[];
  isSaving: boolean;
  apiError: string | null;
  onClose: () => void;
  onSave: (id: string, payload: ResumeUpdatePayload) => Promise<void>;
}

export function ResumeEditModal({
  resume,
  preferences,
  isSaving,
  apiError,
  onClose,
  onSave,
}: ResumeEditModalProps) {
  const [resumeName, setResumeName] = useState(() => resume?.resume_name ?? '');
  const [selectedPreferenceIds, setSelectedPreferenceIds] = useState<string[]>(() =>
    resume ? resume.associated_preferences.map((p) => p.id) : [],
  );
  const [nameError, setNameError] = useState<string | null>(null);

  useEffect(() => {
    if (!resume) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isSaving) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [resume, isSaving, onClose]);

  if (!resume) return null;

  const togglePreferenceId = (prefId: string) => {
    setSelectedPreferenceIds((prev) =>
      prev.includes(prefId)
        ? prev.filter((id) => id !== prefId)
        : [...prev, prefId],
    );
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = resumeName.trim();
    if (!trimmed) {
      setNameError('Resume name is required.');
      return;
    }
    setNameError(null);
    await onSave(resume.id, {
      resume_name: trimmed,
      preference_ids: selectedPreferenceIds,
    });
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-resume-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
    >
      <div
        aria-hidden="true"
        onClick={() => {
          if (!isSaving) onClose();
        }}
        className="fixed inset-0 bg-black/50 backdrop-blur-[2px]"
      />

      <div className="relative z-10 flex max-h-[90vh] w-full max-w-lg flex-col rounded-2xl border border-line bg-surface shadow-card">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-line px-6 py-4">
          <div>
            <h2
              id="edit-resume-modal-title"
              className="text-lg font-semibold text-ink"
            >
              Rename & Manage Preferences
            </h2>
            <p className="mt-0.5 text-xs text-muted">
              Update the display name and job preference associations for this resume.
            </p>
          </div>

          <button
            type="button"
            disabled={isSaving}
            onClick={onClose}
            aria-label="Close edit resume modal"
            className="rounded-xl p-1.5 text-muted transition-colors hover:bg-surface-2 hover:text-ink"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} noValidate className="overflow-y-auto px-6 py-5">
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
            {/* Resume Name */}
            <div>
              <label
                htmlFor="edit-resume-name"
                className="block text-xs font-medium text-ink"
              >
                Resume Name <span className="text-accent">*</span>
              </label>
              <input
                id="edit-resume-name"
                type="text"
                disabled={isSaving}
                value={resumeName}
                onChange={(e) => {
                  setResumeName(e.target.value);
                  if (nameError) setNameError(null);
                }}
                className="mt-1.5 w-full rounded-xl border border-line bg-surface-2 px-3.5 py-2 text-sm text-ink placeholder:text-subtle focus:border-accent focus:outline-none"
              />
              {nameError && <p className="mt-1 text-xs text-rose-500">{nameError}</p>}
            </div>

            {/* Associated Preferences */}
            <div>
              <div className="flex items-center justify-between">
                <span className="block text-xs font-medium text-ink">
                  Associated Job Preferences
                </span>
                <span className="text-[11px] text-muted">
                  {selectedPreferenceIds.length} selected
                </span>
              </div>
              <p className="mt-0.5 text-[11px] text-muted">
                Select one or more job preferences to pair with this resume.
              </p>

              {preferences.length === 0 ? (
                <p className="mt-2 rounded-xl border border-line bg-surface-2 p-3 text-xs text-muted">
                  No job preferences available. Create a preference on the Preferences
                  page first.
                </p>
              ) : (
                <div className="mt-2 max-h-48 space-y-1.5 overflow-y-auto rounded-xl border border-line bg-surface-2 p-2">
                  {preferences.map((pref) => {
                    const isChecked = selectedPreferenceIds.includes(pref.id);
                    return (
                      <button
                        key={pref.id}
                        type="button"
                        disabled={isSaving}
                        onClick={() => togglePreferenceId(pref.id)}
                        className={`flex w-full items-center justify-between gap-2.5 rounded-lg px-2.5 py-2 text-left text-xs transition-colors ${
                          isChecked
                            ? 'bg-accent-soft font-semibold text-accent-ink'
                            : 'text-ink hover:bg-surface'
                        }`}
                      >
                        <div className="flex min-w-0 items-center gap-2">
                          <span
                            className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                              pref.is_active ? 'bg-emerald-500' : 'bg-subtle'
                            }`}
                          />
                          <span className="truncate">{pref.preference_name}</span>
                        </div>

                        <span
                          className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                            isChecked
                              ? 'border-accent bg-accent text-white'
                              : 'border-line bg-surface'
                          }`}
                        >
                          {isChecked && <Check className="h-3 w-3" strokeWidth={2.5} />}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="mt-6 flex items-center justify-end gap-2.5 border-t border-line pt-4">
            <button
              type="button"
              disabled={isSaving}
              onClick={onClose}
              className="rounded-xl border border-line bg-surface-2 px-4 py-2 text-xs font-medium text-ink transition-colors hover:border-subtle/50 disabled:opacity-60"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={isSaving}
              className="rounded-xl bg-accent px-4 py-2 text-xs font-semibold text-white shadow-card transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSaving ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

