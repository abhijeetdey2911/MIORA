"""Unit and integration tests for MIORA Job Discovery and Matching Location Filtering."""

import uuid
from typing import List, Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.job_preference import JobPreference
from app.models.multi_agent import DiscoveredJob, JobMatch
from app.services.agents.agent1_discovery import (
    BaseJobSourceAdapter,
    JobDiscoveryAgent,
    RawDiscoveredJobItem,
)
from app.services.agents.agent2_matching import JobMatchingAgent
from app.services.location_matcher import (
    evaluate_location_eligibility,
    extract_canonical_city,
)


@pytest.fixture
def in_memory_db():
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


class MockJobSourceAdapter(BaseJobSourceAdapter):
    """Test double returning controlled listings for discovery verification."""

    source_name = "Mock Adapter"
    adapter_type = "mock"

    def __init__(self, raw_items: List[RawDiscoveredJobItem]) -> None:
        self.raw_items = raw_items

    def fetch_jobs(
        self,
        preference: JobPreference,
        max_results: int = 25,
    ) -> List[RawDiscoveredJobItem]:
        filtered = []
        for item in self.raw_items:
            loc_elig = evaluate_location_eligibility(
                job_location=item.location,
                job_work_mode=item.work_mode,
                preference_locations=preference.locations or [],
                location_mode=getattr(preference, "location_mode", "INDIA_ONLY") or "INDIA_ONLY",
                preference_work_mode=preference.work_mode,
                job_description=item.description,
                raw_metadata=item.raw_metadata,
            )
            if loc_elig.is_eligible:
                filtered.append(item)
            if len(filtered) >= max_results:
                break
        return filtered


# ==============================================================================
# 1. CORE REQUIREMENT 8 TEST CASES
# ==============================================================================


def test_bangalore_onsite_job_is_eligible():
    """Requirement 8: Bangalore on-site job: eligible."""
    res = evaluate_location_eligibility(
        job_location="Bangalore, Karnataka",
        job_work_mode="On-site",
        preference_locations=["Bangalore", "Hyderabad"],
        location_mode="INDIA_ONLY",
    )
    assert res.is_eligible is True
    assert "Bangalore" in res.reason


def test_hyderabad_hybrid_job_eligible_if_selected():
    """Requirement 8: Hyderabad hybrid job: eligible if selected, excluded if not."""
    # Selected case
    res_selected = evaluate_location_eligibility(
        job_location="Hyderabad, Telangana",
        job_work_mode="Hybrid",
        preference_locations=["Bangalore", "Hyderabad"],
        location_mode="SELECTED_LOCATIONS_ONLY",
    )
    assert res_selected.is_eligible is True
    assert "Hyderabad" in res_selected.reason

    # Not selected case
    res_not_selected = evaluate_location_eligibility(
        job_location="Hyderabad, Telangana",
        job_work_mode="Hybrid",
        preference_locations=["Bangalore", "Pune"],
        location_mode="SELECTED_LOCATIONS_ONLY",
    )
    assert res_not_selected.is_eligible is False
    assert "does not match selected preferred locations" in res_not_selected.reason


def test_hamburg_onsite_job_is_excluded():
    """Requirement 8: Hamburg on-site job: excluded."""
    # Under INDIA_ONLY
    res_india = evaluate_location_eligibility(
        job_location="Hamburg, Germany",
        job_work_mode="On-site",
        preference_locations=["Bangalore"],
        location_mode="INDIA_ONLY",
    )
    assert res_india.is_eligible is False
    assert "International on-site job" in res_india.reason

    # Under SELECTED_LOCATIONS_ONLY
    res_selected = evaluate_location_eligibility(
        job_location="Hamburg",
        job_work_mode="On-site",
        preference_locations=["Bangalore", "Hyderabad"],
        location_mode="SELECTED_LOCATIONS_ONLY",
    )
    assert res_selected.is_eligible is False

    # Under WORLDWIDE_REMOTE: on-site international jobs must STILL be excluded!
    res_ww = evaluate_location_eligibility(
        job_location="Hamburg, Germany",
        job_work_mode="On-site",
        preference_locations=["Bangalore"],
        location_mode="WORLDWIDE_REMOTE",
    )
    assert res_ww.is_eligible is False
    assert "International on-site job" in res_ww.reason


