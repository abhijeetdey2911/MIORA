"""SQLAlchemy ORM models for Phase 3B AI Resume Intelligence:
- ResumeAnalysis: Structured candidate profile extraction, preference-based evaluation, and 0-100 scoring.
- ResumeSuggestion: Section-specific improvement recommendations with accept/reject/edit workflow.
- ResumeVersion: Version history (Original Uploaded, AI-Generated Draft, User-Edited Version, Approved Version).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.resume import Resume


class ResumeAnalysis(Base):
    """Stores structured AI analysis, preference-based evaluations, and 0-100 scores for a Resume."""

    __tablename__ = "resume_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="openai",
    )
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="gpt-4o-mini",
    )

    # 1. Extracted & Evaluated Candidate Profile Sections (JSONB)
    candidate_profile: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    education: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    technical_skills: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    soft_skills: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    work_experience: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    internships: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    projects: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    certifications: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    achievements: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    tools_and_technologies: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # 2. Preference-Based Analysis (separate evaluation per associated JobPreference)
    preference_analyses: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # 3. Resume Scoring (0-100 scale estimates + brief explanations)
    overall_quality_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    preference_relevance_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    skills_alignment_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    experience_alignment_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    project_relevance_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    ats_readability_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    score_explanations: Mapped[Dict[str, str]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Overall Strengths, Weaknesses & Clarifying Questions
    overall_strengths: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    overall_weaknesses: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    missing_information_questions: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
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

    resume: Mapped["Resume"] = relationship("Resume", back_populates="analyses")
    suggestions: Mapped[List["ResumeSuggestion"]] = relationship(
        "ResumeSuggestion",
        back_populates="analysis",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ResumeSuggestion(Base):
    """Stores an actionable section-level improvement suggestion for a Resume."""

    __tablename__ = "resume_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    analysis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resume_analyses.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    section_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
    )
    current_content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    suggested_improvement: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    user_edited_content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="Medium",
    )
    clarifying_question: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="Pending",
        server_default="Pending",
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

    resume: Mapped["Resume"] = relationship("Resume", back_populates="suggestions")
    analysis: Mapped[Optional["ResumeAnalysis"]] = relationship(
        "ResumeAnalysis",
        back_populates="suggestions",
    )

    @property
    def effective_content(self) -> str:
        """Return user-edited content if provided, otherwise the AI suggested improvement."""
        if self.user_edited_content and self.user_edited_content.strip():
            return self.user_edited_content
        return self.suggested_improvement


class ResumeVersion(Base):
    """Stores immutable and draft versions of a Resume (Original, AI-Generated, User-Edited, Approved)."""

    __tablename__ = "resume_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    parent_resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    version_type: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
        default="Original Uploaded",
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    section_changes: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    target_preference_ids: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    approval_status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="Draft",
        server_default="Draft",
        index=True,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
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

    parent_resume: Mapped["Resume"] = relationship(
        "Resume",
        back_populates="versions",
    )

    @property
    def creation_date(self) -> datetime:
        """Alias for created_at matching Phase 3B specification."""
        return self.created_at

