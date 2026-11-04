import { useEffect, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Plus,
  RefreshCw,
  SlidersHorizontal,
  X,
} from 'lucide-react';
import { DeleteConfirmModal } from '../components/preferences/DeleteConfirmModal';
import { PreferenceCard } from '../components/preferences/PreferenceCard';
import { PreferenceFormModal } from '../components/preferences/PreferenceFormModal';
import {
  createPreference,
  deletePreference,
  getPreferences,
  updatePreference,
  updatePreferenceStatus,
} from '../services/preferenceService';
import type { JobPreference, JobPreferencePayload } from '../types/preference';

interface FeedbackBanner {
  type: 'success' | 'error';
  message: string;
}

export function PreferencesPage() {
  const [preferences, setPreferences] = useState<JobPreference[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingPreference, setEditingPreference] = useState<JobPreference | null>(null);
  const [isSubmittingForm, setIsSubmittingForm] = useState(false);
  const [formApiError, setFormApiError] = useState<string | null>(null);

  const [togglingId, setTogglingId] = useState<string | null>(null);

  const [deletingPreference, setDeletingPreference] = useState<JobPreference | null>(
    null,
  );
  const [isDeleting, setIsDeleting] = useState(false);

  const [feedback, setFeedback] = useState<FeedbackBanner | null>(null);

  useEffect(() => {
    let cancelled = false;
    getPreferences()
      .then((data) => {
        if (!cancelled) {
          setPreferences(data);
          setLoadError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(
            err instanceof Error ? err.message : 'Failed to load job preferences.',
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const handleRetryLoad = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const data = await getPreferences();
      setPreferences(data);
    } catch (err) {
      setLoadError(
        err instanceof Error ? err.message : 'Failed to load job preferences.',
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!feedback || feedback.type !== 'success') return;
    const timer = window.setTimeout(() => setFeedback(null), 4500);
    return () => window.clearTimeout(timer);
  }, [feedback]);

  const handleOpenCreate = () => {
    setEditingPreference(null);
    setFormApiError(null);
    setIsFormOpen(true);
  };

  const handleOpenEdit = (preference: JobPreference) => {
    setEditingPreference(preference);
    setFormApiError(null);
    setIsFormOpen(true);
  };

  const handleCloseForm = () => {
    if (isSubmittingForm) return;
    setIsFormOpen(false);
    setEditingPreference(null);
    setFormApiError(null);
  };

  const handleFormSubmit = async (payload: JobPreferencePayload) => {
    setIsSubmittingForm(true);
    setFormApiError(null);
    try {
      if (editingPreference) {
        const updated = await updatePreference(editingPreference.id, payload);
        setPreferences((prev) =>
          prev.map((item) => (item.id === updated.id ? updated : item)),
        );
        setFeedback({
          type: 'success',
          message: `Updated preference “${updated.preference_name}”.`,
        });
      } else {
        const created = await createPreference(payload);
        setPreferences((prev) => [created, ...prev]);
        setFeedback({
          type: 'success',
          message: `Created preference “${created.preference_name}”.`,
        });
      }
      setIsFormOpen(false);
      setEditingPreference(null);
    } catch (err) {
      setFormApiError(
        err instanceof Error ? err.message : 'Unable to save job preference.',
      );
    } finally {
      setIsSubmittingForm(false);
    }
  };

  const handleToggleStatus = async (preference: JobPreference) => {
    const nextStatus = !preference.is_active;
    // Update the UI immediately (optimistic update)
    setPreferences((prev) =>
      prev.map((item) =>
        item.id === preference.id ? { ...item, is_active: nextStatus } : item,
      ),
    );
    setTogglingId(preference.id);
    try {
      const updated = await updatePreferenceStatus(preference.id, nextStatus);
      setPreferences((prev) =>
        prev.map((item) => (item.id === updated.id ? updated : item)),
      );
      setFeedback({
        type: 'success',
        message: `Preference “${updated.preference_name}” is now ${
          updated.is_active ? 'Active' : 'Paused'
        }.`,
      });
    } catch (err) {
      // Revert optimistic update on failure
      setPreferences((prev) =>
        prev.map((item) =>
          item.id === preference.id
            ? { ...item, is_active: preference.is_active }
            : item,
        ),
      );
      setFeedback({
        type: 'error',
        message:
          err instanceof Error ? err.message : 'Failed to update preference status.',
      });
    } finally {
      setTogglingId(null);
    }
  };

  const handleConfirmDelete = async (preference: JobPreference) => {
    setIsDeleting(true);
    try {
      await deletePreference(preference.id);
      setPreferences((prev) => prev.filter((item) => item.id !== preference.id));
      setDeletingPreference(null);
      setFeedback({
        type: 'success',
        message: `Deleted preference “${preference.preference_name}”.`,
      });
    } catch (err) {
      setFeedback({
        type: 'error',
        message:
          err instanceof Error ? err.message : 'Failed to delete job preference.',
      });
      setDeletingPreference(null);
    } finally {
      setIsDeleting(false);
    }
  };

  const activeCount = preferences.filter((item) => item.is_active).length;
  const pausedCount = preferences.length - activeCount;

  return (
    <div className="space-y-6">
      {/* Top Action Bar */}
      <div className="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-4 shadow-card sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-surface-2 px-2.5 py-1 font-medium text-ink">
            {preferences.length}{' '}
            {preferences.length === 1 ? 'Preference Profile' : 'Preference Profiles'}
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500/10 px-2.5 py-1 font-medium text-emerald-600 dark:bg-emerald-400/15 dark:text-emerald-300">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            {activeCount} Active
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-surface-2 px-2.5 py-1 font-medium text-muted">
            <span className="h-1.5 w-1.5 rounded-full bg-subtle" />
            {pausedCount} Paused
          </span>
        </div>

        <button
          type="button"
          onClick={handleOpenCreate}
          className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-white shadow-card transition hover:brightness-105 active:scale-[0.99]"
        >
          <Plus className="h-4 w-4" strokeWidth={2.3} />
          + Create Preference
        </button>
      </div>

      {/* Feedback Banner */}
      {feedback && (
        <div
          role="status"
          className={`flex items-center justify-between gap-3 rounded-2xl border px-4 py-3 text-xs font-medium shadow-card ${
            feedback.type === 'success'
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
              : 'border-rose-500/30 bg-rose-500/10 text-rose-600 dark:text-rose-300'
          }`}
        >
          <div className="flex items-center gap-2">
            {feedback.type === 'success' ? (
              <CheckCircle2 className="h-4 w-4 shrink-0" />
            ) : (
              <AlertCircle className="h-4 w-4 shrink-0" />
            )}
            <span>{feedback.message}</span>
          </div>

          <button
            type="button"
            onClick={() => setFeedback(null)}
            aria-label="Dismiss message"
            className="rounded-lg p-1 opacity-75 transition-opacity hover:opacity-100"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Loading State */}
      {isLoading ? (
        <div
          aria-label="Loading job preferences"
          className="grid grid-cols-1 gap-4 md:grid-cols-2"
        >
          {[0, 1].map((skeleton) => (
            <div
              key={skeleton}
              className="h-64 animate-pulse rounded-2xl border border-line bg-surface p-5 shadow-card"
            >
              <div className="flex items-center justify-between">
                <div className="h-4 w-44 rounded bg-surface-2" />
                <div className="h-5 w-16 rounded-full bg-surface-2" />
              </div>
              <div className="mt-4 h-3 w-28 rounded bg-surface-2" />
              <div className="mt-4 flex gap-2">
                <div className="h-6 w-24 rounded-lg bg-surface-2" />
                <div className="h-6 w-28 rounded-lg bg-surface-2" />
              </div>
              <div className="mt-4 h-20 rounded-xl bg-surface-2" />
            </div>
          ))}
        </div>
      ) : loadError ? (
        /* Error State */
        <div
          role="alert"
          className="flex flex-col items-center justify-center rounded-2xl border border-line bg-surface px-6 py-12 text-center shadow-card"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-rose-500/10 text-rose-600 dark:bg-rose-400/15 dark:text-rose-400">
            <AlertCircle className="h-6 w-6" strokeWidth={1.9} />
          </div>
          <h2 className="mt-4 text-base font-semibold text-ink">
            Could not load job preferences
          </h2>
          <p className="mt-1 max-w-md text-xs text-muted">{loadError}</p>
          <button
            type="button"
            onClick={() => void handleRetryLoad()}
            className="mt-5 inline-flex items-center gap-1.5 rounded-xl border border-line bg-surface-2 px-4 py-2 text-xs font-medium text-ink transition-colors hover:border-subtle/50"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Try Again
          </button>
        </div>
      ) : preferences.length === 0 ? (
        /* Empty State */
        <div className="flex flex-col items-center justify-center rounded-2xl border border-line bg-surface px-6 py-14 text-center shadow-card">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent-soft text-accent-ink">
            <SlidersHorizontal className="h-5 w-5" strokeWidth={1.9} />
          </div>
          <h2 className="mt-4 text-base font-semibold text-ink">
            No job preferences configured yet
          </h2>
          <p className="mt-1 max-w-md text-xs text-muted">
            Create your first preference profile with target roles, locations, salary
            expectations, and required skills so JobHunter knows what opportunities to look
            for.
          </p>
          <button
            type="button"
            onClick={handleOpenCreate}
            className="mt-5 inline-flex items-center gap-1.5 rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-white shadow-card transition hover:brightness-105"
          >
            <Plus className="h-4 w-4" strokeWidth={2.3} />
            + Create Preference
          </button>
        </div>
      ) : (
        /* Preference Cards Grid */
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {preferences.map((preference) => (
            <PreferenceCard
              key={preference.id}
              preference={preference}
              isTogglingStatus={togglingId === preference.id}
              onEdit={handleOpenEdit}
              onToggleStatus={(pref) => void handleToggleStatus(pref)}
              onRequestDelete={(pref) => setDeletingPreference(pref)}
            />
          ))}
        </div>
      )}

      {/* Create / Edit Preference Modal */}
      {isFormOpen && (
        <PreferenceFormModal
          key={editingPreference?.id ?? 'create'}
          isOpen={isFormOpen}
          initialPreference={editingPreference}
          isSubmitting={isSubmittingForm}
          apiError={formApiError}
          onClose={handleCloseForm}
          onSubmit={handleFormSubmit}
        />
      )}

      {/* Delete Confirmation Modal */}
      <DeleteConfirmModal
        preference={deletingPreference}
        isDeleting={isDeleting}
        onCancel={() => setDeletingPreference(null)}
        onConfirm={(pref) => void handleConfirmDelete(pref)}
      />
    </div>
  );
}
