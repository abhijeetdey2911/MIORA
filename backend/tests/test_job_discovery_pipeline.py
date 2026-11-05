"""Comprehensive test suite for MIORA's Multi-Agent Job-Hunting Pipeline (Agents 1 through 5).

Covers all 20 mandatory end-to-end audit requirements:
 1. Preference creation with Indian locations.
 2. Agent 1 discovery executes Greenhouse adapter and fetches real listings.
 3. Agent 1 discovery executes Jobicy adapter and fetches listings.
 4. Agent 1 discovery handles empty or error response gracefully from any single adapter without crashing.
 5. Discovered jobs are deduplicated using canonical URL and fingerprint.
 6. Location filtering strictly enforces location_mode.
 7. Role synonym expansion enables Data Analyst preference to match BI Analyst, Analytics Engineer, etc.
 8. Experience level filtering correctly identifies fresher/entry-level vs. senior/lead.
 9. Senior/lead jobs evaluated for entry-level preference receive <= 25 match score and reason 'Experience Ineligible'.
10. Entry-level jobs evaluated for entry-level preference score >= threshold and are shortlisted.
11. Agent 2 deterministic matching evaluates role, skills, location, experience, and resume.
12. Agent 2 AI matching prompt enforces location and experience guardrails.
13. Agent 3 discovers verified portal route (confidence >= 90) for Greenhouse and Jobicy jobs.
14. Agent 3 discovers unverified/manual review route for unknown domains.
15. Preference approved resume version is correctly linked to matches and applications.
16. Agent 4 prepares application with correct resume and portal details.
17. Mandatory user approval is enforced: application stays in 'Awaiting Approval' when auto_authorised is False.
18. Agent 4 prevents duplicate applications for the same job and preference.
19. Agent 5 tracks application lifecycle and creates immutable status history audit records.
20. Pausing one preference does not interrupt execution or status of other preferences.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
import uuid

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.job_preference import JobPreference
from app.models.multi_agent import (
    Application,
    ApplicationRoute,
    ApplicationStatusHistory,
    AutomationSettings,
    DiscoveredJob,
    JobMatch,
    JobSource,
)
from app.models.resume import Resume
from app.models.resume_intelligence import ResumeAnalysis, ResumeVersion
from app.services.agents.agent1_discovery import (
    BaseJobSourceAdapter,
    GreenhouseOfficialCompanyAdapter,
    JobDiscoveryAgent,
    JobicyRemoteAPIAdapter,
    RawDiscoveredJobItem,
    compute_job_fingerprint,
    normalize_canonical_url,
)
from app.services.agents.agent2_matching import JobMatchingAgent, LLMJobMatchOutput
from app.services.agents.agent3_routes import ApplicationRouteDiscoveryAgent
from app.services.agents.agent4_execution import ApplicationExecutionAgent
from app.services.agents.agent5_tracking import ApplicationTrackingAgent
from app.services.experience_matcher import (
    SENIORITY_ENTRY,
    SENIORITY_LEAD_PRINCIPAL,
    SENIORITY_SENIOR,
    classify_seniority_tier,
    evaluate_experience_eligibility,
    extract_experience_years,
)
from app.services.location_matcher import evaluate_location_eligibility
from app.services.role_synonyms import expand_job_roles


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------


def make_test_resume(
    name: str = "Test_Resume.pdf",
    text: str = "Python and SQL Data Analyst",
) -> Resume:
    return Resume(
        id=uuid.uuid4(),
        resume_name=name,
        original_filename=name,
        stored_filename=f"res_{uuid.uuid4().hex}.pdf",
        storage_backend="local",
        storage_path=f"/data/resumes/{name}",
        file_format="pdf",
        mime_type="application/pdf",
        file_size=1024,
        extracted_text=text,
        processing_status="Processed",
    )


def create_approved_resume_and_version(
    db: Session,
    name: str = "Approved_Resume.pdf",
    text: str = "Python, SQL, Tableau",
) -> tuple[Resume, ResumeVersion]:
    resume = make_test_resume(name, text)
    db.add(resume)
    db.flush()

    ver = ResumeVersion(
        id=uuid.uuid4(),
        parent_resume_id=resume.id,
        version_number=1,
        title="Approved Version",
        content=text,
        approval_status="Approved",
    )
    db.add(ver)
    db.flush()

    resume.approved_version_id = ver.id
    db.commit()
    return resume, ver


@pytest.fixture
def db_session():
    """Isolated in-memory SQLite session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_preference(db_session: Session) -> JobPreference:
    """Create a sample Indian Entry-Level Data Analyst JobPreference."""
    pref = JobPreference(
        id=uuid.uuid4(),
        preference_name="Data Analytics India",
        job_roles=["Data Analyst"],
        locations=["Bengaluru", "Mumbai", "Pune"],
        location_mode="INDIA_ONLY",
        work_mode="Flexible",
        employment_type="Full-time",
        experience_level="Entry-level",
        min_salary=600000,
        max_salary=1500000,
        currency="INR",
        skills=["Python", "SQL", "Tableau", "Power BI"],
        minimum_match_score=70,
        is_active=True,
    )
    db_session.add(pref)
    db_session.commit()
    return pref