def test_germany_remote_job_excluded_unless_india_confirmed():
    """Requirement 8: Germany remote job: excluded unless India eligibility is explicitly confirmed."""
    # Without India confirmation -> excluded
    res_unconfirmed = evaluate_location_eligibility(
        job_location="Germany",
        job_work_mode="Remote",
        preference_locations=["Bangalore"],
        location_mode="INDIA_ONLY",
        raw_metadata={"candidate_required_location": "Germany"},
    )
    assert res_unconfirmed.is_eligible is False
    assert "Remote job restricted to candidates in" in res_unconfirmed.reason

    # With explicit confirmation in job description -> eligible
    res_confirmed = evaluate_location_eligibility(
        job_location="Germany",
        job_work_mode="Remote",
        preference_locations=["Bangalore"],
        location_mode="INDIA_ONLY",
        job_description="Candidates based in India or Germany are welcome to apply.",
    )
    assert res_confirmed.is_eligible is True


def test_india_wide_remote_job_is_eligible():
    """Requirement 8: India-wide remote job: eligible."""
    res = evaluate_location_eligibility(
        job_location="Remote (India)",
        job_work_mode="Remote",
        preference_locations=["Bangalore"],
        location_mode="INDIA_ONLY",
    )
    assert res.is_eligible is True
    assert "India-wide remote job is eligible" in res.reason


def test_worldwide_remote_job_eligible_only_in_worldwide_remote_mode():
    """Requirement 8: Worldwide remote job: eligible only in WORLDWIDE_REMOTE mode."""
    # In INDIA_ONLY mode -> excluded
    res_india_mode = evaluate_location_eligibility(
        job_location="Worldwide",
        job_work_mode="Remote",
        preference_locations=["Bangalore"],
        location_mode="INDIA_ONLY",
    )
    assert res_india_mode.is_eligible is False
    assert "Worldwide remote job excluded under strict India mode" in res_india_mode.reason

    # In WORLDWIDE_REMOTE mode -> eligible
    res_ww_mode = evaluate_location_eligibility(
        job_location="Worldwide",
        job_work_mode="Remote",
        preference_locations=["Bangalore"],
        location_mode="WORLDWIDE_REMOTE",
    )
    assert res_ww_mode.is_eligible is True
    assert "Worldwide remote job is eligible under WORLDWIDE_REMOTE mode" in res_ww_mode.reason


def test_job_with_unknown_location_excluded_in_strict_mode():
    """Requirement 8: Job with unknown location: excluded in strict mode."""
    res_none = evaluate_location_eligibility(
        job_location=None,
        job_work_mode="On-site",
        preference_locations=["Bangalore"],
        location_mode="INDIA_ONLY",
    )
    assert res_none.is_eligible is False
    assert "Missing or ambiguous location" in res_none.reason

    res_empty = evaluate_location_eligibility(
        job_location="",
        job_work_mode="On-site",
        preference_locations=["Bangalore"],
        location_mode="SELECTED_LOCATIONS_ONLY",
    )
    assert res_empty.is_eligible is False


# ==============================================================================
# 2. LOCATION NORMALIZATION & ALIASES TESTS
# ==============================================================================


def test_city_aliases_and_spelling_variations():
    """Requirement 5: Normalize city, state and country names with aliases."""
    # Bangalore / Bengaluru
    assert extract_canonical_city("Bengaluru") == "bangalore"
    assert extract_canonical_city("BLR Urban") == "bangalore"
    assert extract_canonical_city("Bangalore, Karnataka") == "bangalore"

    # Bombay / Mumbai
    assert extract_canonical_city("Bombay") == "mumbai"
    assert extract_canonical_city("Navi Mumbai") == "mumbai"

    # Gurgaon / Noida / Delhi NCR
    assert extract_canonical_city("Gurugram") == "delhi ncr"
    assert extract_canonical_city("Noida, UP") == "delhi ncr"

    # Calcutta / Kolkata
    assert extract_canonical_city("Calcutta") == "kolkata"

    # Madras / Chennai
    assert extract_canonical_city("Madras") == "chennai"

    # Poona / Pune
    assert extract_canonical_city("Poona") == "pune"

    # Spelled differently in preference and job
    res = evaluate_location_eligibility(
        job_location="Bengaluru",
        job_work_mode="On-site",
        preference_locations=["Bangalore"],
        location_mode="SELECTED_LOCATIONS_ONLY",
    )
    assert res.is_eligible is True
    assert res.matched_location == "Bangalore"


# ==============================================================================
# 3. AGENT 2 MATCHING: HIGH SKILLS CANNOT OVERRIDE INCOMPATIBLE LOCATION
# ==============================================================================


