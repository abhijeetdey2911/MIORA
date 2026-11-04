"""Pydantic schemas for Resume Manager CRUD and preference associations."""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ResumeFormat = Literal["PDF", "DOCX"]
ResumeProcessingStatus = Literal["Uploaded", "Processing", "Processed", "Failed"]


class AssociatedPreferenceSummary(BaseModel):
    """Lightweight JobPreference reference attached to a resume."""

    id: UUID
    preference_name: str
    is_active: bool
    approved_resume_version_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class ResumeUpdate(BaseModel):
    """Schema for renaming a resume and/or updating its associated preferences."""

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Updated display name for the resume.",
    )
    resume_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Updated display name for the resume.",
    )
    preference_ids: Optional[List[UUID]] = Field(
        default=None,
        description="List of JobPreference UUIDs to associate with this resume.",
    )

    @field_validator("name", "resume_name")
    @classmethod
    def validate_resume_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Resume name cannot be empty.")
        return trimmed


class ResumeResponse(BaseModel):
    """Schema returned for a stored resume record."""

    id: UUID
    name: str
    resume_name: str
    original_filename: str
    file_type: ResumeFormat
    file_format: ResumeFormat
    mime_type: str
    file_size: int
    extracted_text: Optional[str] = None
    processing_status: ResumeProcessingStatus
    processing_message: Optional[str] = None
    requires_ocr: bool = False
    ai_status: str = "Not Analysed"
    approved_version_id: Optional[UUID] = None
    overall_quality_score: Optional[int] = None
    associated_preferences: List[AssociatedPreferenceSummary] = Field(
        default_factory=list
    )
    upload_date: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

