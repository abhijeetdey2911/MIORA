import { useEffect, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  FileText,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from 'lucide-react';
import { ResumeCard } from '../components/resumes/ResumeCard';
import { ResumeDeleteModal } from '../components/resumes/ResumeDeleteModal';
import { ResumeEditModal } from '../components/resumes/ResumeEditModal';
import {
  ResumeIntelligenceModal,
  type IntelligenceTab,
} from '../components/resumes/ResumeIntelligenceModal';
import { ResumeUploadModal } from '../components/resumes/ResumeUploadModal';
import { ResumeViewModal } from '../components/resumes/ResumeViewModal';
import { getPreferences } from '../services/preferenceService';
import {
  analyseResume,
  deleteResume,
  getAIProviderStatus,
  getResumeById,
  getResumes,
  updateResume,
  uploadResume,
} from '../services/resumeService';
import type { JobPreference } from '../types/preference';
import type {
  AIProviderStatus,
  ResumeItem,
  ResumeUpdatePayload,
} from '../types/resume';

interface FeedbackBanner {
  type: 'success' | 'error';
  message: string;
}

export function ResumesPage() {
  const [resumes, setResumes] = useState<ResumeItem[]>([]);
  const [preferences, setPreferences] = useState<JobPreference[]>([]);
  const [aiStatus, setAiStatus] = useState<AIProviderStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [uploadKey, setUploadKey] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadApiError, setUploadApiError] = useState<string | null>(null);

  const [viewingResume, setViewingResume] = useState<ResumeItem | null>(null);

  const [editingResume, setEditingResume] = useState<ResumeItem | null>(null);
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [editApiError, setEditApiError] = useState<string | null>(null);

  const [deletingResume, setDeletingResume] = useState<ResumeItem | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Phase 3B — AI Resume Intelligence state
  const [analysingResumeId, setAnalysingResumeId] = useState<string | null>(
    null,
  );
  const [intelligenceTarget, setIntelligenceTarget] = useState<{
    resume: ResumeItem;
    initialTab: IntelligenceTab;
  } | null>(null);

  const [feedback, setFeedback] = useState<FeedbackBanner | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      getResumes(),
      getPreferences().catch(() => []),
      getAIProviderStatus().catch(() => null),
    ])
      .then(([resumeData, prefData, providerStatus]) => {
        if (!cancelled) {
          setResumes(resumeData);
          setPreferences(prefData);
          setAiStatus(providerStatus);
          setLoadError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(
            err instanceof Error ? err.message : 'Failed to load resumes.',
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

  useEffect(() => {
    if (!feedback || feedback.type !== 'success') return;
    const timer = window.setTimeout(() => setFeedback(null), 4500);
    return () => window.clearTimeout(timer);
  }, [feedback]);

  const handleRetryLoad = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const [resumeData, prefData, providerStatus] = await Promise.all([
        getResumes(),
        getPreferences().catch(() => []),
        getAIProviderStatus().catch(() => null),
      ]);
      setResumes(resumeData);
      setPreferences(prefData);
      setAiStatus(providerStatus);
    } catch (err) {
      setLoadError(
        err instanceof Error ? err.message : 'Failed to load resumes.',
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefreshResumeAndPreferences = async (updatedResumeId: string) => {
    try {
      const [freshResume, prefData] = await Promise.all([
        getResumeById(updatedResumeId),
        getPreferences().catch(() => preferences),
      ]);
      setResumes((prev) =>
        prev.map((item) => (item.id === freshResume.id ? freshResume : item)),
      );
      setPreferences(prefData);
      setIntelligenceTarget((prev) =>
        prev && prev.resume.id === freshResume.id
          ? { ...prev, resume: freshResume }
          : prev,
      );
    } catch {
      // Keep current list on transient error
    }
  };

  const handleOpenUpload = () => {
    setUploadApiError(null);
    setUploadProgress(0);
    setUploadKey((prev) => prev + 1);
    setIsUploadOpen(true);
  };

  const handleUploadSubmit = async (options: {
    file: File;
    resumeName: string;
    preferenceIds: string[];
  }) => {
    setIsUploading(true);
    setUploadProgress(10);
    setUploadApiError(null);
    try {
      const created = await uploadResume({
        file: options.file,
        resumeName: options.resumeName,
        preferenceIds: options.preferenceIds,
        onProgress: (pct) => setUploadProgress(pct),
      });
      setResumes((prev) => [created, ...prev]);
      setIsUploadOpen(false);
      setFeedback({
        type: created.processing_status === 'Processed' ? 'success' : 'error',
        message:
          created.processing_status === 'Processed'
            ? `Uploaded and processed “${created.resume_name}”.`
            : `Uploaded “${created.resume_name}” with status: ${
                created.processing_message || created.processing_status
              }`,
      });
    } catch (err) {
      setUploadApiError(
        err instanceof Error ? err.message : 'Failed to upload resume.',
      );
    } finally {
      setIsUploading(false);
    }
  };

  const handleOpenEdit = (resume: ResumeItem) => {
    setEditApiError(null);
    setEditingResume(resume);
  };

  const handleSaveEdit = async (id: string, payload: ResumeUpdatePayload) => {
    setIsSavingEdit(true);
    setEditApiError(null);
    try {
      const updated = await updateResume(id, payload);
      setResumes((prev) =>
        prev.map((item) => (item.id === updated.id ? updated : item)),
      );
      setEditingResume(null);
      setFeedback({
        type: 'success',
        message: `Updated resume “${updated.resume_name}”.`,
      });
    } catch (err) {
      setEditApiError(
        err instanceof Error ? err.message : 'Failed to update resume.',
      );
    } finally {
      setIsSavingEdit(false);
    }
  };

  const handleConfirmDelete = async (resume: ResumeItem) => {
    setIsDeleting(true);
    try {
      await deleteResume(resume.id);
      setResumes((prev) => prev.filter((item) => item.id !== resume.id));
      setDeletingResume(null);
      setFeedback({
        type: 'success',
        message: `Deleted resume “${resume.resume_name}”.`,
      });
    } catch (err) {
      setFeedback({
        type: 'error',
        message:
          err instanceof Error ? err.message : 'Failed to delete resume.',
      });
      setDeletingResume(null);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleViewResume = async (resume: ResumeItem) => {
    setViewingResume(resume);
    try {
      const fresh = await getResumeById(resume.id);
      setViewingResume(fresh);
      setResumes((prev) =>
        prev.map((item) => (item.id === fresh.id ? fresh : item)),
      );
    } catch {
      // Keep already-loaded resume item displayed
    }
  };

  const handleOpenIntelligence = (
    resume: ResumeItem,
    initialTab: IntelligenceTab = 'overview',
  ) => {
    setIntelligenceTarget({ resume, initialTab });
  };

  const handleAnalyseNow = async (resume: ResumeItem) => {
    setAnalysingResumeId(resume.id);
    try {
      await analyseResume(resume.id);
      const fresh = await getResumeById(resume.id);
      setResumes((prev) =>
        prev.map((item) => (item.id === fresh.id ? fresh : item)),
      );
      setIntelligenceTarget({ resume: fresh, initialTab: 'overview' });
      setFeedback({
        type: 'success',
        message: `Completed AI Resume Analysis for “${fresh.resume_name}”.`,
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to analyse resume.';
      setFeedback({ type: 'error', message });
      setIntelligenceTarget({ resume, initialTab: 'overview' });
    } finally {
      setAnalysingResumeId(null);
    }
  };

  const processedCount = resumes.filter(
    (item) => item.processing_status === 'Processed',
  ).length;
  const processingCount = resumes.filter(
    (item) =>
      item.processing_status === 'Processing' ||
      item.processing_status === 'Uploaded',
  ).length;
  const failedCount = resumes.filter(
    (item) => item.processing_status === 'Failed',
  ).length;
  const approvedCount = resumes.filter(
    (item) => item.ai_status === 'Approved',
  ).length;
  const linkedCount = resumes.filter(
    (item) => item.associated_preferences.length > 0,
  ).length;

  const processingIndicator = (() => {
    if (isUploading || processingCount > 0 || analysingResumeId !== null) {
      return {
        label: analysingResumeId ? 'Status: AI Analysing…' : 'Status: Processing…',
        dotClass: 'bg-amber-500 animate-pulse',
        badgeClass:
          'bg-amber-500/10 text-amber-700 dark:bg-amber-400/15 dark:text-amber-300',
      };
    }
    if (failedCount > 0) {
      return {
        label: `Status: ${failedCount} Failed`,
        dotClass: 'bg-rose-500',
        badgeClass:
          'bg-rose-500/10 text-rose-600 dark:bg-rose-400/15 dark:text-rose-300',
      };
    }
    if (resumes.length > 0 && processedCount === resumes.length) {
      return {
        label: 'Status: All Ready',
        dotClass: 'bg-emerald-500',
        badgeClass:
          'bg-emerald-500/10 text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-300',
      };
    }
    return {
      label: 'Status: Idle',
      dotClass: 'bg-subtle',
      badgeClass: 'bg-surface-2 text-muted',
    };
  })();

  return (
    <div className="space-y-6">
      {/* Top Action Bar */}
      <div className="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-4 shadow-card sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-surface-2 px-2.5 py-1 font-medium text-ink">
            Total Resumes: {resumes.length}
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500/10 px-2.5 py-1 font-medium text-emerald-600 dark:bg-emerald-400/15 dark:text-emerald-300">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Processed: {processedCount}
          </span>
          <span
            className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 font-medium ${processingIndicator.badgeClass}`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${processingIndicator.dotClass}`}
            />
            {processingIndicator.label}
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-accent-soft px-2.5 py-1 font-medium text-accent-ink">
            <ShieldCheck className="h-3.5 w-3.5" strokeWidth={2} />
            Approved: {approvedCount}
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-surface-2 px-2.5 py-1 font-medium text-muted">
            {linkedCount} Linked to Preferences
          </span>
        </div>

        <button
          type="button"
          onClick={handleOpenUpload}
          className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-white shadow-card transition hover:brightness-105 active:scale-[0.99]"
        >
          <Upload className="h-4 w-4" strokeWidth={2.2} />
          Upload Resume
        </button>
      </div>

      {/* AI Provider Setup Notice when no API key is configured */}
      {aiStatus && !aiStatus.configured && (
        <div
          role="status"
          className="flex items-start gap-3 rounded-2xl border border-amber-500/35 bg-amber-500/10 px-4 py-3 text-xs text-amber-800 shadow-card dark:text-amber-200"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div className="space-y-0.5">
            <p className="font-semibold">
              AI Resume Intelligence Setup Required ({aiStatus.provider} /{' '}
              {aiStatus.model})
            </p>
            <p>
              {aiStatus.setup_message ||
                'Add AI_API_KEY to your backend .env file to enable live AI Resume Analysis and Improve My Resume draft generation. You can still manage versions and approve resumes now.'}
            </p>
          </div>
        </div>
      )}

      {aiStatus && aiStatus.configured && (
        <div className="flex items-center gap-2 rounded-2xl border border-line bg-surface px-4 py-2.5 text-xs text-muted shadow-card">
          <Sparkles className="h-4 w-4 shrink-0 text-accent" />
          <span>
            AI Resume Intelligence active (
            <strong className="font-semibold text-ink">
              {aiStatus.provider} · {aiStatus.model}
            </strong>
            ). Click <strong className="font-semibold text-ink">Analyse Resume</strong>{' '}
            on any processed resume to evaluate skills, preferences, and generate
            improvements.
          </span>
        </div>
      )}

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

      {/* Content Area */}
      {isLoading ? (
        <div
          aria-label="Loading resumes"
          className="grid grid-cols-1 gap-4 md:grid-cols-2"
        >
          {[0, 1].map((skeleton) => (
            <div
              key={skeleton}
              className="h-60 animate-pulse rounded-2xl border border-line bg-surface p-5 shadow-card"
            >
              <div className="flex items-center justify-between">
                <div className="h-5 w-48 rounded bg-surface-2" />
                <div className="h-5 w-20 rounded-full bg-surface-2" />
              </div>
              <div className="mt-4 h-9 rounded-xl bg-surface-2" />
              <div className="mt-4 flex gap-2">
                <div className="h-6 w-28 rounded-lg bg-surface-2" />
                <div className="h-6 w-24 rounded-lg bg-surface-2" />
              </div>
            </div>
          ))}
        </div>
      ) : loadError ? (
        <div
          role="alert"
          className="flex flex-col items-center justify-center rounded-2xl border border-line bg-surface px-6 py-12 text-center shadow-card"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-rose-500/10 text-rose-600 dark:bg-rose-400/15 dark:text-rose-400">
            <AlertCircle className="h-6 w-6" strokeWidth={1.9} />
          </div>
          <h2 className="mt-4 text-base font-semibold text-ink">
            Could not load resumes
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
      ) : resumes.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-line bg-surface px-6 py-14 text-center shadow-card">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent-soft text-accent-ink">
            <FileText className="h-5 w-5" strokeWidth={1.9} />
          </div>
          <h2 className="mt-4 text-base font-semibold text-ink">
            No resumes uploaded yet
          </h2>
          <p className="mt-1 max-w-md text-xs text-muted">
            Upload your PDF or DOCX resumes, associate them with your job preferences,
            analyse them with AI, and approve a final version.
          </p>
          <button
            type="button"
            onClick={handleOpenUpload}
            className="mt-5 inline-flex items-center gap-1.5 rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-white shadow-card transition hover:brightness-105"
          >
            <Upload className="h-4 w-4" strokeWidth={2.2} />
            Upload Resume
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {resumes.map((resume) => (
            <ResumeCard
              key={resume.id}
              resume={resume}
              isAnalysingThisResume={analysingResumeId === resume.id}
              onView={(item) => void handleViewResume(item)}
              onEdit={(item) => handleOpenEdit(item)}
              onRequestDelete={(item) => setDeletingResume(item)}
              onOpenIntelligence={handleOpenIntelligence}
              onAnalyseNow={(item) => void handleAnalyseNow(item)}
            />
          ))}
        </div>
      )}

      {/* Upload Modal */}
      {isUploadOpen && (
        <ResumeUploadModal
          key={uploadKey}
          isOpen={isUploadOpen}
          existingResumes={resumes}
          preferences={preferences}
          isUploading={isUploading}
          uploadProgress={uploadProgress}
          apiError={uploadApiError}
          onClose={() => {
            if (!isUploading) setIsUploadOpen(false);
          }}
          onUpload={handleUploadSubmit}
        />
      )}

      {/* View Modal */}
      <ResumeViewModal
        resume={viewingResume}
        onClose={() => setViewingResume(null)}
      />

      {/* Rename & Preference Association Modal */}
      {editingResume && (
        <ResumeEditModal
          key={editingResume.id}
          resume={editingResume}
          preferences={preferences}
          isSaving={isSavingEdit}
          apiError={editApiError}
          onClose={() => {
            if (!isSavingEdit) setEditingResume(null);
          }}
          onSave={handleSaveEdit}
        />
      )}

      {/* Delete Confirmation Modal */}
      <ResumeDeleteModal
        resume={deletingResume}
        isDeleting={isDeleting}
        onCancel={() => setDeletingResume(null)}
        onConfirm={(item) => void handleConfirmDelete(item)}
      />

      {/* Phase 3B — AI Resume Intelligence & Version Approval Modal */}
      {intelligenceTarget && (
        <ResumeIntelligenceModal
          key={`${intelligenceTarget.resume.id}-${intelligenceTarget.initialTab}`}
          resume={intelligenceTarget.resume}
          initialTab={intelligenceTarget.initialTab}
          aiStatus={aiStatus}
          preferences={preferences}
          onClose={() => setIntelligenceTarget(null)}
          onResumeUpdated={handleRefreshResumeAndPreferences}
        />
      )}
    </div>
  );
}
