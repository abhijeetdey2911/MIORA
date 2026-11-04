import { useEffect } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileText,
  X,
} from 'lucide-react';
import { getResumeDownloadUrl } from '../../services/resumeService';
import {
  formatFileSize,
  formatUploadDate,
  type ResumeItem,
} from '../../types/resume';

interface ResumeViewModalProps {
  resume: ResumeItem | null;
  onClose: () => void;
}

export function ResumeViewModal({ resume, onClose }: ResumeViewModalProps) {
  useEffect(() => {
    if (!resume) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [resume, onClose]);

  if (!resume) return null;

  const downloadUrl = getResumeDownloadUrl(resume.id);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="view-resume-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
    >
      <div
        aria-hidden="true"
        onClick={onClose}
        className="fixed inset-0 bg-black/50 backdrop-blur-[2px]"
      />

      <div className="relative z-10 flex max-h-[90vh] w-full max-w-2xl flex-col rounded-2xl border border-line bg-surface shadow-card">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 border-b border-line px-6 py-4">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent-ink">
              <FileText className="h-5 w-5" strokeWidth={1.9} />
            </div>
            <div className="min-w-0">
              <h2
                id="view-resume-title"
                className="truncate text-lg font-semibold text-ink"
              >
                {resume.resume_name}
              </h2>
              <p className="mt-0.5 truncate text-xs text-muted">
                {resume.original_filename} · {resume.file_format} ·{' '}
                {formatFileSize(resume.file_size)} · Uploaded{' '}
                {formatUploadDate(resume.created_at)}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close resume view"
            className="rounded-xl p-1.5 text-muted transition-colors hover:bg-surface-2 hover:text-ink"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="space-y-4 overflow-y-auto px-6 py-5">
          {/* Status Banner */}
          <div
            className={`flex items-start gap-2.5 rounded-xl border p-3 text-xs ${
              resume.processing_status === 'Processed'
                ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                : 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300'
            }`}
          >
            {resume.processing_status === 'Processed' ? (
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            ) : (
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            )}
            <div>
              <p className="font-semibold">
                Status: {resume.processing_status}
                {resume.requires_ocr ? ' (Scanned PDF — Requires OCR)' : ''}
              </p>
              {resume.processing_message && (
                <p className="mt-0.5 opacity-90">{resume.processing_message}</p>
              )}
            </div>
          </div>

          {/* Associated Preferences */}
          <div>
            <p className="text-xs font-medium text-ink">Associated Job Preferences</p>
            {resume.associated_preferences.length === 0 ? (
              <p className="mt-1 text-xs text-muted">
                Not associated with any job preferences yet.
              </p>
            ) : (
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {resume.associated_preferences.map((pref) => (
                  <span
                    key={pref.id}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-accent/25 bg-accent-soft px-2.5 py-1 text-xs font-medium text-accent-ink"
                  >
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${
                        pref.is_active ? 'bg-emerald-500' : 'bg-subtle'
                      }`}
                    />
                    {pref.preference_name}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Extracted Text Viewer */}
          <div>
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-ink">Extracted Resume Text</p>
              {resume.extracted_text && (
                <span className="text-[11px] text-muted">
                  {resume.extracted_text.length.toLocaleString()} characters
                </span>
              )}
            </div>

            {resume.extracted_text ? (
              <pre className="mt-1.5 max-h-80 overflow-y-auto whitespace-pre-wrap rounded-xl border border-line bg-surface-2 p-4 font-sans text-xs leading-relaxed text-ink">
                {resume.extracted_text}
              </pre>
            ) : (
              <div className="mt-1.5 rounded-xl border border-line bg-surface-2 p-6 text-center text-xs text-muted">
                {resume.requires_ocr
                  ? 'This PDF appears to be a scanned image without an embedded text layer. OCR is required before text can be extracted.'
                  : 'No readable text could be extracted from this document.'}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-2.5 border-t border-line px-6 py-4">
          <a
            href={downloadUrl}
            download
            className="inline-flex items-center gap-1.5 rounded-xl border border-line bg-surface-2 px-4 py-2 text-xs font-medium text-ink transition-colors hover:border-subtle/50"
          >
            <Download className="h-3.5 w-3.5" strokeWidth={1.9} />
            Download Original File
          </a>

          <button
            type="button"
            onClick={onClose}
            className="rounded-xl bg-accent px-4 py-2 text-xs font-semibold text-white shadow-card transition hover:brightness-105"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
