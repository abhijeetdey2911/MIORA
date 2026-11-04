"""Pydantic schemas for the Complete Multi-Agent JobHunting System (Parts 1–14)."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ApplicationLifecycleStatus = Literal[
    "Prepared",
    "Awaiting Approval",
    "Submitted",
    "Submission Unconfirmed",
    "Under Review",
    "Recruiter Response",
    "Interview",
    "Rejected",
    "Offer",
    "Withdrawn",
    "No Response",
]

ApprovalMode = Literal["manual", "auto_authorised"]

RouteType = Literal[
    "official_company_portal",
    "official_application_form",
    "published_hr_email",
    "verified_recruiter_contact",
]

RouteVerificationStatus = Literal[
    "verified",
    "unverified",
    "manual_review_required",
]


# ==============================================================================
# Job Sources, Discovered Jobs & Preference Job Matches (Agents 1 & 2)
# ==============================================================================


class JobSourceResponse(BaseModel):
    """Schema for a configured job discovery source adapter."""

    id: UUID
    name: str
    adapter_type: str
    base_url: Optional[str] = None
    is_enabled: bool
    requires_credentials: bool
    rate_limit_per_minute: int
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationRouteResponse(BaseModel):
    """Schema for an application route discovered by Agent 3."""

    id: UUID
    discovered_job_id: UUID
    preference_id: UUID
    route_type: str
    url_or_contact: str
    source: str
    verification_status: str
    last_verified_at: Optional[datetime] = None
    confidence_level: int
    requires_manual_review: bool
    verification_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiscoveredJobResponse(BaseModel):
    """Schema for a deduplicated job discovered by Agent 1."""

    id: UUID
    source_id: Optional[UUID] = None
    source_name: str
    external_job_id: Optional[str] = None
    canonical_url: str
    fingerprint: str
    title: str
    company: str
    location: Optional[str] = None
    work_mode: Optional[str] = None
    employment_type: Optional[str] = None
    experience_requirement: Optional[str] = None
    description: str
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    salary_currency: Optional[str] = None
    salary_raw: Optional[str] = None
    posted_at: Optional[datetime] = None
    official_job_url: str
    discovered_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobMatchResponse(BaseModel):
    """Schema for a preference-isolated job match evaluated by Agent 2."""

    id: UUID
    preference_id: UUID
    preference_name: Optional[str] = None
    preference_run_id: Optional[UUID] = None
    discovered_job_id: UUID
    resume_version_id: Optional[UUID] = None
    match_score: int
    threshold_used: int
    is_matching: bool
    shortlisted: bool
    skills_matched: List[str] = Field(default_factory=list)
    relevant_experience: List[str] = Field(default_factory=list)
    missing_or_unverified_requirements: List[str] = Field(default_factory=list)
    reasons_for_matching: List[str] = Field(default_factory=list)
    reasons_for_rejection: List[str] = Field(default_factory=list)
    evaluation_method: str
    discovered_job: DiscoveredJobResponse
    routes: List[ApplicationRouteResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# Applications & Tracking (Agents 4 & 5)
# ==============================================================================


class ApplicationStatusHistoryResponse(BaseModel):
    """Audit trail item for an application status transition."""

    id: UUID
    application_id: UUID
    previous_status: Optional[str] = None
    new_status: str
    source: str
    notes: Optional[str] = None
    evidence: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationResponse(BaseModel):
    """Full application record returned by Agent 4 & Agent 5 APIs."""

    id: UUID
    preference_id: UUID
    preference_name: Optional[str] = None
    preference_run_id: Optional[UUID] = None
    discovered_job_id: UUID
    job_match_id: Optional[UUID] = None
    route_id: Optional[UUID] = None
    resume_id: Optional[UUID] = None
    resume_version_id: Optional[UUID] = None
    resume_version_title: Optional[str] = None
    company: str
    job_title: str
    route_type: str
    route_target: str
    status: str
    approval_required: bool
    approved_by_user: bool
    approved_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None
    confirmation_evidence: Optional[str] = None
    prepared_payload: Dict[str, Any] = Field(default_factory=dict)
    interview_date: Optional[datetime] = None
    recruiter_response_text: Optional[str] = None
    follow_up_reminder_at: Optional[datetime] = None
    notes: Optional[str] = None
    retry_count: int
    error_message: Optional[str] = None
    idempotency_key: str
    status_history: List[ApplicationStatusHistoryResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationApproveRequest(BaseModel):
    """Request payload when user approves a prepared application for submission."""

    confirmation_evidence: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional confirmation reference or note from official portal/submission.",
    )
    notes: Optional[str] = Field(default=None, max_length=2000)


class ApplicationStatusUpdateRequest(BaseModel):
    """Request payload for updating an application's tracking status (Agent 5)."""

    status: ApplicationLifecycleStatus
    notes: Optional[str] = Field(default=None, max_length=2000)
    evidence: Optional[str] = Field(default=None, max_length=1000)
    interview_date: Optional[datetime] = None
    recruiter_response_text: Optional[str] = Field(default=None, max_length=5000)
    follow_up_reminder_at: Optional[datetime] = None


