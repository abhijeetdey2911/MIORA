"""Comprehensive Phase 4 Automated Unit Tests for AI Provider Reliability & Error Handling.

Covers the 11 required test scenarios:
1. Successful Gemini response.
2. Retry after HTTP 503 (high demand).
3. Retry after HTTP 429 (rate limit).
4. Fallback model after primary-model transient failure.
5. No fallback for invalid API credentials (HTTP 401/403).
6. No fallback for invalid model configuration (HTTP 400/404).
7. Timeout handling (httpx.TimeoutException).
8. Invalid JSON response.
9. Pydantic validation failure.
10. No duplicate analysis records in database.
11. Resume-analysis endpoint error handling and status rollback.
"""

import json
from typing import Any, Dict, List, Optional
from unittest.mock import patch
import uuid

from fastapi import HTTPException
from fastapi.testclient import TestClient
import httpx
import pytest

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models.resume import Resume
from app.models.resume_intelligence import ResumeAnalysis
from app.schemas.resume_intelligence import (
    CandidateProfileSummary,
    EducationItem,
    ExperienceItem,
    LLMResumeAnalysisPayload,
    PreferenceAnalysisItem,
    ProjectItem,
    ResumeScoreExplanations,
    SuggestionPayloadItem,
)
from app.services.ai_provider import (
    AIProviderClient,
    AIProviderPermanentError,
    AIProviderTransientError,
    get_ai_provider_client,
)
from app.services.resume_intelligence import ResumeIntelligenceService

client = TestClient(app)


def _sample_valid_analysis_dict() -> Dict[str, Any]:
    """Return a dictionary conforming to LLMResumeAnalysisPayload."""
    return {
        "candidate_profile": {
            "full_name": "Test Candidate",
            "headline": "Python Engineer",
            "location": "Bangalore",
            "years_of_experience": "2",
            "contact_channels_present": ["email"],
            "summary_evaluation": "Good profile",
        },
        "education": [{
            "degree": "B.Tech",
            "institution": "University",
            "graduation_year": "2024",
            "details": None,
        }],
        "technical_skills": ["Python", "FastAPI"],
        "soft_skills": ["Problem Solving"],
        "work_experience": [{
            "role": "Engineer",
            "company": "Tech Corp",
            "duration": "2024-Present",
            "key_contributions": ["Built backend APIs"],
        }],
        "internships": [],
        "projects": [{
            "title": "Platform",
            "technologies": ["Python"],
            "summary": "Project summary",
            "impact": "High",
        }],
        "certifications": ["AWS"],
        "achievements": ["Hackathon Winner"],
        "tools_and_technologies": ["Git", "Docker"],
        "preference_analyses": [],
        "overall_quality_score": 85,
        "preference_relevance_score": 80,
        "skills_alignment_score": 88,
        "experience_alignment_score": 82,
        "project_relevance_score": 84,
        "ats_readability_score": 90,
        "score_explanations": {
            "overall_quality": "High",
            "preference_relevance": "Good",
            "skills_alignment": "Aligned",
            "experience_alignment": "Relevant",
            "project_relevance": "Demonstrated",
            "ats_readability": "Clean",
        },
        "overall_strengths": ["Strong skills"],
        "overall_weaknesses": ["Add metrics"],
        "missing_information_questions": [],
        "suggestions": [{
            "section_name": "Skills Section",
            "current_content": "Python",
            "suggested_improvement": "Python, FastAPI, PostgreSQL",
            "reason": "Explicit skill keywords",
            "priority": "High",
            "clarifying_question": None,
        }],
    }


def _sample_valid_analysis_json() -> str:
    """Return a JSON string conforming to LLMResumeAnalysisPayload."""
    return json.dumps(_sample_valid_analysis_dict())


# ------------------------------------------------------------------------------
# Test 1: Successful Gemini Response
# ------------------------------------------------------------------------------
def test_successful_gemini_response() -> None:
    """Scenario 1: Successful Gemini response on first attempt."""
    calls: List[str] = []

    ai_client = AIProviderClient(
        provider="gemini",
        api_key="mock-gemini-key",
        model="gemini-2.5-flash",
    )

    def mock_call_gemini(self_inst, client_http, system_prompt, user_prompt, model):
        calls.append(model)
        return _sample_valid_analysis_json()

    with patch.object(AIProviderClient, "_call_gemini", mock_call_gemini):
        result = ai_client.analyse_resume("Candidate resume text...", [])

    assert isinstance(result, LLMResumeAnalysisPayload)
    assert len(calls) == 1
    assert calls[0] == "gemini-2.5-flash"
    assert result.candidate_profile.full_name == "Test Candidate"