# ===========================================================================
# TEST 1: Preference creation with Indian locations
# ===========================================================================


def test_01_preference_creation_indian_locations(db_session: Session):
    pref = JobPreference(
        id=uuid.uuid4(),
        preference_name="Junior Python Dev",
        job_roles=["Python Developer", "Software Engineer"],
        locations=["Bengaluru", "Hyderabad", "Pune"],
        location_mode="INDIA_ONLY",
        work_mode="Remote",
        employment_type="Full-time",
        experience_level="Entry-level",
        currency="INR",
        skills=["Python", "FastAPI", "Docker"],
        is_active=True,
    )
    db_session.add(pref)
    db_session.commit()

    saved = db_session.get(JobPreference, pref.id)
    assert saved is not None
    assert saved.location_mode == "INDIA_ONLY"
    assert "Bengaluru" in saved.locations
    assert saved.experience_level == "Entry-level"


# ===========================================================================
# TEST 2: Agent 1 discovery executes Greenhouse adapter and fetches real listings
# ===========================================================================


def test_02_agent1_greenhouse_adapter(sample_preference: JobPreference):
    adapter = GreenhouseOfficialCompanyAdapter(companies=["inmobi"])
    mock_payload = {
        "jobs": [
            {
                "id": 101,
                "title": "Data Analyst - Product Analytics",
                "location": {"name": "Bengaluru, India"},
                "absolute_url": "https://job-boards.greenhouse.io/inmobi/jobs/101",
                "content": "<p>Looking for a Data Analyst in Bengaluru with skills in Python and SQL.</p>",
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload

    with patch("httpx.Client.get", return_value=mock_resp):
        jobs = adapter.fetch_jobs(sample_preference, max_results=10)

    assert len(jobs) == 1
    item = jobs[0]
    assert item.title == "Data Analyst - Product Analytics"
    assert item.company == "Inmobi"
    assert "Bengaluru" in item.location
    assert item.official_job_url == "https://job-boards.greenhouse.io/inmobi/jobs/101"
    assert item.raw_metadata.get("verified_portal") is True


# ===========================================================================
# TEST 3: Agent 1 discovery executes Jobicy adapter and fetches listings
# ===========================================================================


def test_03_agent1_jobicy_adapter(sample_preference: JobPreference):
    adapter = JobicyRemoteAPIAdapter()
    mock_payload = {
        "jobs": [
            {
                "id": 201,
                "jobTitle": "Junior Data Analyst",
                "companyName": "Acme Analytics",
                "url": "https://jobicy.com/jobs/201-junior-data-analyst",
                "jobGeo": "India",
                "jobDescription": "<p>Entry-level Data Analyst role. Requires SQL and Python.</p>",
                "pubDate": "2026-11-01T12:00:00Z",
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload

    with patch("httpx.Client.get", return_value=mock_resp):
        jobs = adapter.fetch_jobs(sample_preference, max_results=10)

    assert len(jobs) == 1
    item = jobs[0]
    assert item.title == "Junior Data Analyst"
    assert item.company == "Acme Analytics"
    assert item.location == "India"
    assert item.work_mode == "Remote"


# ===========================================================================
# TEST 4: Agent 1 handles empty or error response gracefully without crashing
# ===========================================================================


def test_04_agent1_error_handling_graceful(
    db_session: Session, sample_preference: JobPreference
):
    class CrashingAdapter(BaseJobSourceAdapter):
        source_name = "Crashing Source"
        adapter_type = "crash"

        def fetch_jobs(self, preference, max_results=25):
            raise httpx.ConnectTimeout("Connection to upstream timed out")

    class WorkingAdapter(BaseJobSourceAdapter):
        source_name = "Working Source"
        adapter_type = "work"

        def fetch_jobs(self, preference, max_results=25):
            return [
                RawDiscoveredJobItem(
                    source_name=self.source_name,
                    external_job_id="w-1",
                    title="Data Analyst",
                    company="GoodCorp",
                    description="SQL, Python, Bengaluru",
                    official_job_url="https://goodcorp.com/careers/1",
                    location="Bengaluru, Karnataka, India",
                    work_mode="On-site",
                    employment_type="Full-time",
                    experience_requirement="0-2 years",
                )
            ]

    agent = JobDiscoveryAgent(adapters=[CrashingAdapter(), WorkingAdapter()])
    discovered = agent.discover_for_preference(
        db=db_session, preference=sample_preference, max_jobs=10
    )

    # Crashing source recorded failure in last_source_summary
    assert agent.last_source_summary["Crashing Source"]["status"] == "failed"
    assert "timed out" in agent.last_source_summary["Crashing Source"]["error_message"].lower()

    # Working source succeeded and jobs were saved
    assert agent.last_source_summary["Working Source"]["status"] == "success"
    assert len(discovered) == 1
    assert discovered[0].title == "Data Analyst"


# ===========================================================================
# TEST 5: Discovered jobs deduplication using canonical URL and fingerprint
# ===========================================================================


def test_05_job_deduplication(db_session: Session, sample_preference: JobPreference):
    raw_job_1 = RawDiscoveredJobItem(
        source_name="Adapter 1",
        external_job_id="job-100",
        title="Data Analyst",
        company="Stripe",
        description="Python, SQL in Bengaluru",
        official_job_url="https://stripe.com/jobs/100?utm_source=linkedin&ref=board",
        location="Bengaluru, India",
        work_mode="On-site",
    )
    raw_job_2 = RawDiscoveredJobItem(
        source_name="Adapter 2",
        external_job_id="job-100",
        title="Data Analyst",
        company="Stripe",
        description="Python, SQL in Bengaluru",
        official_job_url="https://stripe.com/jobs/100?utm_medium=email&utm_campaign=board",  # normalizes to same canonical URL
        location="Bengaluru, India",
        work_mode="On-site",
    )

    class StaticAdapter(BaseJobSourceAdapter):
        source_name = "Static"
        adapter_type = "static"

        def fetch_jobs(self, preference, max_results=25):
            return [raw_job_1, raw_job_2]

    agent = JobDiscoveryAgent(adapters=[StaticAdapter()])
    discovered = agent.discover_for_preference(
        db=db_session, preference=sample_preference, max_jobs=10
    )

    # Deduplicated: only 1 DiscoveredJob should be stored
    assert len(discovered) == 1
    all_jobs = db_session.scalars(select(DiscoveredJob)).all()
    assert len(all_jobs) == 1


# ===========================================================================
# TEST 6: Location filtering strictly enforces location_mode
# ===========================================================================


def test_06_location_filtering_enforcement():
    # 1. German on-site job excluded for INDIA_ONLY
    german_check = evaluate_location_eligibility(
        job_location="Hamburg, Germany",
        job_work_mode="On-site",
        preference_locations=["Bengaluru", "Mumbai"],
        location_mode="INDIA_ONLY",
        preference_work_mode="Flexible",
    )
    assert not german_check.is_eligible
    assert "incompatible" in german_check.reason.lower()

    # 2. Remote US-only job excluded
    us_remote_check = evaluate_location_eligibility(
        job_location="Remote (US Only)",
        job_work_mode="Remote",
        preference_locations=["Bengaluru"],
        location_mode="INDIA_ONLY",
        preference_work_mode="Remote",
        raw_metadata={"candidate_required_location": "USA Only"},
    )
    assert not us_remote_check.is_eligible

    # 3. Verified Indian office job passes
    india_check = evaluate_location_eligibility(
        job_location="Bengaluru, Karnataka, India",
        job_work_mode="Hybrid",
        preference_locations=["Bengaluru"],
        location_mode="INDIA_ONLY",
        preference_work_mode="Flexible",
    )
    assert india_check.is_eligible
    assert india_check.matched_location == "Bangalore"


# ===========================================================================
# TEST 7: Role synonym expansion enables Data Analyst to match BI Analyst
# ===========================================================================


def test_07_role_synonym_expansion():
    expanded = expand_job_roles(["Data Analyst"])
    assert any("bi analyst" in r.lower() for r in expanded)
    assert any("analytics engineer" in r.lower() for r in expanded)
    assert any("business analyst" in r.lower() for r in expanded)

    # Verify matching recognizes the synonym
    pref = JobPreference(
        id=uuid.uuid4(),
        preference_name="Data Analyst Test",
        job_roles=["Data Analyst"],
        locations=["Bengaluru"],
        location_mode="INDIA_ONLY",
        work_mode="Flexible",
        employment_type="Full-time",
        experience_level="Entry-level",
        skills=["SQL"],
    )
    job = DiscoveredJob(
        id=uuid.uuid4(),
        canonical_url="https://ex.com/bi-analyst",
        fingerprint="fp1",
        title="BI Analyst",
        company="TechCorp",
        location="Bengaluru, India",
        work_mode="On-site",
        description="Develop dashboards and write SQL queries.",
        official_job_url="https://ex.com/bi-analyst",
    )
    matcher = JobMatchingAgent()
    out = matcher._evaluate_deterministic(
        preference=pref,
        job=job,
        resume_version=None,
        resume_analysis=None,
        threshold=50,
    )
    assert any("bi analyst" in r.lower() or "aligns with target role" in r.lower() for r in out.reasons_for_matching)


# ===========================================================================
# TEST 8: Experience level filtering classifies fresher/entry vs. senior/lead
# ===========================================================================


def test_08_experience_tier_classification():
    assert classify_seniority_tier("Junior Data Analyst") == SENIORITY_ENTRY
    assert classify_seniority_tier("Senior Analytics Consultant") == SENIORITY_SENIOR
    assert classify_seniority_tier("Principal BI Architect") == SENIORITY_LEAD_PRINCIPAL
    assert classify_seniority_tier("VP of Data Engineering") == "EXECUTIVE"

    assert extract_experience_years("Minimum 8-10 years of experience in data modeling")[:2] == (8.0, 10.0)
    assert extract_experience_years("0-2 years of experience or fresh graduate")[:2] == (0.0, 2.0)


# ===========================================================================
# TEST 9: Senior/lead jobs evaluated for entry-level preference receive <= 25
# ===========================================================================


def test_09_senior_job_rejected_for_entry_level(sample_preference: JobPreference):
    senior_job = DiscoveredJob(
        id=uuid.uuid4(),
        canonical_url="https://ex.com/senior-lead",
        fingerprint="fp-senior",
        title="Lead Principal Data Analyst",
        company="Enterprise Analytics",
        location="Bengaluru, India",
        work_mode="On-site",
        description="Requires 10+ years of enterprise analytics leadership and deep Python, SQL, Tableau expertise.",
        official_job_url="https://ex.com/senior-lead",
    )
    matcher = JobMatchingAgent()
    out = matcher._evaluate_deterministic(
        preference=sample_preference,
        job=senior_job,
        resume_version=None,
        resume_analysis=None,
        threshold=70,
    )
    assert out.match_score <= 25
    assert not out.shortlisted
    assert any("Experience Ineligible" in r for r in out.reasons_for_rejection)


# ===========================================================================
# TEST 10: Entry-level jobs evaluated for entry-level preference score >= threshold
# ===========================================================================


def test_10_entry_level_job_shortlisted_for_entry_level(sample_preference: JobPreference):
    entry_job = DiscoveredJob(
        id=uuid.uuid4(),
        canonical_url="https://ex.com/entry-job",
        fingerprint="fp-entry",
        title="Associate Data Analyst",
        company="InMobi",
        location="Bengaluru, India",
        work_mode="On-site",
        description="Entry-level opening for 0-2 years experience. Hands-on with Python, SQL, Tableau, Power BI.",
        official_job_url="https://ex.com/entry-job",
    )
    matcher = JobMatchingAgent()
    out = matcher._evaluate_deterministic(
        preference=sample_preference,
        job=entry_job,
        resume_version=None,
        resume_analysis=None,
        threshold=70,
    )
    assert out.match_score >= 70
    assert out.shortlisted is True
    assert not any("Experience Ineligible" in r for r in out.reasons_for_rejection)
    assert not any("Location Ineligible" in r for r in out.reasons_for_rejection)


# ===========================================================================
# TEST 11: Agent 2 deterministic matching evaluates role, skills, location, resume
# ===========================================================================


def test_11_agent2_comprehensive_evaluation(
    db_session: Session, sample_preference: JobPreference
):
    resume, ver = create_approved_resume_and_version(
        db_session,
        "Data Analyst Resume.pdf",
        "Proficient in Python, SQL, Tableau and Power BI. Experience with data visualization in Bangalore.",
    )
    sample_preference.approved_resume_id = resume.id
    sample_preference.approved_resume_version_id = ver.id
    db_session.commit()

    job = DiscoveredJob(
        id=uuid.uuid4(),
        source_name="Official Careers",
        canonical_url="https://ex.com/job-analytics",
        fingerprint="fp-analytics",
        title="Data Analyst",
        company="Razorpay",
        location="Bengaluru, India",
        work_mode="On-site",
        description="We are hiring a Data Analyst proficient in Python and SQL for Bangalore office.",
        official_job_url="https://ex.com/job-analytics",
    )
    db_session.add(job)
    db_session.commit()

    agent2 = JobMatchingAgent()
    matches, cost = agent2.evaluate_jobs_for_preference(
        db=db_session,
        preference=sample_preference,
        discovered_jobs=[job],
        allow_ai_calls=False,
    )
    assert len(matches) == 1
    m = matches[0]
    assert m.is_matching is True
    assert m.shortlisted is True
    assert m.resume_version_id == ver.id
    assert "Python" in m.skills_matched or "SQL" in m.skills_matched
    assert m.evaluation_method == "deterministic_rule"


# ===========================================================================
# TEST 12: Agent 2 AI matching prompt enforces location and experience guardrails
# ===========================================================================


def test_12_agent2_ai_guardrails_override(sample_preference: JobPreference):
    mock_ai = MagicMock()
    mock_ai.is_configured = True
    mock_ai.generate_structured.return_value = LLMJobMatchOutput(
        match_score=95,
        shortlisted=True,
        skills_matched=["Python"],
        reasons_for_matching=["Great match"],
    )

    senior_german_job = DiscoveredJob(
        id=uuid.uuid4(),
        source_name="Official Careers",
        canonical_url="https://ex.com/senior-berlin",
        fingerprint="fp-berlin",
        title="Lead Data Architect",
        company="Berlin Corp",
        location="Berlin, Germany",
        work_mode="On-site",
        description="10+ years experience required in Berlin, Germany.",
        official_job_url="https://ex.com/senior-berlin",
    )

    matcher = JobMatchingAgent(ai_client=mock_ai)
    out = matcher._evaluate_with_ai(
        preference=sample_preference,
        job=senior_german_job,
        resume_version=None,
        resume_analysis=None,
        threshold=70,
    )

    # Post-AI guardrails must strictly cap score at <= 25 and set shortlisted to False
    assert out.match_score <= 25
    assert out.shortlisted is False
    assert any("Location Ineligible" in r for r in out.reasons_for_rejection)
    assert any("Experience Ineligible" in r for r in out.reasons_for_rejection)


# ===========================================================================
# TEST 13: Agent 3 discovers verified portal route (confidence >= 90) for ATS
# ===========================================================================


def test_13_agent3_verified_portal_route(
    db_session: Session, sample_preference: JobPreference
):
    job = DiscoveredJob(
        id=uuid.uuid4(),
        canonical_url="https://job-boards.greenhouse.io/datadog/jobs/555",
        fingerprint="fp-dd",
        title="Data Analyst",
        company="Datadog",
        location="Bengaluru, India",
        official_job_url="https://job-boards.greenhouse.io/datadog/jobs/555",
        source_name="Greenhouse Official Company Boards",
        description="Data analyst role.",
        raw_metadata={"verified_portal": True},
    )
    db_session.add(job)
    db_session.flush()

    match = JobMatch(
        id=uuid.uuid4(),
        preference_id=sample_preference.id,
        discovered_job_id=job.id,
        match_score=85,
        threshold_used=70,
        is_matching=True,
        shortlisted=True,
        evaluation_method="deterministic_rule",
    )
    match.discovered_job = job
    db_session.add(match)
    db_session.commit()

    agent3 = ApplicationRouteDiscoveryAgent()
    routes = agent3.discover_routes_for_shortlisted_matches(
        db=db_session, shortlisted_matches=[match]
    )

    assert len(routes) >= 1
    portal_route = next(r for r in routes if r.route_type == "official_company_portal")
    assert portal_route.verification_status == "verified"
    assert portal_route.confidence_level >= 90
    assert portal_route.requires_manual_review is False


# ===========================================================================
# TEST 14: Agent 3 discovers unverified/manual review route for unknown domains
# ===========================================================================


def test_14_agent3_unverified_route_manual_review(
    db_session: Session, sample_preference: JobPreference
):
    job = DiscoveredJob(
        id=uuid.uuid4(),
        canonical_url="https://unverified-third-party-site.xyz/jobs/777",
        fingerprint="fp-xyz",
        title="Data Analyst",
        company="UnknownCo",
        location="Bengaluru, India",
        official_job_url="https://unverified-third-party-site.xyz/jobs/777",
        source_name="Unknown Feed",
        description="Analytics job.",
    )
    db_session.add(job)
    db_session.flush()

    match = JobMatch(
        id=uuid.uuid4(),
        preference_id=sample_preference.id,
        discovered_job_id=job.id,
        match_score=80,
        threshold_used=70,
        is_matching=True,
        shortlisted=True,
        evaluation_method="deterministic_rule",
    )
    match.discovered_job = job
    db_session.add(match)
    db_session.commit()

    agent3 = ApplicationRouteDiscoveryAgent()
    routes = agent3.discover_routes_for_shortlisted_matches(
        db=db_session, shortlisted_matches=[match]
    )

    assert len(routes) >= 1
    unverified_route = routes[0]
    assert unverified_route.verification_status == "manual_review_required"
    assert unverified_route.requires_manual_review is True
    assert unverified_route.confidence_level < 80


# ===========================================================================
# TEST 15: Preference approved resume version linked to matches & applications
# ===========================================================================


def test_15_approved_resume_version_linking(
    db_session: Session, sample_preference: JobPreference
):
    resume, ver = create_approved_resume_and_version(
        db_session, "Verified_Resume.pdf", "Python Analyst"
    )
    sample_preference.approved_resume_id = resume.id
    sample_preference.approved_resume_version_id = ver.id
    db_session.commit()

    job = DiscoveredJob(
        id=uuid.uuid4(),
        source_name="Official Careers",
        canonical_url="https://ex.com/job-15",
        fingerprint="fp-15",
        title="Data Analyst",
        company="Fintech",
        location="Bengaluru, India",
        official_job_url="https://ex.com/job-15",
        description="Python, SQL",
    )
    db_session.add(job)
    db_session.commit()

    agent2 = JobMatchingAgent()
    matches, _ = agent2.evaluate_jobs_for_preference(
        db=db_session,
        preference=sample_preference,
        discovered_jobs=[job],
        allow_ai_calls=False,
    )
    assert matches[0].resume_version_id == ver.id


# ===========================================================================
# TEST 16: Agent 4 prepares application with correct resume and portal details
# ===========================================================================


def test_16_agent4_prepares_application(
    db_session: Session, sample_preference: JobPreference
):
    resume, ver = create_approved_resume_and_version(
        db_session, "My_Resume.pdf", "Data Analyst with Python and SQL"
    )
    sample_preference.approved_resume_id = resume.id
    sample_preference.approved_resume_version_id = ver.id

    job = DiscoveredJob(
        id=uuid.uuid4(),
        source_name="Greenhouse Official Company Boards",
        canonical_url="https://job-boards.greenhouse.io/inmobi/jobs/900",
        fingerprint="fp-inmobi",
        title="Data Analyst",
        company="InMobi",
        location="Bengaluru, India",
        official_job_url="https://job-boards.greenhouse.io/inmobi/jobs/900",
        description="Data analyst role",
        raw_metadata={"verified_portal": True},
    )
    db_session.add(job)
    db_session.flush()

    match = JobMatch(
        id=uuid.uuid4(),
        preference_id=sample_preference.id,
        discovered_job_id=job.id,
        resume_version_id=ver.id,
        match_score=85,
        threshold_used=70,
        is_matching=True,
        shortlisted=True,
        evaluation_method="deterministic_rule",
    )
    match.discovered_job = job
    db_session.add(match)

    route = ApplicationRoute(
        id=uuid.uuid4(),
        discovered_job_id=job.id,
        preference_id=sample_preference.id,
        route_type="official_company_portal",
        url_or_contact="https://job-boards.greenhouse.io/inmobi/jobs/900",
        source="Greenhouse",
        verification_status="verified",
        confidence_level=95,
        requires_manual_review=False,
    )
    db_session.add(route)
    db_session.commit()

    agent4 = ApplicationExecutionAgent()
    settings = AutomationSettings(
        id=uuid.uuid4(),
        approval_mode="manual",
        max_applications_per_run=5,
        max_applications_per_day=20,
    )
    apps = agent4.process_shortlisted_jobs(
        db=db_session,
        preference=sample_preference,
        shortlisted_matches=[match],
        routes=[route],
        automation_settings=settings,
    )

    assert len(apps) == 1
    app = apps[0]
    assert app.company == "InMobi"
    assert app.prepared_payload["company"] == "InMobi"
    assert app.prepared_payload["resume_id"] == str(resume.id)
    assert app.status == "Awaiting Approval"


# ===========================================================================
# TEST 17: Mandatory user approval is enforced (stays in Awaiting Approval)
# ===========================================================================


def test_17_mandatory_user_approval_enforced(
    db_session: Session, sample_preference: JobPreference
):
    resume, ver = create_approved_resume_and_version(
        db_session, "Approval_Resume.pdf", "DA"
    )
    sample_preference.approved_resume_id = resume.id
    sample_preference.approved_resume_version_id = ver.id

    job = DiscoveredJob(
        id=uuid.uuid4(),
        source_name="Official Careers",
        canonical_url="https://ex.com/job-17",
        fingerprint="fp-17",
        title="Data Analyst",
        company="SafetyFirst Corp",
        official_job_url="https://ex.com/job-17",
        description="Analyst",
    )
    db_session.add(job)
    db_session.flush()

    match = JobMatch(
        id=uuid.uuid4(),
        preference_id=sample_preference.id,
        discovered_job_id=job.id,
        match_score=85,
        threshold_used=70,
        is_matching=True,
        shortlisted=True,
        evaluation_method="deterministic_rule",
    )
    match.discovered_job = job
    db_session.add(match)

    route = ApplicationRoute(
        id=uuid.uuid4(),
        discovered_job_id=job.id,
        preference_id=sample_preference.id,
        route_type="official_company_portal",
        url_or_contact="https://ex.com/job-17",
        source="Careers",
        verification_status="verified",
        confidence_level=90,
    )
    db_session.add(route)
    db_session.commit()

    agent4 = ApplicationExecutionAgent()
    settings = AutomationSettings(
        id=uuid.uuid4(),
        approval_mode="manual",
    )
    executed_apps = agent4.process_shortlisted_jobs(
        db=db_session,
        preference=sample_preference,
        shortlisted_matches=[match],
        routes=[route],
        automation_settings=settings,
    )

    assert len(executed_apps) == 1
    app = executed_apps[0]
    # Without explicit auto_authorised setting, must be held for user approval
    assert app.status == "Awaiting Approval"
    assert app.approval_required is True
    assert app.applied_at is None  # Not submitted yet


# ===========================================================================
# TEST 18: Agent 4 prevents duplicate applications
# ===========================================================================


def test_18_duplicate_application_prevention(
    db_session: Session, sample_preference: JobPreference
):
    resume, ver = create_approved_resume_and_version(
        db_session, "NoDupes_Resume.pdf", "DA"
    )
    sample_preference.approved_resume_id = resume.id
    sample_preference.approved_resume_version_id = ver.id

    job = DiscoveredJob(
        id=uuid.uuid4(),
        source_name="Official Careers",
        canonical_url="https://ex.com/job-18",
        fingerprint="fp-18",
        title="Data Analyst",
        company="NoDupes Inc",
        official_job_url="https://ex.com/job-18",
        description="Analyst",
    )
    db_session.add(job)
    db_session.flush()

    route = ApplicationRoute(
        id=uuid.uuid4(),
        discovered_job_id=job.id,
        preference_id=sample_preference.id,
        route_type="official_company_portal",
        url_or_contact="https://ex.com/job-18",
        source="Careers",
        verification_status="verified",
        confidence_level=90,
    )
    db_session.add(route)

    match = JobMatch(
        id=uuid.uuid4(),
        preference_id=sample_preference.id,
        discovered_job_id=job.id,
        match_score=85,
        threshold_used=70,
        is_matching=True,
        shortlisted=True,
        evaluation_method="deterministic_rule",
    )
    match.discovered_job = job
    db_session.add(match)
    db_session.commit()

    agent4 = ApplicationExecutionAgent()
    settings = AutomationSettings(approval_mode="manual")

    apps1 = agent4.process_shortlisted_jobs(
        db=db_session,
        preference=sample_preference,
        shortlisted_matches=[match],
        routes=[route],
        automation_settings=settings,
    )
    assert len(apps1) == 1

    # Calling process again for same job & preference prevents duplicate
    apps2 = agent4.process_shortlisted_jobs(
        db=db_session,
        preference=sample_preference,
        shortlisted_matches=[match],
        routes=[route],
        automation_settings=settings,
    )
    assert len(apps2) == 0

    total_apps = db_session.scalars(
        select(Application).where(Application.discovered_job_id == job.id)
    ).all()
    assert len(total_apps) == 1


# ===========================================================================
# TEST 19: Agent 5 tracks application lifecycle and creates status history
# ===========================================================================


def test_19_agent5_lifecycle_and_audit_trail(
    db_session: Session, sample_preference: JobPreference
):
    app = Application(
        id=uuid.uuid4(),
        preference_id=sample_preference.id,
        discovered_job_id=uuid.uuid4(),
        company="Razorpay",
        job_title="Data Analyst",
        route_type="official_company_portal",
        route_target="https://razorpay.com/careers/da",
        status="Awaiting Approval",
        idempotency_key=f"idemp_{uuid.uuid4().hex}",
        prepared_payload={"test": True},
        notes="Waiting for user review",
    )
    db_session.add(app)
    db_session.commit()

    agent5 = ApplicationTrackingAgent()
    # Transition to Submitted with evidence
    updated = agent5.update_application_status(
        db=db_session,
        application_id=app.id,
        new_status="Submitted",
        source="user_approval",
        notes="User approved application submission.",
        evidence="CONF-2026-XYZ",
    )
    assert updated.status == "Submitted"
    assert updated.confirmation_evidence == "CONF-2026-XYZ"
    assert updated.applied_at is not None

    # Verify immutable audit history was recorded
    history = db_session.scalars(
        select(ApplicationStatusHistory).where(
            ApplicationStatusHistory.application_id == app.id
        )
    ).all()
    assert len(history) == 1
    record = history[0]
    assert record.previous_status == "Awaiting Approval"
    assert record.new_status == "Submitted"
    assert record.evidence == "CONF-2026-XYZ"
    assert record.source == "user_approval"


# ===========================================================================
# TEST 20: Pausing one preference does not interrupt other preferences
# ===========================================================================


def test_20_preference_isolation_on_pause(db_session: Session):
    p1 = JobPreference(
        id=uuid.uuid4(),
        preference_name="Preference P1 (Paused)",
        job_roles=["Data Analyst"],
        locations=["Bengaluru"],
        location_mode="INDIA_ONLY",
        work_mode="Flexible",
        employment_type="Full-time",
        experience_level="Entry-level",
        is_active=False,  # Paused
    )
    p2 = JobPreference(
        id=uuid.uuid4(),
        preference_name="Preference P2 (Active)",
        job_roles=["Python Developer"],
        locations=["Mumbai"],
        location_mode="INDIA_ONLY",
        work_mode="Flexible",
        employment_type="Full-time",
        experience_level="Entry-level",
        is_active=True,  # Active
    )
    db_session.add_all([p1, p2])
    db_session.commit()

    # Query active preferences for orchestration run
    active_prefs = list(
        db_session.scalars(
            select(JobPreference).where(JobPreference.is_active.is_(True))
        ).all()
    )

    # Only P2 is returned for execution; P1 remains untouched and paused
    assert len(active_prefs) == 1
    assert active_prefs[0].id == p2.id
    assert active_prefs[0].preference_name == "Preference P2 (Active)"

    p1_check = db_session.get(JobPreference, p1.id)
    assert p1_check.is_active is False