# ==============================================================================
# Automation Control Centre, Settings, Scheduling & Notifications (Parts 8–12)
# ==============================================================================


class AutomationSettingsResponse(BaseModel):
    """Response schema for Central Automation Control Centre settings."""

    id: UUID
    is_kill_switch_engaged: bool
    automation_state: str
    approval_mode: str
    max_jobs_per_run: int
    max_applications_per_run: int
    max_applications_per_day: int
    max_runtime_seconds: int
    max_api_spend_usd: float
    current_api_spend_usd: float
    minimum_match_score: int
    retry_limit: int
    allow_portal_auto_submit: bool
    allow_form_auto_submit: bool
    allow_hr_email_auto_submit: bool
    allow_recruiter_outreach: bool
    telegram_notifications_enabled: bool
    telegram_configured: bool = False
    notify_on_workflow_start: bool
    notify_on_workflow_complete: bool
    notify_on_errors: bool
    notify_on_application_submitted: bool
    notify_on_submission_unconfirmed: bool
    notify_on_interview: bool
    notify_on_recruiter_response: bool
    notify_on_offer: bool
    notify_daily_summary: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AutomationSettingsUpdate(BaseModel):
    """Request schema for updating Automation Control Centre limits and permissions."""

    approval_mode: Optional[ApprovalMode] = None
    max_jobs_per_run: Optional[int] = Field(default=None, ge=1, le=500)
    max_applications_per_run: Optional[int] = Field(default=None, ge=0, le=100)
    max_applications_per_day: Optional[int] = Field(default=None, ge=0, le=200)
    max_runtime_seconds: Optional[int] = Field(default=None, ge=60, le=14400)
    max_api_spend_usd: Optional[float] = Field(default=None, ge=0.0, le=500.0)
    minimum_match_score: Optional[int] = Field(default=None, ge=0, le=100)
    retry_limit: Optional[int] = Field(default=None, ge=0, le=5)
    allow_portal_auto_submit: Optional[bool] = None
    allow_form_auto_submit: Optional[bool] = None
    allow_hr_email_auto_submit: Optional[bool] = None
    allow_recruiter_outreach: Optional[bool] = None
    telegram_notifications_enabled: Optional[bool] = None
    notify_on_workflow_start: Optional[bool] = None
    notify_on_workflow_complete: Optional[bool] = None
    notify_on_errors: Optional[bool] = None
    notify_on_application_submitted: Optional[bool] = None
    notify_on_submission_unconfirmed: Optional[bool] = None
    notify_on_interview: Optional[bool] = None
    notify_on_recruiter_response: Optional[bool] = None
    notify_on_offer: Optional[bool] = None
    notify_daily_summary: Optional[bool] = None


