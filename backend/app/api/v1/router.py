"""API v1 router registry."""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    applications,
    health,
    jobs,
    orchestration,
    preferences,
    resumes,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(preferences.router, tags=["Job Preferences"])
api_router.include_router(orchestration.router, tags=["Orchestration"])
api_router.include_router(resumes.router, tags=["Resumes"])
api_router.include_router(jobs.router, tags=["Job Discovery & Matching"])
api_router.include_router(applications.router, tags=["Applications & Tracking"])
