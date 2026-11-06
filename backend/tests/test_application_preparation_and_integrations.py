"""Tests for MIORA 2.0 Application Preparation, Lever Public API Adapter & Listing Freshness.

Verifies:
- Extraction of candidate name from resume text.
- Deterministic and AI-powered cover letter generation.
- Screening question preparation.
- Assembly of cohesive application packages stored in `Application.prepared_payload`.
- Lever ATS adapter parsing, role matching, and location filtering.
- Listing freshness / expiration detection.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import uuid

import pytest

from app.models.job_preference import JobPreference
from app.models.multi_agent import ApplicationRoute, DiscoveredJob
from app.models.resume import Resume
from app.models.resume_intelligence import ResumeVersion
from app.services.agents.agent1_discovery import (
    LeverOfficialCompanyAdapter,
    check_listing_freshness,
)
from app.services.agents.agent4_execution import (
    OfficialCompanyPortalHandler,
    PublishedHREmailHandler,
)
from app.services.application_preparer import (
    build_full_application_package,
    extract_candidate_name_from_text,
    generate_cover_letter,
    generate_screening_answers,
)


def test_extract_candidate_name_from_text():
    resume_text = "Abhijeet Dey\nSenior Software Engineer\nBengaluru, India\nSkills: Python, FastAPI"
    name = extract_candidate_name_from_text(resume_text)
    assert name == "Abhijeet Dey"

    empty_text = ""
    assert extract_candidate_name_from_text(empty_text, fallback="Test Candidate") == "Test Candidate"

    resume_with_header = "RESUME\nJane Doe\nFull Stack Developer"
    assert extract_candidate_name_from_text(resume_with_header) == "Jane Doe"


def test_generate_cover_letter_deterministic():
    letter = generate_cover_letter(
        candidate_name="Abhijeet Dey",
        company="Razorpay",
        job_title="Senior Backend Engineer",
        job_description="Looking for Python, FastAPI, PostgreSQL, and distributed systems experience.",
        skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        ai_client=None,
    )
    assert "Abhijeet Dey" in letter
    assert "Razorpay" in letter
    assert "Senior Backend Engineer" in letter
    assert "Python, FastAPI, PostgreSQL, Docker" in letter
    assert "Hiring Team at Razorpay" in letter


def test_generate_cover_letter_ai_success():
    mock_ai = MagicMock()
    mock_ai.generate_content.return_value = MagicMock(
        text=(
            "Dear Hiring Team at Razorpay,\n\n"
            "I am excited to apply for the Senior Backend Engineer role. "
            "With expertise in Python, FastAPI, and scalable architecture, I am eager to contribute.\n\n"
            "Sincerely,\nAbhijeet Dey"
        )
    )
    letter = generate_cover_letter(
        candidate_name="Abhijeet Dey",
        company="Razorpay",
        job_title="Senior Backend Engineer",
        job_description="Backend development",
        skills=["Python", "FastAPI"],
        ai_client=mock_ai,
    )
    assert "Dear Hiring Team at Razorpay" in letter
    assert "Abhijeet Dey" in letter
    mock_ai.generate_content.assert_called_once()


def test_generate_screening_answers():
    answers = generate_screening_answers(
        candidate_name="Abhijeet Dey",
        company="Groww",
        job_title="Python Developer",
        skills=["Python", "Django", "FastAPI"],
        work_mode_pref="Hybrid",
        location_pref="Bengaluru",
    )
    assert len(answers) == 4
    assert any("Groww" in a["question"] for a in answers)
    assert any("Bengaluru" in a["answer"] for a in answers)
    assert any("Python" in a["answer"] for a in answers)


def test_build_full_application_package():
    pkg = build_full_application_package(
        subagent_name="4.1_official_company_portal",
        company="Atlassian",
        job_title="Senior Software Engineer",
        route_type="official_company_portal",
        route_target="https://atlassian.com/careers/job123",
        job_description="Distributed systems in Python and Go.",
        candidate_name="Abhijeet Dey",
        skills=["Python", "Go", "Kubernetes"],
        resume_id=str(uuid.uuid4()),
        resume_name="Abhijeet_Software_Resume.pdf",
        resume_version_id=str(uuid.uuid4()),
        resume_version_number=2,
    )
    assert pkg["subagent"] == "4.1_official_company_portal"
    assert pkg["company"] == "Atlassian"
    assert pkg["job_title"] == "Senior Software Engineer"
    assert "Atlassian" in pkg["cover_letter"]
    assert len(pkg["answers_to_common_questions"]) == 4
    assert pkg["safety_checks"]["captcha_bypass"] == "prohibited"
    assert pkg["safety_checks"]["approved_resume_verified"] is True


def test_official_portal_handler_prepares_full_package():
    job = DiscoveredJob(
        id=uuid.uuid4(),
        canonical_url="https://boards.greenhouse.io/inmobi/jobs/12345",
        fingerprint="fp123",
        title="Backend Software Engineer",
        company="InMobi",
        description="Build high-throughput services with Python and Redis.",
        official_job_url="https://boards.greenhouse.io/inmobi/jobs/12345",
        source_name="Greenhouse Official Company Boards",
    )
    pref = JobPreference(
        id=uuid.uuid4(),
        preference_name="Backend India",
        job_roles=["Backend Software Engineer"],
        skills=["Python", "Redis", "PostgreSQL"],
        locations=["Bengaluru", "India"],
        work_mode="Remote",
    )
    route = ApplicationRoute(
        id=uuid.uuid4(),
        discovered_job_id=job.id,
        preference_id=pref.id,
        route_type="official_company_portal",
        url_or_contact=job.official_job_url,
        source=job.source_name,
    )
    resume = Resume(
        id=uuid.uuid4(),
        resume_name="Abhijeet_Resume.pdf",
        extracted_text="Abhijeet Dey\nSenior Engineer\nSkills: Python, Redis, SQL",
    )
    version = ResumeVersion(
        id=uuid.uuid4(),
        parent_resume_id=resume.id,
        version_number=1,
        title="Original Uploaded",
        content=resume.extracted_text,
    )

    handler = OfficialCompanyPortalHandler()
    pkg = handler.prepare_package(
        job=job,
        preference=pref,
        route=route,
        resume=resume,
        resume_version=version,
    )

    assert "cover_letter" in pkg
    assert "InMobi" in pkg["cover_letter"]
    assert "Abhijeet Dey" in pkg["cover_letter"]
    assert "answers_to_common_questions" in pkg
    assert pkg["portal_url"] == job.official_job_url


def test_published_hr_email_handler_prepares_full_package():
    job = DiscoveredJob(
        id=uuid.uuid4(),
        canonical_url="https://careers.startup.com/job/456",
        fingerprint="fp456",
        title="Full Stack Engineer",
        company="Acme Corp",
        description="Join our team: send resume to careers@acmeworks.com",
        official_job_url="https://careers.startup.com/job/456",
        source_name="Remotive Official API",
    )
    pref = JobPreference(
        id=uuid.uuid4(),
        preference_name="Full Stack Preference",
        job_roles=["Full Stack Engineer"],
        skills=["React", "TypeScript", "Python"],
        locations=["Remote"],
        work_mode="Remote",
    )
    route = ApplicationRoute(
        id=uuid.uuid4(),
        discovered_job_id=job.id,
        preference_id=pref.id,
        route_type="published_hr_email",
        url_or_contact="careers@acmeworks.com",
        source="Listing Description",
    )
    resume = Resume(
        id=uuid.uuid4(),
        resume_name="FullStack_Resume.pdf",
        extracted_text="Abhijeet Dey\nFull Stack Developer",
    )

    handler = PublishedHREmailHandler()
    pkg = handler.prepare_package(
        job=job,
        preference=pref,
        route=route,
        resume=resume,
        resume_version=None,
    )

    assert pkg["recipient_email"] == "careers@acmeworks.com"
    assert "Application for Full Stack Engineer" in pkg["subject"]
    assert "cover_letter" in pkg
    assert "Acme Corp" in pkg["cover_letter"]


def test_lever_adapter_fetch_jobs_mock():
    mock_postings = [
        {
            "id": "lever-job-001",
            "text": "Senior Backend Engineer",
            "hostedUrl": "https://jobs.lever.co/postman/lever-job-001",
            "applyUrl": "https://jobs.lever.co/postman/lever-job-001/apply",
            "descriptionPlain": "We are seeking a Senior Backend Engineer with Python and microservices experience.",
            "categories": {
                "commitment": "Full-time",
                "location": "Bengaluru, Karnataka, India",
                "team": "Engineering",
            },
            "createdAt": 1700000000000,
        },
        {
            "id": "lever-job-002",
            "text": "Sales Manager",
            "hostedUrl": "https://jobs.lever.co/postman/lever-job-002",
            "applyUrl": "https://jobs.lever.co/postman/lever-job-002/apply",
            "descriptionPlain": "Sales lead for international enterprise clients.",
            "categories": {
                "commitment": "Full-time",
                "location": "Berlin, Germany",
            },
            "createdAt": 1700000000000,
        },
    ]

    adapter = LeverOfficialCompanyAdapter(companies=["postman"])
    pref = JobPreference(
        id=uuid.uuid4(),
        preference_name="Backend India",
        job_roles=["Backend Engineer"],
        skills=["Python"],
        locations=["Bengaluru", "India"],
        location_mode="INDIA_ONLY",
        experience_level="Senior",
        work_mode="On-site",
    )

    with patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_postings
        mock_get.return_value = mock_resp

        results = adapter.fetch_jobs(preference=pref, max_results=10)

        # Should match Backend Engineer in Bengaluru, exclude Sales Manager in Berlin
        assert len(results) == 1
        assert results[0].title == "Senior Backend Engineer"
        assert results[0].company == "Postman"
        assert results[0].location == "Bengaluru, Karnataka, India"
        assert results[0].external_job_id == "lever-job-001"
        assert results[0].raw_metadata["ats"] == "lever"


def test_check_listing_freshness():
    with patch("httpx.Client.head") as mock_head:
        # 200 OK -> Fresh
        mock_head.return_value = MagicMock(status_code=200)
        assert check_listing_freshness("https://company.com/jobs/1") is True

        # 404 Not Found -> Expired
        mock_head.return_value = MagicMock(status_code=404)
        assert check_listing_freshness("https://company.com/jobs/expired") is False

        # 410 Gone -> Expired
        mock_head.return_value = MagicMock(status_code=410)
        assert check_listing_freshness("https://company.com/jobs/gone") is False