class ScheduledJobResponse(BaseModel):
    """Response schema for a scheduled JobHunter run."""

    id: UUID
    name: str
    is_enabled: bool
    cron_expression: str
    daily_time: str
    timezone: str
    max_jobs_per_run: int
    max_applications_per_run: int
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScheduledJobUpdate(BaseModel):
    """Request schema for configuring scheduled execution (e.g. daily at 09:00)."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    is_enabled: Optional[bool] = None
    daily_time: Optional[str] = Field(
        default=None,
        description="24-hour time string HH:MM (e.g. '09:00')",
    )
    timezone: Optional[str] = Field(default=None, max_length=64)
    max_jobs_per_run: Optional[int] = Field(default=None, ge=1, le=500)
    max_applications_per_run: Optional[int] = Field(default=None, ge=0, le=100)

    @field_validator("daily_time")
    @classmethod
    def validate_daily_time(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        parts = trimmed.split(":")
        if len(parts) != 2:
            raise ValueError("daily_time must be in HH:MM format (e.g. '09:00').")
        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("daily_time hour must be 00-23 and minute 00-59.")
        return f"{hour:02d}:{minute:02d}"


class AgentExecutionResponse(BaseModel):
    """Step-level agent execution record."""

    id: UUID
    workflow_run_id: UUID
    preference_run_id: Optional[UUID] = None
    preference_id: Optional[UUID] = None
    agent_name: str
    status: str
    items_processed: int
    api_cost_usd: float
    details: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PreferenceRunSummaryResponse(BaseModel):
    """Independent per-preference workflow execution summary."""

    id: UUID
    run_id: UUID
    preference_id: UUID
    preference_name: Optional[str] = None
    status: str
    current_agent: str
    approved_resume_version_id: Optional[UUID] = None
    jobs_discovered: int
    matching_jobs: int
    shortlisted_jobs: int
    applications_submitted: int
    interviews_scheduled: int
    offers_received: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowRunSummaryResponse(BaseModel):
    """Central JobHunter workflow run summary."""

    id: UUID
    status: str
    trigger_source: str
    current_stage: str
    approval_mode: str
    total_preferences: int
    active_preferences: int
    max_jobs_per_run: int
    max_applications_per_run: int
    api_spend_usd: float
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    preference_executions: List[PreferenceRunSummaryResponse] = Field(
        default_factory=list
    )

    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(BaseModel):
    """Application update or automation notification item."""

    id: UUID
    preference_id: Optional[UUID] = None
    application_id: Optional[UUID] = None
    workflow_run_id: Optional[UUID] = None
    event_type: str
    title: str
    message: str
    company: Optional[str] = None
    job_title: Optional[str] = None
    status_badge: Optional[str] = None
    is_read: bool
    telegram_sent: bool
    telegram_error: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# Dashboard Overview Schema (Part 10 — All Data Sourced from PostgreSQL)
# ==============================================================================


class DashboardPreferenceCardItem(BaseModel):
    """Per-preference performance card backed by PostgreSQL."""

    preference_id: UUID
    code: str
    preference_name: str
    target_roles: List[str]
    locations: List[str]
    work_mode: str
    is_active: bool
    has_approved_resume: bool
    eligible_for_applications: bool
    workflow_status: str
    jobs_discovered: int
    matching_jobs: int
    shortlisted_jobs: int
    applications_submitted: int
    interviews: int
    offers: int
    recent_matches: List[Dict[str, Any]] = Field(default_factory=list)


class DashboardOverviewResponse(BaseModel):
    """Complete Dashboard state sourced from PostgreSQL."""

    jobs_discovered: int
    matching_jobs: int
    shortlisted_jobs: int
    applications_submitted: int
    interviews: int
    offers: int
    automation_state: str
    is_kill_switch_engaged: bool
    approval_mode: str
    active_preferences_count: int
    paused_preferences_count: int
    eligible_preferences_count: int
    last_run: Optional[WorkflowRunSummaryResponse] = None
    preference_performance: List[DashboardPreferenceCardItem] = Field(
        default_factory=list
    )
    recent_updates: List[NotificationResponse] = Field(default_factory=list)
    activity_series: List[Dict[str, Any]] = Field(default_factory=list)