# ------------------------------------------------------------------------------
# Test 2: Retry after HTTP 503
# ------------------------------------------------------------------------------
def test_retry_after_http_503() -> None:
    """Scenario 2: HTTP 503 High Demand triggers retry and succeeds."""
    calls: List[int] = []
    slept: List[float] = []

    ai_client = AIProviderClient(
        provider="gemini",
        api_key="mock-key",
        model="gemini-2.5-flash",
        max_retries=3,
        initial_backoff_seconds=0.01,
        sleep_fn=lambda d: slept.append(d),
    )

    def mock_call_gemini(self_inst, client_http, system_prompt, user_prompt, model):
        calls.append(len(calls) + 1)
        if len(calls) < 2:
            raise AIProviderTransientError(
                "This model is currently experiencing high demand. Please try again later.",
                status_code=503,
                model=model,
            )
        return _sample_valid_analysis_json()

    with patch.object(AIProviderClient, "_call_gemini", mock_call_gemini):
        result = ai_client.analyse_resume("Resume...", [])

    assert isinstance(result, LLMResumeAnalysisPayload)
    assert len(calls) == 2
    assert len(slept) == 1
    assert slept[0] > 0


# ------------------------------------------------------------------------------
# Test 3: Retry after HTTP 429
# ------------------------------------------------------------------------------
def test_retry_after_http_429() -> None:
    """Scenario 3: HTTP 429 Rate Limit triggers retry with backoff and succeeds."""
    calls: List[int] = []
    slept: List[float] = []

    ai_client = AIProviderClient(
        provider="gemini",
        api_key="mock-key",
        model="gemini-2.5-flash",
        max_retries=3,
        initial_backoff_seconds=0.01,
        sleep_fn=lambda d: slept.append(d),
    )

    def mock_call_gemini(self_inst, client_http, system_prompt, user_prompt, model):
        calls.append(len(calls) + 1)
        if len(calls) == 1:
            raise AIProviderTransientError(
                "Quota exhausted (HTTP 429)",
                status_code=429,
                model=model,
            )
        return _sample_valid_analysis_json()

    with patch.object(AIProviderClient, "_call_gemini", mock_call_gemini):
        result = ai_client.analyse_resume("Resume...", [])

    assert isinstance(result, LLMResumeAnalysisPayload)
    assert len(calls) == 2
    assert len(slept) == 1


# ------------------------------------------------------------------------------
# Test 4: Fallback Model after Primary Transient Failure
# ------------------------------------------------------------------------------
def test_fallback_model_after_primary_transient_failure() -> None:
    """Scenario 4: Fallback model is invoked when primary model exhausts retries."""
    calls: List[str] = []

    ai_client = AIProviderClient(
        provider="gemini",
        api_key="mock-key",
        model="gemini-2.5-flash",
        fallback_model="gemini-1.5-flash",
        max_retries=3,
        initial_backoff_seconds=0.01,
        sleep_fn=lambda _: None,
    )

    def mock_call_gemini(self_inst, client_http, system_prompt, user_prompt, model):
        calls.append(model)
        if model == "gemini-2.5-flash":
            raise AIProviderTransientError("High demand 503", status_code=503, model=model)
        return _sample_valid_analysis_json()

    with patch.object(AIProviderClient, "_call_gemini", mock_call_gemini):
        result = ai_client.analyse_resume("Resume...", [])

    assert isinstance(result, LLMResumeAnalysisPayload)
    assert calls.count("gemini-2.5-flash") == 3
    assert calls.count("gemini-1.5-flash") == 1
    assert getattr(result, "_model_used") == "gemini-1.5-flash"


