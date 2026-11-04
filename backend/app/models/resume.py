"""SQLAlchemy ORM model for Resume and its JobPreference associations."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.job_preference import JobPreference
    from app.models.resume_intelligence import (
        ResumeAnalysis,
        ResumeSuggestion,
        ResumeVersion,
    )


resume_preferences = Table(
    "resume_preferences",
    Base.metadata,
    Column(
        "resume_id",
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "preference_id",
        UUID(as_uuid=True),
        ForeignKey("job_preferences.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Resume(Base):
    """Stores resume metadata, extracted text, processing status, and preference associations."""

    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    resume_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    stored_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    storage_backend: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="local",
        server_default="local",
    )
    storage_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    file_format: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    mime_type: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    extracted_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    processing_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="Uploaded",
        server_default="Uploaded",
        index=True,
    )
    processing_message: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    requires_ocr: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    ai_status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="Not Analysed",
        server_default="Not Analysed",
        index=True,
    )
    approved_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
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

    preferences: Mapped[List["JobPreference"]] = relationship(
        "JobPreference",
        secondary=resume_preferences,
        lazy="selectin",
    )
    analyses: Mapped[List["ResumeAnalysis"]] = relationship(
        "ResumeAnalysis",
        back_populates="resume",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(ResumeAnalysis.created_at)",
    )
    suggestions: Mapped[List["ResumeSuggestion"]] = relationship(
        "ResumeSuggestion",
        back_populates="resume",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    versions: Mapped[List["ResumeVersion"]] = relationship(
        "ResumeVersion",
        back_populates="parent_resume",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ResumeVersion.version_number",
    )

    @property
    def name(self) -> str:
        """Alias for resume_name matching Phase 3A specification."""
        return self.resume_name

    @name.setter
    def name(self, value: str) -> None:
        self.resume_name = value

    @property
    def file_type(self) -> str:
        """Alias for file_format matching Phase 3A specification."""
        return self.file_format

    @property
    def upload_date(self) -> datetime:
        """Alias for created_at matching Phase 3A specification."""
        return self.created_at

    @property
    def overall_quality_score(self) -> Optional[int]:
        """Return the latest overall resume quality score if analysed."""
        if self.analyses:
            return self.analyses[0].overall_quality_score
        return None

    @property
    def associated_preferences(self) -> List[dict]:
        """Return lightweight preference mapping summaries."""
        return [
            {
                "id": pref.id,
                "preference_name": pref.preference_name,
                "is_active": pref.is_active,
                "approved_resume_version_id": getattr(
                    pref, "approved_resume_version_id", None
                ),
            }
            for pref in (self.preferences or [])
        ]

