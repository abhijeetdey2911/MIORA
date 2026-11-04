"""Resume Manager REST API endpoints."""

import json
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.resume import ResumeResponse, ResumeUpdate
from app.schemas.resume_intelligence import (
    AIProviderStatusResponse,
    ApproveResumeVersionRequest,
    ApproveResumeVersionResponse,
    CreateUserVersionRequest,
    EnhanceResumeRequest,
    RegenerateSuggestionRequest,
    ResumeAnalysisResponse,
    ResumeSuggestionResponse,
    ResumeVersionResponse,
    SuggestionActionRequest,
    UpdateVersionRequest,
)
from app.services.ai_provider import AIProviderClient, get_ai_provider_client
from app.services.resume import ResumeService
from app.services.resume_intelligence import ResumeIntelligenceService

router = APIRouter(prefix="/resumes")


def _parse_preference_ids_form(raw: Optional[str]) -> Optional[List[UUID]]:
    """Parse optional preference_ids from multipart Form field (JSON array or comma-separated)."""
    if raw is None:
        return None
    trimmed = raw.strip()
    if not trimmed:
        return []

    try:
        if trimmed.startswith("["):
            loaded = json.loads(trimmed)
            if not isinstance(loaded, list):
                raise ValueError("preference_ids JSON must be a list.")
            return [UUID(str(item).strip()) for item in loaded if str(item).strip()]
        return [UUID(part.strip()) for part in trimmed.split(",") if part.strip()]
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid preference_ids format: {str(exc)}",
        ) from exc


@router.post(
    "",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Resume",
    description="Upload a PDF or DOCX resume (max 10 MB), extract text, and optionally associate job preferences.",
)
async def upload_resume(
    file: UploadFile = File(..., description="PDF or DOCX resume file (max 10 MB)"),
    resume_name: Optional[str] = Form(
        default=None,
        description="Optional display name for the resume",
    ),
    name: Optional[str] = Form(
        default=None,
        description="Optional display name alias for the resume",
    ),
    preference_ids: Optional[str] = Form(
        default=None,
        description="Optional JSON array or comma-separated list of JobPreference UUIDs",
    ),
    db: Session = Depends(get_db),
) -> ResumeResponse:
    """Upload and parse a resume document."""
    content = await file.read()
    parsed_pref_ids = _parse_preference_ids_form(preference_ids)
    chosen_name = resume_name if resume_name is not None else name
    return ResumeService.upload_resume(
        db=db,
        filename=file.filename or "resume",
        content=content,
        resume_name=chosen_name,
        preference_ids=parsed_pref_ids,
        content_type=file.content_type,
    )


@router.get(
    "/ai-status",
    response_model=AIProviderStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get AI Provider Configuration Status",
    description="Returns whether the backend LLM provider is configured without exposing any API keys.",
)
def get_ai_provider_status(
    ai_client: AIProviderClient = Depends(get_ai_provider_client),
) -> AIProviderStatusResponse:
    """Return safe backend AI provider configuration status."""
    return ai_client.get_status()


@router.get(
    "",
    response_model=List[ResumeResponse],
    status_code=status.HTTP_200_OK,
    summary="List Resumes",
    description="Retrieve all uploaded resumes ordered by newest first.",
)
def list_resumes(db: Session = Depends(get_db)) -> List[ResumeResponse]:
    """Retrieve all resumes."""
    return ResumeService.list_resumes(db)


@router.get(
    "/{resume_id}",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Resume Details",
    description="Retrieve a single resume including its extracted text and associated preferences.",
)
def get_resume(
    resume_id: UUID,
    db: Session = Depends(get_db),
) -> ResumeResponse:
    """Retrieve a single resume by ID."""
    return ResumeService.get_resume(db, resume_id)