# ------------------------------------------------------------------------------
# Test 5: No Fallback for Invalid API Credentials (HTTP 401/403)
# ------------------------------------------------------------------------------
def test_no_fallback_for_invalid_api_credentials() -> None:
    """Scenario 5: 401/403 Authentication error fails fast immediately without retrying or fallback."""
    calls: List[str] = []

    ai_client = AIProviderClient(
        provider="gemini",
        api_key="invalid-api-key",
        model="gemini-2.5-flash",
        fallback_model="gemini-1.5-flash",
        max_retries=3,
        sleep_fn=lambda _: None,
    )

    def mock_call_gemini(self_inst, client_http, system_prompt, user_prompt, model):
        calls.append(model)
        raise AIProviderPermanentError("API key not valid (HTTP 401)", status_code=401, model=model)

    with patch.object(AIProviderClient, "_call_gemini", mock_call_gemini):
        with pytest.raises(HTTPException) as exc_info:
            ai_client.analyse_resume("Resume...", [])

    assert len(calls) == 1
    assert calls[0] == "gemini-2.5-flash"
    assert exc_info.value.status_code == 502


# ------------------------------------------------------------------------------
# Test 6: No Fallback for Invalid Model Configuration (HTTP 400/404)
# ------------------------------------------------------------------------------
def test_no_fallback_for_invalid_model_configuration() -> None:
    """Scenario 6: 404 Model Not Found fails fast without fallback."""
    calls: List[str] = []

    ai_client = AIProviderClient(
        provider="gemini",
        api_key="mock-key",
        model="non-existent-model",
        fallback_model="gemini-1.5-flash",
        max_retries=3,
        sleep_fn=lambda _: None,
    )

    def mock_call_gemini(self_inst, client_http, system_prompt, user_prompt, model):
        calls.append(model)
        raise AIProviderPermanentError("Model not found (HTTP 404)", status_code=404, model=model)

    with patch.object(AIProviderClient, "_call_gemini", mock_call_gemini):
        with pytest.raises(HTTPException) as exc_info:
            ai_client.analyse_resume("Resume...", [])

    assert len(calls) == 1
    assert calls[0] == "non-existent-model"


# ------------------------------------------------------------------------------
# Test 7: Timeout Handling
# ------------------------------------------------------------------------------
def test_timeout_handling_triggers_retry() -> None:
    """Scenario 7: Request timeout triggers transient retry backoff and succeeds on attempt 2."""
    calls: List[int] = []

    ai_client = AIProviderClient(
        provider="gemini",
        api_key="mock-key",
        model="gemini-2.5-flash",
        timeout_seconds=5.0,
        max_retries=3,
        initial_backoff_seconds=0.01,
        sleep_fn=lambda _: None,
    )

    def mock_call_gemini(self_inst, client_http, system_prompt, user_prompt, model):
        calls.append(len(calls) + 1)
        if len(calls) == 1:
            raise httpx.ReadTimeout("Timed out waiting for response.")
        return _sample_valid_analysis_json()

    with patch.object(AIProviderClient, "_call_gemini", mock_call_gemini):
        result = ai_client.analyse_resume("Resume...", [])

    assert isinstance(result, LLMResumeAnalysisPayload)
    assert len(calls) == 2


# ------------------------------------------------------------------------------
# Test 8: Invalid JSON Response
# ------------------------------------------------------------------------------
def test_invalid_json_response_raises_502() -> None:
    """Scenario 8: Non-JSON raw text returned by provider raises HTTP 502 Bad Gateway."""
    ai_client = AIProviderClient(
        provider="gemini",
        api_key="mock-key",
        model="gemini-2.5-flash",
    )

    def mock_call_gemini(self_inst, client_http, system_prompt, user_prompt, model):
        return "Not valid JSON {incomplete text"

    with patch.object(AIProviderClient, "_call_gemini", mock_call_gemini):
        with pytest.raises(HTTPException) as exc_info:
            ai_client.analyse_resume("Resume...", [])

    assert exc_info.value.status_code == 502
    assert "invalid structured response" in exc_info.value.detail.lower()


# ------------------------------------------------------------------------------
# Test 9: Pydantic Validation Failure
# ------------------------------------------------------------------------------
def test_pydantic_validation_failure_raises_502() -> None:
    """Scenario 9: JSON with invalid schema constraints triggers Pydantic ValidationError and raises HTTP 502."""
    ai_client = AIProviderClient(
        provider="gemini",
        api_key="mock-key",
        model="gemini-2.5-flash",
    )

    def mock_call_gemini(self_inst, client_http, system_prompt, user_prompt, model):
        # Overall quality score violates le=100, candidate_profile violates dict requirement
        return json.dumps({"candidate_profile": "invalid-primitive", "overall_quality_score": 9999})

    with patch.object(AIProviderClient, "_call_gemini", mock_call_gemini):
        with pytest.raises(HTTPException) as exc_info:
            ai_client.analyse_resume("Resume...", [])

    assert exc_info.value.status_code == 502
    assert "invalid structured response" in exc_info.value.detail.lower()


