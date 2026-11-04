"""Job Preferences REST API endpoints."""

from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.job_preference import (
    JobPreferenceCreate,
    JobPreferenceResponse,
    JobPreferenceStatusUpdate,
    JobPreferenceUpdate,
)
from app.services.job_preference import JobPreferenceService

router = APIRouter(prefix="/preferences")


@router.get(
    "",
    response_model=List[JobPreferenceResponse],
    status_code=status.HTTP_200_OK,
    summary="List Job Preferences",
    description="Retrieve all saved job preference profiles ordered by newest first.",
)
def list_preferences(db: Session = Depends(get_db)) -> List[JobPreferenceResponse]:
    """Retrieve all job preferences."""
    return JobPreferenceService.list_preferences(db)


@router.get(
    "/{preference_id}",
    response_model=JobPreferenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Job Preference",
    description="Retrieve a single job preference profile by its UUID.",
)
def get_preference(
    preference_id: UUID,
    db: Session = Depends(get_db),
) -> JobPreferenceResponse:
    """Retrieve a single job preference by ID."""
    return JobPreferenceService.get_preference(db, preference_id)


@router.post(
    "",
    response_model=JobPreferenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Job Preference",
    description="Create a new job preference profile.",
)
def create_preference(
    payload: JobPreferenceCreate,
    db: Session = Depends(get_db),
) -> JobPreferenceResponse:
    """Create a new job preference."""
    return JobPreferenceService.create_preference(db, payload)


@router.put(
    "/{preference_id}",
    response_model=JobPreferenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Job Preference",
    description="Update an existing job preference profile.",
)
def update_preference(
    preference_id: UUID,
    payload: JobPreferenceUpdate,
    db: Session = Depends(get_db),
) -> JobPreferenceResponse:
    """Update an existing job preference."""
    return JobPreferenceService.update_preference(db, preference_id, payload)


@router.patch(
    "/{preference_id}/status",
    response_model=JobPreferenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate or Pause Job Preference",
    description="Set or toggle the active/paused status of a job preference profile.",
)
def update_preference_status(
    preference_id: UUID,
    payload: Optional[JobPreferenceStatusUpdate] = Body(default=None),
    db: Session = Depends(get_db),
) -> JobPreferenceResponse:
    """Activate or pause a job preference."""
    return JobPreferenceService.update_preference_status(db, preference_id, payload)


@router.delete(
    "/{preference_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Job Preference",
    description="Permanently delete a job preference profile.",
)
def delete_preference(
    preference_id: UUID,
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Delete a job preference by ID."""
    JobPreferenceService.delete_preference(db, preference_id)
    return {
        "message": "Job preference deleted successfully.",
        "id": str(preference_id),
    }

