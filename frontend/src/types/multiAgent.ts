export type ApplicationLifecycleStatus =
  | 'Prepared'
  | 'Awaiting Approval'
  | 'Submitted'
  | 'Submission Unconfirmed'
  | 'Under Review'
  | 'Recruiter Response'
  | 'Interview'
  | 'Rejected'
  | 'Offer'
  | 'Withdrawn'
  | 'No Response';

export type ApprovalMode = 'manual' | 'auto_authorised';

export interface JobSourceItem {
  id: string;
  name: string;
  adapter_type: string;
  base_url: string | null;
  is_enabled: boolean;
  requires_credentials: boolean;
  rate_limit_per_minute: number;
  last_synced_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationRouteItem {
  id: string;
  discovered_job_id: string;
  preference_id: string;
  route_type: string;
  url_or_contact: string;
  source: string;
  verification_status: string;
  last_verified_at: string | null;
  confidence_level: number;
  requires_manual_review: boolean;
  verification_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface DiscoveredJobItem {
  id: string;
  source_id: string | null;
  source_name: string;
  external_job_id: string | null;
  canonical_url: string;
  fingerprint: string;
  title: string;
  company: string;
  location: string | null;
  work_mode: string | null;
  employment_type: string | null;
  experience_requirement: string | null;
  description: string;
  min_salary: number | null;
  max_salary: number | null;
  salary_currency: string | null;
  salary_raw: string | null;
  posted_at: string | null;
  official_job_url: string;
  discovered_at: string;
  created_at: string;
  updated_at: string;
}

export interface JobMatchItem {
  id: string;
  preference_id: string;
  preference_name?: string | null;
  preference_run_id: string | null;
  discovered_job_id: string;
  resume_version_id: string | null;
  match_score: number;
  threshold_used: number;
  is_matching: boolean;
  shortlisted: boolean;
  skills_matched: string[];
  relevant_experience: string[];
  missing_or_unverified_requirements: string[];
  reasons_for_matching: string[];
  reasons_for_rejection: string[];
  evaluation_method: string;
  discovered_job: DiscoveredJobItem;
  routes: ApplicationRouteItem[];
  created_at: string;
  updated_at: string;
}

export interface ApplicationStatusHistoryItem {
  id: string;
  application_id: string;
  previous_status: string | null;
  new_status: string;
  source: string;
  notes: string | null;
  evidence: string | null;
  created_at: string;
}

export interface ApplicationItem {
  id: string;
  preference_id: string;
  preference_name?: string | null;
  preference_run_id: string | null;
  discovered_job_id: string;
  job_match_id: string | null;
  route_id: string | null;
  resume_id: string | null;
  resume_version_id: string | null;
  resume_version_title?: string | null;
  company: string;
  job_title: string;
  route_type: string;
  route_target: string;
  status: ApplicationLifecycleStatus;
  approval_required: boolean;
  approved_by_user: boolean;
  approved_at: string | null;
  applied_at: string | null;
  confirmation_evidence: string | null;
  prepared_payload: Record<string, unknown>;
  interview_date: string | null;
  recruiter_response_text: string | null;
  follow_up_reminder_at: string | null;
  notes: string | null;
  retry_count: number;
  error_message: string | null;
  idempotency_key: string;
  status_history: ApplicationStatusHistoryItem[];
  created_at: string;
  updated_at: string;
}

export interface AutomationSettingsData {
  id: string;
  is_kill_switch_engaged: boolean;
  automation_state: string;
  approval_mode: ApprovalMode;
  max_jobs_per_run: number;
  max_applications_per_run: number;
  max_applications_per_day: number;
  max_runtime_seconds: number;
  max_api_spend_usd: number;
  current_api_spend_usd: number;
  minimum_match_score: number;
  retry_limit: number;
  allow_portal_auto_submit: boolean;
  allow_form_auto_submit: boolean;
  allow_hr_email_auto_submit: boolean;
  allow_recruiter_outreach: boolean;
  telegram_notifications_enabled: boolean;
  telegram_configured: boolean;
  notify_on_workflow_start: boolean;
  notify_on_workflow_complete: boolean;
  notify_on_errors: boolean;
  notify_on_application_submitted: boolean;
  notify_on_submission_unconfirmed: boolean;
  notify_on_interview: boolean;
  notify_on_recruiter_response: boolean;
  notify_on_offer: boolean;
  notify_daily_summary: boolean;
  created_at: string;
  updated_at: string;
}

export interface ScheduledJobData {
  id: string;
  name: string;
  is_enabled: boolean;
  cron_expression: string;
  daily_time: string;
  timezone: string;
  max_jobs_per_run: number;
  max_applications_per_run: number;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PreferenceRunSummary {
  id: string;
  run_id: string;
  preference_id: string;
  preference_name?: string | null;
  status: string;
  current_agent: string;
  approved_resume_version_id: string | null;
  jobs_discovered: number;
  matching_jobs: number;
  shortlisted_jobs: number;
  applications_submitted: number;
  interviews_scheduled: number;
  offers_received: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowRunSummary {
  id: string;
  status: string;
  trigger_source: string;
  current_stage: string;
  approval_mode: string;
  total_preferences: number;
  active_preferences: number;
  max_jobs_per_run: number;
  max_applications_per_run: number;
  api_spend_usd: number;
  error_message: string | null;
  started_at: string | null;
  paused_at: string | null;
  stopped_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  preference_executions: PreferenceRunSummary[];
}

export interface NotificationItem {
  id: string;
  preference_id: string | null;
  application_id: string | null;
  workflow_run_id: string | null;
  event_type: string;
  title: string;
  message: string;
  company: string | null;
  job_title: string | null;
  status_badge: string | null;
  is_read: boolean;
  telegram_sent: boolean;
  telegram_error: string | null;
  created_at: string;
}

export interface DashboardPreferenceCard {
  preference_id: string;
  code: string;
  preference_name: string;
  target_roles: string[];
  locations: string[];
  work_mode: string;
  is_active: boolean;
  has_approved_resume: boolean;
  eligible_for_applications: boolean;
  workflow_status: string;
  jobs_discovered: number;
  matching_jobs: number;
  shortlisted_jobs: number;
  applications_submitted: number;
  interviews: number;
  offers: number;
  recent_matches: {
    match_id: string;
    job_id: string | null;
    title: string;
    company: string;
    location: string;
    work_mode: string;
    match_score: number;
    shortlisted: boolean;
    official_job_url: string;
    skills_matched: string[];
  }[];
}

export interface DashboardOverviewData {
  jobs_discovered: number;
  matching_jobs: number;
  shortlisted_jobs: number;
  applications_submitted: number;
  interviews: number;
  offers: number;
  automation_state: string;
  is_kill_switch_engaged: boolean;
  approval_mode: string;
  active_preferences_count: number;
  paused_preferences_count: number;
  eligible_preferences_count: number;
  last_run: WorkflowRunSummary | null;
  preference_performance: DashboardPreferenceCard[];
  recent_updates: NotificationItem[];
  activity_series: {
    day: string;
    date: string;
    discovered: number;
    applications: number;
  }[];
}