@router.get(
    "/{resume_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download Resume File",
    description="Download the original PDF or DOCX resume file.",
)
def download_resume(
    resume_id: UUID,
    db: Session = Depends(get_db),
) -> FileResponse:
    """Download the stored resume file with safe content headers."""
    resume, local_path = ResumeService.get_download_path(db, resume_id)
    ext = f".{resume.file_format.lower()}"
    base_name = resume.resume_name.strip() or "resume"
    download_filename = (
        base_name if base_name.lower().endswith(ext) else f"{base_name}{ext}"
    )

    return FileResponse(
        path=str(local_path),
        media_type=resume.mime_type,
        filename=download_filename,
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.patch(
    "/{resume_id}",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Resume",
    description="Rename a resume and/or update its associated job preferences.",
)
def update_resume(
    resume_id: UUID,
    payload: ResumeUpdate,
    db: Session = Depends(get_db),
) -> ResumeResponse:
    """Rename a resume or update its preference mappings."""
    return ResumeService.update_resume(db, resume_id, payload)


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Resume",
    description="Permanently delete a resume record and its stored file.",
)
def delete_resume(
    resume_id: UUID,
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Delete a resume by ID."""
    ResumeService.delete_resume(db, resume_id)
    return {
        "message": "Resume deleted successfully.",
        "id": str(resume_id),
    }


# ==============================================================================
# Phase 3B — AI Resume Intelligence Endpoints
# ==============================================================================


@router.post(
    "/{resume_id}/analyse",
    response_model=ResumeAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyse Resume with AI",
    description=(
        "Analyse the extracted resume text using the configured AI provider, "
        "generate preference-specific evaluations, 0-100 scores, and section suggestions."
    ),
)
def analyse_resume(
    resume_id: UUID,
    db: Session = Depends(get_db),
    ai_client: AIProviderClient = Depends(get_ai_provider_client),
) -> ResumeAnalysisResponse:
    """Start and execute AI resume analysis."""
    return ResumeIntelligenceService.analyse_resume(db, resume_id, ai_client)


@router.get(
    "/{resume_id}/analysis",
    response_model=ResumeAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Latest Resume Analysis",
    description="Retrieve the latest structured AI analysis, scores, and preference evaluations for a resume.",
)
def get_resume_analysis(
    resume_id: UUID,
    db: Session = Depends(get_db),
) -> ResumeAnalysisResponse:
    """Retrieve the latest AI analysis for a resume."""
    return ResumeIntelligenceService.get_latest_analysis(db, resume_id)


@router.get(
    "/{resume_id}/suggestions",
    response_model=List[ResumeSuggestionResponse],
    status_code=status.HTTP_200_OK,
    summary="List Resume Improvement Suggestions",
    description="Retrieve all actionable section improvement suggestions for a resume.",
)
def list_resume_suggestions(
    resume_id: UUID,
    db: Session = Depends(get_db),
) -> List[ResumeSuggestionResponse]:
    """Retrieve all suggestions for a resume."""
    return ResumeIntelligenceService.list_suggestions(db, resume_id)


@router.patch(
    "/{resume_id}/suggestions/{suggestion_id}",
    response_model=ResumeSuggestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept, Reject, or Edit Suggestion",
    description="Accept, reject, or save user edits on a resume section suggestion.",
)
def update_resume_suggestion(
    resume_id: UUID,
    suggestion_id: UUID,
    payload: SuggestionActionRequest,
    db: Session = Depends(get_db),
) -> ResumeSuggestionResponse:
    """Update a suggestion's status or user-edited text."""
    return ResumeIntelligenceService.update_suggestion(
        db, resume_id, suggestion_id, payload
    )


@router.post(
    "/{resume_id}/suggestions/{suggestion_id}/regenerate",
    response_model=ResumeSuggestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Regenerate Section Suggestion",
    description="Ask the AI provider to regenerate an alternative suggestion for this resume section.",
)
def regenerate_resume_suggestion(
    resume_id: UUID,
    suggestion_id: UUID,
    payload: Optional[RegenerateSuggestionRequest] = Body(default=None),
    db: Session = Depends(get_db),
    ai_client: AIProviderClient = Depends(get_ai_provider_client),
) -> ResumeSuggestionResponse:
    """Regenerate a single section suggestion."""
    return ResumeIntelligenceService.regenerate_suggestion(
        db, resume_id, suggestion_id, payload, ai_client
    )


@router.post(
    "/{resume_id}/enhance",
    response_model=ResumeVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Improve My Resume (Generate AI Draft)",
    description=(
        "Generate a fact-preserving AI-enhanced resume draft with side-by-side "
        "Original vs AI Suggested section comparisons."
    ),
)
def enhance_resume(
    resume_id: UUID,
    payload: Optional[EnhanceResumeRequest] = Body(default=None),
    db: Session = Depends(get_db),
    ai_client: AIProviderClient = Depends(get_ai_provider_client),
) -> ResumeVersionResponse:
    """Generate an AI-enhanced resume draft version."""
    return ResumeIntelligenceService.enhance_resume_draft(
        db, resume_id, payload, ai_client
    )


@router.get(
    "/{resume_id}/versions",
    response_model=List[ResumeVersionResponse],
    status_code=status.HTTP_200_OK,
    summary="List Resume Versions",
    description="Retrieve all versions of a resume (Original Uploaded, AI-Generated Draft, User-Edited, Approved).",
)
def list_resume_versions(
    resume_id: UUID,
    db: Session = Depends(get_db),
) -> List[ResumeVersionResponse]:
    """List all versions of a resume."""
    return ResumeIntelligenceService.list_versions(db, resume_id)


@router.post(
    "/{resume_id}/versions",
    response_model=ResumeVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create User-Edited Resume Version",
    description="Save a new User-Edited resume version without overwriting the original uploaded resume.",
)
def create_user_resume_version(
    resume_id: UUID,
    payload: CreateUserVersionRequest,
    db: Session = Depends(get_db),
) -> ResumeVersionResponse:
    """Create a user-edited version of a resume."""
    return ResumeIntelligenceService.create_user_version(db, resume_id, payload)


@router.patch(
    "/{resume_id}/versions/{version_id}",
    response_model=ResumeVersionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Draft Resume Version",
    description="Edit an existing draft version before approving it (never overwrites v1 Original Uploaded).",
)
def update_resume_version(
    resume_id: UUID,
    version_id: UUID,
    payload: UpdateVersionRequest,
    db: Session = Depends(get_db),
) -> ResumeVersionResponse:
    """Update a draft resume version."""
    return ResumeIntelligenceService.update_version(db, resume_id, version_id, payload)


@router.post(
    "/{resume_id}/versions/{version_id}/approve",
    response_model=ApproveResumeVersionResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve Final Resume Version",
    description=(
        "Approve a resume version and link it to the relevant job preferences so "
        "those preferences become eligible for automated job applications."
    ),
)
def approve_resume_version(
    resume_id: UUID,
    version_id: UUID,
    payload: Optional[ApproveResumeVersionRequest] = Body(default=None),
    db: Session = Depends(get_db),
) -> ApproveResumeVersionResponse:
    """Approve a final resume version."""
    return ResumeIntelligenceService.approve_version(db, resume_id, version_id, payload)