def test_high_skills_score_cannot_override_incompatible_location(in_memory_db: Session):
    """Requirement 6: Location compatibility is a mandatory eligibility check.
    A high skills score must NOT override an incompatible location (e.g. Hamburg, Germany).
    """
    preference = JobPreference(
        id=uuid.uuid4(),
        preference_name="Data Analytics Lead",
        job_roles=["Data Analyst", "Senior Data Analyst"],
        locations=["Bangalore", "Hyderabad"],
        location_mode="INDIA_ONLY",
        work_mode="Hybrid",
        employment_type="Full-time",
        experience_level="Experienced",
        min_salary=800000,
        max_salary=2000000,
        currency="INR",
        skills=["Python", "SQL", "Tableau", "PowerBI"],
        minimum_match_score=70,
        is_active=True,
    )
    in_memory_db.add(preference)
    in_memory_db.commit()

    # Job in Hamburg, Germany with 100% matching role and skills
    hamburg_job = DiscoveredJob(
        id=uuid.uuid4(),
        source_name="Arbeitnow Public API",
        canonical_url="https://example.com/jobs/hamburg-data-analyst",
        fingerprint="hamburg-fingerprint-123",
        title="Senior Data Analyst",
        company="Nordic Tech GmbH",
        location="Hamburg, Germany",
        work_mode="On-site",
        employment_type="Full-time",
        description="Senior Data Analyst with strong Python, SQL, Tableau, PowerBI. Must work on-site in Hamburg.",
        min_salary=900000,
        max_salary=1500000,
        salary_currency="INR",
        official_job_url="https://example.com/jobs/hamburg-data-analyst",
    )
    in_memory_db.add(hamburg_job)
    in_memory_db.commit()

    matcher = JobMatchingAgent(ai_client=None)
    matches, _ = matcher.evaluate_jobs_for_preference(
        db=in_memory_db,
        preference=preference,
        discovered_jobs=[hamburg_job],
        allow_ai_calls=False,
    )

    assert len(matches) == 1
    match = matches[0]

    # Must be marked ineligible, not shortlisted, and score capped
    assert match.is_matching is False
    assert match.shortlisted is False
    assert match.match_score <= 25
    assert any("Location Ineligible" in r for r in match.reasons_for_rejection)


# ==============================================================================
# 4. AGENT 1 DISCOVERY: EXCLUDES INTERNATIONAL JOBS FOR INDIA PREFERENCE
# ==============================================================================


def test_discovery_agent_filters_out_international_jobs(in_memory_db: Session):
    """Requirement 1 & 4: Agent 1 does not discover/persist international on-site jobs for Indian preference."""
    preference = JobPreference(
        id=uuid.uuid4(),
        preference_name="Data Analyst - India",
        job_roles=["Data Analyst"],
        locations=["Bangalore"],
        location_mode="INDIA_ONLY",
        work_mode="Hybrid",
        employment_type="Full-time",
        experience_level="Entry-level",
        skills=["Python", "SQL"],
        minimum_match_score=70,
        is_active=True,
    )
    in_memory_db.add(preference)
    in_memory_db.commit()

    raw_items = [
        RawDiscoveredJobItem(
            source_name="Mock Adapter",
            external_job_id="1",
            title="Data Analyst",
            company="Bangalore Analytics",
            description="Python SQL role in Bangalore.",
            official_job_url="https://example.com/jobs/bangalore-analyst",
            location="Bangalore, Karnataka",
            work_mode="On-site",
        ),
        RawDiscoveredJobItem(
            source_name="Mock Adapter",
            external_job_id="2",
            title="Data Analyst",
            company="Hamburg Big Data",
            description="Python SQL role in Hamburg.",
            official_job_url="https://example.com/jobs/hamburg-analyst",
            location="Hamburg, Germany",
            work_mode="On-site",
        ),
        RawDiscoveredJobItem(
            source_name="Mock Adapter",
            external_job_id="3",
            title="Data Analyst",
            company="Berlin AI Labs",
            description="Python SQL role in Berlin.",
            official_job_url="https://example.com/jobs/berlin-analyst",
            location="Berlin, Germany",
            work_mode="Remote",
            raw_metadata={"candidate_required_location": "Germany"},
        ),
    ]

    mock_adapter = MockJobSourceAdapter(raw_items)
    agent = JobDiscoveryAgent(adapters=[mock_adapter])

    discovered = agent.discover_for_preference(
        db=in_memory_db,
        preference=preference,
        max_jobs=10,
    )

    # Only the Bangalore job should be discovered and persisted
    assert len(discovered) == 1
    assert discovered[0].title == "Data Analyst"
    assert "Bangalore" in discovered[0].location
