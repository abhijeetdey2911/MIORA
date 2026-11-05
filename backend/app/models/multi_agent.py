"""SQLAlchemy ORM models for the Complete Multi-Agent JobHunting System (Part 13):
- JobSource: Configured job source adapters (Official APIs, feeds, company career pages).
- DiscoveredJob: Deduplicated jobs discovered by Agent 1.
- JobMatch: Preference-isolated AI/rule job matching scores and shortlisting decisions (Agent 2).
- ApplicationRoute: Verified or manual-review application routes (Agent 3).
- Application: Application preparation, approval, execution, and tracking records (Agent 4 & Agent 5).
- ApplicationStatusHistory: Full audit trail of application status changes (Agent 5).
- AgentExecution: Step-level execution logs and API cost tracking per preference workflow.
- AutomationSettings: Central Automation Control Centre settings, limits, permissions, and kill switch.
- ScheduledJob: Configurable recurring schedule records.
- Notification: System, application, and Telegram notification history.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class JobSource(Base):
    """Represents a permitted job discovery source adapter."""

    __tablename__ = "job_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        unique=True,
        index=True,
    )
    adapter_type: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
        index=True,
    )
    base_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    requires_credentials: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    rate_limit_per_minute: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30,
        server_default="30",
    )
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class DiscoveredJob(Base):
    """Stores a deduplicated job listing discovered by Agent 1."""

    __tablename__ = "discovered_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
    )
    external_job_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    canonical_url: Mapped[str] = mapped_column(
        String(600),
        nullable=False,
        unique=True,
        index=True,
    )
    fingerprint: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
        index=True,
    )
    company: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )
    location: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )
    work_mode: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    employment_type: Mapped[Optional[str]] = mapped_column(
        String(60),
        nullable=True,
    )
    experience_requirement: Mapped[Optional[str]] = mapped_column(
        String(120),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    min_salary: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    max_salary: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    salary_currency: Mapped[Optional[str]] = mapped_column(
        String(16),
        nullable=True,
    )
    salary_raw: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )
    posted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    official_job_url: Mapped[str] = mapped_column(
        String(600),
        nullable=False,
    )
    raw_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    matches: Mapped[List["JobMatch"]] = relationship(
        "JobMatch",
        back_populates="discovered_job",
        cascade="all, delete-orphan",
    )
    routes: Mapped[List["ApplicationRoute"]] = relationship(
        "ApplicationRoute",
        back_populates="discovered_job",
        cascade="all, delete-orphan",
    )


class JobMatch(Base):
    """Preference-isolated evaluation of a DiscoveredJob produced by Agent 2."""

    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint(
            "preference_id",
            "discovered_job_id",
            name="uq_job_match_preference_job",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    preference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_preferences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    preference_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("preference_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    discovered_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discovered_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resume_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    match_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        index=True,
    )
    threshold_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=70,
    )
    is_matching: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )
    shortlisted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )
    skills_matched: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    relevant_experience: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    missing_or_unverified_requirements: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    reasons_for_matching: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    reasons_for_rejection: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    evaluation_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="deterministic_rule",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    discovered_job: Mapped["DiscoveredJob"] = relationship(
        "DiscoveredJob",
        back_populates="matches",
        lazy="selectin",
    )


class ApplicationRoute(Base):
    """Stores a legitimate application route discovered and verified by Agent 3."""

    __tablename__ = "application_routes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    discovered_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discovered_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    preference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_preferences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    route_type: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
        index=True,
    )
    url_or_contact: Mapped[str] = mapped_column(
        String(600),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    verification_status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="unverified",
        index=True,
    )
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    confidence_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
    )
    requires_manual_review: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    verification_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    discovered_job: Mapped["DiscoveredJob"] = relationship(
        "DiscoveredJob",
        back_populates="routes",
    )


class Application(Base):
    """Central job application record managed by Agent 4 (Execution) and Agent 5 (Tracking).

    Enforces cross-preference duplicate prevention via unique constraint on `discovered_job_id`
    and `idempotency_key`.
    """

    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint(
            "discovered_job_id",
            name="uq_application_discovered_job",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    preference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_preferences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    preference_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("preference_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    discovered_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discovered_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_match_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_matches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    route_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("application_routes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resume_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resume_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resume_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    company: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )
    job_title: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
        index=True,
    )
    route_type: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
    )
    route_target: Mapped[str] = mapped_column(
        String(600),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Prepared",
        server_default="Prepared",
        index=True,
    )
    approval_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    approved_by_user: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    approval_reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    submission_attempted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    applied_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    external_application_id: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
    )
    submission_result: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    confirmation_evidence: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    prepared_payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    interview_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    recruiter_response_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    follow_up_reminder_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    status_history: Mapped[List["ApplicationStatusHistory"]] = relationship(
        "ApplicationStatusHistory",
        back_populates="application",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ApplicationStatusHistory.created_at.asc()",
    )


class ApplicationStatusHistory(Base):
    """Audit trail of status transitions for an Application (Agent 5)."""

    __tablename__ = "application_status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    new_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        default="system",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    evidence: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="status_history",
    )


class AgentExecution(Base):
    """Records execution metrics, duration, and API cost for each agent invocation."""

    __tablename__ = "agent_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_hunt_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    preference_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("preference_executions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    preference_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_preferences.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="running",
        index=True,
    )
    items_processed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    api_cost_usd: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    details: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class AutomationSettings(Base):
    """Stores central automation limits, approval permissions, and kill-switch state."""

    __tablename__ = "automation_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    is_kill_switch_engaged: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    automation_state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ready",
        server_default="ready",
    )
    approval_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="manual",
        server_default="manual",
    )
    max_jobs_per_run: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
        server_default="50",
    )
    max_applications_per_run: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
    )
    max_applications_per_day: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=25,
        server_default="25",
    )
    max_runtime_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1800,
        server_default="1800",
    )
    max_api_spend_usd: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=5.0,
        server_default="5.0",
    )
    current_api_spend_usd: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0.0",
    )
    minimum_match_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=70,
        server_default="70",
    )
    retry_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
        server_default="2",
    )
    allow_portal_auto_submit: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    allow_form_auto_submit: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    allow_hr_email_auto_submit: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    allow_recruiter_outreach: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    telegram_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    notify_on_workflow_start: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    notify_on_workflow_complete: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    notify_on_errors: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    notify_on_application_submitted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    notify_on_submission_unconfirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    notify_on_interview: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    notify_on_recruiter_response: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    notify_on_offer: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    notify_daily_summary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ScheduledJob(Base):
    """Stores a configurable schedule for automated JobHunter workflow runs."""

    __tablename__ = "scheduled_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        default="Daily JobHunter Run",
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )
    cron_expression: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
        default="0 9 * * *",
    )
    daily_time: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="09:00",
    )
    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="Asia/Kolkata",
    )
    max_jobs_per_run: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
    )
    max_applications_per_run: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )
    last_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Notification(Base):
    """Stores application updates, workflow events, and Telegram notification dispatch logs."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    preference_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_preferences.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workflow_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_hunt_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    company: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )
    job_title: Mapped[Optional[str]] = mapped_column(
        String(250),
        nullable=True,
    )
    status_badge: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )
    telegram_sent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    telegram_error: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

