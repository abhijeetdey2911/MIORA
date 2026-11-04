"""SQLAlchemy ORM models for central orchestration and preference-scoped execution."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class JobHuntRun(Base):
    """Central orchestration run record triggered by the user ('Start JobHunter')."""

    __tablename__ = "job_hunt_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ready",
        server_default="ready",
        index=True,
    )
    trigger_source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="manual",
        server_default="manual",
    )
    total_preferences: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    active_preferences: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    current_stage: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="idle",
        server_default="idle",
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
    api_spend_usd: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0",
    )
    celery_task_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        unique=True,
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    paused_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    stopped_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
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

    preference_executions: Mapped[List["PreferenceExecution"]] = relationship(
        "PreferenceExecution",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class PreferenceExecution(Base):
    """Independent execution record for a single active JobPreference within a run."""

    __tablename__ = "preference_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_hunt_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    preference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_preferences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )
    jobs_discovered: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    matching_jobs: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    shortlisted_jobs: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    applications_submitted: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    interviews_scheduled: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    offers_received: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    approved_resume_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resume_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    current_agent: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    checkpoint_state: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
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

    run: Mapped["JobHuntRun"] = relationship(
        "JobHuntRun",
        back_populates="preference_executions",
    )
    job_results: Mapped[List["PreferenceJobResult"]] = relationship(
        "PreferenceJobResult",
        back_populates="execution",
        cascade="all, delete-orphan",
    )


class PreferenceJobResult(Base):
    """Preference-specific discovered and scored job record."""

    __tablename__ = "preference_job_results"

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
    execution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("preference_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    company: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    location: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    work_mode: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    job_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    match_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    is_matching: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    is_shortlisted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    execution: Mapped[Optional["PreferenceExecution"]] = relationship(
        "PreferenceExecution",
        back_populates="job_results",
    )
    applications: Mapped[List["PreferenceApplication"]] = relationship(
        "PreferenceApplication",
        back_populates="job_result",
        cascade="all, delete-orphan",
    )


class PreferenceApplication(Base):
    """Preference-specific job application tracking record."""

    __tablename__ = "preference_applications"

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
    execution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("preference_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    job_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("preference_job_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="queued",
        server_default="queued",
        index=True,
    )
    applied_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status_note: Mapped[Optional[str]] = mapped_column(
        String(500),
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

    job_result: Mapped["PreferenceJobResult"] = relationship(
        "PreferenceJobResult",
        back_populates="applications",
    )


# Aliases matching Part 13 specification
WorkflowRun = JobHuntRun
PreferenceRun = PreferenceExecution


