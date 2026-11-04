"""Pydantic schemas for Phase 3B AI Resume Intelligence:
- Structured LLM response validation schemas (Analysis, Suggestions, Draft Enhancement).
- REST API request and response schemas for analysis, suggestions, versions, and approval.
"""

from datetime import datetime
from typing import Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ResumeAIStatus = Literal[
    "Not Analysed",
    "Analysing",
    "Analysis Complete",
    "Draft Generated",
    "Awaiting Approval",
    "Approved",
]

SuggestionPriority = Literal["High", "Medium", "Low"]
SuggestionStatus = Literal["Pending", "Accepted", "Rejected"]

VersionType = Literal[
    "Original Uploaded",
    "AI-Generated Draft",
    "User-Edited Version",
    "Approved Version",
]

VersionApprovalStatus = Literal[
    "Original",
    "Draft",
    "Awaiting Approval",
    "Approved",
    "Superseded",
]

SCORE_ESTIMATE_DISCLAIMER = (
    "Scores are AI-generated estimates (0–100) for guidance only and are not "
    "guarantees of ATS performance or interview success."
)

MISSING_KEYWORDS_NOTE = (
    "Missing keywords indicate terms not explicitly found in the resume text and "
    "are not proof that the candidate lacks the underlying skill."
)


def _clamp_score(value: int) -> int:
    """Clamp integer score to [0, 100]."""
    return max(0, min(100, int(value)))


# ==============================================================================
# 1. Structured Candidate Extraction & Evaluation Schemas
# ==============================================================================


class CandidateProfileSummary(BaseModel):
    """Extracted candidate profile overview."""

    full_name: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    years_of_experience: Optional[str] = None
    contact_channels_present: List[str] = Field(default_factory=list)
    summary_evaluation: str = ""


class EducationItem(BaseModel):
    """Extracted education entry."""

    degree: str
    institution: Optional[str] = None
    graduation_year: Optional[str] = None
    details: Optional[str] = None


class ExperienceItem(BaseModel):
    """Extracted work experience or internship entry."""

    role: str
    company: Optional[str] = None
    duration: Optional[str] = None
    key_contributions: List[str] = Field(default_factory=list)


class ProjectItem(BaseModel):
    """Extracted project entry."""

    title: str
    technologies: List[str] = Field(default_factory=list)
    summary: str = ""
    impact: Optional[str] = None


# ==============================================================================
# 2. Preference-Based Analysis Schema
# ==============================================================================


class PreferenceAnalysisItem(BaseModel):
    """Separate evaluation of the resume against a specific JobPreference."""

    preference_id: str
    preference_name: str
    target_roles: List[str] = Field(default_factory=list)
    preference_relevance_score: int = Field(default=0, ge=0, le=100)
    score_explanation: str = ""
    relevant_skills: List[str] = Field(default_factory=list)
    relevant_projects: List[str] = Field(default_factory=list)
    experience_alignment: str = ""
    missing_relevant_keywords: List[str] = Field(default_factory=list)
    missing_keywords_note: str = Field(default=MISSING_KEYWORDS_NOTE)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    improvement_opportunities: List[str] = Field(default_factory=list)

    @field_validator("preference_relevance_score", mode="before")
    @classmethod
    def validate_score(cls, v: int) -> int:
        return _clamp_score(v)


# ==============================================================================
# 3. Resume Scoring Explanations Schema
# ==============================================================================


class ResumeScoreExplanations(BaseModel):
    """Brief explanations for why each of the 6 scores (0-100) was assigned."""

    overall_quality: str = ""
    preference_relevance: str = ""
    skills_alignment: str = ""
    experience_alignment: str = ""
    project_relevance: str = ""
    ats_readability: str = ""


# ==============================================================================
# 4. Improvement Suggestion Schema (LLM + API)
# ==============================================================================


