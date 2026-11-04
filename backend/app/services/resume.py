"""Service layer for Resume Manager operations."""

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import uuid
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.job_preference import JobPreference
from app.models.resume import Resume
from app.models.resume_intelligence import ResumeVersion
from app.schemas.resume import ResumeUpdate
from app.services.resume_parser import extract_resume_text, validate_resume_file_type
from app.services.storage import get_resume_storage


def _clean_original_filename(filename: str) -> str:
    """Sanitize original filename for display without path components."""
    base = Path(filename or "resume").name.strip()
    return base[:255] if base else "resume"


def _default_resume_name(original_filename: str) -> str:
    """Derive a clean human-readable resume name from the filename stem."""
    stem = Path(original_filename).stem.replace("_", " ").replace("-", " ").strip()
    return stem[:200] if stem else "Untitled Resume"


class ResumeService:
    """Encapsulates file storage, text parsing, and database operations for Resumes."""

    @staticmethod
    def list_resumes(db: Session) -> List[Resume]:
        """Return all uploaded resumes ordered by newest first."""
        stmt = select(Resume).order_by(Resume.created_at.desc())
        return list(db.scalars(stmt).all())

    @staticmethod
    def get_resume(db: Session, resume_id: UUID) -> Resume:
        """Retrieve a single resume by UUID or raise 404."""
        resume = db.get(Resume, resume_id)
        if resume is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resume with id '{resume_id}' not found.",
            )
        return resume

    @staticmethod
    def _resolve_preferences(
        db: Session, preference_ids: Optional[List[UUID]]
    ) -> List[JobPreference]:
        """Load JobPreference models matching the provided UUIDs."""
        if not preference_ids:
            return []
        unique_ids = list(dict.fromkeys(preference_ids))
        stmt = select(JobPreference).where(JobPreference.id.in_(unique_ids))
        found = list(db.scalars(stmt).all())
        found_ids = {pref.id for pref in found}
        missing = [str(pid) for pid in unique_ids if pid not in found_ids]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job preference(s) not found: {', '.join(missing)}",
            )
        return found

    @staticmethod
    def upload_resume(
        db: Session,
        filename: str,
        content: bytes,
        resume_name: Optional[str] = None,
        preference_ids: Optional[List[UUID]] = None,
        content_type: Optional[str] = None,
    ) -> Resume:
        """Validate, store, parse, and persist a newly uploaded resume."""
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes).",
            )

        if len(content) > settings.MAX_RESUME_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds the maximum allowed limit of 10 MB.",
            )

        try:
            file_format, canonical_mime, safe_ext = validate_resume_file_type(
                filename, content, content_type=content_type
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        clean_orig = _clean_original_filename(filename)
        display_name = (
            resume_name.strip()[:200]
            if resume_name and resume_name.strip()
            else _default_resume_name(clean_orig)
        )

        preferences = ResumeService._resolve_preferences(db, preference_ids)

        storage = get_resume_storage()
        stored_filename = f"{uuid.uuid4().hex}{safe_ext}"
        storage_path = storage.save(stored_filename, content)

        try:
            # 1. Record initial Uploaded -> Processing state
            resume = Resume(
                resume_name=display_name,
                original_filename=clean_orig,
                stored_filename=stored_filename,
                storage_backend=storage.backend_name,
                storage_path=storage_path,
                file_format=file_format,
                mime_type=canonical_mime,
                file_size=len(content),
                processing_status="Processing",
                processing_message="Extracting text from document...",
                requires_ocr=False,
                preferences=preferences,
            )
            db.add(resume)
            db.flush()

            # 2. Run text extraction (PyMuPDF for PDF, python-docx for DOCX)
            parse_result = extract_resume_text(content, file_format)
            resume.extracted_text = parse_result.extracted_text
            resume.processing_status = parse_result.processing_status
            resume.processing_message = parse_result.processing_message
            resume.requires_ocr = parse_result.requires_ocr
            resume.ai_status = "Not Analysed"

            if parse_result.extracted_text:
                original_version = ResumeVersion(
                    parent_resume_id=resume.id,
                    version_number=1,
                    version_type="Original Uploaded",
                    title="v1 — Original Uploaded Resume",
                    content=parse_result.extracted_text,
                    section_changes=[],
                    target_preference_ids=[str(pref.id) for pref in preferences],
                    approval_status="Original",
                )
                db.add(original_version)

            db.commit()
            db.refresh(resume)
            return resume
        except Exception:
            storage.delete(storage_path)
            db.rollback()
            raise

    @staticmethod
    def update_resume(
        db: Session, resume_id: UUID, payload: ResumeUpdate
    ) -> Resume:
        """Rename a resume and/or update its associated job preferences."""
        resume = ResumeService.get_resume(db, resume_id)

        updated_name = (
            payload.resume_name if payload.resume_name is not None else payload.name
        )
        if updated_name is not None:
            resume.resume_name = updated_name

        if payload.preference_ids is not None:
            resume.preferences = ResumeService._resolve_preferences(
                db, payload.preference_ids
            )

        resume.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(resume)
        return resume

    @staticmethod
    def get_download_path(db: Session, resume_id: UUID) -> tuple[Resume, Path]:
        """Resolve local filesystem path for downloading a stored resume."""
        resume = ResumeService.get_resume(db, resume_id)
        storage = get_resume_storage()
        local_path = storage.resolve_local_path(resume.storage_path)
        if not local_path.exists() or not local_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stored resume file was not found on disk.",
            )
        return resume, local_path

    @staticmethod
    def delete_resume(db: Session, resume_id: UUID) -> None:
        """Delete a resume from storage and PostgreSQL."""
        resume = ResumeService.get_resume(db, resume_id)
        storage_path = resume.storage_path
        db.delete(resume)
        db.commit()
        get_resume_storage().delete(storage_path)

