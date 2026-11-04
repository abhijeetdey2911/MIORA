import { useEffect, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  Award,
  Briefcase,
  Check,
  CheckCircle2,
  FolderGit2,
  GraduationCap,
  HelpCircle,
  Info,
  Loader2,
  Pencil,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Target,
  Wrench,
  X,
} from 'lucide-react';
import {
  analyseResume,
  approveResumeVersion,
  createUserResumeVersion,
  enhanceResumeDraft,
  getResumeAnalysis,
  getResumeVersions,
  regenerateResumeSuggestion,
  updateResumeSuggestion,
} from '../../services/resumeService';
import type { JobPreference } from '../../types/preference';
import {
  formatUploadDate,
  type AIProviderStatus,
  type ResumeAnalysisData,
  type ResumeItem,
  type ResumeSuggestionItem,
  type ResumeVersionItem,
  type SuggestionPriority,
} from '../../types/resume';

export type IntelligenceTab =
  | 'overview'
  | 'preferences'
  | 'suggestions'
  | 'versions';

interface ResumeIntelligenceModalProps {
  resume: ResumeItem;
  initialTab: IntelligenceTab;
  aiStatus: AIProviderStatus | null;
  preferences: JobPreference[];
  onClose: () => void;
  onResumeUpdated: (updatedResumeId: string) => Promise<void>;
}

const PRIORITY_STYLES: Record<SuggestionPriority, string> = {
  High: 'bg-rose-500/15 text-rose-600 dark:text-rose-300',
  Medium: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  Low: 'bg-sky-500/15 text-sky-600 dark:text-sky-300',
};

function scoreBadgeColor(score: number): string {
  if (score >= 80) {
    return 'text-emerald-600 dark:text-emerald-300 bg-emerald-500/10 border-emerald-500/30';
  }
  if (score >= 60) {
    return 'text-amber-600 dark:text-amber-300 bg-amber-500/10 border-amber-500/30';
  }
  return 'text-rose-600 dark:text-rose-300 bg-rose-500/10 border-rose-500/30';
}

