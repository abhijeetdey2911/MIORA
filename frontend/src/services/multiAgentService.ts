import type {
  ApplicationItem,
  ApplicationLifecycleStatus,
  AutomationSettingsData,
  DashboardOverviewData,
  DiscoveredJobItem,
  JobMatchItem,
  JobSourceItem,
  NotificationItem,
  PreferenceRunSummary,
  ScheduledJobData,
  WorkflowRunSummary,
} from '../types/multiAgent';

const RAW_URL = import.meta.env.VITE_API_URL;
const BACKEND_BASE_URL = typeof RAW_URL === 'string' ? RAW_URL.replace(/\/+$/, '') : '';

const ORCHESTRATION_API = `${BACKEND_BASE_URL}/api/v1/orchestration`;
const JOBS_API = `${BACKEND_BASE_URL}/api/v1/jobs`;
const APPLICATIONS_API = `${BACKEND_BASE_URL}/api/v1/applications`;

interface BackendErrorDetail {
  loc?: (string | number)[];
  msg?: string;
}

interface BackendErrorBody {
  message?: string;
  detail?: string | BackendErrorDetail[];
  details?: BackendErrorDetail[];
}

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as BackendErrorBody;
    const validationList =
      body.details ?? (Array.isArray(body.detail) ? body.detail : undefined);
    if (validationList && validationList.length > 0) {
      const first = validationList[0];
      return (first.msg ?? 'Invalid input').replace(/^Value error,\s*/i, '');
    }
    if (typeof body.message === 'string' && body.message) {
      return body.message;
    }
    if (typeof body.detail === 'string' && body.detail) {
      return body.detail;
    }
  } catch {
    // Fallback below
  }
  return `Request failed with status ${response.status}`;
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const msg = await parseErrorMessage(response);
    throw new Error(msg);
  }
  return (await response.json()) as T;
}

// ============================================================================
// Dashboard & Central Orchestration Control
// ============================================================================

export async function getDashboardOverview(): Promise<DashboardOverviewData> {
  return requestJson<DashboardOverviewData>(`${ORCHESTRATION_API}/dashboard`);
}

export async function startJobHunterWorkflow(options?: {
  preference_ids?: string[];
  trigger_source?: string;
}): Promise<WorkflowRunSummary> {
  return requestJson<WorkflowRunSummary>(`${ORCHESTRATION_API}/start`, {
    method: 'POST',
    body: JSON.stringify(options ?? { trigger_source: 'manual' }),
  });
}

export async function pauseJobHunterWorkflow(options?: {
  workflow_run_id?: string;
  preference_id?: string;
}): Promise<AutomationSettingsData> {
  return requestJson<AutomationSettingsData>(`${ORCHESTRATION_API}/pause`, {
    method: 'POST',
    body: JSON.stringify(options ?? {}),
  });
}

export async function resumeJobHunterWorkflow(options?: {
  workflow_run_id?: string;
  preference_id?: string;
}): Promise<PreferenceRunSummary[]> {
  return requestJson<PreferenceRunSummary[]>(`${ORCHESTRATION_API}/resume`, {
    method: 'POST',
    body: JSON.stringify(options ?? {}),
  });
}

export async function stopJobHunterWorkflow(
  reason?: string,
): Promise<AutomationSettingsData> {
  return requestJson<AutomationSettingsData>(`${ORCHESTRATION_API}/stop`, {
    method: 'POST',
    body: JSON.stringify({
      reason: reason || 'Emergency kill switch engaged by user.',
    }),
  });
}

export async function recoverInterruptedWorkflows(): Promise<
  PreferenceRunSummary[]
> {
  return requestJson<PreferenceRunSummary[]>(`${ORCHESTRATION_API}/recover`, {
    method: 'POST',
  });
}

export async function getAutomationSettings(): Promise<AutomationSettingsData> {
  return requestJson<AutomationSettingsData>(`${ORCHESTRATION_API}/settings`);
}

