"""Service layer for Phase 3B AI Resume Intelligence:
- AI Resume Analysis & Preference-Based Evaluation
- Actionable Section Suggestions (Accept / Reject / Edit / Regenerate)
- AI Resume Enhancement ('Improve My Resume' Draft Generation)
- Resume Version Management (Original, AI-Generated Draft, User-Edited, Approved)
- User Approval Workflow & JobPreference Eligibility Linking
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.job_preference import JobPreference
from app.models.resume import Resume
from app.models.resume_intelligence import (
    ResumeAnalysis,
    ResumeSuggestion,
    ResumeVersion,
)
from app.schemas.resume_intelligence import (
    ApproveResumeVersionRequest,
    ApproveResumeVersionResponse,
    CreateUserVersionRequest,
    EnhanceResumeRequest,
    RegenerateSuggestionRequest,
    ResumeVersionResponse,
    SuggestionActionRequest,
    UpdateVersionRequest,
)
from app.services.ai_provider import AIProviderClient
from app.services.resume import ResumeService


def _serialize_preferences_for_ai(preferences: List[JobPreference]) -> List[Dict[str, Any]]:
    """Convert associated JobPreference ORM objects into clean dictionaries for LLM prompts."""
    return [
        {
            "preference_id": str(pref.id),
            "preference_name": pref.preference_name,
            "target_roles": pref.job_roles or [],
            "skills": pref.skills or [],
            "experience_level": pref.experience_level,
            "work_mode": pref.work_mode,
            "employment_type": pref.employment_type,
            "locations": pref.locations or [],
            "minimum_match_score": pref.minimum_match_score,
        }
        for pref in preferences
    ]


class ResumeIntelligenceService:
    """Encapsulates Phase 3B AI analysis, enhancement, versioning, and approval operations."""

    @staticmethod
    def ensure_original_version(db: Session, resume: Resume) -> Optional[ResumeVersion]:
        """Guarantee that version 1 ('Original Uploaded') exists if the resume has extracted text.

        Never overwrites an existing original version.
        """
        if not resume.extracted_text:
            return None

        stmt = (
            select(ResumeVersion)
            .where(
                ResumeVersion.parent_resume_id == resume.id,
                ResumeVersion.version_number == 1,
            )
            .limit(1)
        )
        existing_v1 = db.scalars(stmt).first()
        if existing_v1 is not None:
            return existing_v1

        original_version = ResumeVersion(
            parent_resume_id=resume.id,
            version_number=1,
            version_type="Original Uploaded",
            title="v1 — Original Uploaded Resume",
            content=resume.extracted_text,
            section_changes=[],
            target_preference_ids=[str(pref.id) for pref in (resume.preferences or [])],
            approval_status="Original",
        )
        db.add(original_version)
        db.commit()
        db.refresh(original_version)
        return original_version

    @staticmethod
    def _next_version_number(db: Session, resume_id: UUID) -> int:
        """Compute the next sequential version_number for a parent resume."""
        stmt = select(func.max(ResumeVersion.version_number)).where(
            ResumeVersion.parent_resume_id == resume_id
        )
        current_max = db.scalar(stmt)
        return (current_max or 0) + 1

    # ==========================================================================
    # 1–4. AI Resume Analysis, Preference-Based Analysis, Scoring & Suggestions
    # ==========================================================================

    @staticmethod
    def analyse_resume(
        db: Session,
        resume_id: UUID,
        ai_client: AIProviderClient,
    ) -> ResumeAnalysis:
        """Run AI analysis on a processed resume and store structured results & suggestions."""
        resume = ResumeService.get_resume(db, resume_id)

        if not resume.extracted_text or not resume.extracted_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "This resume does not contain extractable text to analyse. "
                    "Please upload a machine-readable PDF or DOCX resume."
                ),
            )

        # Prevent duplicate concurrent analysis requests
        if resume.ai_status == "Analysing":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Resume analysis is already in progress for this resume.",
            )

        # Fail fast with HTTP 503 if no API key is configured (never substitute fake data)
        ai_client.require_configured()

        ResumeIntelligenceService.ensure_original_version(db, resume)

        previous_status = resume.ai_status or "Not Analysed"
        resume.ai_status = "Analysing"
        resume.updated_at = datetime.now(timezone.utc)
        db.commit()

        try:
            preferences_context = _serialize_preferences_for_ai(resume.preferences or [])
            ai_payload = ai_client.analyse_resume(
                resume_text=resume.extracted_text,
                preferences_context=preferences_context,
            )

            # Remove previous un-approved analyses/suggestions on re-analysis to keep state clean
            old_analyses = list(
                db.scalars(
                    select(ResumeAnalysis).where(ResumeAnalysis.resume_id == resume.id)
                ).all()
            )
            for old in old_analyses:
                db.delete(old)
            db.flush()

            model_used = getattr(ai_payload, "_model_used", ai_client.model)
            analysis = ResumeAnalysis(
                resume_id=resume.id,
                provider=ai_client.provider,
                model_name=model_used,
                candidate_profile=ai_payload.candidate_profile.model_dump(),
                education=[item.model_dump() for item in ai_payload.education],
                technical_skills=ai_payload.technical_skills,
                soft_skills=ai_payload.soft_skills,
                work_experience=[
                    item.model_dump() for item in ai_payload.work_experience
                ],
                internships=[item.model_dump() for item in ai_payload.internships],
                projects=[item.model_dump() for item in ai_payload.projects],
                certifications=ai_payload.certifications,
                achievements=ai_payload.achievements,
                tools_and_technologies=ai_payload.tools_and_technologies,
                preference_analyses=[
                    item.model_dump() for item in ai_payload.preference_analyses
                ],
                overall_quality_score=ai_payload.overall_quality_score,
                preference_relevance_score=ai_payload.preference_relevance_score,
                skills_alignment_score=ai_payload.skills_alignment_score,
                experience_alignment_score=ai_payload.experience_alignment_score,
                project_relevance_score=ai_payload.project_relevance_score,
                ats_readability_score=ai_payload.ats_readability_score,
                score_explanations=ai_payload.score_explanations.model_dump(),
                overall_strengths=ai_payload.overall_strengths,
                overall_weaknesses=ai_payload.overall_weaknesses,
                missing_information_questions=ai_payload.missing_information_questions,
            )
            db.add(analysis)
            db.flush()

            for sug in ai_payload.suggestions:
                suggestion_row = ResumeSuggestion(
                    resume_id=resume.id,
                    analysis_id=analysis.id,
                    section_name=sug.section_name,
                    current_content=sug.current_content,
                    suggested_improvement=sug.suggested_improvement,
                    reason=sug.reason,
                    priority=sug.priority,
                    clarifying_question=sug.clarifying_question,
                    status="Pending",
                )
                db.add(suggestion_row)

            # Transition status to Analysis Complete (unless already Approved)
            resume.ai_status = (
                "Approved" if previous_status == "Approved" else "Analysis Complete"
            )
            resume.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(analysis)
            return analysis

        except Exception:
            db.rollback()
            # Restore prior status so resume is never stuck in 'Analysing'
            resume_refreshed = db.get(Resume, resume_id)
            if resume_refreshed is not None:
                resume_refreshed.ai_status = (
                    previous_status
                    if previous_status != "Analysing"
                    else "Not Analysed"
                )
                db.commit()
            raise

    @staticmethod
    def get_latest_analysis(db: Session, resume_id: UUID) -> ResumeAnalysis:
        """Retrieve the most recent ResumeAnalysis for a resume or raise 404."""
        ResumeService.get_resume(db, resume_id)
        stmt = (
            select(ResumeAnalysis)
            .where(ResumeAnalysis.resume_id == resume_id)
            .order_by(ResumeAnalysis.created_at.desc())
            .limit(1)
        )
        analysis = db.scalars(stmt).first()
        if analysis is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No AI analysis found for this resume yet. Click 'Analyse Resume' to start.",
            )
        return analysis

    @staticmethod
    def list_suggestions(db: Session, resume_id: UUID) -> List[ResumeSuggestion]:
        """List all improvement suggestions for a resume."""
        ResumeService.get_resume(db, resume_id)
        stmt = (
            select(ResumeSuggestion)
            .where(ResumeSuggestion.resume_id == resume_id)
            .order_by(ResumeSuggestion.created_at.asc())
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def update_suggestion(
        db: Session,
        resume_id: UUID,
        suggestion_id: UUID,
        payload: SuggestionActionRequest,
    ) -> ResumeSuggestion:
        """Accept, reject, or save user edits on a resume suggestion."""
        ResumeService.get_resume(db, resume_id)
        suggestion = db.get(ResumeSuggestion, suggestion_id)
        if suggestion is None or suggestion.resume_id != resume_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Suggestion '{suggestion_id}' not found for this resume.",
            )

        if payload.user_edited_content is not None:
            suggestion.user_edited_content = payload.user_edited_content
            if payload.status is None:
                suggestion.status = "Accepted"

        if payload.status is not None:
            suggestion.status = payload.status

        suggestion.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(suggestion)
        return suggestion

    @staticmethod
    def regenerate_suggestion(
        db: Session,
        resume_id: UUID,
        suggestion_id: UUID,
        payload: Optional[RegenerateSuggestionRequest],
        ai_client: AIProviderClient,
    ) -> ResumeSuggestion:
        """Regenerate a single section suggestion using the AI provider."""
        resume = ResumeService.get_resume(db, resume_id)
        suggestion = db.get(ResumeSuggestion, suggestion_id)
        if suggestion is None or suggestion.resume_id != resume_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Suggestion '{suggestion_id}' not found for this resume.",
            )

        if not resume.extracted_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resume has no extracted text available.",
            )

        ai_client.require_configured()

        preferences_context = _serialize_preferences_for_ai(resume.preferences or [])
        regenerated = ai_client.regenerate_suggestion(
            resume_text=resume.extracted_text,
            section_name=suggestion.section_name,
            current_content=suggestion.current_content,
            previous_suggestion=suggestion.effective_content,
            user_instruction=payload.user_instruction if payload else None,
            preferences_context=preferences_context,
        )

        suggestion.suggested_improvement = regenerated.suggested_improvement
        suggestion.user_edited_content = None
        suggestion.reason = regenerated.reason
        suggestion.priority = regenerated.priority
        suggestion.clarifying_question = regenerated.clarifying_question
        suggestion.status = "Pending"
        suggestion.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(suggestion)
        return suggestion

    # ==========================================================================
    # 5 & 6. AI Resume Enhancement ('Improve My Resume') & Version Management
    # ==========================================================================

    @staticmethod
    def enhance_resume_draft(
        db: Session,
        resume_id: UUID,
        payload: Optional[EnhanceResumeRequest],
        ai_client: AIProviderClient,
    ) -> ResumeVersion:
        """Generate an AI-enhanced resume draft version with side-by-side section comparisons."""
        resume = ResumeService.get_resume(db, resume_id)
        if not resume.extracted_text or not resume.extracted_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resume does not have extracted text to enhance.",
            )

        ai_client.require_configured()
        ResumeIntelligenceService.ensure_original_version(db, resume)

        req = payload or EnhanceResumeRequest()

        # Filter target preferences if requested, otherwise use all associated preferences
        target_prefs = list(resume.preferences or [])
        if req.target_preference_ids:
            requested_set = set(req.target_preference_ids)
            target_prefs = [p for p in target_prefs if p.id in requested_set]

        preferences_context = _serialize_preferences_for_ai(target_prefs)

        accepted_suggestions_data: List[Dict[str, Any]] = []
        if req.apply_accepted_suggestions:
            suggestions = ResumeIntelligenceService.list_suggestions(db, resume.id)
            for sug in suggestions:
                if sug.status == "Accepted":
                    accepted_suggestions_data.append(
                        {
                            "section_name": sug.section_name,
                            "current_content": sug.current_content,
                            "accepted_improvement": sug.effective_content,
                        }
                    )

        enhanced = ai_client.enhance_resume(
            resume_text=resume.extracted_text,
            sections=req.sections,
            preferences_context=preferences_context,
            accepted_suggestions=accepted_suggestions_data,
        )

        next_num = ResumeIntelligenceService._next_version_number(db, resume.id)
        version_title = (
            f"v{next_num} — {enhanced.title.strip()}"
            if not enhanced.title.strip().lower().startswith(f"v{next_num}")
            else enhanced.title.strip()
        )

        draft_version = ResumeVersion(
            parent_resume_id=resume.id,
            version_number=next_num,
            version_type="AI-Generated Draft",
            title=version_title[:200],
            content=enhanced.improved_full_content,
            section_changes=[item.model_dump() for item in enhanced.section_changes],
            target_preference_ids=[str(pref.id) for pref in target_prefs],
            approval_status="Awaiting Approval",
        )
        db.add(draft_version)

        # Record Draft Generated -> Awaiting Approval status
        resume.ai_status = "Awaiting Approval"
        resume.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(draft_version)
        return draft_version

    @staticmethod
    def list_versions(db: Session, resume_id: UUID) -> List[ResumeVersion]:
        """List all versions of a resume ordered by version_number ascending."""
        resume = ResumeService.get_resume(db, resume_id)
        ResumeIntelligenceService.ensure_original_version(db, resume)

        stmt = (
            select(ResumeVersion)
            .where(ResumeVersion.parent_resume_id == resume_id)
            .order_by(ResumeVersion.version_number.asc())
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def create_user_version(
        db: Session,
        resume_id: UUID,
        payload: CreateUserVersionRequest,
    ) -> ResumeVersion:
        """Create a new User-Edited Version without overwriting the original uploaded resume."""
        resume = ResumeService.get_resume(db, resume_id)
        ResumeIntelligenceService.ensure_original_version(db, resume)

        next_num = ResumeIntelligenceService._next_version_number(db, resume.id)
        title = (
            payload.title.strip()[:200]
            if payload.title and payload.title.strip()
            else f"v{next_num} — User-Edited Version"
        )
        target_pref_ids = (
            [str(pid) for pid in payload.target_preference_ids]
            if payload.target_preference_ids is not None
            else [str(pref.id) for pref in (resume.preferences or [])]
        )

        user_version = ResumeVersion(
            parent_resume_id=resume.id,
            version_number=next_num,
            version_type="User-Edited Version",
            title=title,
            content=payload.content,
            section_changes=(
                [item.model_dump() for item in payload.section_changes]
                if payload.section_changes
                else []
            ),
            target_preference_ids=target_pref_ids,
            approval_status="Awaiting Approval",
        )
        db.add(user_version)

        resume.ai_status = "Awaiting Approval"
        resume.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(user_version)
        return user_version

    @staticmethod
    def update_version(
        db: Session,
        resume_id: UUID,
        version_id: UUID,
        payload: UpdateVersionRequest,
    ) -> ResumeVersion:
        """Edit an existing draft version (never overwrites v1 Original Uploaded)."""
        resume = ResumeService.get_resume(db, resume_id)
        version = db.get(ResumeVersion, version_id)
        if version is None or version.parent_resume_id != resume_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resume version '{version_id}' not found.",
            )

        if version.version_number == 1 or version.version_type == "Original Uploaded":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "The original uploaded resume version (v1) is immutable and cannot be "
                    "overwritten. Create a new User-Edited Version instead."
                ),
            )

        if payload.title is not None and payload.title.strip():
            version.title = payload.title.strip()[:200]
        if payload.content is not None:
            version.content = payload.content
        if payload.section_changes is not None:
            version.section_changes = [
                item.model_dump() for item in payload.section_changes
            ]

        version.version_type = "User-Edited Version"
        version.approval_status = "Awaiting Approval"
        version.updated_at = datetime.now(timezone.utc)

        resume.ai_status = "Awaiting Approval"
        resume.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(version)
        return version

    # ==========================================================================
    # 7. Approval System & Job Preference Eligibility Linking
    # ==========================================================================

    @staticmethod
    def approve_version(
        db: Session,
        resume_id: UUID,
        version_id: UUID,
        payload: Optional[ApproveResumeVersionRequest] = None,
    ) -> ApproveResumeVersionResponse:
        """Approve a specific resume version and link it to the relevant job preferences.

        Only user-approved resume versions make associated job preferences eligible
        for future automated job applications.
        """
        resume = ResumeService.get_resume(db, resume_id)
        version = db.get(ResumeVersion, version_id)
        if version is None or version.parent_resume_id != resume_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resume version '{version_id}' not found for this resume.",
            )

        now = datetime.now(timezone.utc)

        # Mark any previously approved versions of this resume as Superseded
        all_versions = ResumeIntelligenceService.list_versions(db, resume_id)
        for v in all_versions:
            if v.id != version.id and v.approval_status == "Approved":
                v.approval_status = "Superseded"
                v.updated_at = now

        version.approval_status = "Approved"
        version.approved_at = now
        version.updated_at = now

        resume.ai_status = "Approved"
        resume.approved_version_id = version.id
        resume.updated_at = now

        # Determine which JobPreferences to link to this approved resume version
        requested_pref_ids = (
            payload.preference_ids
            if payload and payload.preference_ids is not None
            else [pref.id for pref in (resume.preferences or [])]
        )

        linked_pref_ids: List[UUID] = []
        if requested_pref_ids:
            unique_ids = list(dict.fromkeys(requested_pref_ids))
            prefs = list(
                db.scalars(
                    select(JobPreference).where(JobPreference.id.in_(unique_ids))
                ).all()
            )
            associated_ids = {p.id for p in (resume.preferences or [])}
            for pref in prefs:
                pref.approved_resume_id = resume.id
                pref.approved_resume_version_id = version.id
                pref.updated_at = now
                linked_pref_ids.append(pref.id)
                if pref.id not in associated_ids:
                    resume.preferences.append(pref)

        version.target_preference_ids = [str(pid) for pid in linked_pref_ids]

        db.commit()
        db.refresh(version)
        db.refresh(resume)

        return ApproveResumeVersionResponse(
            resume_id=resume.id,
            ai_status="Approved",
            approved_version=ResumeVersionResponse.model_validate(version),
            linked_preference_ids=linked_pref_ids,
            message=(
                f"Approved '{version.title}' and linked it to "
                f"{len(linked_pref_ids)} job {'preference' if len(linked_pref_ids) == 1 else 'preferences'}."
            ),
        )