class SuggestionPayloadItem(BaseModel):
    """Structured improvement suggestion produced by the AI analysis."""

    section_name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Resume section (e.g. Professional Summary, Skills Section, Project Descriptions, Experience Descriptions, Education Section, Keywords, Formatting and Readability).",
    )
    current_content: Optional[str] = None
    suggested_improvement: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)
    priority: SuggestionPriority = "Medium"
    clarifying_question: Optional[str] = None

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, v: str) -> SuggestionPriority:
        if isinstance(v, str):
            cap = v.strip().capitalize()
            if cap in ("High", "Medium", "Low"):
                return cap  # type: ignore[return-value]
        return "Medium"


class LLMResumeAnalysisPayload(BaseModel):
    """Strict Pydantic validation model for the structured JSON returned by the LLM."""

    candidate_profile: CandidateProfileSummary = Field(
        default_factory=CandidateProfileSummary
    )
    education: List[EducationItem] = Field(default_factory=list)
    technical_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    work_experience: List[ExperienceItem] = Field(default_factory=list)
    internships: List[ExperienceItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    tools_and_technologies: List[str] = Field(default_factory=list)

    preference_analyses: List[PreferenceAnalysisItem] = Field(default_factory=list)

    overall_quality_score: int = Field(default=0, ge=0, le=100)
    preference_relevance_score: int = Field(default=0, ge=0, le=100)
    skills_alignment_score: int = Field(default=0, ge=0, le=100)
    experience_alignment_score: int = Field(default=0, ge=0, le=100)
    project_relevance_score: int = Field(default=0, ge=0, le=100)
    ats_readability_score: int = Field(default=0, ge=0, le=100)

    score_explanations: ResumeScoreExplanations = Field(
        default_factory=ResumeScoreExplanations
    )
    overall_strengths: List[str] = Field(default_factory=list)
    overall_weaknesses: List[str] = Field(default_factory=list)
    missing_information_questions: List[str] = Field(default_factory=list)
    suggestions: List[SuggestionPayloadItem] = Field(default_factory=list)

    @field_validator(
        "overall_quality_score",
        "preference_relevance_score",
        "skills_alignment_score",
        "experience_alignment_score",
        "project_relevance_score",
        "ats_readability_score",
        mode="before",
    )
    @classmethod
    def clamp_all_scores(cls, v: int) -> int:
        return _clamp_score(v)


# ==============================================================================
# 5. AI Resume Enhancement & Comparison Schemas
# ==============================================================================


class SectionComparisonItem(BaseModel):
    """Side-by-side comparison of Original Content vs AI Suggested Content for a section."""

    section_name: str
    original_content: str = ""
    suggested_content: str = ""
    final_content: Optional[str] = None
    reason: Optional[str] = None
    status: SuggestionStatus = "Pending"


class LLMResumeEnhancementPayload(BaseModel):
    """Structured LLM output for 'Improve My Resume' draft generation."""

    title: str = "AI-Enhanced Resume Draft"
    improved_full_content: str = Field(..., min_length=1)
    section_changes: List[SectionComparisonItem] = Field(default_factory=list)


class LLMRegenerateSuggestionPayload(BaseModel):
    """Structured LLM output when regenerating a single resume section suggestion."""

    section_name: str
    current_content: Optional[str] = None
    suggested_improvement: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)
    priority: SuggestionPriority = "Medium"
    clarifying_question: Optional[str] = None


# ==============================================================================
# 6. REST API Request / Response Schemas
# ==============================================================================


class AIProviderStatusResponse(BaseModel):
    """Safe backend AI configuration status (never exposes API keys)."""

    configured: bool
    provider: str
    model: str
    setup_message: Optional[str] = None


class ResumeSuggestionResponse(BaseModel):
    """API response schema for a stored ResumeSuggestion."""

    id: UUID
    resume_id: UUID
    analysis_id: Optional[UUID] = None
    section_name: str
    current_content: Optional[str] = None
    suggested_improvement: str
    user_edited_content: Optional[str] = None
    effective_content: str
    reason: str
    priority: SuggestionPriority
    clarifying_question: Optional[str] = None
    status: SuggestionStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SuggestionActionRequest(BaseModel):
    """Request payload for accepting, rejecting, or editing a suggestion."""

    status: Optional[SuggestionStatus] = None
    user_edited_content: Optional[str] = Field(
        default=None,
        max_length=10000,
        description="Optional user-edited replacement text for this suggestion.",
    )

    @field_validator("user_edited_content")
    @classmethod
    def clean_edited_content(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Edited suggestion content cannot be empty.")
        return trimmed


class RegenerateSuggestionRequest(BaseModel):
    """Optional guidance when asking AI to regenerate a specific suggestion."""

    user_instruction: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional factual clarification or focus area from the user.",
    )


