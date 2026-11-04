import {
  AlertTriangle,
  Calendar,
  CheckCircle2,
  Clock,
  Download,
  Eye,
  FileText,
  History,
  Loader2,
  Pencil,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Trash2,
} from 'lucide-react';
import { getResumeDownloadUrl } from '../../services/resumeService';
import {
  formatFileSize,
  formatUploadDate,
  type ResumeAIStatus,
  type ResumeItem,
  type ResumeProcessingStatus,
} from '../../types/resume';

interface ResumeCardProps {
  resume: ResumeItem;
  isAnalysingThisResume?: boolean;
  onView: (resume: ResumeItem) => void;
  onEdit: (resume: ResumeItem) => void;
  onRequestDelete: (resume: ResumeItem) => void;
  onOpenIntelligence: (
    resume: ResumeItem,
    initialTab?: 'overview' | 'preferences' | 'suggestions' | 'versions',
  ) => void;
  onAnalyseNow: (resume: ResumeItem) => void;
}

const STATUS_BADGE_STYLES: Record<
  ResumeProcessingStatus,
  { badge: string; label: string }
> = {
  Uploaded: {
    badge: 'bg-sky-500/10 text-sky-600 dark:bg-sky-400/15 dark:text-sky-300',
    label: 'Uploaded',
  },
  Processing: {
    badge: 'bg-accent-soft text-accent-ink',
    label: 'Processing',
  },
  Processed: {
    badge:
      'bg-emerald-500/10 text-emerald-600 dark:bg-emerald-400/15 dark:text-emerald-300',
    label: 'Processed',
  },
  Failed: {
    badge: 'bg-rose-500/10 text-rose-600 dark:bg-rose-400/15 dark:text-rose-300',
    label: 'Failed',
  },
};

const AI_STATUS_STYLES: Record<
  ResumeAIStatus,
  { badge: string; label: string }
> = {
  'Not Analysed': {
    badge: 'border border-line bg-surface-2 text-muted',
    label: 'Not Analysed',
  },
  Analysing: {
    badge: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
    label: 'Analysing…',
  },
  'Analysis Complete': {
    badge: 'bg-sky-500/15 text-sky-700 dark:text-sky-300',
    label: 'Analysis Complete',
  },
  'Draft Generated': {
    badge: 'bg-purple-500/15 text-purple-700 dark:text-purple-300',
    label: 'Draft Generated',
  },
  'Awaiting Approval': {
    badge: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
    label: 'Awaiting Approval',
  },
  Approved: {
    badge:
      'bg-emerald-500/15 text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-300',
    label: 'Approved',
  },
};

