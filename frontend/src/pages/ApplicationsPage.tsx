import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Eye,
  FileCheck,
  Search,
  Send,
  Sparkles,
  X,
} from 'lucide-react';
import {
  approveApplication,
  listApplications,
  reconcileApplication,
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
  'Submitted',
  'Submission Unconfirmed',
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
    case 'Under Review':
      return 'bg-sky-500/10 text-sky-600 dark:bg-sky-400/15 dark:text-sky-300';
    case 'Interview':
    case 'Offer':
    case 'Recruiter Response':
      return 'bg-emerald-500/10 text-emerald-600 dark:bg-emerald-400/15 dark:text-emerald-300';
    case 'Submission Unconfirmed':
    case 'Awaiting Approval':
    case 'Prepared':
      return 'bg-amber-500/10 text-amber-600 dark:bg-amber-400/15 dark:text-amber-300';
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
  const [approvingApp, setApprovingApp] = useState<ApplicationItem | null>(
    null,
  );
  const [confirmationReceipt, setConfirmationReceipt] = useState<string>('');
  const [confirmSubmissionToggle, setConfirmSubmissionToggle] =
    useState<boolean>(true);
  const [approvalNotes, setApprovalNotes] = useState<string>('');

  const [reconcilingApp, setReconcilingApp] =
    useState<ApplicationItem | null>(null);
  const [reconcileResolution, setReconcileResolution] = useState<
    'Submitted' | 'Awaiting Approval' | 'Withdrawn'
  >('Submitted');
  const [reconcileEvidence, setReconcileEvidence] = useState<string>('');

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
        confirm_submission: confirmSubmissionToggle,
        confirmation_evidence: confirmationReceipt.trim() || undefined,
        notes: approvalNotes.trim() || undefined,
      });
      setApprovingApp(null);
      setConfirmationReceipt('');
      setApprovalNotes('');
      await loadData();
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to approve application.',
      );
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
          Cross-preference duplicate prevention active · Approved resumes only
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
                          {app.confirmation_evidence && (
                            <p className="mt-0.5 text-[10px] text-muted">
                              Ref: {app.confirmation_evidence}
                            </p>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="inline-flex flex-wrap items-center justify-end gap-1.5">
                            {(app.status === 'Awaiting Approval' ||
                              app.status === 'Prepared') && (
                              <button
                                type="button"
                                onClick={() => {
                                  setApprovingApp(app);
                                  setConfirmSubmissionToggle(true);
                                  setConfirmationReceipt('');
                                }}
                                className="inline-flex items-center gap-1 rounded-lg bg-accent px-2.5 py-1 text-[11px] font-semibold text-white hover:brightness-105"
                              >
                                <CheckCircle2 className="h-3 w-3" />
                                Approve
                              </button>
                            )}

                            {app.status === 'Submission Unconfirmed' && (
                              <button
                                type="button"
                                onClick={() => {
                                  setReconcilingApp(app);
                                  setReconcileResolution('Submitted');
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

      {/* Approve Prepared Application Modal */}
      {approvingApp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            onClick={() => setApprovingApp(null)}
            className="fixed inset-0 bg-black/50 backdrop-blur-[2px]"
          />
          <div className="relative z-10 w-full max-w-md rounded-2xl border border-line bg-surface p-5 shadow-card">
            <h3 className="text-sm font-semibold text-ink">
              Approve & Submit Application (Agent 4)
            </h3>
            <p className="mt-1 text-xs text-muted">
              {approvingApp.job_title} at {approvingApp.company}
            </p>

            <div className="mt-3 space-y-3 text-xs">
              <label className="flex items-center gap-2 font-medium text-ink">
                <input
                  type="checkbox"
                  checked={confirmSubmissionToggle}
                  onChange={(e) => setConfirmSubmissionToggle(e.target.checked)}
                />
                Submission receipt confirmed (marks as &quot;Submitted&quot;;
                uncheck if receipt is uncertain to record &quot;Submission
                Unconfirmed&quot;)
              </label>

              <div>
                <label className="block text-[11px] font-medium text-muted">
                  Confirmation Receipt / Reference (Optional)
                </label>
                <input
                  type="text"
                  value={confirmationReceipt}
                  onChange={(e) => setConfirmationReceipt(e.target.value)}
                  placeholder="e.g. PORTAL-RECEIPT-88412"
                  className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted">
                  Submission Notes
                </label>
                <textarea
                  rows={2}
                  value={approvalNotes}
                  onChange={(e) => setApprovalNotes(e.target.value)}
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
                Confirm & Execute
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reconcile Submission Unconfirmed Modal */}
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
                        | 'Awaiting Approval'
                        | 'Withdrawn',
                    )
                  }
                  className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                >
                  <option value="Submitted">
                    Confirmed Submitted (Requires Receipt Evidence)
                  </option>
                  <option value="Awaiting Approval">
                    Did Not Submit — Return to Awaiting Approval for Safe Retry
                  </option>
                  <option value="Withdrawn">Withdraw Application</option>
                </select>
              </div>

              {reconcileResolution === 'Submitted' && (
                <div>
                  <label className="block text-[11px] font-medium text-muted">
                    Confirmation Evidence (Required)
                  </label>
                  <input
                    type="text"
                    value={reconcileEvidence}
                    onChange={(e) => setReconcileEvidence(e.target.value)}
                    placeholder="e.g. Confirmation email received at 14:20"
                    className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                  />
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

      {/* Update Status Modal (Agent 5) */}
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
                  Confirmation Evidence (Required if marking Submitted)
                </label>
                <input
                  type="text"
                  value={statusEvidence}
                  onChange={(e) => setStatusEvidence(e.target.value)}
                  placeholder="Receipt ID or confirmation note"
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

      {/* View Application Details & Status Audit History Modal */}
      {selectedApp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            onClick={() => setSelectedApp(null)}
            className="fixed inset-0 bg-black/50 backdrop-blur-[2px]"
          />
          <div className="relative z-10 max-h-[85vh] w-full max-w-xl overflow-y-auto rounded-2xl border border-line bg-surface p-6 shadow-card">
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

            <div className="mt-4 grid grid-cols-2 gap-3 rounded-xl border border-line bg-surface-2 p-3 text-xs">
              <div>
                <span className="text-muted">Current Status:</span>{' '}
                <span className="font-semibold text-ink">
                  {selectedApp.status}
                </span>
              </div>
              <div>
                <span className="text-muted">Route:</span>{' '}
                <span className="font-medium capitalize text-ink">
                  {selectedApp.route_type.replace(/_/g, ' ')}
                </span>
              </div>
              <div>
                <span className="text-muted">Confirmation Evidence:</span>{' '}
                <span className="font-medium text-ink">
                  {selectedApp.confirmation_evidence || 'None'}
                </span>
              </div>
              <div>
                <span className="text-muted">Follow-Up Reminder:</span>{' '}
                <span className="font-medium text-ink">
                  {selectedApp.follow_up_reminder_at
                    ? new Date(
                        selectedApp.follow_up_reminder_at,
                      ).toLocaleDateString()
                    : 'Not scheduled'}
                </span>
              </div>
            </div>

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
