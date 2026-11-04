"""SQLAlchemy ORM model for JobPreference."""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobPreference(Base):
    """Stores user job hunting search and matching preferences."""

    __tablename__ = "job_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    preference_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )
    job_roles: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    locations: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    location_mode: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="INDIA_ONLY",
        server_default="INDIA_ONLY",
    )
    work_mode: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    employment_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    experience_level: Mapped[str] = mapped_column(
        String(50),
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
    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="INR",
        server_default="INR",
    )
    skills: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    minimum_match_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=70,
        server_default="70",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    approved_resume_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approved_resume_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resume_versions.id", ondelete="SET NULL"),
        nullable=True,
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

    @property
    def has_approved_resume(self) -> bool:
        """Return True when a final resume version has been approved for this preference."""
        return self.approved_resume_version_id is not None

    @property
    def eligible_for_applications(self) -> bool:
        """A preference must not become eligible for automated job applications until its resume is approved."""
        return bool(self.is_active and self.approved_resume_version_id is not None)