export async function updateAutomationSettings(
  payload: Partial<AutomationSettingsData>,
): Promise<AutomationSettingsData> {
  return requestJson<AutomationSettingsData>(`${ORCHESTRATION_API}/settings`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function getAutomationSchedule(): Promise<ScheduledJobData> {
  return requestJson<ScheduledJobData>(`${ORCHESTRATION_API}/schedule`);
}

export async function updateAutomationSchedule(payload: {
  name?: string;
  is_enabled?: boolean;
  daily_time?: string;
  timezone?: string;
  max_jobs_per_run?: number;
  max_applications_per_run?: number;
}): Promise<ScheduledJobData> {
  return requestJson<ScheduledJobData>(`${ORCHESTRATION_API}/schedule`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function listWorkflowRuns(
  limit = 20,
): Promise<WorkflowRunSummary[]> {
  return requestJson<WorkflowRunSummary[]>(
    `${ORCHESTRATION_API}/runs?limit=${limit}`,
  );
}

// ============================================================================
// Job Discovery, Matching & Routes (Agents 1, 2, 3)
// ============================================================================

export async function listJobSources(): Promise<JobSourceItem[]> {
  return requestJson<JobSourceItem[]>(`${JOBS_API}/sources`);
}

export async function toggleJobSource(
  sourceId: string,
  isEnabled: boolean,
): Promise<JobSourceItem> {
  return requestJson<JobSourceItem>(`${JOBS_API}/sources/${sourceId}`, {
    method: 'PATCH',
    body: JSON.stringify({ is_enabled: isEnabled }),
  });
}

export async function listDiscoveredJobs(params?: {
  preference_id?: string;
  search?: string;
  work_mode?: string;
  source_name?: string;
}): Promise<DiscoveredJobItem[]> {
  const qs = new URLSearchParams();
  if (params?.preference_id) qs.set('preference_id', params.preference_id);
  if (params?.search) qs.set('search', params.search);
  if (params?.work_mode) qs.set('work_mode', params.work_mode);
  if (params?.source_name) qs.set('source_name', params.source_name);
  const suffix = qs.toString() ? `?${qs.toString()}` : '';
  return requestJson<DiscoveredJobItem[]>(`${JOBS_API}/discovered${suffix}`);
}

export async function listJobMatches(params?: {
  preference_id?: string;
  shortlisted_only?: boolean;
  min_score?: number;
  search?: string;
}): Promise<JobMatchItem[]> {
  const qs = new URLSearchParams();
  if (params?.preference_id) qs.set('preference_id', params.preference_id);
  if (params?.shortlisted_only) qs.set('shortlisted_only', 'true');
  if (params?.min_score !== undefined)
    qs.set('min_score', String(params.min_score));
  if (params?.search) qs.set('search', params.search);
  const suffix = qs.toString() ? `?${qs.toString()}` : '';
  return requestJson<JobMatchItem[]>(`${JOBS_API}/matches${suffix}`);
}

export async function toggleMatchShortlist(
  matchId: string,
  shortlisted: boolean,
): Promise<JobMatchItem> {
  return requestJson<JobMatchItem>(
    `${JOBS_API}/matches/${matchId}/shortlist`,
    {
      method: 'PATCH',
      body: JSON.stringify({ shortlisted }),
    },
  );
}

// ============================================================================
// Applications, Approvals, Reconciliation, Tracking & Notifications (Agents 4 & 5)
// ============================================================================

export async function listApplications(params?: {
  preference_id?: string;
  status?: string;
  search?: string;
}): Promise<ApplicationItem[]> {
  const qs = new URLSearchParams();
  if (params?.preference_id) qs.set('preference_id', params.preference_id);
  if (params?.status) qs.set('status', params.status);
  if (params?.search) qs.set('search', params.search);
  const suffix = qs.toString() ? `?${qs.toString()}` : '';
  return requestJson<ApplicationItem[]>(`${APPLICATIONS_API}${suffix}`);
}

export async function approveApplication(
  applicationId: string,
  payload?: {
    approved_by_user?: boolean;
    confirm_submission?: boolean;
    confirmation_evidence?: string;
    notes?: string;
  },
): Promise<ApplicationItem> {
  return requestJson<ApplicationItem>(
    `${APPLICATIONS_API}/${applicationId}/approve`,
    {
      method: 'POST',
      body: JSON.stringify(
        payload ?? { approved_by_user: true, confirm_submission: true },
      ),
    },
  );
}

export async function reconcileApplication(
  applicationId: string,
  payload: {
    resolution: 'Submitted' | 'Awaiting Approval' | 'Withdrawn';
    confirmation_evidence?: string;
    notes?: string;
  },
): Promise<ApplicationItem> {
  return requestJson<ApplicationItem>(
    `${APPLICATIONS_API}/${applicationId}/reconcile`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  );
}

export async function updateApplicationStatus(
  applicationId: string,
  payload: {
    status: ApplicationLifecycleStatus;
    notes?: string;
    evidence?: string;
    interview_date?: string | null;
    recruiter_response_text?: string | null;
    follow_up_reminder_at?: string | null;
  },
): Promise<ApplicationItem> {
  return requestJson<ApplicationItem>(
    `${APPLICATIONS_API}/${applicationId}/status`,
    {
      method: 'PATCH',
      body: JSON.stringify(payload),
    },
  );
}

export async function listNotifications(params?: {
  event_type?: string;
  unread_only?: boolean;
}): Promise<NotificationItem[]> {
  const qs = new URLSearchParams();
  if (params?.event_type) qs.set('event_type', params.event_type);
  if (params?.unread_only) qs.set('unread_only', 'true');
  const suffix = qs.toString() ? `?${qs.toString()}` : '';
  return requestJson<NotificationItem[]>(
    `${APPLICATIONS_API}/notifications/list${suffix}`,
  );
}

export async function markNotificationRead(
  notificationId: string,
): Promise<NotificationItem> {
  return requestJson<NotificationItem>(
    `${APPLICATIONS_API}/notifications/${notificationId}/read`,
    {
      method: 'PATCH',
    },
  );
}

export async function markAllNotificationsRead(): Promise<{
  marked_read_count: number;
}> {
  return requestJson<{ marked_read_count: number }>(
    `${APPLICATIONS_API}/notifications/read-all`,
    {
      method: 'POST',
    },
  );
}

