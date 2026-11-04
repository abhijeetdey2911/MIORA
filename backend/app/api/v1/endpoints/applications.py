"""Application Execution, Approval, Reconciliation, Tracking & Notifications API endpoints (Agents 4, 5 & Part 12)."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.multi_agent import Application, Notification
from app.models.job_preference import JobPreference
from app.models.resume import Resume
from app.models.resume_intelligence import ResumeVersion
from app.schemas.multi_agent import (
    ApplicationApproveRequest,
    ApplicationResponse,
    ApplicationStatusHistoryResponse,
    ApplicationStatusUpdateRequest,
    NotificationResponse,
)
from app.services.agents import agent4_execution, agent5_tracking

router = APIRouter(prefix="/applications")


class ReconcileSubmissionRequest(BaseModel):
    resolution: str = Field(
        ...,
        description="Must be 'Submitted', 'Awaiting Approval', or 'Withdrawn'",
    )
    confirmation_evidence: Optional[str] = Field(default=None, max_length=1000)
    notes: Optional[str] = Field(default=None, max_length=2000)


class ApprovalActionPayload(ApplicationApproveRequest):
    approved_by_user: bool = True
    confirm_submission: bool = True


def _serialize_application(
    db: Session,
    app_record: Application,
    pref_names: Optional[dict] = None,
    version_titles: Optional[dict] = None,
) -> ApplicationResponse:
    if pref_names is None:
        pref = db.get(JobPreference, app_record.preference_id)
        pref_name = pref.preference_name if pref else "Job Preference"
    else:
        pref_name = pref_names.get(app_record.preference_id, "Job Preference")

    ver_title = None
    if app_record.resume_version_id:
        if version_titles is not None:
            ver_title = version_titles.get(app_record.resume_version_id)
        else:
            rv = db.get(ResumeVersion, app_record.resume_version_id)
            if rv:
                ver_title = rv.title
    elif app_record.resume_id:
        res = db.get(Resume, app_record.resume_id)
        if res:
            ver_title = res.resume_name

    return ApplicationResponse(
        id=app_record.id,
        preference_id=app_record.preference_id,
        preference_name=pref_name,
        preference_run_id=app_record.preference_run_id,
        discovered_job_id=app_record.discovered_job_id,
        job_match_id=app_record.job_match_id,
        route_id=app_record.route_id,
        resume_id=app_record.resume_id,
        resume_version_id=app_record.resume_version_id,
        resume_version_title=ver_title,
        company=app_record.company,
        job_title=app_record.job_title,
        route_type=app_record.route_type,
        route_target=app_record.route_target,
        status=app_record.status,
        approval_required=app_record.approval_required,
        approved_by_user=app_record.approved_by_user,
        approved_at=app_record.approved_at,
        applied_at=app_record.applied_at,
        confirmation_evidence=app_record.confirmation_evidence,
        prepared_payload=app_record.prepared_payload,
        interview_date=app_record.interview_date,
        recruiter_response_text=app_record.recruiter_response_text,
        follow_up_reminder_at=app_record.follow_up_reminder_at,
        notes=app_record.notes,
        retry_count=app_record.retry_count,
        error_message=app_record.error_message,
        idempotency_key=app_record.idempotency_key,
        status_history=[
            ApplicationStatusHistoryResponse.model_validate(h)
            for h in app_record.status_history
        ],
        created_at=app_record.created_at,
        updated_at=app_record.updated_at,
    )


@router.get(
    "",
    response_model=List[ApplicationResponse],
    status_code=status.HTTP_200_OK,
    summary="List Job Applications with Filters (Agents 4 & 5)",
)
def list_applications(
    preference_id: Optional[UUID] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    db: Session = Depends(get_db),
) -> List[ApplicationResponse]:
    stmt = select(Application).order_by(Application.created_at.desc())
    if preference_id:
        stmt = stmt.where(Application.preference_id == preference_id)
    if status_filter:
        stmt = stmt.where(Application.status == status_filter)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            Application.company.ilike(pattern)
            | Application.job_title.ilike(pattern)
            | Application.route_target.ilike(pattern)
        )

    apps = list(db.scalars(stmt.limit(limit)).all())
    pref_names = {
        p.id: p.preference_name for p in db.scalars(select(JobPreference)).all()
    }
    version_titles = {
        rv.id: rv.title for rv in db.scalars(select(ResumeVersion)).all()
    }
    return [
        _serialize_application(db, a, pref_names, version_titles) for a in apps
    ]


@router.get(
    "/notifications/list",
    response_model=List[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="List Application Updates & Automation Notifications",
)
def list_notifications(
    event_type: Optional[str] = Query(default=None),
    unread_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=300),
    db: Session = Depends(get_db),
) -> List[NotificationResponse]:
    stmt = select(Notification).order_by(Notification.created_at.desc())
    if event_type:
        stmt = stmt.where(Notification.event_type == event_type)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    rows = list(db.scalars(stmt.limit(limit)).all())
    return [NotificationResponse.model_validate(n) for n in rows]


@router.patch(
    "/notifications/{notification_id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark Notification as Read",
)
def mark_notification_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
) -> NotificationResponse:
    notif = db.get(Notification, notification_id)
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return NotificationResponse.model_validate(notif)


@router.post(
    "/notifications/read-all",
    status_code=status.HTTP_200_OK,
    summary="Mark All Notifications as Read",
)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
) -> dict:
    unread = list(
        db.scalars(
            select(Notification).where(Notification.is_read.is_(False))
        ).all()
    )
    for n in unread:
        n.is_read = True
    db.commit()
    return {"marked_read_count": len(unread)}


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Application Details & Status History",
)
def get_application(
    application_id: UUID,
    db: Session = Depends(get_db),
) -> ApplicationResponse:
    app_record = db.get(Application, application_id)
    if not app_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        )
    return _serialize_application(db, app_record)


@router.post(
    "/{application_id}/approve",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve & Execute a Prepared Application (Agent 4)",
)
def approve_application(
    application_id: UUID,
    payload: Optional[ApprovalActionPayload] = None,
    db: Session = Depends(get_db),
) -> ApplicationResponse:
    req = payload or ApprovalActionPayload()
    try:
        updated = agent4_execution.approve_and_execute_application(
            db=db,
            application_id=application_id,
            approved_by_user=req.approved_by_user,
            confirm_submission=req.confirm_submission,
            confirmation_evidence=req.confirmation_evidence,
            notes=req.notes,
        )
        return _serialize_application(db, updated)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/{application_id}/reconcile",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Reconcile a 'Submission Unconfirmed' Application (Agents 4 & 5)",
)
def reconcile_application(
    application_id: UUID,
    payload: ReconcileSubmissionRequest,
    db: Session = Depends(get_db),
) -> ApplicationResponse:
    try:
        updated = agent5_tracking.reconcile_unconfirmed_submission(
            db=db,
            application_id=application_id,
            resolution=payload.resolution,
            confirmation_evidence=payload.confirmation_evidence,
            notes=payload.notes,
        )
        return _serialize_application(db, updated)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{application_id}/status",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Application Tracking Status & Details (Agent 5)",
)
def update_application_status(
    application_id: UUID,
    payload: ApplicationStatusUpdateRequest,
    db: Session = Depends(get_db),
) -> ApplicationResponse:
    try:
        updated = agent5_tracking.update_application_status(
            db=db,
            application_id=application_id,
            new_status=payload.status,
            source="user_tracking_update",
            notes=payload.notes,
            evidence=payload.evidence,
            interview_date=payload.interview_date,
            recruiter_response_text=payload.recruiter_response_text,
            follow_up_reminder_at=payload.follow_up_reminder_at,
        )
        return _serialize_application(db, updated)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