class ResumeAnalysisResponse(BaseModel):
    """Complete AI Resume Analysis response including scores, preference evaluations, and suggestions."""

    id: UUID
    resume_id: UUID
    provider: str
    model_name: str

    candidate_profile: CandidateProfileSummary
    education: List[EducationItem]
    technical_skills: List[str]
    soft_skills: List[str]
    work_experience: List[ExperienceItem]
    internships: List[ExperienceItem]
    projects: List[ProjectItem]
    certifications: List[str]
    achievements: List[str]
    tools_and_technologies: List[str]

    preference_analyses: List[PreferenceAnalysisItem]

    overall_quality_score: int
    preference_relevance_score: int
    skills_alignment_score: int
    experience_alignment_score: int
    project_relevance_score: int
    ats_readability_score: int
    score_explanations: Dict[str, str]
    score_disclaimer: str = Field(default=SCORE_ESTIMATE_DISCLAIMER)
    missing_keywords_disclaimer: str = Field(default=MISSING_KEYWORDS_NOTE)

    overall_strengths: List[str]
    overall_weaknesses: List[str]
    missing_information_questions: List[str]
    suggestions: List[ResumeSuggestionResponse] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EnhanceResumeRequest(BaseModel):
    """Request payload for 'Improve My Resume' draft generation."""

    sections: Optional[List[str]] = Field(
        default=None,
        description="Optional list of section names to enhance. If omitted, enhances all key sections.",
    )
    target_preference_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Optional subset of associated JobPreference UUIDs to tailor the draft toward.",
    )
    apply_accepted_suggestions: bool = Field(
        default=True,
        description="Include accepted/user-edited suggestions when generating the enhanced draft.",
    )


class ResumeVersionResponse(BaseModel):
    """API response schema for a ResumeVersion record."""

    id: UUID
    parent_resume_id: UUID
    version_number: int
    version_type: str
    title: str
    content: str
    section_changes: List[SectionComparisonItem] = Field(default_factory=list)
    target_preference_ids: List[str] = Field(default_factory=list)
    approval_status: str
    approved_at: Optional[datetime] = None
    creation_date: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreateUserVersionRequest(BaseModel):
    """Request payload for saving a user-edited resume version."""

    title: Optional[str] = Field(
        default=None,
        max_length=200,
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=150000,
        description="Full resume text edited by the user.",
    )
    section_changes: Optional[List[SectionComparisonItem]] = None
    target_preference_ids: Optional[List[UUID]] = None

    @field_validator("content")
    @classmethod
    def validate_content_not_blank(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Resume version content cannot be empty.")
        return trimmed


class UpdateVersionRequest(BaseModel):
    """Request payload for editing an existing draft version before approval."""

    title: Optional[str] = Field(default=None, max_length=200)
    content: Optional[str] = Field(default=None, min_length=1, max_length=150000)
    section_changes: Optional[List[SectionComparisonItem]] = None

    @field_validator("content")
    @classmethod
    def validate_optional_content(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Resume version content cannot be empty.")
        return trimmed


class ApproveResumeVersionRequest(BaseModel):
    """Request payload for approving a final resume version and linking it to job preferences."""

    preference_ids: Optional[List[UUID]] = Field(
        default=None,
        description="JobPreference UUIDs to link this approved version to. Defaults to all preferences associated with the resume.",
    )


class ApproveResumeVersionResponse(BaseModel):
    """Response returned when a user approves a resume version."""

    resume_id: UUID
    ai_status: ResumeAIStatus
    approved_version: ResumeVersionResponse
    linked_preference_ids: List[UUID]
    message: str