export function ResumeCard({
  resume,
  isAnalysingThisResume = false,
  onView,
  onEdit,
  onRequestDelete,
  onOpenIntelligence,
  onAnalyseNow,
}: ResumeCardProps) {
  const {
    id,
    resume_name,
    original_filename,
    file_format,
    file_size,
    processing_status,
    processing_message,
    requires_ocr,
    ai_status,
    overall_quality_score,
    associated_preferences,
    created_at,
  } = resume;

  const statusMeta =
    STATUS_BADGE_STYLES[processing_status] ?? STATUS_BADGE_STYLES.Uploaded;
  const effectiveAIStatus: ResumeAIStatus = isAnalysingThisResume
    ? 'Analysing'
    : (ai_status ?? 'Not Analysed');
  const aiMeta =
    AI_STATUS_STYLES[effectiveAIStatus] ?? AI_STATUS_STYLES['Not Analysed'];
  const downloadUrl = getResumeDownloadUrl(id);
  const canAnalyse = processing_status === 'Processed' && !requires_ocr;

  return (
    <article className="flex flex-col justify-between rounded-2xl border border-line bg-surface p-5 shadow-card transition-colors hover:border-subtle/40">
      <div>
        {/* Top Row: File Icon + Resume Name + Format & Status Badges */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent-ink">
              <FileText className="h-5 w-5" strokeWidth={1.9} />
            </div>

            <div className="min-w-0">
              <h2 className="truncate text-base font-semibold text-ink">
                {resume_name}
              </h2>
              <p className="mt-0.5 truncate text-xs text-muted">
                {original_filename} · {formatFileSize(file_size)}
              </p>
            </div>
          </div>

          <div className="flex shrink-0 flex-wrap items-center justify-end gap-1.5">
            <span className="rounded-lg border border-line bg-surface-2 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider text-ink">
              {file_format}
            </span>

            <span
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-medium ${statusMeta.badge}`}
            >
              {processing_status === 'Processed' ? (
                <CheckCircle2 className="h-3 w-3" strokeWidth={2.2} />
              ) : processing_status === 'Processing' ? (
                <Loader2 className="h-3 w-3 animate-spin" strokeWidth={2.2} />
              ) : processing_status === 'Failed' ? (
                <AlertTriangle className="h-3 w-3" strokeWidth={2.2} />
              ) : (
                <Clock className="h-3 w-3" strokeWidth={2.2} />
              )}
              {statusMeta.label}
            </span>
          </div>
        </div>

        {/* AI Intelligence & Approval Status Strip */}
        <div className="mt-3.5 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${aiMeta.badge}`}
            >
              {effectiveAIStatus === 'Analysing' ? (
                <Loader2 className="h-3 w-3 animate-spin" strokeWidth={2.2} />
              ) : effectiveAIStatus === 'Approved' ? (
                <ShieldCheck className="h-3 w-3" strokeWidth={2.2} />
              ) : (
                <Sparkles className="h-3 w-3" strokeWidth={2} />
              )}
              {aiMeta.label}
            </span>

            {overall_quality_score !== null &&
              overall_quality_score !== undefined && (
                <span
                  title="AI estimated resume quality score (not a guarantee of ATS performance)"
                  className="inline-flex items-center gap-1 rounded-lg bg-accent-soft px-2 py-0.5 text-[11px] font-semibold text-accent-ink"
                >
                  Quality Score: {overall_quality_score}/100 (Est.)
                </span>
              )}
          </div>

          <span className="inline-flex items-center gap-1.5 text-[11px] text-muted">
            <Calendar className="h-3.5 w-3.5 text-subtle" strokeWidth={1.9} />
            Uploaded {formatUploadDate(created_at)}
          </span>
        </div>

        {/* OCR / Processing Notice if Failed */}
        {(requires_ocr || processing_status === 'Failed') && (
          <div className="mt-2.5 flex items-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" strokeWidth={2} />
            <span className="truncate">
              {requires_ocr
                ? 'Scanned PDF — Requires OCR before AI analysis'
                : processing_message || 'Document could not be parsed'}
            </span>
          </div>
        )}

        {/* Associated Preferences */}
        <div className="mt-4">
          <div className="flex items-center justify-between gap-2">
            <p className="text-[11px] font-medium uppercase tracking-wider text-subtle">
              Associated Preferences
            </p>
            <button
              type="button"
              onClick={() => onEdit(resume)}
              className="inline-flex items-center gap-1 text-[11px] font-medium text-accent hover:underline"
            >
              <SlidersHorizontal className="h-3 w-3" strokeWidth={2} />
              Change
            </button>
          </div>

          {associated_preferences.length === 0 ? (
            <p className="mt-1.5 text-xs text-muted">
              No preferences linked yet. Associate this resume with one or more job
              preferences.
            </p>
          ) : (
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {associated_preferences.map((pref) => {
                const isApprovedForPref = Boolean(pref.approved_resume_version_id);
                return (
                  <span
                    key={pref.id}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-accent/25 bg-accent-soft px-2.5 py-1 text-xs font-medium text-accent-ink"
                  >
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${
                        pref.is_active ? 'bg-emerald-500' : 'bg-subtle'
                      }`}
                    />
                    <span>{pref.preference_name}</span>
                    {isApprovedForPref && (
                      <span
                        title="Approved resume linked for this preference"
                        className="rounded bg-emerald-500/20 px-1 py-0.2 text-[10px] font-semibold text-emerald-700 dark:text-emerald-300"
                      >
                        Approved
                      </span>
                    )}
                  </span>
                );
              })}
            </div>
          )}
        </div>

        {/* Phase 3B AI Actions Row */}
        {canAnalyse && (
          <div className="mt-4 flex flex-wrap items-center gap-2 rounded-xl border border-line bg-surface-2 p-2.5">
            <button
              type="button"
              disabled={effectiveAIStatus === 'Analysing'}
              onClick={() => {
                if (effectiveAIStatus === 'Not Analysed') {
                  onAnalyseNow(resume);
                } else {
                  onOpenIntelligence(resume, 'overview');
                }
              }}
              className="inline-flex items-center gap-1.5 rounded-xl bg-accent px-3 py-1.5 text-xs font-semibold text-white shadow-card transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {effectiveAIStatus === 'Analysing' ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={2.2} />
                  Analysing…
                </>
              ) : effectiveAIStatus === 'Not Analysed' ? (
                <>
                  <Sparkles className="h-3.5 w-3.5" strokeWidth={2.2} />
                  Analyse Resume
                </>
              ) : (
                <>
                  <Sparkles className="h-3.5 w-3.5" strokeWidth={2.2} />
                  AI Intelligence & Scores
                </>
              )}
            </button>

            <button
              type="button"
              onClick={() => onOpenIntelligence(resume, 'versions')}
              className="inline-flex items-center gap-1.5 rounded-xl border border-line bg-surface px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:border-subtle/50"
            >
              <History className="h-3.5 w-3.5 text-accent" strokeWidth={2} />
              Improve & Versions
            </button>

            {effectiveAIStatus !== 'Approved' && (
              <button
                type="button"
                onClick={() => onOpenIntelligence(resume, 'versions')}
                className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-500/35 bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-700 transition-colors hover:bg-emerald-500/20 dark:text-emerald-300"
              >
                <ShieldCheck className="h-3.5 w-3.5" strokeWidth={2.1} />
                Approve Resume
              </button>
            )}
          </div>
        )}
      </div>

      {/* Card Footer Actions: View, Download, Rename, Delete */}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-line pt-3.5">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => onView(resume)}
            className="inline-flex items-center gap-1.5 rounded-xl border border-line bg-surface-2 px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:border-subtle/50"
          >
            <Eye className="h-3.5 w-3.5 text-muted" strokeWidth={1.9} />
            View
          </button>

          <a
            href={downloadUrl}
            download
            className="inline-flex items-center gap-1.5 rounded-xl border border-line bg-surface-2 px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:border-subtle/50"
          >
            <Download className="h-3.5 w-3.5 text-muted" strokeWidth={1.9} />
            Download
          </a>

          <button
            type="button"
            onClick={() => onEdit(resume)}
            className="inline-flex items-center gap-1.5 rounded-xl border border-line bg-surface-2 px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:border-subtle/50"
          >
            <Pencil className="h-3.5 w-3.5 text-muted" strokeWidth={1.9} />
            Rename
          </button>
        </div>

        <button
          type="button"
          onClick={() => onRequestDelete(resume)}
          aria-label={`Delete ${resume_name}`}
          className="inline-flex items-center gap-1.5 rounded-xl border border-line bg-surface-2 px-3 py-1.5 text-xs font-medium text-rose-600 transition-colors hover:border-rose-500/30 hover:bg-rose-500/10 dark:text-rose-400"
        >
          <Trash2 className="h-3.5 w-3.5" strokeWidth={1.9} />
          Delete
        </button>
      </div>
    </article>
  );
}
