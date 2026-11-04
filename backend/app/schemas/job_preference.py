"""Pydantic schemas for JobPreference CRUD operations."""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

WorkMode = Literal["Remote", "Hybrid", "On-site"]
EmploymentType = Literal["Full-time", "Internship", "Contract", "Part-time"]
ExperienceLevel = Literal["Fresher", "Entry-level", "Experienced"]


def _clean_string_list(values: List[str], field_label: str) -> List[str]:
    """Strip whitespace, remove empty entries, and deduplicate preserving order."""
    if not isinstance(values, list):
        raise ValueError(f"{field_label} must be a list of strings.")
    cleaned: List[str] = []
    seen = set()
    for item in values:
        if not isinstance(item, str):
            raise ValueError(f"Each entry in {field_label} must be a string.")
        trimmed = item.strip()
        if trimmed and trimmed.lower() not in seen:
            seen.add(trimmed.lower())
            cleaned.append(trimmed)
    if not cleaned:
        raise ValueError(f"At least one {field_label} entry is required.")
    return cleaned


class JobPreferenceBase(BaseModel):
    """Shared properties for job preference schemas."""

    preference_name: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Human-readable name for this preference profile",
    )
    job_roles: List[str] = Field(
        ...,
        min_length=1,
        description="Target job titles/roles",
    )
    locations: List[str] = Field(
        ...,
        min_length=1,
        description="Preferred job locations",
    )
    work_mode: WorkMode = Field(
        ...,
        description="Work mode: Remote, Hybrid, or On-site",
    )
    employment_type: EmploymentType = Field(
        ...,
        description="Employment type: Full-time, Internship, Contract, or Part-time",
    )
    experience_level: ExperienceLevel = Field(
        ...,
        description="Experience level: Fresher, Entry-level, or Experienced",
    )
    min_salary: Optional[int] = Field(
        default=None,
        ge=0,
        description="Minimum expected salary",
    )
    max_salary: Optional[int] = Field(
        default=None,
        ge=0,
        description="Maximum expected salary",
    )
    currency: str = Field(
        default="INR",
        min_length=1,
        max_length=10,
        description="Salary currency code (default INR)",
    )
    skills: List[str] = Field(
        ...,
        min_length=1,
        description="Required technical or domain skills",
    )
    minimum_match_score: int = Field(
        default=70,
        ge=0,
        le=100,
        description="Minimum AI job match threshold percentage (0-100)",
    )
    is_active: bool = Field(
        default=True,
        description="Whether this preference profile is active or paused",
    )

    @field_validator("preference_name")
    @classmethod
    def validate_preference_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Preference name cannot be empty.")
        return trimmed

    @field_validator("job_roles")
    @classmethod
    def validate_job_roles(cls, v: List[str]) -> List[str]:
        return _clean_string_list(v, "target job role")

    @field_validator("locations")
    @classmethod
    def validate_locations(cls, v: List[str]) -> List[str]:
        return _clean_string_list(v, "preferred location")

    @field_validator("skills")
    @classmethod
    def validate_skills(cls, v: List[str]) -> List[str]:
        return _clean_string_list(v, "skill")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        trimmed = v.strip().upper()
        if not trimmed:
            raise ValueError("Currency cannot be empty.")
        return trimmed

    @model_validator(mode="after")
    def validate_salary_range(self) -> "JobPreferenceBase":
        if (
            self.min_salary is not None
            and self.max_salary is not None
            and self.max_salary < self.min_salary
        ):
            raise ValueError(
                "Maximum salary must be greater than or equal to minimum salary."
            )
        return self


class JobPreferenceCreate(JobPreferenceBase):
    """Schema for creating a new job preference."""

    pass


class JobPreferenceUpdate(JobPreferenceBase):
    """Schema for updating an existing job preference."""

    pass


class JobPreferenceStatusUpdate(BaseModel):
    """Schema for activating or pausing a job preference."""

    is_active: Optional[bool] = Field(
        default=None,
        description="Explicit active status; if omitted, status is toggled.",
    )


class JobPreferenceResponse(JobPreferenceBase):
    """Schema returned for a persisted job preference."""

    id: UUID
    approved_resume_id: Optional[UUID] = None
    approved_resume_version_id: Optional[UUID] = None
    has_approved_resume: bool = False
    eligible_for_applications: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

