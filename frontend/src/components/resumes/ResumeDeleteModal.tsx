import { useEffect } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import type { ResumeItem } from '../../types/resume';

interface ResumeDeleteModalProps {
  resume: ResumeItem | null;
  isDeleting: boolean;
  onCancel: () => void;
  onConfirm: (resume: ResumeItem) => void;
}

export function ResumeDeleteModal({
  resume,
  isDeleting,
  onCancel,
  onConfirm,
}: ResumeDeleteModalProps) {
  useEffect(() => {
    if (!resume) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isDeleting) {
        onCancel();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [resume, isDeleting, onCancel]);

  if (!resume) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-resume-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <div
        aria-hidden="true"
        onClick={() => {
          if (!isDeleting) onCancel();
        }}
        className="fixed inset-0 bg-black/50 backdrop-blur-[2px]"
      />

      <div className="relative z-10 w-full max-w-md rounded-2xl border border-line bg-surface p-6 shadow-card">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-rose-500/10 text-rose-600 dark:bg-rose-400/15 dark:text-rose-400">
              <AlertTriangle className="h-5 w-5" strokeWidth={1.9} />
            </div>
            <div>
              <h2 id="delete-resume-title" className="text-base font-semibold text-ink">
                Delete Resume
              </h2>
              <p className="mt-0.5 text-xs text-muted">
                This action cannot be undone.
              </p>
            </div>
          </div>

          <button
            type="button"
            disabled={isDeleting}
            onClick={onCancel}
            aria-label="Close delete confirmation"
            className="rounded-lg p-1.5 text-muted transition-colors hover:bg-surface-2 hover:text-ink"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <p className="mt-4 text-sm text-muted">
          Are you sure you want to permanently delete{' '}
          <span className="font-semibold text-ink">“{resume.resume_name}”</span> (
          {resume.original_filename})?
        </p>

        <div className="mt-6 flex items-center justify-end gap-2.5">
          <button
            type="button"
            disabled={isDeleting}
            onClick={onCancel}
            className="rounded-xl border border-line bg-surface-2 px-4 py-2 text-xs font-medium text-ink transition-colors hover:border-subtle/50 disabled:opacity-60"
          >
            Cancel
          </button>

          <button
            type="button"
            disabled={isDeleting}
            onClick={() => onConfirm(resume)}
            className="rounded-xl bg-rose-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isDeleting ? 'Deleting…' : 'Delete Resume'}
          </button>
        </div>
      </div>
    </div>
  );
}

