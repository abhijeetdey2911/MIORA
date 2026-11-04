"""Pydantic schemas for Central Orchestration and Preference Execution readiness."""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

AutomationState = Literal["ready", "running", "paused", "completed", "failed"]
PreferenceExecutionState = Literal["pending", "running", "paused", "completed", "failed"]


class OrchestrationPreferenceSummary(BaseModel):
    """Summary of how a saved JobPreference participates in central orchestration."""

    preference_id: UUID
    preference_name: str
    is_active: bool
    eligible_for_discovery: bool = Field(
        ...,
        description="True when active; paused preferences are excluded from future discovery runs.",
    )
    has_approved_resume: bool = Field(
        default=False,
        description="True when a resume version has been approved for this job preference.",
    )
    approved_resume_id: Optional[UUID] = None
    approved_resume_version_id: Optional[UUID] = None
    eligible_for_applications: bool = Field(
        default=False,
        description="True only when active AND an approved resume version is linked.",
    )
    job_roles: List[str]
    locations: List[str]
    work_mode: str
    minimum_match_score: int


class PreferenceExecutionRead(BaseModel):
    """Schema for an independent per-preference execution record."""

    id: UUID
    run_id: UUID
    preference_id: UUID
    status: PreferenceExecutionState
    jobs_discovered: int
    matching_jobs: int
    shortlisted_jobs: int
    applications_submitted: int
    interviews_scheduled: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobHuntRunRead(BaseModel):
    """Schema for a central JobHunter orchestration run."""

    id: UUID
    status: AutomationState
    trigger_source: str
    total_preferences: int
    active_preferences: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    preference_executions: List[PreferenceExecutionRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class OrchestrationReadinessResponse(BaseModel):
    """Read-only orchestration overview reporting preference eligibility and engine state."""

    engine_connected: bool = Field(
        default=False,
        description="False until the multi-agent automation engine is connected in a later phase.",
    )
    automation_state: AutomationState = Field(
        default="ready",
        description="Current central automation state (ready, running, paused, completed, failed).",
    )
    message: str
    total_preferences: int
    active_preferences: int
    paused_preferences: int
    workflow_steps: List[str]
    preferences: List[OrchestrationPreferenceSummary]