# ------------------------------------------------------------------------------
# Test 10: No Duplicate Analysis Records
# ------------------------------------------------------------------------------
def test_no_duplicate_analysis_records() -> None:
    """Scenario 10: When analysis retries before succeeding, only one ResumeAnalysis record exists in DB."""
    db = SessionLocal()
    resume_id = uuid.uuid4()
    test_resume = Resume(
        id=resume_id,
        resume_name="Deduplication_Scenario_Test",
        original_filename="resume.pdf",
        stored_filename=f"{resume_id}.pdf",
        storage_path=f"storage/resumes/{resume_id}.pdf",
        file_format="pdf",
        mime_type="application/pdf",
        file_size=2048,
        extracted_text="Jane Doe\nStaff Machine Learning Engineer with 6 years experience.",
        ai_status="Not Analysed",
    )
    db.add(test_resume)
    db.commit()

    call_count = 0

    class RetrySuccessClient(AIProviderClient):
        def __init__(self) -> None:
            super().__init__(
                provider="gemini",
                api_key="test-key",
                model="gemini-2.5-flash",
                max_retries=3,
                initial_backoff_seconds=0.001,
                sleep_fn=lambda _: None,
            )

        def _call_gemini(self, client_http, system_prompt, user_prompt, model):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise AIProviderTransientError("Temporary 503", status_code=503, model=model)
            return _sample_valid_analysis_json()

    try:
        ai_client = RetrySuccessClient()
        analysis = ResumeIntelligenceService.analyse_resume(db, resume_id, ai_client)
        assert analysis is not None
        assert call_count == 2

        # Verify only one analysis record is present
        analyses = db.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id == resume_id).all()
        assert len(analyses) == 1
        assert analyses[0].id == analysis.id
    finally:
        db.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id == resume_id).delete()
        db.query(Resume).filter(Resume.id == resume_id).delete()
        db.commit()
        db.close()


# ------------------------------------------------------------------------------
# Test 11: Resume-Analysis Endpoint Error Handling
# ------------------------------------------------------------------------------
def test_resume_analysis_endpoint_error_handling() -> None:
    """Scenario 11: When AI provider exhaust retries, POST /api/v1/resumes/{id}/analyse returns 503 and rolls back status."""
    db = SessionLocal()
    resume_id = uuid.uuid4()
    test_resume = Resume(
        id=resume_id,
        resume_name="Endpoint_Error_Test",
        original_filename="resume.pdf",
        stored_filename=f"{resume_id}.pdf",
        storage_path=f"storage/resumes/{resume_id}.pdf",
        file_format="pdf",
        mime_type="application/pdf",
        file_size=2048,
        extracted_text="Candidate with valid extracted text.",
        ai_status="Not Analysed",
    )
    db.add(test_resume)
    db.commit()
    db.close()

    class FailingTransientClient(AIProviderClient):
        def __init__(self) -> None:
            super().__init__(
                provider="gemini",
                api_key="test-key",
                model="gemini-2.5-flash",
                fallback_model="gemini-1.5-flash",
                max_retries=2,
                initial_backoff_seconds=0.001,
                sleep_fn=lambda _: None,
            )

        def _call_gemini(self, client_http, system_prompt, user_prompt, model):
            raise AIProviderTransientError("High demand 503", status_code=503, model=model)

    app.dependency_overrides[get_ai_provider_client] = FailingTransientClient
    try:
        res = client.post(f"/api/v1/resumes/{resume_id}/analyse")
        assert res.status_code == 503
        data = res.json()
        err_text = data.get("detail") or data.get("message") or ""
        assert "temporarily unavailable due to high demand" in err_text

        # Verify resume ai_status was restored and not stuck in 'Analysing'
        db2 = SessionLocal()
        refreshed = db2.get(Resume, resume_id)
        assert refreshed is not None
        assert refreshed.ai_status == "Not Analysed"
        db2.close()
    finally:
        app.dependency_overrides.pop(get_ai_provider_client, None)
        db_cleanup = SessionLocal()
        db_cleanup.query(Resume).filter(Resume.id == resume_id).delete()
        db_cleanup.commit()
        db_cleanup.close()
