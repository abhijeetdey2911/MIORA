import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Eye,
  FileCheck,
  RotateCcw,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react';
import {
  approveApplication,
  listApplications,
  reconcileApplication,
  submitApplication,
  updateApplicationStatus,
} from '../services/multiAgentService';
import { getPreferences } from '../services/preferenceService';
import type {
  ApplicationItem,
  ApplicationLifecycleStatus,
} from '../types/multiAgent';
import type { JobPreference } from '../types/preference';
import { JobsDiscoveryPage } from './JobsDiscoveryPage';

const ALL_STATUSES: readonly ApplicationLifecycleStatus[] = [
  'Prepared',
  'Awaiting Approval',
  'Approved',
  'Submission In Progress',
  'Submitted',
  'Submission Unconfirmed',
  'Failed',
  'Under Review',
  'Recruiter Response',
  'Interview',
  'Rejected',
  'Offer',
  'Withdrawn',
  'No Response',
];

function getStatusBadgeClass(status: string): string {
  switch (status) {
    case 'Submitted':
      return 'bg-emerald-500/10 text-emerald-600 dark:bg-emerald-400/15 dark:text-emerald-300';
    case 'Approved':
      return 'bg-blue-500/10 text-blue-600 dark:bg-blue-400/15 dark:text-blue-300';
    case 'Submission In Progress':
      return 'bg-indigo-500/15 text-indigo-600 dark:bg-indigo-400/20 dark:text-indigo-300 animate-pulse';
    case 'Under Review':
      return 'bg-sky-500/10 text-sky-600 dark:bg-sky-400/15 dark:text-sky-300';
    case 'Interview':
    case 'Offer':
    case 'Recruiter Response':
      return 'bg-teal-500/10 text-teal-600 dark:bg-teal-400/15 dark:text-teal-300';
    case 'Submission Unconfirmed':
      return 'bg-amber-500/10 text-amber-600 dark:bg-amber-400/15 dark:text-amber-300';
    case 'Awaiting Approval':
      return 'bg-purple-500/10 text-purple-600 dark:bg-purple-400/15 dark:text-purple-300';
    case 'Prepared':
      return 'bg-slate-500/10 text-slate-600 dark:bg-slate-400/15 dark:text-slate-300';
    case 'Failed':
    case 'Rejected':
    case 'Withdrawn':
      return 'bg-rose-500/10 text-rose-600 dark:bg-rose-400/15 dark:text-rose-300';
    default:
      return 'bg-surface-2 text-muted';
  }
}