export function ResumeIntelligenceModal({
  resume,
  initialTab,
  aiStatus,
  preferences,
  onClose,
  onResumeUpdated,
}: ResumeIntelligenceModalProps) {
  const [activeTab, setActiveTab] = useState<IntelligenceTab>(() => initialTab);
  const [analysis, setAnalysis] = useState<ResumeAnalysisData | null>(null);
  const [suggestions, setSuggestions] = useState<ResumeSuggestionItem[]>([]);
  const [versions, setVersions] = useState<ResumeVersionItem[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(
    () => resume.approved_version_id,
  );

  const [isLoadingData, setIsLoadingData] = useState(true);
  const [isAnalysing, setIsAnalysing] = useState(false);
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [isSavingVersion, setIsSavingVersion] = useState(false);
  const [isApproving, setIsApproving] = useState(false);

  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  // Suggestion inline editing & regeneration state
  const [editingSuggestionId, setEditingSuggestionId] = useState<string | null>(
    null,
  );
  const [editingSuggestionText, setEditingSuggestionText] = useState('');
  const [regeneratingSuggestionId, setRegeneratingSuggestionId] = useState<
    string | null
  >(null);

  // User-edited version editor state
  const [isEditingVersionText, setIsEditingVersionText] = useState(false);
  const [customVersionTitle, setCustomVersionTitle] = useState('');
  const [customVersionContent, setCustomVersionContent] = useState('');

  // Selected preferences to link when clicking Approve Resume
  const [approvalPreferenceIds, setApprovalPreferenceIds] = useState<string[]>(
    () => resume.associated_preferences.map((p) => p.id),
  );

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      getResumeAnalysis(resume.id).catch(() => null),
      getResumeVersions(resume.id).catch(() => []),
    ])
      .then(([loadedAnalysis, loadedVersions]) => {
        if (cancelled) return;
        if (loadedAnalysis) {
          setAnalysis(loadedAnalysis);
          setSuggestions(loadedAnalysis.suggestions ?? []);
        }
        setVersions(loadedVersions);
        if (loadedVersions.length > 0) {
          const latest = loadedVersions[loadedVersions.length - 1];
          setSelectedVersionId((prev) => prev ?? latest.id);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingData(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [resume.id]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isAnalysing && !isEnhancing && !isApproving) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isAnalysing, isEnhancing, isApproving, onClose]);

  const handleRunAnalysis = async () => {
    setIsAnalysing(true);
    setErrorBanner(null);
    setSuccessBanner(null);
    try {
      const result = await analyseResume(resume.id);
      setAnalysis(result);
      setSuggestions(result.suggestions ?? []);
      const updatedVersions = await getResumeVersions(resume.id).catch(
        () => versions,
      );
      setVersions(updatedVersions);
      if (updatedVersions.length > 0 && !selectedVersionId) {
        setSelectedVersionId(updatedVersions[updatedVersions.length - 1].id);
      }
      setActiveTab('overview');
      setSuccessBanner(
        `AI Resume Analysis completed for “${resume.resume_name}”.`,
      );
      await onResumeUpdated(resume.id);
    } catch (err) {
      setErrorBanner(
        err instanceof Error ? err.message : 'Failed to analyse resume.',
      );
    } finally {
      setIsAnalysing(false);
    }
  };

  const handleSuggestionAction = async (
    suggestionId: string,
    status: 'Accepted' | 'Rejected' | 'Pending',
    editedText?: string,
  ) => {
    setErrorBanner(null);
    try {
      const updated = await updateResumeSuggestion(resume.id, suggestionId, {
        status,
        ...(editedText !== undefined
          ? { user_edited_content: editedText }
          : {}),
      });
      setSuggestions((prev) =>
        prev.map((item) => (item.id === updated.id ? updated : item)),
      );
      setEditingSuggestionId(null);
    } catch (err) {
      setErrorBanner(
        err instanceof Error ? err.message : 'Failed to update suggestion.',
      );
    }
  };

  const handleRegenerateSuggestion = async (suggestionId: string) => {
    setRegeneratingSuggestionId(suggestionId);
    setErrorBanner(null);
    try {
      const updated = await regenerateResumeSuggestion(resume.id, suggestionId);
      setSuggestions((prev) =>
        prev.map((item) => (item.id === updated.id ? updated : item)),
      );
      setSuccessBanner(`Regenerated suggestion for ${updated.section_name}.`);
    } catch (err) {
      setErrorBanner(
        err instanceof Error ? err.message : 'Failed to regenerate suggestion.',
      );
    } finally {
      setRegeneratingSuggestionId(null);
    }
  };

  const handleEnhanceResume = async () => {
    setIsEnhancing(true);
    setErrorBanner(null);
    setSuccessBanner(null);
    try {
      const draftVersion = await enhanceResumeDraft(resume.id, {
        apply_accepted_suggestions: true,
      });
      const refreshedVersions = await getResumeVersions(resume.id);
      setVersions(refreshedVersions);
      setSelectedVersionId(draftVersion.id);
      setIsEditingVersionText(false);
      setActiveTab('versions');
      setSuccessBanner(
        `Generated AI-enhanced draft “${draftVersion.title}”. Review the side-by-side comparison below and approve when ready.`,
      );
      await onResumeUpdated(resume.id);
    } catch (err) {
      setErrorBanner(
        err instanceof Error ? err.message : 'Failed to generate improved draft.',
      );
    } finally {
      setIsEnhancing(false);
    }
  };

  const handleStartUserEditVersion = (sourceVersion: ResumeVersionItem) => {
    setCustomVersionTitle(
      `User-Edited Draft (based on v${sourceVersion.version_number})`,
    );
    setCustomVersionContent(sourceVersion.content);
    setIsEditingVersionText(true);
  };

  const handleSaveUserVersion = async () => {
    if (!customVersionContent.trim()) {
      setErrorBanner('Resume version content cannot be empty.');
      return;
    }
    setIsSavingVersion(true);
    setErrorBanner(null);
    try {
      const created = await createUserResumeVersion(resume.id, {
        title: customVersionTitle.trim() || undefined,
        content: customVersionContent,
        target_preference_ids: approvalPreferenceIds,
      });
      const refreshedVersions = await getResumeVersions(resume.id);
      setVersions(refreshedVersions);
      setSelectedVersionId(created.id);
      setIsEditingVersionText(false);
      setSuccessBanner(
        `Saved new user-edited version “${created.title}” without modifying the original resume.`,
      );
      await onResumeUpdated(resume.id);
    } catch (err) {
      setErrorBanner(
        err instanceof Error ? err.message : 'Failed to save user-edited version.',
      );
    } finally {
      setIsSavingVersion(false);
    }
  };

  const handleApproveSelectedVersion = async (version: ResumeVersionItem) => {
    setIsApproving(true);
    setErrorBanner(null);
    setSuccessBanner(null);
    try {
      const response = await approveResumeVersion(
        resume.id,
        version.id,
        approvalPreferenceIds,
      );
      const refreshedVersions = await getResumeVersions(resume.id);
      setVersions(refreshedVersions);
      setSelectedVersionId(response.approved_version.id);
      setSuccessBanner(response.message);
      await onResumeUpdated(resume.id);
    } catch (err) {
      setErrorBanner(
        err instanceof Error ? err.message : 'Failed to approve resume version.',
      );
    } finally {
      setIsApproving(false);
    }
  };

  const toggleApprovalPreference = (prefId: string) => {
    setApprovalPreferenceIds((prev) =>
      prev.includes(prefId)
        ? prev.filter((id) => id !== prefId)
        : [...prev, prefId],
    );
  };

  const originalVersion =
    versions.find((v) => v.version_number === 1) ?? versions[0] ?? null;
  const selectedVersion =
    versions.find((v) => v.id === selectedVersionId) ??
    versions[versions.length - 1] ??
    null;

  const scoreCards = analysis
    ? [
        {
          key: 'overall_quality',
          label: 'Overall Resume Quality',
          score: analysis.overall_quality_score,
          explanation:
            analysis.score_explanations?.overall_quality ||
            'Overall structural clarity, completeness, and impact.',
        },
        {
          key: 'preference_relevance',
          label: 'Job Preference Relevance',
          score: analysis.preference_relevance_score,
          explanation:
            analysis.score_explanations?.preference_relevance ||
            'Alignment with target job roles in associated preferences.',
        },
        {
          key: 'skills_alignment',
          label: 'Skills Alignment',
          score: analysis.skills_alignment_score,
          explanation:
            analysis.score_explanations?.skills_alignment ||
            'Match between extracted skills and target preference skills.',
        },
        {
          key: 'experience_alignment',
          label: 'Experience Alignment',
          score: analysis.experience_alignment_score,
          explanation:
            analysis.score_explanations?.experience_alignment ||
            'Relevance of work history and internships to target level.',
        },
        {
          key: 'project_relevance',
          label: 'Project Relevance',
          score: analysis.project_relevance_score,
          explanation:
            analysis.score_explanations?.project_relevance ||
            'Technical depth and domain alignment of listed projects.',
        },
        {
          key: 'ats_readability',
          label: 'ATS Readability',
          score: analysis.ats_readability_score,
          explanation:
            analysis.score_explanations?.ats_readability ||
            'Section hierarchy, machine-readability, and keyword clarity.',
        },
      ]
    : [];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="resume-intelligence-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6"
    >
      <div
        aria-hidden="true"
        onClick={() => {
          if (!isAnalysing && !isEnhancing && !isApproving) onClose();
        }}
        className="fixed inset-0 bg-black/55 backdrop-blur-[2px]"
      />

      <div className="relative z-10 flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-line bg-surface shadow-card">
        {/* Modal Header */}
        <div className="flex flex-col gap-3 border-b border-line px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2
                id="resume-intelligence-modal-title"
                className="truncate text-lg font-semibold text-ink"
              >
                {resume.resume_name}
              </h2>
              <span className="rounded-full bg-accent-soft px-2.5 py-0.5 text-[11px] font-semibold text-accent-ink">
                {isAnalysing ? 'Analysing…' : resume.ai_status || 'Not Analysed'}
              </span>
            </div>
            <p className="mt-0.5 text-xs text-muted">
              AI Resume Intelligence · Preference Evaluation · Improvement
              Suggestions · Version History & Approval
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={isAnalysing || isEnhancing}
              onClick={() => void handleRunAnalysis()}
              className="inline-flex items-center gap-1.5 rounded-xl bg-accent px-3.5 py-2 text-xs font-semibold text-white shadow-card transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isAnalysing ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={2.2} />
                  Analysing Resume…
                </>
              ) : (
                <>
                  <Sparkles className="h-3.5 w-3.5" strokeWidth={2.2} />
                  {analysis ? 'Re-analyse Resume' : 'Analyse Resume'}
                </>
              )}
            </button>

            <button
              type="button"
              disabled={isAnalysing || isEnhancing}
              onClick={() => void handleEnhanceResume()}
              className="inline-flex items-center gap-1.5 rounded-xl border border-accent/35 bg-accent-soft px-3.5 py-2 text-xs font-semibold text-accent-ink transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isEnhancing ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={2.2} />
                  Generating Draft…
                </>
              ) : (
                <>
                  <Wrench className="h-3.5 w-3.5" strokeWidth={2} />
                  Improve My Resume
                </>
              )}
            </button>

            <button
              type="button"
              onClick={onClose}
              aria-label="Close AI Intelligence modal"
              className="rounded-xl p-1.5 text-muted transition-colors hover:bg-surface-2 hover:text-ink"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex flex-wrap items-center gap-1 border-b border-line bg-surface-2 px-6 py-2">
          {[
            { id: 'overview', label: '1. Overview & Scores' },
            {
              id: 'preferences',
              label: `2. Preference Relevance (${
                analysis?.preference_analyses.length ??
                resume.associated_preferences.length
              })`,
            },
            {
              id: 'suggestions',
              label: `3. Improvement Suggestions (${suggestions.length})`,
            },
            {
              id: 'versions',
              label: `4. Compare, Versions & Approve (${versions.length})`,
            },
          ].map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id as IntelligenceTab)}
                className={`rounded-xl px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                  isActive
                    ? 'bg-accent text-white shadow-card'
                    : 'text-muted hover:bg-surface hover:text-ink'
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 space-y-5 overflow-y-auto px-6 py-5">
          {/* Missing AI Provider Setup Banner */}
          {aiStatus && !aiStatus.configured && (
            <div
              role="status"
              className="flex items-start gap-3 rounded-2xl border border-amber-500/35 bg-amber-500/10 p-4 text-xs text-amber-800 dark:text-amber-200"
            >
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <div className="space-y-1">
                <p className="font-semibold">
                  AI Provider Not Configured ({aiStatus.provider} / {aiStatus.model})
                </p>
                <p>
                  {aiStatus.setup_message ||
                    'Set AI_API_KEY in your backend .env file to enable live AI resume analysis and draft generation. JobHunter never substitutes fake or mock AI data.'}
                </p>
                <p className="text-[11px] opacity-85">
                  Note: You can still view version history, create user-edited
                  versions, and approve a resume version below.
                </p>
              </div>
            </div>
          )}

          {/* Live Progress Indicator */}
          {(isAnalysing || isEnhancing) && (
            <div className="flex items-center gap-3 rounded-2xl border border-accent/30 bg-accent-soft p-4 text-xs font-medium text-accent-ink">
              <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
              <span>
                {isAnalysing
                  ? 'Analysing extracted resume text, evaluating associated job preferences, and computing 0–100 score estimates…'
                  : 'Generating fact-preserving AI resume enhancement draft with side-by-side section comparisons…'}
              </span>
            </div>
          )}

          {/* Error / Success Banners */}
          {errorBanner && (
            <div
              role="alert"
              className="flex items-start justify-between gap-3 rounded-2xl border border-rose-500/35 bg-rose-500/10 p-3.5 text-xs text-rose-600 dark:text-rose-300"
            >
              <div className="flex items-start gap-2">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{errorBanner}</span>
              </div>
              <button
                type="button"
                onClick={() => setErrorBanner(null)}
                className="rounded p-0.5 opacity-75 hover:opacity-100"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          )}

          {successBanner && (
            <div
              role="status"
              className="flex items-start justify-between gap-3 rounded-2xl border border-emerald-500/35 bg-emerald-500/10 p-3.5 text-xs text-emerald-700 dark:text-emerald-300"
            >
              <div className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{successBanner}</span>
              </div>
              <button
                type="button"
                onClick={() => setSuccessBanner(null)}
                className="rounded p-0.5 opacity-75 hover:opacity-100"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          )}

          {isLoadingData ? (
            <div className="flex items-center justify-center py-12 text-xs text-muted">
              <Loader2 className="mr-2 h-4 w-4 animate-spin text-accent" />
              Loading resume intelligence data…
            </div>
          ) : (
            <>
              {/* ============================================================ */}
              {/* TAB 1: OVERVIEW & SCORES                                     */}
              {/* ============================================================ */}
              {activeTab === 'overview' && (
                <>
                  {!analysis ? (
                    <div className="flex flex-col items-center justify-center rounded-2xl border border-line bg-surface-2 px-6 py-12 text-center">
                      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent-soft text-accent-ink">
                        <Sparkles className="h-5 w-5" strokeWidth={1.9} />
                      </div>
                      <h3 className="mt-3 text-base font-semibold text-ink">
                        Resume Not Analysed Yet
                      </h3>
                      <p className="mt-1 max-w-md text-xs text-muted">
                        Click “Analyse Resume” to extract your structured candidate
                        profile, evaluate alignment with your associated job
                        preferences, and generate 0–100 score estimates and
                        actionable section suggestions.
                      </p>
                      <button
                        type="button"
                        disabled={isAnalysing}
                        onClick={() => void handleRunAnalysis()}
                        className="mt-4 inline-flex items-center gap-1.5 rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-white shadow-card transition hover:brightness-105 disabled:opacity-60"
                      >
                        <Sparkles className="h-4 w-4" strokeWidth={2.2} />
                        Analyse Resume
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-5">
                      {/* Score Estimate Disclaimer */}
                      <div className="flex items-center gap-2 rounded-xl border border-line bg-surface-2 px-3.5 py-2.5 text-xs text-muted">
                        <Info className="h-4 w-4 shrink-0 text-accent" />
                        <span>{analysis.score_disclaimer}</span>
                      </div>

                      {/* 6 Score Cards (0-100) */}
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        {scoreCards.map((card) => (
                          <div
                            key={card.key}
                            className="flex flex-col justify-between rounded-2xl border border-line bg-surface-2 p-4"
                          >
                            <div>
                              <div className="flex items-center justify-between gap-2">
                                <span className="text-xs font-semibold text-ink">
                                  {card.label}
                                </span>
                                <span
                                  className={`rounded-lg border px-2 py-0.5 text-xs font-bold ${scoreBadgeColor(
                                    card.score,
                                  )}`}
                                >
                                  {card.score}/100
                                </span>
                              </div>
                              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface">
                                <div
                                  className="h-full rounded-full bg-accent"
                                  style={{ width: `${card.score}%` }}
                                />
                              </div>
                            </div>
                            <p className="mt-2.5 text-[11px] leading-relaxed text-muted">
                              {card.explanation}
                            </p>
                          </div>
                        ))}
                      </div>

                      {/* Candidate Profile & Skills Overview */}
                      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                        <div className="rounded-2xl border border-line bg-surface-2 p-4">
                          <h3 className="text-xs font-semibold uppercase tracking-wider text-subtle">
                            Candidate Profile Evaluation
                          </h3>
                          <div className="mt-2.5 space-y-1.5 text-xs text-ink">
                            <p>
                              <strong className="font-semibold">Name:</strong>{' '}
                              {analysis.candidate_profile.full_name ||
                                'Not explicitly stated'}
                            </p>
                            <p>
                              <strong className="font-semibold">Headline:</strong>{' '}
                              {analysis.candidate_profile.headline ||
                                'Not explicitly stated'}
                            </p>
                            <p>
                              <strong className="font-semibold">
                                Experience:
                              </strong>{' '}
                              {analysis.candidate_profile.years_of_experience ||
                                'Not explicitly stated'}
                            </p>
                            <p>
                              <strong className="font-semibold">Location:</strong>{' '}
                              {analysis.candidate_profile.location ||
                                'Not explicitly stated'}
                            </p>
                            {analysis.candidate_profile.summary_evaluation && (
                              <p className="mt-2 rounded-xl border border-line bg-surface p-2.5 text-muted">
                                {analysis.candidate_profile.summary_evaluation}
                              </p>
                            )}
                          </div>
                        </div>

                        <div className="rounded-2xl border border-line bg-surface-2 p-4">
                          <h3 className="text-xs font-semibold uppercase tracking-wider text-subtle">
                            Skills & Tools Overview
                          </h3>
                          <div className="mt-2.5 space-y-3 text-xs">
                            <div>
                              <p className="font-semibold text-ink">
                                Technical Skills (
                                {analysis.technical_skills.length})
                              </p>
                              <div className="mt-1 flex flex-wrap gap-1.5">
                                {analysis.technical_skills.length === 0 ? (
                                  <span className="text-muted">None listed</span>
                                ) : (
                                  analysis.technical_skills.map((skill) => (
                                    <span
                                      key={skill}
                                      className="rounded-lg border border-accent/25 bg-accent-soft px-2 py-0.5 text-[11px] font-medium text-accent-ink"
                                    >
                                      {skill}
                                    </span>
                                  ))
                                )}
                              </div>
                            </div>

                            <div>
                              <p className="font-semibold text-ink">
                                Tools & Technologies (
                                {analysis.tools_and_technologies.length})
                              </p>
                              <div className="mt-1 flex flex-wrap gap-1.5">
                                {analysis.tools_and_technologies.length === 0 ? (
                                  <span className="text-muted">None listed</span>
                                ) : (
                                  analysis.tools_and_technologies.map((tool) => (
                                    <span
                                      key={tool}
                                      className="rounded-lg border border-line bg-surface px-2 py-0.5 text-[11px] text-ink"
                                    >
                                      {tool}
                                    </span>
                                  ))
                                )}
                              </div>
                            </div>

                            <div>
                              <p className="font-semibold text-ink">
                                Soft Skills ({analysis.soft_skills.length})
                              </p>
                              <div className="mt-1 flex flex-wrap gap-1.5">
                                {analysis.soft_skills.length === 0 ? (
                                  <span className="text-muted">None listed</span>
                                ) : (
                                  analysis.soft_skills.map((soft) => (
                                    <span
                                      key={soft}
                                      className="rounded-lg border border-line bg-surface px-2 py-0.5 text-[11px] text-muted"
                                    >
                                      {soft}
                                    </span>
                                  ))
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Strengths & Weaknesses */}
                      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                        <div className="rounded-2xl border border-emerald-500/25 bg-emerald-500/5 p-4">
                          <h3 className="text-xs font-semibold text-emerald-700 dark:text-emerald-300">
                            Key Resume Strengths
                          </h3>
                          <ul className="mt-2 list-disc space-y-1.5 pl-4 text-xs text-ink">
                            {analysis.overall_strengths.map((item, idx) => (
                              <li key={idx}>{item}</li>
                            ))}
                          </ul>
                        </div>

                        <div className="rounded-2xl border border-amber-500/25 bg-amber-500/5 p-4">
                          <h3 className="text-xs font-semibold text-amber-700 dark:text-amber-300">
                            Areas for Improvement
                          </h3>
                          <ul className="mt-2 list-disc space-y-1.5 pl-4 text-xs text-ink">
                            {analysis.overall_weaknesses.map((item, idx) => (
                              <li key={idx}>{item}</li>
                            ))}
                          </ul>
                        </div>
                      </div>

                      {/* Clarifying Questions (No-Assumption Guarantee) */}
                      {analysis.missing_information_questions.length > 0 && (
                        <div className="rounded-2xl border border-sky-500/30 bg-sky-500/10 p-4 text-xs">
                          <div className="flex items-center gap-2 font-semibold text-sky-700 dark:text-sky-300">
                            <HelpCircle className="h-4 w-4 shrink-0" />
                            <span>
                              Questions to Strengthen Your Resume (No Assumptions
                              Made)
                            </span>
                          </div>
                          <ul className="mt-2 list-disc space-y-1 pl-5 text-ink">
                            {analysis.missing_information_questions.map(
                              (q, idx) => (
                                <li key={idx}>{q}</li>
                              ),
                            )}
                          </ul>
                        </div>
                      )}

                      {/* Extracted Experience, Projects, Education, Certifications */}
                      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                        <div className="rounded-2xl border border-line bg-surface-2 p-4">
                          <div className="flex items-center gap-2 text-xs font-semibold text-ink">
                            <Briefcase className="h-4 w-4 text-accent" />
                            <span>
                              Work Experience ({analysis.work_experience.length}) &
                              Internships ({analysis.internships.length})
                            </span>
                          </div>
                          <div className="mt-2.5 space-y-2.5 text-xs">
                            {[
                              ...analysis.work_experience,
                              ...analysis.internships,
                            ].map((exp, idx) => (
                              <div
                                key={idx}
                                className="rounded-xl border border-line bg-surface p-2.5"
                              >
                                <p className="font-semibold text-ink">
                                  {exp.role}{' '}
                                  {exp.company ? `· ${exp.company}` : ''}
                                </p>
                                {exp.duration && (
                                  <p className="text-[11px] text-muted">
                                    {exp.duration}
                                  </p>
                                )}
                              </div>
                            ))}
                            {analysis.work_experience.length === 0 &&
                              analysis.internships.length === 0 && (
                                <p className="text-muted">
                                  No experience entries extracted.
                                </p>
                              )}
                          </div>
                        </div>

                        <div className="rounded-2xl border border-line bg-surface-2 p-4">
                          <div className="flex items-center gap-2 text-xs font-semibold text-ink">
                            <FolderGit2 className="h-4 w-4 text-accent" />
                            <span>Projects ({analysis.projects.length})</span>
                          </div>
                          <div className="mt-2.5 space-y-2.5 text-xs">
                            {analysis.projects.map((proj, idx) => (
                              <div
                                key={idx}
                                className="rounded-xl border border-line bg-surface p-2.5"
                              >
                                <p className="font-semibold text-ink">
                                  {proj.title}
                                </p>
                                <p className="mt-0.5 text-muted">{proj.summary}</p>
                              </div>
                            ))}
                            {analysis.projects.length === 0 && (
                              <p className="text-muted">
                                No project entries extracted.
                              </p>
                            )}
                          </div>
                        </div>

                        <div className="rounded-2xl border border-line bg-surface-2 p-4">
                          <div className="flex items-center gap-2 text-xs font-semibold text-ink">
                            <GraduationCap className="h-4 w-4 text-accent" />
                            <span>Education ({analysis.education.length})</span>
                          </div>
                          <div className="mt-2.5 space-y-2 text-xs">
                            {analysis.education.map((edu, idx) => (
                              <div
                                key={idx}
                                className="rounded-xl border border-line bg-surface p-2.5"
                              >
                                <p className="font-semibold text-ink">
                                  {edu.degree}
                                </p>
                                <p className="text-[11px] text-muted">
                                  {[edu.institution, edu.graduation_year]
                                    .filter(Boolean)
                                    .join(' · ')}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>

                        <div className="rounded-2xl border border-line bg-surface-2 p-4">
                          <div className="flex items-center gap-2 text-xs font-semibold text-ink">
                            <Award className="h-4 w-4 text-accent" />
                            <span>Certifications & Achievements</span>
                          </div>
                          <ul className="mt-2.5 list-disc space-y-1 pl-4 text-xs text-ink">
                            {[
                              ...analysis.certifications,
                              ...analysis.achievements,
                            ].map((item, idx) => (
                              <li key={idx}>{item}</li>
                            ))}
                            {analysis.certifications.length === 0 &&
                              analysis.achievements.length === 0 && (
                                <li className="list-none text-muted">
                                  None explicitly listed in the resume.
                                </li>
                              )}
                          </ul>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* ============================================================ */}
              {/* TAB 2: PREFERENCE-BASED ANALYSIS                             */}
              {/* ============================================================ */}
              {activeTab === 'preferences' && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2 rounded-xl border border-line bg-surface-2 px-3.5 py-2.5 text-xs text-muted">
                    <Target className="h-4 w-4 shrink-0 text-accent" />
                    <span>
                      {analysis?.missing_keywords_disclaimer ||
                        'Missing keywords indicate terms not explicitly found in the resume text and are not proof that the candidate lacks a skill.'}
                    </span>
                  </div>

                  {!analysis || analysis.preference_analyses.length === 0 ? (
                    <div className="rounded-2xl border border-line bg-surface-2 p-8 text-center text-xs text-muted">
                      {resume.associated_preferences.length === 0
                        ? 'Associate this resume with one or more Job Preferences (e.g. Data Analytics or Software Development), then click “Analyse Resume” to generate per-preference evaluations.'
                        : 'Click “Analyse Resume” to evaluate this resume against each associated job preference.'}
                    </div>
                  ) : (
                    analysis.preference_analyses.map((prefEval) => (
                      <div
                        key={prefEval.preference_id}
                        className="space-y-3 rounded-2xl border border-line bg-surface-2 p-5"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
                          <div>
                            <h3 className="text-sm font-semibold text-ink">
                              {prefEval.preference_name}
                            </h3>
                            {prefEval.target_roles.length > 0 && (
                              <p className="mt-0.5 text-xs text-muted">
                                Target Roles: {prefEval.target_roles.join(', ')}
                              </p>
                            )}
                          </div>
                          <span
                            className={`rounded-xl border px-3 py-1 text-xs font-bold ${scoreBadgeColor(
                              prefEval.preference_relevance_score,
                            )}`}
                          >
                            Relevance: {prefEval.preference_relevance_score}/100
                            (Est.)
                          </span>
                        </div>

                        {prefEval.score_explanation && (
                          <p className="text-xs text-ink">
                            {prefEval.score_explanation}
                          </p>
                        )}

                        {prefEval.experience_alignment && (
                          <p className="rounded-xl border border-line bg-surface p-3 text-xs text-muted">
                            <strong className="font-semibold text-ink">
                              Experience Alignment:
                            </strong>{' '}
                            {prefEval.experience_alignment}
                          </p>
                        )}

                        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                          <div className="rounded-xl border border-line bg-surface p-3 text-xs">
                            <p className="font-semibold text-ink">
                              Relevant Skills
                            </p>
                            <div className="mt-1.5 flex flex-wrap gap-1">
                              {prefEval.relevant_skills.map((s) => (
                                <span
                                  key={s}
                                  className="rounded bg-emerald-500/15 px-2 py-0.5 text-[11px] font-medium text-emerald-700 dark:text-emerald-300"
                                >
                                  {s}
                                </span>
                              ))}
                            </div>
                          </div>

                          <div className="rounded-xl border border-line bg-surface p-3 text-xs">
                            <p className="font-semibold text-ink">
                              Relevant Projects
                            </p>
                            <ul className="mt-1.5 list-disc space-y-0.5 pl-4 text-muted">
                              {prefEval.relevant_projects.map((p) => (
                                <li key={p}>{p}</li>
                              ))}
                            </ul>
                          </div>

                          <div className="rounded-xl border border-line bg-surface p-3 text-xs">
                            <p className="font-semibold text-ink">
                              Unmentioned Keywords (Not Proof of Missing Skill)
                            </p>
                            <div className="mt-1.5 flex flex-wrap gap-1">
                              {prefEval.missing_relevant_keywords.length === 0 ? (
                                <span className="text-muted">None</span>
                              ) : (
                                prefEval.missing_relevant_keywords.map((kw) => (
                                  <span
                                    key={kw}
                                    className="rounded bg-amber-500/15 px-2 py-0.5 text-[11px] font-medium text-amber-700 dark:text-amber-300"
                                  >
                                    {kw}
                                  </span>
                                ))
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                          <div className="rounded-xl border border-line bg-surface p-3 text-xs">
                            <p className="font-semibold text-emerald-700 dark:text-emerald-300">
                              Strengths
                            </p>
                            <ul className="mt-1 list-disc space-y-1 pl-4 text-ink">
                              {prefEval.strengths.map((st, idx) => (
                                <li key={idx}>{st}</li>
                              ))}
                            </ul>
                          </div>

                          <div className="rounded-xl border border-line bg-surface p-3 text-xs">
                            <p className="font-semibold text-amber-700 dark:text-amber-300">
                              Weaknesses
                            </p>
                            <ul className="mt-1 list-disc space-y-1 pl-4 text-ink">
                              {prefEval.weaknesses.map((wk, idx) => (
                                <li key={idx}>{wk}</li>
                              ))}
                            </ul>
                          </div>

                          <div className="rounded-xl border border-line bg-surface p-3 text-xs">
                            <p className="font-semibold text-accent">
                              Improvement Opportunities
                            </p>
                            <ul className="mt-1 list-disc space-y-1 pl-4 text-ink">
                              {prefEval.improvement_opportunities.map(
                                (op, idx) => (
                                  <li key={idx}>{op}</li>
                                ),
                              )}
                            </ul>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* ============================================================ */}
              {/* TAB 3: IMPROVEMENT SUGGESTIONS                               */}
              {/* ============================================================ */}
              {activeTab === 'suggestions' && (
                <div className="space-y-4">
                  {suggestions.length === 0 ? (
                    <div className="rounded-2xl border border-line bg-surface-2 p-8 text-center text-xs text-muted">
                      No suggestions generated yet. Click “Analyse Resume” to
                      generate section-by-section improvement recommendations.
                    </div>
                  ) : (
                    suggestions.map((sug) => {
                      const isEditingThis = editingSuggestionId === sug.id;
                      const isRegeneratingThis =
                        regeneratingSuggestionId === sug.id;

                      return (
                        <div
                          key={sug.id}
                          className="space-y-3 rounded-2xl border border-line bg-surface-2 p-4"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="text-sm font-semibold text-ink">
                                {sug.section_name}
                              </span>
                              <span
                                className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                                  PRIORITY_STYLES[sug.priority] ??
                                  PRIORITY_STYLES.Medium
                                }`}
                              >
                                {sug.priority} Priority
                              </span>
                              <span
                                className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                                  sug.status === 'Accepted'
                                    ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                                    : sug.status === 'Rejected'
                                      ? 'bg-rose-500/15 text-rose-600 dark:text-rose-300'
                                      : 'bg-surface text-muted'
                                }`}
                              >
                                {sug.status}
                              </span>
                            </div>

                            <div className="flex flex-wrap items-center gap-1.5">
                              <button
                                type="button"
                                onClick={() =>
                                  void handleSuggestionAction(sug.id, 'Accepted')
                                }
                                className="inline-flex items-center gap-1 rounded-lg bg-emerald-500/15 px-2.5 py-1 text-xs font-semibold text-emerald-700 transition hover:bg-emerald-500/25 dark:text-emerald-300"
                              >
                                <Check className="h-3.5 w-3.5" />
                                Accept
                              </button>

                              <button
                                type="button"
                                onClick={() =>
                                  void handleSuggestionAction(sug.id, 'Rejected')
                                }
                                className="inline-flex items-center gap-1 rounded-lg bg-rose-500/15 px-2.5 py-1 text-xs font-semibold text-rose-600 transition hover:bg-rose-500/25 dark:text-rose-300"
                              >
                                <X className="h-3.5 w-3.5" />
                                Reject
                              </button>

                              <button
                                type="button"
                                onClick={() => {
                                  setEditingSuggestionId(sug.id);
                                  setEditingSuggestionText(sug.effective_content);
                                }}
                                className="inline-flex items-center gap-1 rounded-lg border border-line bg-surface px-2.5 py-1 text-xs font-medium text-ink hover:border-subtle/60"
                              >
                                <Pencil className="h-3 w-3" />
                                Edit
                              </button>

                              <button
                                type="button"
                                disabled={isRegeneratingThis}
                                onClick={() =>
                                  void handleRegenerateSuggestion(sug.id)
                                }
                                className="inline-flex items-center gap-1 rounded-lg border border-line bg-surface px-2.5 py-1 text-xs font-medium text-ink hover:border-subtle/60 disabled:opacity-60"
                              >
                                <RefreshCw
                                  className={`h-3 w-3 ${
                                    isRegeneratingThis ? 'animate-spin' : ''
                                  }`}
                                />
                                Regenerate
                              </button>
                            </div>
                          </div>

                          {/* Side-by-Side Comparison: Original Content | AI Suggested Content */}
                          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                            <div className="rounded-xl border border-line bg-surface p-3 text-xs">
                              <p className="text-[11px] font-semibold uppercase tracking-wider text-subtle">
                                Original Content
                              </p>
                              <p className="mt-1.5 whitespace-pre-wrap text-muted">
                                {sug.current_content ||
                                  'No existing section text extracted.'}
                              </p>
                            </div>

                            <div className="rounded-xl border border-accent/30 bg-accent-soft/40 p-3 text-xs">
                              <p className="text-[11px] font-semibold uppercase tracking-wider text-accent-ink">
                                AI Suggested Content
                                {sug.user_edited_content ? ' (User Edited)' : ''}
                              </p>
                              {isEditingThis ? (
                                <div className="mt-2 space-y-2">
                                  <textarea
                                    rows={3}
                                    value={editingSuggestionText}
                                    onChange={(e) =>
                                      setEditingSuggestionText(e.target.value)
                                    }
                                    className="w-full rounded-xl border border-line bg-surface p-2 text-xs text-ink focus:border-accent focus:outline-none"
                                  />
                                  <div className="flex justify-end gap-2">
                                    <button
                                      type="button"
                                      onClick={() => setEditingSuggestionId(null)}
                                      className="rounded-lg border border-line bg-surface px-2.5 py-1 text-xs text-muted"
                                    >
                                      Cancel
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() =>
                                        void handleSuggestionAction(
                                          sug.id,
                                          'Accepted',
                                          editingSuggestionText,
                                        )
                                      }
                                      className="rounded-lg bg-accent px-3 py-1 text-xs font-semibold text-white"
                                    >
                                      Save & Accept
                                    </button>
                                  </div>
                                </div>
                              ) : (
                                <p className="mt-1.5 whitespace-pre-wrap text-ink">
                                  {sug.effective_content}
                                </p>
                              )}
                            </div>
                          </div>

                          <p className="text-xs text-muted">
                            <strong className="font-semibold text-ink">
                              Why:
                            </strong>{' '}
                            {sug.reason}
                          </p>

                          {sug.clarifying_question && (
                            <p className="rounded-xl border border-sky-500/30 bg-sky-500/10 px-3 py-2 text-xs text-sky-700 dark:text-sky-300">
                              <strong className="font-semibold">
                                Clarifying Question:
                              </strong>{' '}
                              {sug.clarifying_question}
                            </p>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
              )}

              {/* ============================================================ */}
              {/* TAB 4: SIDE-BY-SIDE COMPARISON, VERSION HISTORY & APPROVAL   */}
              {/* ============================================================ */}
              {activeTab === 'versions' && (
                <div className="space-y-5">
                  {/* Version History Selector Strip */}
                  <div className="rounded-2xl border border-line bg-surface-2 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-subtle">
                          Resume Version History (Original Preserved)
                        </h3>
                        <p className="mt-0.5 text-xs text-muted">
                          Select any version to compare against the original
                          uploaded resume, edit a custom version, or approve a
                          final version.
                        </p>
                      </div>

                      {selectedVersion && !isEditingVersionText && (
                        <button
                          type="button"
                          onClick={() =>
                            handleStartUserEditVersion(selectedVersion)
                          }
                          className="inline-flex items-center gap-1.5 rounded-xl border border-line bg-surface px-3 py-1.5 text-xs font-semibold text-ink transition hover:border-subtle/60"
                        >
                          <Pencil className="h-3.5 w-3.5 text-accent" />
                          Create User-Edited Version
                        </button>
                      )}
                    </div>

                    <div className="mt-3 grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
                      {versions.map((ver) => {
                        const isSelected = selectedVersion?.id === ver.id;
                        const isApproved = ver.approval_status === 'Approved';
                        return (
                          <button
                            key={ver.id}
                            type="button"
                            onClick={() => {
                              setSelectedVersionId(ver.id);
                              setIsEditingVersionText(false);
                            }}
                            className={`flex flex-col justify-between rounded-xl border p-3 text-left text-xs transition-colors ${
                              isSelected
                                ? 'border-accent bg-accent-soft/60'
                                : 'border-line bg-surface hover:border-subtle/50'
                            }`}
                          >
                            <div>
                              <div className="flex items-center justify-between gap-2">
                                <span className="font-semibold text-ink">
                                  v{ver.version_number} · {ver.version_type}
                                </span>
                                <span
                                  className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                                    isApproved
                                      ? 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300'
                                      : 'bg-surface-2 text-muted'
                                  }`}
                                >
                                  {ver.approval_status}
                                </span>
                              </div>
                              <p className="mt-1 truncate text-[11px] text-muted">
                                {ver.title}
                              </p>
                            </div>
                            <p className="mt-2 text-[10px] text-subtle">
                              Created {formatUploadDate(ver.created_at)} · ID:{' '}
                              {ver.id.slice(0, 8)}
                            </p>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* User-Edited Version Editor (if active) */}
                  {isEditingVersionText && (
                    <div className="space-y-3 rounded-2xl border border-accent/40 bg-surface-2 p-4">
                      <h3 className="text-sm font-semibold text-ink">
                        Create New User-Edited Version (Original Resume Preserved)
                      </h3>
                      <div>
                        <label
                          htmlFor="custom-version-title"
                          className="block text-xs font-medium text-ink"
                        >
                          Version Title
                        </label>
                        <input
                          id="custom-version-title"
                          type="text"
                          value={customVersionTitle}
                          onChange={(e) => setCustomVersionTitle(e.target.value)}
                          className="mt-1 w-full rounded-xl border border-line bg-surface px-3 py-2 text-xs text-ink focus:border-accent focus:outline-none"
                        />
                      </div>
                      <div>
                        <label
                          htmlFor="custom-version-content"
                          className="block text-xs font-medium text-ink"
                        >
                          Resume Content
                        </label>
                        <textarea
                          id="custom-version-content"
                          rows={10}
                          value={customVersionContent}
                          onChange={(e) =>
                            setCustomVersionContent(e.target.value)
                          }
                          className="mt-1 w-full rounded-xl border border-line bg-surface p-3 font-sans text-xs leading-relaxed text-ink focus:border-accent focus:outline-none"
                        />
                      </div>
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => setIsEditingVersionText(false)}
                          className="rounded-xl border border-line bg-surface px-3.5 py-2 text-xs font-medium text-muted"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          disabled={isSavingVersion}
                          onClick={() => void handleSaveUserVersion()}
                          className="rounded-xl bg-accent px-4 py-2 text-xs font-semibold text-white shadow-card disabled:opacity-60"
                        >
                          {isSavingVersion
                            ? 'Saving Version…'
                            : 'Save User-Edited Version'}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Section-Level Side-by-Side Comparison (if selected version has section_changes) */}
                  {selectedVersion &&
                    selectedVersion.section_changes &&
                    selectedVersion.section_changes.length > 0 && (
                      <div className="space-y-3 rounded-2xl border border-line bg-surface-2 p-4">
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-subtle">
                          Section-by-Section Comparison (Original Content vs AI
                          Suggested Content)
                        </h3>
                        {selectedVersion.section_changes.map((change, idx) => (
                          <div
                            key={idx}
                            className="grid grid-cols-1 gap-3 rounded-xl border border-line bg-surface p-3 md:grid-cols-2"
                          >
                            <div>
                              <p className="text-[11px] font-semibold text-subtle">
                                {change.section_name} — Original Content
                              </p>
                              <p className="mt-1 whitespace-pre-wrap text-xs text-muted">
                                {change.original_content}
                              </p>
                            </div>
                            <div>
                              <p className="text-[11px] font-semibold text-accent">
                                {change.section_name} — AI Suggested Content
                              </p>
                              <p className="mt-1 whitespace-pre-wrap text-xs text-ink">
                                {change.suggested_content}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                  {/* Full Resume Side-by-Side Comparison */}
                  {originalVersion && selectedVersion && (
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                      <div className="rounded-2xl border border-line bg-surface-2 p-4">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-ink">
                            Original Content (v1 — Immutable)
                          </span>
                          <span className="text-[11px] text-muted">
                            {originalVersion.content.length.toLocaleString()} chars
                          </span>
                        </div>
                        <pre className="mt-2.5 max-h-72 overflow-y-auto whitespace-pre-wrap rounded-xl border border-line bg-surface p-3.5 font-sans text-xs leading-relaxed text-muted">
                          {originalVersion.content}
                        </pre>
                      </div>

                      <div className="rounded-2xl border border-accent/35 bg-surface-2 p-4">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-accent-ink">
                            Selected Version: {selectedVersion.title}
                          </span>
                          <span className="text-[11px] text-muted">
                            {selectedVersion.content.length.toLocaleString()} chars
                          </span>
                        </div>
                        <pre className="mt-2.5 max-h-72 overflow-y-auto whitespace-pre-wrap rounded-xl border border-line bg-surface p-3.5 font-sans text-xs leading-relaxed text-ink">
                          {selectedVersion.content}
                        </pre>
                      </div>
                    </div>
                  )}

                  {/* Approval System Panel */}
                  {selectedVersion && (
                    <div className="rounded-2xl border border-emerald-500/35 bg-emerald-500/10 p-5">
                      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <ShieldCheck className="h-5 w-5 text-emerald-600 dark:text-emerald-300" />
                            <h3 className="text-sm font-semibold text-ink">
                              Approve Resume Version for Job Preferences
                            </h3>
                          </div>
                          <p className="text-xs text-muted">
                            Only you can approve a final resume version. A job
                            preference will not become eligible for automated job
                            applications until its resume has been approved.
                          </p>
                        </div>

                        <button
                          type="button"
                          disabled={isApproving}
                          onClick={() =>
                            void handleApproveSelectedVersion(selectedVersion)
                          }
                          className="inline-flex shrink-0 items-center justify-center gap-1.5 rounded-xl bg-emerald-600 px-4 py-2.5 text-xs font-semibold text-white shadow-card transition hover:bg-emerald-500 disabled:opacity-60"
                        >
                          {isApproving ? (
                            <>
                              <Loader2 className="h-4 w-4 animate-spin" />
                              Approving…
                            </>
                          ) : (
                            <>
                              <ShieldCheck className="h-4 w-4" />
                              {selectedVersion.approval_status === 'Approved'
                                ? `Re-confirm Approval (v${selectedVersion.version_number})`
                                : `Approve Version v${selectedVersion.version_number}`}
                            </>
                          )}
                        </button>
                      </div>

                      {/* Preference Checkboxes for Approval Linking */}
                      {preferences.length > 0 && (
                        <div className="mt-3.5 border-t border-emerald-500/20 pt-3">
                          <p className="text-xs font-medium text-ink">
                            Link Approved Version to Job Preferences:
                          </p>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {preferences.map((pref) => {
                              const checked = approvalPreferenceIds.includes(
                                pref.id,
                              );
                              return (
                                <button
                                  key={pref.id}
                                  type="button"
                                  onClick={() =>
                                    toggleApprovalPreference(pref.id)
                                  }
                                  className={`inline-flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-medium transition-colors ${
                                    checked
                                      ? 'border-emerald-500 bg-emerald-500/20 text-ink'
                                      : 'border-line bg-surface text-muted'
                                  }`}
                                >
                                  <span
                                    className={`flex h-3.5 w-3.5 items-center justify-center rounded border ${
                                      checked
                                        ? 'border-emerald-600 bg-emerald-600 text-white'
                                        : 'border-line bg-surface-2'
                                    }`}
                                  >
                                    {checked && (
                                      <Check className="h-2.5 w-2.5" strokeWidth={3} />
                                    )}
                                  </span>
                                  <span>{pref.preference_name}</span>
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between border-t border-line px-6 py-3.5 text-xs text-muted">
          <span>
            Original uploaded file ({resume.original_filename}) is permanently
            preserved.
          </span>
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-line bg-surface-2 px-4 py-1.5 text-xs font-semibold text-ink hover:border-subtle/60"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
