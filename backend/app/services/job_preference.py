"""Service layer for JobPreference CRUD operations."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_preference import JobPreference
from app.schemas.job_preference import (
    JobPreferenceCreate,
    JobPreferenceStatusUpdate,
    JobPreferenceUpdate,
)


class JobPreferenceService:
    """Encapsulates database operations for JobPreference entities."""

    @staticmethod
    def list_preferences(db: Session) -> List[JobPreference]:
        """Return all job preferences ordered by newest first."""
        stmt = select(JobPreference).order_by(JobPreference.created_at.desc())
        return list(db.scalars(stmt).all())

    @staticmethod
    def get_preference(db: Session, preference_id: UUID) -> JobPreference:
        """Return a single job preference by ID or raise 404."""
        preference = db.get(JobPreference, preference_id)
        if preference is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job preference with id '{preference_id}' not found.",
            )
        return preference

    @staticmethod
    def create_preference(
        db: Session, payload: JobPreferenceCreate
    ) -> JobPreference:
        """Create and persist a new job preference."""
        preference = JobPreference(**payload.model_dump())
        db.add(preference)
        db.commit()
        db.refresh(preference)
        return preference

    @staticmethod
    def update_preference(
        db: Session, preference_id: UUID, payload: JobPreferenceUpdate
    ) -> JobPreference:
        """Update an existing job preference."""
        preference = JobPreferenceService.get_preference(db, preference_id)
        update_data = payload.model_dump()
        for field, value in update_data.items():
            setattr(preference, field, value)
        preference.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(preference)
        return preference

    @staticmethod
    def update_preference_status(
        db: Session,
        preference_id: UUID,
        payload: Optional[JobPreferenceStatusUpdate] = None,
    ) -> JobPreference:
        """Activate or pause a job preference (toggles if is_active is omitted)."""
        preference = JobPreferenceService.get_preference(db, preference_id)
        if payload is not None and payload.is_active is not None:
            preference.is_active = payload.is_active
        else:
            preference.is_active = not preference.is_active
        preference.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(preference)
        return preference

    @staticmethod
    def delete_preference(db: Session, preference_id: UUID) -> None:
        """Delete an existing job preference."""
        preference = JobPreferenceService.get_preference(db, preference_id)
        db.delete(preference)
        db.commit()