export function ApplicationsPage() {
  const [searchParams] = useSearchParams();
  const initialPrefId = searchParams.get('preference_id') || '';

  const [activeTab, setActiveTab] = useState<'applications' | 'discovery'>(
    'applications',
  );
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [preferences, setPreferences] = useState<JobPreference[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [selectedPreferenceId, setSelectedPreferenceId] =
    useState<string>(initialPrefId);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const [selectedApp, setSelectedApp] = useState<ApplicationItem | null>(null);

  // Approval Modal State
  const [approvingApp, setApprovingApp] = useState<ApplicationItem | null>(
    null,
  );
  const [approvalNotes, setApprovalNotes] = useState<string>('');

  // Submit Modal State (for Approved or Failed applications)
  const [submittingApp, setSubmittingApp] = useState<ApplicationItem | null>(
    null,
  );
  const [submitEvidence, setSubmitEvidence] = useState<string>('');
  const [submitNotes, setSubmitNotes] = useState<string>('');
  const [simulateUncertainToggle, setSimulateUncertainToggle] =
    useState<boolean>(false);
  const [isSubmittingAction, setIsSubmittingAction] = useState<boolean>(false);

  // Reconcile Modal State
  const [reconcilingApp, setReconcilingApp] =
    useState<ApplicationItem | null>(null);
  const [reconcileResolution, setReconcileResolution] = useState<
    'Submitted' | 'Approved' | 'Awaiting Approval' | 'Withdrawn'
  >('Approved');
  const [reconcileEvidence, setReconcileEvidence] = useState<string>('');

  // Tracking Status Update Modal State
  const [updatingStatusApp, setUpdatingStatusApp] =
    useState<ApplicationItem | null>(null);
  const [nextStatus, setNextStatus] =
    useState<ApplicationLifecycleStatus>('Under Review');
  const [statusNotes, setStatusNotes] = useState<string>('');
  const [statusEvidence, setStatusEvidence] = useState<string>('');
  const [recruiterResponseText, setRecruiterResponseText] =
    useState<string>('');
  const [interviewDateStr, setInterviewDateStr] = useState<string>('');

  const loadData = useCallback(async () => {
    try {
      const [appRows, prefRows] = await Promise.all([
        listApplications({
          preference_id: selectedPreferenceId || undefined,
          status: statusFilter || undefined,
          search: searchQuery || undefined,
        }),
        getPreferences(),
      ]);
      setApplications(appRows);
      setPreferences(prefRows);
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to load applications.',
      );
    } finally {
      setLoading(false);
    }
  }, [selectedPreferenceId, statusFilter, searchQuery]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      listApplications({
        preference_id: selectedPreferenceId || undefined,
        status: statusFilter || undefined,
        search: searchQuery || undefined,
      }),
      getPreferences(),
    ])
      .then(([appRows, prefRows]) => {
        if (!cancelled) {
          setApplications(appRows);
          setPreferences(prefRows);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setErrorMessage(
            err instanceof Error
              ? err.message
              : 'Failed to load applications.',
          );
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedPreferenceId, statusFilter, searchQuery]);

  const handleApproveSubmit = async () => {
    if (!approvingApp) return;
    setErrorMessage(null);
    try {
      await approveApplication(approvingApp.id, {
        approved_by_user: true,
        notes: approvalNotes.trim() || undefined,
      });
      setApprovingApp(null);
      setApprovalNotes('');
      await loadData();
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to approve application.',
      );
    }
  };

  const handleDirectSubmit = async () => {
    if (!submittingApp) return;
    setErrorMessage(null);
    setIsSubmittingAction(true);
    try {
      await submitApplication(submittingApp.id, {
        simulate_uncertain: simulateUncertainToggle,
        explicit_confirmation_evidence: submitEvidence.trim() || undefined,
        notes: submitNotes.trim() || undefined,
      });
      setSubmittingApp(null);
      setSubmitEvidence('');
      setSubmitNotes('');
      setSimulateUncertainToggle(false);
      await loadData();
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to submit application.',
      );
    } finally {
      setIsSubmittingAction(false);
    }
  };

  const handleReconcileSubmit = async () => {
    if (!reconcilingApp) return;
    setErrorMessage(null);
    try {
      await reconcileApplication(reconcilingApp.id, {
        resolution: reconcileResolution,
        confirmation_evidence: reconcileEvidence.trim() || undefined,
        notes: `Reconciled by user to ${reconcileResolution}.`,
      });
      setReconcilingApp(null);
      setReconcileEvidence('');
      await loadData();
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to reconcile application.',
      );
    }
  };

  const handleStatusUpdateSubmit = async () => {
    if (!updatingStatusApp) return;
    setErrorMessage(null);
    try {
      await updateApplicationStatus(updatingStatusApp.id, {
        status: nextStatus,
        notes: statusNotes.trim() || undefined,
        evidence: statusEvidence.trim() || undefined,
        recruiter_response_text: recruiterResponseText.trim() || undefined,
        interview_date: interviewDateStr
          ? new Date(interviewDateStr).toISOString()
          : undefined,
      });
      setUpdatingStatusApp(null);
      setStatusNotes('');
      setStatusEvidence('');
      setRecruiterResponseText('');
      setInterviewDateStr('');
      await loadData();
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : 'Failed to update application status.',
      );
    }
  };

  return (
    <div className="space-y-4">
      {/* Top View Switcher: Applications Tracker vs Job Discovery */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-line bg-surface p-3 shadow-card">
        <div className="inline-flex rounded-xl border border-line bg-surface-2 p-1">
          <button
            type="button"
            onClick={() => setActiveTab('applications')}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition ${
              activeTab === 'applications'
                ? 'bg-surface text-ink shadow-card'
                : 'text-muted hover:text-ink'
            }`}
          >
            <Send className="h-3.5 w-3.5 text-accent" />
            Applications Tracker ({applications.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('discovery')}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition ${
              activeTab === 'discovery'
                ? 'bg-surface text-ink shadow-card'
                : 'text-muted hover:text-ink'
            }`}
          >
            <Sparkles className="h-3.5 w-3.5 text-amber-500" />
            Job Discovery & Matching
          </button>
        </div>

        <p className="text-xs text-muted">
          Manual approval required · Strict confirmation evidence required for Submitted
        </p>
      </div>

      {activeTab === 'discovery' ? (
        <JobsDiscoveryPage />
      ) : (
        <>
          {/* Filters */}
          <section className="rounded-2xl border border-line bg-surface p-4 shadow-card">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-2.5 h-3.5 w-3.5 text-subtle" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search company, role, or route..."
                  className="w-full rounded-xl border border-line bg-surface-2 py-2 pl-8 pr-3 text-xs text-ink placeholder:text-subtle focus:border-accent focus:outline-none"
                />
              </div>

              <select
                value={selectedPreferenceId}
                onChange={(e) => setSelectedPreferenceId(e.target.value)}
                aria-label="Filter applications by preference"
                className="rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink focus:border-accent focus:outline-none"
              >
                <option value="">All Job Preferences</option>
                {preferences.map((pref) => (
                  <option key={pref.id} value={pref.id}>
                    {pref.preference_name}
                  </option>
                ))}
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                aria-label="Filter applications by status"
                className="rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink focus:border-accent focus:outline-none"
              >
                <option value="">All Lifecycle Statuses</option>
                {ALL_STATUSES.map((st) => (
                  <option key={st} value={st}>
                    {st}
                  </option>
                ))}
              </select>
            </div>
          </section>

          {errorMessage && (
            <div className="flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-600 dark:text-rose-300">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Applications Table */}
          <section className="overflow-hidden rounded-2xl border border-line bg-surface shadow-card">
            {loading ? (
              <div className="p-8 text-center text-xs text-muted">
                Loading applications...
              </div>
            ) : applications.length === 0 ? (
              <div className="p-8 text-center">
                <p className="text-sm font-semibold text-ink">
                  No applications recorded yet
                </p>
                <p className="mt-1 text-xs text-muted">
                  Run JobHunter to prepare applications for shortlisted jobs
                  using your approved resume versions.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-line bg-surface-2 text-[11px] font-semibold uppercase tracking-wider text-muted">
                    <tr>
                      <th className="px-4 py-3">Role & Company</th>
                      <th className="px-4 py-3">Preference</th>
                      <th className="px-4 py-3">Route</th>
                      <th className="px-4 py-3">Resume Used</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {applications.map((app) => (
                      <tr
                        key={app.id}
                        className="transition-colors hover:bg-surface-2/60"
                      >
                        <td className="px-4 py-3">
                          <p className="font-semibold text-ink">
                            {app.job_title}
                          </p>
                          <p className="text-[11px] text-muted">
                            {app.company}
                          </p>
                        </td>
                        <td className="px-4 py-3 text-muted">
                          {app.preference_name || 'Job Preference'}
                        </td>
                        <td className="px-4 py-3">
                          <span className="capitalize text-ink">
                            {app.route_type.replace(/_/g, ' ')}
                          </span>
                          <p className="max-w-[180px] truncate text-[11px] text-muted">
                            {app.route_target}
                          </p>
                        </td>
                        <td className="px-4 py-3">
                          <span className="inline-flex items-center gap-1 rounded-md border border-line bg-surface-2 px-2 py-0.5 text-[11px] text-ink">
                            <FileCheck className="h-3 w-3 text-emerald-500" />
                            {app.resume_version_title || 'Approved Resume'}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${getStatusBadgeClass(
                              app.status,
                            )}`}
                          >
                            {app.status}
                          </span>
                          {app.approval_reference && (
                            <p className="mt-0.5 text-[10px] text-muted" title="Internal approval authorization reference">
                              Approval: {app.approval_reference}
                            </p>
                          )}
                          {app.confirmation_evidence && (
                            <p className="mt-0.5 text-[10px] text-emerald-600 dark:text-emerald-400 font-medium" title="Verified external confirmation receipt">
                              Employer Ref: {app.confirmation_evidence}
                            </p>
                          )}
                          {app.error_message && app.status === 'Failed' && (
                            <p className="mt-0.5 max-w-[200px] truncate text-[10px] text-rose-500" title={app.error_message}>
                              Error: {app.error_message}
                            </p>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="inline-flex flex-wrap items-center justify-end gap-1.5">
                            {/* Step 1: User Approval */}
                            {(app.status === 'Awaiting Approval' ||
                              app.status === 'Prepared') && (
                              <button
                                type="button"
                                onClick={() => {
                                  setApprovingApp(app);
                                  setApprovalNotes('');
                                }}
                                className="inline-flex items-center gap-1 rounded-lg bg-accent px-2.5 py-1 text-[11px] font-semibold text-white hover:brightness-105"
                              >
                                <CheckCircle2 className="h-3 w-3" />
                                Approve
                              </button>
                            )}

                            {/* Step 2: External Submission for Approved application */}
                            {app.status === 'Approved' && (
                              <button
                                type="button"
                                onClick={() => {
                                  setSubmittingApp(app);
                                  setSubmitEvidence('');
                                  setSubmitNotes('');
                                  setSimulateUncertainToggle(false);
                                }}
                                className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-2.5 py-1 text-[11px] font-semibold text-white shadow-sm hover:bg-emerald-500"
                              >
                                <Send className="h-3 w-3" />
                                Submit to Employer
                              </button>
                            )}

                            {/* Retry for Failed application */}
                            {app.status === 'Failed' && (
                              <button
                                type="button"
                                onClick={() => {
                                  setSubmittingApp(app);
                                  setSubmitEvidence('');
                                  setSubmitNotes('');
                                  setSimulateUncertainToggle(false);
                                }}
                                className="inline-flex items-center gap-1 rounded-lg border border-rose-500/40 bg-rose-500/10 px-2.5 py-1 text-[11px] font-semibold text-rose-600 dark:text-rose-300"
                              >
                                <RotateCcw className="h-3 w-3" />
                                Retry Submit
                              </button>
                            )}

                            {/* Reconcile for Submission Unconfirmed */}
                            {app.status === 'Submission Unconfirmed' && (
                              <button
                                type="button"
                                onClick={() => {
                                  setReconcilingApp(app);
                                  setReconcileResolution('Approved');
                                  setReconcileEvidence('');
                                }}
                                className="inline-flex items-center gap-1 rounded-lg border border-amber-500/40 bg-amber-500/10 px-2.5 py-1 text-[11px] font-semibold text-amber-600 dark:text-amber-300"
                              >
                                Reconcile
                              </button>
                            )}

                            <button
                              type="button"
                              onClick={() => {
                                setUpdatingStatusApp(app);
                                setNextStatus(app.status);
                                setStatusNotes(app.notes || '');
                                setStatusEvidence(
                                  app.confirmation_evidence || '',
                                );
                                setRecruiterResponseText(
                                  app.recruiter_response_text || '',
                                );
                              }}
                              className="rounded-lg border border-line bg-surface-2 px-2.5 py-1 text-[11px] font-medium text-ink hover:border-subtle/50"
                            >
                              Update Status
                            </button>

                            <button
                              type="button"
                              onClick={() => setSelectedApp(app)}
                              className="inline-flex items-center gap-1 rounded-lg border border-line bg-surface-2 px-2 py-1 text-[11px] text-muted hover:text-ink"
                              title="View application details & audit history"
                            >
                              <Eye className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}

      {/* 1. Approve Prepared Application Modal (Transitions to 'Approved') */}
      {approvingApp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            onClick={() => setApprovingApp(null)}
            className="fixed inset-0 bg-black/50 backdrop-blur-[2px]"
          />
          <div className="relative z-10 w-full max-w-md rounded-2xl border border-line bg-surface p-5 shadow-card">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-sm font-semibold text-ink">
                  Approve Application for Submission
                </h3>
                <p className="mt-0.5 text-xs text-muted">
                  {approvingApp.job_title} at {approvingApp.company}
                </p>
              </div>
              <ShieldCheck className="h-5 w-5 text-accent shrink-0" />
            </div>

            <div className="mt-3 space-y-3 text-xs">
              <div className="rounded-xl border border-blue-500/20 bg-blue-500/10 p-3 text-[11px] text-blue-700 dark:text-blue-300">
                Approving confirms this job and resume for application submission.
                It transitions status to <strong className="font-semibold">&quot;Approved&quot;</strong> and generates an internal approval audit reference.
                It does not prematurely mark the application as submitted.
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted">
                  Approval Notes (Optional)
                </label>
                <textarea
                  rows={2}
                  value={approvalNotes}
                  onChange={(e) => setApprovalNotes(e.target.value)}
                  placeholder="e.g. Reviewed and approved for submission"
                  className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                />
              </div>
            </div>

            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setApprovingApp(null)}
                className="rounded-xl border border-line px-3 py-1.5 text-xs text-muted"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleApproveSubmit}
                className="rounded-xl bg-accent px-4 py-1.5 text-xs font-semibold text-white"
              >
                Confirm User Approval
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 2. Submit to Employer Modal (Initiates 'Submission In Progress') */}
      {submittingApp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            onClick={() => !isSubmittingAction && setSubmittingApp(null)}
            className="fixed inset-0 bg-black/50 backdrop-blur-[2px]"
          />
          <div className="relative z-10 w-full max-w-md rounded-2xl border border-line bg-surface p-5 shadow-card">
            <h3 className="text-sm font-semibold text-ink">
              Submit Application to Employer (Agent 4)
            </h3>
            <p className="mt-0.5 text-xs text-muted">
              {submittingApp.job_title} at {submittingApp.company}
            </p>

            <div className="mt-3 space-y-3 text-xs">
              <div className="rounded-xl border border-line bg-surface-2 p-3 text-xs space-y-1">
                <p><span className="text-muted">Route Target:</span> <span className="font-medium text-ink">{submittingApp.route_target}</span></p>
                <p><span className="text-muted">Route Type:</span> <span className="capitalize font-medium text-ink">{submittingApp.route_type.replace(/_/g, ' ')}</span></p>
                <p><span className="text-muted">Approval Reference:</span> <span className="font-mono text-ink text-[11px]">{submittingApp.approval_reference || 'Explicitly Approved'}</span></p>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted">
                  External Confirmation Receipt (Optional — from employer or portal)
                </label>
                <input
                  type="text"
                  value={submitEvidence}
                  onChange={(e) => setSubmitEvidence(e.target.value)}
                  placeholder="e.g. PORTAL-CONFIRM-9941 or ATS-APP-2024"
                  className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted">
                  Submission Notes
                </label>
                <textarea
                  rows={2}
                  value={submitNotes}
                  onChange={(e) => setSubmitNotes(e.target.value)}
                  placeholder="Optional submission notes or dispatch details"
                  className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                />
              </div>

              <label className="flex items-center gap-2 text-muted">
                <input
                  type="checkbox"
                  checked={simulateUncertainToggle}
                  onChange={(e) => setSimulateUncertainToggle(e.target.checked)}
                />
                <span>Simulate unconfirmed outcome (sets status to &quot;Submission Unconfirmed&quot;)</span>
              </label>
            </div>

            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                disabled={isSubmittingAction}
                onClick={() => setSubmittingApp(null)}
                className="rounded-xl border border-line px-3 py-1.5 text-xs text-muted"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isSubmittingAction}
                onClick={handleDirectSubmit}
                className="rounded-xl bg-emerald-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
              >
                {isSubmittingAction ? 'Submitting...' : 'Execute Submission'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 3. Reconcile Submission Unconfirmed Modal */}
      {reconcilingApp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            onClick={() => setReconcilingApp(null)}
            className="fixed inset-0 bg-black/50 backdrop-blur-[2px]"
          />
          <div className="relative z-10 w-full max-w-md rounded-2xl border border-line bg-surface p-5 shadow-card">
            <h3 className="text-sm font-semibold text-ink">
              Reconcile &quot;Submission Unconfirmed&quot;
            </h3>
            <p className="mt-1 text-xs text-muted">
              Retries are locked until you verify whether the previous
              submission succeeded.
            </p>

            <div className="mt-3 space-y-3 text-xs">
              <div>
                <label className="block text-[11px] font-medium text-muted">
                  Resolution
                </label>
                <select
                  value={reconcileResolution}
                  onChange={(e) =>
                    setReconcileResolution(
                      e.target.value as
                        | 'Submitted'
                        | 'Approved'
                        | 'Awaiting Approval'
                        | 'Withdrawn',
                    )
                  }
                  className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                >
                  <option value="Approved">
                    Return to Approved (Ready for clean re-submission)
                  </option>
                  <option value="Awaiting Approval">
                    Return to Awaiting Approval (Requires user re-review)
                  </option>
                  <option value="Submitted">
                    Confirmed Submitted (Requires Genuine Employer Receipt Evidence)
                  </option>
                  <option value="Withdrawn">Withdraw Application</option>
                </select>
              </div>

              {reconcileResolution === 'Submitted' && (
                <div>
                  <label className="block text-[11px] font-medium text-muted">
                    External Employer Confirmation Receipt (Required)
                  </label>
                  <input
                    type="text"
                    value={reconcileEvidence}
                    onChange={(e) => setReconcileEvidence(e.target.value)}
                    placeholder="e.g. Employer email confirmation receipt or ATS portal token"
                    className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                  />
                  <p className="mt-1 text-[10px] text-muted">
                    Internal user approval tokens cannot be used as external confirmation evidence.
                  </p>
                </div>
              )}
            </div>

            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setReconcilingApp(null)}
                className="rounded-xl border border-line px-3 py-1.5 text-xs text-muted"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleReconcileSubmit}
                className="rounded-xl bg-accent px-4 py-1.5 text-xs font-semibold text-white"
              >
                Save Reconciliation
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 4. Update Status Modal (Agent 5 Tracking) */}
      {updatingStatusApp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            onClick={() => setUpdatingStatusApp(null)}
            className="fixed inset-0 bg-black/50 backdrop-blur-[2px]"
          />
          <div className="relative z-10 w-full max-w-md rounded-2xl border border-line bg-surface p-5 shadow-card">
            <h3 className="text-sm font-semibold text-ink">
              Update Application Tracking (Agent 5)
            </h3>
            <p className="mt-1 text-xs text-muted">
              {updatingStatusApp.job_title} at {updatingStatusApp.company}
            </p>

            <div className="mt-3 space-y-3 text-xs">
              <div>
                <label className="block text-[11px] font-medium text-muted">
                  Lifecycle Status
                </label>
                <select
                  value={nextStatus}
                  onChange={(e) =>
                    setNextStatus(e.target.value as ApplicationLifecycleStatus)
                  }
                  className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                >
                  {ALL_STATUSES.map((st) => (
                    <option key={st} value={st}>
                      {st}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted">
                  External Confirmation Evidence (Required if marking Submitted)
                </label>
                <input
                  type="text"
                  value={statusEvidence}
                  onChange={(e) => setStatusEvidence(e.target.value)}
                  placeholder="Genuine employer confirmation receipt or portal token"
                  className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted">
                  Interview Date (Optional)
                </label>
                <input
                  type="datetime-local"
                  value={interviewDateStr}
                  onChange={(e) => setInterviewDateStr(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted">
                  Recruiter Response Text (Optional)
                </label>
                <textarea
                  rows={2}
                  value={recruiterResponseText}
                  onChange={(e) => setRecruiterResponseText(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted">
                  Tracking Notes
                </label>
                <textarea
                  rows={2}
                  value={statusNotes}
                  onChange={(e) => setStatusNotes(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                />
              </div>
            </div>

            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setUpdatingStatusApp(null)}
                className="rounded-xl border border-line px-3 py-1.5 text-xs text-muted"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleStatusUpdateSubmit}
                className="rounded-xl bg-accent px-4 py-1.5 text-xs font-semibold text-white"
              >
                Save Status
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 5. View Application Details & Status Audit History Modal */}
      {selectedApp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            onClick={() => setSelectedApp(null)}
            className="fixed inset-0 bg-black/50 backdrop-blur-[2px]"
          />
          <div className="relative z-10 max-h-[88vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-line bg-surface p-6 shadow-card">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-semibold text-ink">
                  {selectedApp.job_title} · {selectedApp.company}
                </h3>
                <p className="mt-0.5 text-xs text-muted">
                  Preference: {selectedApp.preference_name} · Resume Used:{' '}
                  {selectedApp.resume_version_title || 'Approved Resume'}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedApp(null)}
                className="rounded-xl p-1 text-muted hover:bg-surface-2 hover:text-ink"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Section 1: User Approval Audit */}
            <div className="mt-4 rounded-xl border border-blue-500/20 bg-blue-500/5 p-3.5 text-xs">
              <div className="flex items-center gap-1.5 font-semibold text-blue-600 dark:text-blue-400">
                <ShieldCheck className="h-4 w-4" />
                <span>1. User Manual Approval Audit</span>
              </div>
              <div className="mt-2.5 grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                <div>
                  <span className="text-muted block text-[11px]">Approved By User:</span>
                  <span className="font-semibold text-ink">
                    {selectedApp.approved_by_user ? 'Yes (Authorized)' : 'Pending User Approval'}
                  </span>
                </div>
                <div>
                  <span className="text-muted block text-[11px]">Approved At:</span>
                  <span className="font-medium text-ink">
                    {selectedApp.approved_at
                      ? new Date(selectedApp.approved_at).toLocaleString()
                      : 'Not approved'}
                  </span>
                </div>
                <div>
                  <span className="text-muted block text-[11px]">Internal Approval Reference:</span>
                  <span className="font-mono text-ink text-[11px]">
                    {selectedApp.approval_reference || 'None'}
                  </span>
                </div>
              </div>
            </div>

            {/* Section 2: External Submission & Employer Confirmation */}
            <div className="mt-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3.5 text-xs">
              <div className="flex items-center gap-1.5 font-semibold text-emerald-600 dark:text-emerald-400">
                <Send className="h-4 w-4" />
                <span>2. External Employer Submission & Confirmation</span>
              </div>
              <div className="mt-2.5 grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                <div>
                  <span className="text-muted block text-[11px]">Current Status:</span>
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${getStatusBadgeClass(selectedApp.status)}`}>
                    {selectedApp.status}
                  </span>
                </div>
                <div>
                  <span className="text-muted block text-[11px]">Submission Attempted:</span>
                  <span className="font-medium text-ink">
                    {selectedApp.submission_attempted_at
                      ? new Date(selectedApp.submission_attempted_at).toLocaleString()
                      : 'Not attempted'}
                  </span>
                </div>
                <div>
                  <span className="text-muted block text-[11px]">Confirmed Applied At:</span>
                  <span className="font-medium text-ink">
                    {selectedApp.applied_at
                      ? new Date(selectedApp.applied_at).toLocaleString()
                      : 'Not confirmed'}
                  </span>
                </div>
                <div>
                  <span className="text-muted block text-[11px]">External Confirmation Evidence:</span>
                  <span className="font-mono text-emerald-600 dark:text-emerald-400 font-medium">
                    {selectedApp.confirmation_evidence || 'None'}
                  </span>
                </div>
                <div>
                  <span className="text-muted block text-[11px]">External Application ID:</span>
                  <span className="font-mono text-ink">
                    {selectedApp.external_application_id || 'Not returned'}
                  </span>
                </div>
                <div>
                  <span className="text-muted block text-[11px]">Submission Outcome:</span>
                  <span className="font-medium text-ink capitalize">
                    {selectedApp.submission_result || 'N/A'}
                  </span>
                </div>
              </div>
              {selectedApp.error_message && (
                <div className="mt-2 rounded-lg border border-rose-500/30 bg-rose-500/10 p-2 text-rose-600 dark:text-rose-300">
                  <span className="font-semibold">Error Message:</span> {selectedApp.error_message}
                </div>
              )}
            </div>

            {/* Section 3: Route & Follow-Up Reminders */}
            <div className="mt-3 grid grid-cols-2 gap-3 rounded-xl border border-line bg-surface-2 p-3 text-xs">
              <div>
                <span className="text-muted">Route Type:</span>{' '}
                <span className="font-medium capitalize text-ink">
                  {selectedApp.route_type.replace(/_/g, ' ')}
                </span>
              </div>
              <div>
                <span className="text-muted">Route Target:</span>{' '}
                <span className="font-medium text-ink truncate block">
                  {selectedApp.route_target}
                </span>
              </div>
              <div>
                <span className="text-muted">Follow-Up Reminder:</span>{' '}
                <span className="font-medium text-ink">
                  {selectedApp.follow_up_reminder_at
                    ? new Date(selectedApp.follow_up_reminder_at).toLocaleDateString()
                    : 'Not scheduled'}
                </span>
              </div>
              <div>
                <span className="text-muted">Interview Date:</span>{' '}
                <span className="font-medium text-ink">
                  {selectedApp.interview_date
                    ? new Date(selectedApp.interview_date).toLocaleString()
                    : 'None'}
                </span>
              </div>
            </div>

            {/* Section 4: Status History Audit Trail */}
            <div className="mt-4">
              <p className="text-xs font-semibold text-ink">
                Status History Audit Trail ({selectedApp.status_history.length})
              </p>
              <ul className="mt-2 divide-y divide-line rounded-xl border border-line bg-surface-2 px-3">
                {selectedApp.status_history.map((h) => (
                  <li key={h.id} className="py-2.5 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-ink">
                        {h.previous_status ? `${h.previous_status} → ` : ''}
                        {h.new_status}
                      </span>
                      <span className="inline-flex items-center gap-1 text-[11px] text-subtle">
                        <Clock className="h-3 w-3" />
                        {new Date(h.created_at).toLocaleString()}
                      </span>
                    </div>
                    {h.notes && (
                      <p className="mt-0.5 text-[11px] text-muted">{h.notes}</p>
                    )}
                    {h.evidence && (
                      <p className="mt-0.5 text-[10px] text-emerald-600 dark:text-emerald-400">
                        Evidence: {h.evidence}
                      </p>
                    )}
                    <span className="text-[10px] text-subtle">Source: {h.source}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
