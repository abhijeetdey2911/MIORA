"""Job Discovery, Matching, and Application Routes API endpoints (Agents 1, 2, 3)."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.multi_agent import (
    ApplicationRoute,
    DiscoveredJob,
    JobMatch,
    JobSource,
)
from app.models.job_preference import JobPreference
from app.schemas.multi_agent import (
    ApplicationRouteResponse,
    DiscoveredJobResponse,
    JobMatchResponse,
    JobSourceResponse,
)
from app.services.agents import agent1_discovery

router = APIRouter(prefix="/jobs")


class ToggleSourceRequest(BaseModel):
    is_enabled: bool


class ToggleShortlistRequest(BaseModel):
    shortlisted: bool


@router.get(
    "/sources",
    response_model=List[JobSourceResponse],
    status_code=status.HTTP_200_OK,
    summary="List Job Discovery Source Adapters",
)
def list_job_sources(
    db: Session = Depends(get_db),
) -> List[JobSourceResponse]:
    sources = agent1_discovery.ensure_default_sources(db)
    return [JobSourceResponse.model_validate(s) for s in sources]


@router.patch(
    "/sources/{source_id}",
    response_model=JobSourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Enable or Disable a Job Discovery Source Adapter",
)
def toggle_job_source(
    source_id: UUID,
    payload: ToggleSourceRequest,
    db: Session = Depends(get_db),
) -> JobSourceResponse:
    src = db.get(JobSource, source_id)
    if not src:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job source not found.",
        )
    src.is_enabled = payload.is_enabled
    db.commit()
    db.refresh(src)
    return JobSourceResponse.model_validate(src)


@router.get(
    "/discovered",
    response_model=List[DiscoveredJobResponse],
    status_code=status.HTTP_200_OK,
    summary="List Deduplicated Discovered Jobs (Agent 1)",
)
def list_discovered_jobs(
    search: Optional[str] = Query(default=None),
    work_mode: Optional[str] = Query(default=None),
    source_name: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    db: Session = Depends(get_db),
) -> List[DiscoveredJobResponse]:
    stmt = select(DiscoveredJob).order_by(DiscoveredJob.discovered_at.desc())
    if work_mode:
        stmt = stmt.where(DiscoveredJob.work_mode.ilike(f"%{work_mode}%"))
    if source_name:
        stmt = stmt.where(DiscoveredJob.source_name == source_name)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            DiscoveredJob.title.ilike(pattern)
            | DiscoveredJob.company.ilike(pattern)
            | DiscoveredJob.location.ilike(pattern)
        )
    jobs = list(db.scalars(stmt.limit(limit)).all())
    return [DiscoveredJobResponse.model_validate(j) for j in jobs]


@router.get(
    "/matches",
    response_model=List[JobMatchResponse],
    status_code=status.HTTP_200_OK,
    summary="List Preference-Isolated Job Matches & Routes (Agents 2 & 3)",
)
def list_job_matches(
    preference_id: Optional[UUID] = Query(default=None),
    shortlisted_only: bool = Query(default=False),
    min_score: Optional[int] = Query(default=None, ge=0, le=100),
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    db: Session = Depends(get_db),
) -> List[JobMatchResponse]:
    stmt = select(JobMatch).order_by(
        JobMatch.match_score.desc(), JobMatch.created_at.desc()
    )
    if preference_id:
        stmt = stmt.where(JobMatch.preference_id == preference_id)
    if shortlisted_only:
        stmt = stmt.where(JobMatch.shortlisted.is_(True))
    if min_score is not None:
        stmt = stmt.where(JobMatch.match_score >= min_score)

    matches = list(db.scalars(stmt.limit(limit)).all())
    pref_names = {
        p.id: p.preference_name for p in db.scalars(select(JobPreference)).all()
    }

    responses: List[JobMatchResponse] = []
    search_lower = search.strip().lower() if search else None

    for m in matches:
        job = m.discovered_job
        if not job:
            continue
        if search_lower:
            hay = f"{job.title} {job.company} {job.location or ''}".lower()
            if search_lower not in hay:
                continue

        routes = list(
            db.scalars(
                select(ApplicationRoute).where(
                    ApplicationRoute.discovered_job_id == job.id,
                    ApplicationRoute.preference_id == m.preference_id,
                )
            ).all()
        )
        responses.append(
            JobMatchResponse(
                id=m.id,
                preference_id=m.preference_id,
                preference_name=pref_names.get(m.preference_id, "Job Preference"),
                preference_run_id=m.preference_run_id,
                discovered_job_id=m.discovered_job_id,
                resume_version_id=m.resume_version_id,
                match_score=m.match_score,
                threshold_used=m.threshold_used,
                is_matching=m.is_matching,
                shortlisted=m.shortlisted,
                skills_matched=m.skills_matched,
                relevant_experience=m.relevant_experience,
                missing_or_unverified_requirements=m.missing_or_unverified_requirements,
                reasons_for_matching=m.reasons_for_matching,
                reasons_for_rejection=m.reasons_for_rejection,
                evaluation_method=m.evaluation_method,
                discovered_job=DiscoveredJobResponse.model_validate(job),
                routes=[ApplicationRouteResponse.model_validate(r) for r in routes],
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
        )
    return responses


@router.patch(
    "/matches/{match_id}/shortlist",
    response_model=JobMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Toggle Shortlist Status on a Job Match",
)
def toggle_match_shortlist(
    match_id: UUID,
    payload: ToggleShortlistRequest,
    db: Session = Depends(get_db),
) -> JobMatchResponse:
    m = db.get(JobMatch, match_id)
    if not m:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job match not found.",
        )
    m.shortlisted = payload.shortlisted
    if payload.shortlisted:
        m.is_matching = True
    db.commit()
    db.refresh(m)

    pref = db.get(JobPreference, m.preference_id)
    routes = list(
        db.scalars(
            select(ApplicationRoute).where(
                ApplicationRoute.discovered_job_id == m.discovered_job_id,
                ApplicationRoute.preference_id == m.preference_id,
            )
        ).all()
    )
    return JobMatchResponse(
        id=m.id,
        preference_id=m.preference_id,
        preference_name=pref.preference_name if pref else "Job Preference",
        preference_run_id=m.preference_run_id,
        discovered_job_id=m.discovered_job_id,
        resume_version_id=m.resume_version_id,
        match_score=m.match_score,
        threshold_used=m.threshold_used,
        is_matching=m.is_matching,
        shortlisted=m.shortlisted,
        skills_matched=m.skills_matched,
        relevant_experience=m.relevant_experience,
        missing_or_unverified_requirements=m.missing_or_unverified_requirements,
        reasons_for_matching=m.reasons_for_matching,
        reasons_for_rejection=m.reasons_for_rejection,
        evaluation_method=m.evaluation_method,
        discovered_job=DiscoveredJobResponse.model_validate(m.discovered_job),
        routes=[ApplicationRouteResponse.model_validate(r) for r in routes],
        created_at=m.created_at,
        updated_at=m.updated_at,
    )
