"""Comprehensive automated test suite for MIORA's Application Lifecycle, Approval & Submission Audit.

Verifies:
1. Preparation puts applications in 'Prepared' then 'Awaiting Approval' in manual mode.
2. User approval transitions 'Awaiting Approval' -> 'Approved', NEVER directly to 'Submitted'.
3. Internal approval references (USER-APPROVAL-REC-...) are kept distinct and cannot satisfy external confirmation.
4. Submission begins only after explicit user approval, transitioning 'Approved' -> 'Submission In Progress'.
5. Reliable external confirmation transitions to 'Submitted' with confirmation evidence and external application ID.
6. Uncertain external outcome transitions to 'Submission Unconfirmed' with confirmation_evidence=None.
7. External failure transitions to 'Failed' with error_message and increments retry_count.
8. Retrying 'Failed' application transitions to 'Submission In Progress' and can succeed.
9. Duplicate submission prevention blocks re-submission of already 'Submitted' applications.
10. Reconciliation of 'Submission Unconfirmed' requires genuine external evidence for 'Submitted' or allows returning to 'Approved'.
11. Historical reconciliation script correctly audits Finom & Emma (USER-APPROVED-RECEIPT) records without fabricating missing evidence.
12. Telegram notifications strictly map to real lifecycle events and never notify successful submission on approval alone.
"""

from datetime import datetime, timezone
from typing import Optional
from unittest.mock import MagicMock, patch
import uuid

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
    Notification,
)
from app.models.resume import Resume
from app.models.resume_intelligence import ResumeVersion
from app.services.agents.agent4_execution import ApplicationExecutionAgent
from app.services.agents.agent5_tracking import ApplicationTrackingAgent
from app.services.telegram_service import telegram_service
from scripts.reconcile_existing_applications import reconcile_applications


# ---------------------------------------------------------------------------
# Test Fixtures & Helpers
# ---------------------------------------------------------------------------


def make_test_resume(
    name: str = "Test_Resume.pdf",
    text: str = "Python, SQL, Analytics Engineer",
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
    text: str = "Python, SQL, Analytics Engineer",
) -> tuple[Resume, ResumeVersion]:
    resume = make_test_resume(name, text)
    db.add(resume)
    db.flush()

    ver = ResumeVersion(
        id=uuid.uuid4(),
        parent_resume_id=resume.id,
        version_number=1,
        title="Approved Analytics Resume",
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
    """Isolated in-memory SQLite session with full MIORA schema."""
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
    pref = JobPreference(
        id=uuid.uuid4(),
        preference_name="Data Analyst India",
        job_roles=["Data Analyst", "Analytics Engineer"],
        locations=["Bengaluru", "Mumbai"],
        location_mode="INDIA_ONLY",
        work_mode="Flexible",
        employment_type="Full-time",
        experience_level="Entry-level",
        min_salary=800000,
        currency="INR",
        skills=["Python", "SQL"],
        minimum_match_score=70,
        is_active=True,
    )
    db_session.add(pref)
    db_session.commit()
    return pref


def create_sample_job_match_and_route(
    db_session: Session,
    preference: JobPreference,
    company: str = "Razorpay",
    title: str = "Data Analyst",
    route_type: str = "official_company_portal",
    route_url: str = "https://boards.greenhouse.io/razorpay/jobs/9912",
) -> tuple[DiscoveredJob, JobMatch, ApplicationRoute]:
    job = DiscoveredJob(
        id=uuid.uuid4(),
        source_name="Greenhouse Official",
        canonical_url=f"https://boards.greenhouse.io/razorpay/jobs/{uuid.uuid4().hex[:8]}",
        fingerprint=uuid.uuid4().hex,
        title=title,
        company=company,
        location="Bengaluru, India",
        official_job_url=route_url,
        description="Looking for Data Analyst with SQL and Python.",
    )
    db_session.add(job)
    db_session.flush()

    match = JobMatch(
        id=uuid.uuid4(),
        preference_id=preference.id,
        discovered_job_id=job.id,
        match_score=92,
        is_matching=True,
        shortlisted=True,
    )
    db_session.add(match)
    db_session.flush()

    route = ApplicationRoute(
        id=uuid.uuid4(),
        discovered_job_id=job.id,
        preference_id=preference.id,
        route_type=route_type,
        url_or_contact=route_url,
        source="official_careers_page",
        verification_status="verified",
        confidence_level=95,
        requires_manual_review=False,
    )
    db_session.add(route)
    db_session.commit()
    return job, match, route


# ===========================================================================
# TEST 1: Preparation puts application in Prepared then Awaiting Approval
# ===========================================================================


def test_01_preparation_sets_prepared_and_awaiting_approval(
    db_session: Session, sample_preference: JobPreference
):
    resume, ver = create_approved_resume_and_version(db_session)
    sample_preference.approved_resume_id = resume.id
    sample_preference.approved_resume_version_id = ver.id

    job, match, route = create_sample_job_match_and_route(
        db_session, sample_preference, company="Swiggy", title="BI Analyst"
    )

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
    assert app.status == "Awaiting Approval"
    assert app.approved_by_user is False
    assert app.approved_at is None
    assert app.approval_reference is None
    assert app.applied_at is None
    assert app.confirmation_evidence is None
    assert app.submission_result is None

    # Verify status history audit trail
    history = db_session.scalars(
        select(ApplicationStatusHistory)
        .where(ApplicationStatusHistory.application_id == app.id)
        .order_by(ApplicationStatusHistory.created_at.asc())
    ).all()
    statuses = [h.new_status for h in history]
    assert "Prepared" in statuses
    assert "Awaiting Approval" in statuses


# ===========================================================================
# TEST 2: User approval transitions to 'Approved', NEVER directly to 'Submitted'
# ===========================================================================


def test_02_user_approval_transitions_to_approved_never_submitted(
    db_session: Session, sample_preference: JobPreference
):
    resume, ver = create_approved_resume_and_version(db_session)
    sample_preference.approved_resume_id = resume.id
    sample_preference.approved_resume_version_id = ver.id

    job, match, route = create_sample_job_match_and_route(
        db_session, sample_preference, company="CRED", title="Data Analyst"
    )

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
    app = apps[0]
    assert app.status == "Awaiting Approval"

    # User explicitly approves the application
    with patch.object(telegram_service, "_send_telegram_http", return_value=(True, None)):
        approved_app = agent4.approve_application(
            db=db_session,
            application_id=app.id,
            notes="Reviewed resume alignment and approved.",
        )

    # CRITICAL AUDIT ASSERTIONS
    assert approved_app.status == "Approved"
    assert approved_app.status != "Submitted", "User approval must NEVER directly mark application as Submitted!"
    assert approved_app.approved_by_user is True
    assert approved_app.approved_at is not None
    assert approved_app.approval_reference is not None
    assert approved_app.approval_reference.startswith("USER-APPROVAL-REC-")
    assert approved_app.applied_at is None
    assert approved_app.confirmation_evidence is None
    assert approved_app.submission_result is None

    # History audit check
    hist = db_session.scalars(
        select(ApplicationStatusHistory)
        .where(
            ApplicationStatusHistory.application_id == app.id,
            ApplicationStatusHistory.new_status == "Approved",
        )
    ).first()
    assert hist is not None
    assert hist.source == "user_approval"


# ===========================================================================
# TEST 3: Submitted cannot be set without genuine external evidence
# ===========================================================================


def test_03_submitted_cannot_be_set_without_genuine_external_evidence(
    db_session: Session, sample_preference: JobPreference
):
    resume, ver = create_approved_resume_and_version(db_session)
    job, match, route = create_sample_job_match_and_route(db_session, sample_preference)

    app = Application(
        id=uuid.uuid4(),
        preference_id=sample_preference.id,
        discovered_job_id=job.id,
        company=job.company,
        job_title=job.title,
        route_type=route.route_type,
        route_target=route.url_or_contact,
        status="Approved",
        approved_by_user=True,
        resume_id=resume.id,
        resume_version_id=ver.id,
        idempotency_key="key-test-03",
    )
    db_session.add(app)
    db_session.commit()

    agent5 = ApplicationTrackingAgent()

    # Attempt 1: Marking Submitted without evidence must fail
    with pytest.raises(ValueError, match="Cannot mark application as 'Submitted' without confirmation evidence"):
        agent5.update_application_status(db_session, app.id, new_status="Submitted", evidence=None)

    # Attempt 2: Marking Submitted with an internal user approval receipt must fail
    with pytest.raises(ValueError, match="Internal user approval reference cannot be used as external confirmation evidence"):
        agent5.update_application_status(
            db_session,
            app.id,
            new_status="Submitted",
            evidence="USER-APPROVED-RECEIPT-ABCD1234",
        )

    with pytest.raises(ValueError, match="Internal user approval reference cannot be used as external confirmation evidence"):
        agent5.update_application_status(
            db_session,
            app.id,
            new_status="Submitted",
            evidence="USER-APPROVAL-REC-55AA99",
        )


# ===========================================================================
# TEST 4: Submission begins only from Approved and sets Submission In Progress
# ===========================================================================


def test_04_submission_begins_only_from_approved_and_sets_submission_in_progress(
    db_session: Session, sample_preference: JobPreference
):
    resume, ver = create_approved_resume_and_version(db_session)
    job, match, route = create_sample_job_match_and_route(db_session, sample_preference)

    app = Application(
        id=uuid.uuid4(),
        preference_id=sample_preference.id,
        discovered_job_id=job.id,
        company=job.company,
        job_title=job.title,
        route_type=route.route_type,
        route_target=route.url_or_contact,
        status="Awaiting Approval",
        approved_by_user=False,
        resume_id=resume.id,
        resume_version_id=ver.id,
        idempotency_key="key-test-04",
    )
    db_session.add(app)
    db_session.commit()

    agent4 = ApplicationExecutionAgent()

    # Submitting an unapproved application must fail
    with pytest.raises(ValueError, match="Application requires user approval before submission"):
        agent4.execute_submission(db_session, app.id)

    # Approve first
    agent4.approve_application(db_session, app.id)
    assert app.status == "Approved"

    # Now execute submission with uncertain outcome to inspect intermediate states
    with patch.object(telegram_service, "_send_telegram_http", return_value=(True, None)):
        agent4.execute_submission(db_session, app.id, simulate_uncertain=True)

    # Verify history recorded 'Submission In Progress'
    in_progress_hist = db_session.scalars(
        select(ApplicationStatusHistory).where(
            ApplicationStatusHistory.application_id == app.id,
            ApplicationStatusHistory.new_status == "Submission In Progress",
        )
    ).first()
    assert in_progress_hist is not None
    assert in_progress_hist.previous_status == "Approved"
    assert app.submission_attempted_at is not None


# ===========================================================================
# TEST 5: External submission confirmed transitions to 'Submitted'
# ===========================================================================


def test_05_external_submission_confirmed_sets_submitted_with_receipt(
    db_session: Session, sample_preference: JobPreference
):
    resume, ver = create_approved_resume_and_version(db_session)
    job, match, route = create_sample_job_match_and_route(
        db_session, sample_preference, company="PhonePe", title="Data Analyst"
    )

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
        preferred_resume_version_id=ver.id,
    )
    app = apps[0]

    # Step 1: User approves
    agent4.approve_application(db_session, app.id)
    assert app.status == "Approved"

    # Step 2: Execute submission with explicit external confirmation receipt
    external_receipt = "PORTAL-CONFIRM-883921"
    with patch.object(telegram_service, "_send_telegram_http", return_value=(True, None)):
        submitted_app = agent4.execute_submission(
            db=db_session,
            application_id=app.id,
            explicit_confirmation_evidence=external_receipt,
            explicit_application_id="ATS-APP-9988",
        )

    assert submitted_app.status == "Submitted"
    assert submitted_app.applied_at is not None
    assert submitted_app.confirmation_evidence == external_receipt
    assert submitted_app.external_application_id == "ATS-APP-9988"
    assert submitted_app.submission_result == "success"
    assert submitted_app.follow_up_reminder_at is not None

    # History audit check
    submitted_hist = db_session.scalars(
        select(ApplicationStatusHistory).where(
            ApplicationStatusHistory.application_id == app.id,
            ApplicationStatusHistory.new_status == "Submitted",
        )
    ).first()
    assert submitted_hist is not None
    assert submitted_hist.previous_status == "Submission In Progress"
    assert submitted_hist.evidence == external_receipt


# ===========================================================================
# TEST 6: Uncertain external result transitions to 'Submission Unconfirmed'
# ===========================================================================


def test_06_external_submission_uncertain_sets_submission_unconfirmed(
    db_session: Session, sample_preference: JobPreference
):
    resume, ver = create_approved_resume_and_version(db_session)
    job, match, route = create_sample_job_match_and_route(db_session, sample_preference)

    agent4 = ApplicationExecutionAgent()
    settings = AutomationSettings(id=uuid.uuid4(), approval_mode="manual")

    apps = agent4.process_shortlisted_jobs(
        db=db_session,
        preference=sample_preference,
        shortlisted_matches=[match],
        routes=[route],
        automation_settings=settings,
        preferred_resume_version_id=ver.id,
    )
    app = apps[0]
    agent4.approve_application(db_session, app.id)

    # Submitting with uncertain outcome
    with patch.object(telegram_service, "_send_telegram_http", return_value=(True, None)):
        unconfirmed_app = agent4.execute_submission(
            db=db_session,
            application_id=app.id,
            simulate_uncertain=True,
        )

    assert unconfirmed_app.status == "Submission Unconfirmed"
    assert unconfirmed_app.confirmation_evidence is None
    assert unconfirmed_app.submission_result == "unconfirmed"
    assert unconfirmed_app.applied_at is None

    # Verify cannot re-submit while unconfirmed without reconciliation
    with pytest.raises(ValueError, match="is in 'Submission Unconfirmed' state and must be reconciled"):
        agent4.execute_submission(db_session, app.id)


# ===========================================================================
# TEST 7: External failure transitions to 'Failed' and increments retry_count
# ===========================================================================


def test_07_external_submission_failed_sets_failed_and_increments_retry(
    db_session: Session, sample_preference: JobPreference
):
    resume, ver = create_approved_resume_and_version(db_session)
    job, match, route = create_sample_job_match_and_route(db_session, sample_preference)

    agent4 = ApplicationExecutionAgent()
    settings = AutomationSettings(id=uuid.uuid4(), approval_mode="manual")

    apps = agent4.process_shortlisted_jobs(
        db=db_session,
        preference=sample_preference,
        shortlisted_matches=[match],
        routes=[route],
        automation_settings=settings,
        preferred_resume_version_id=ver.id,
    )
    app = apps[0]
    agent4.approve_application(db_session, app.id)

    # Simulate submission failure
    with patch.object(telegram_service, "_send_telegram_http", return_value=(True, None)):
        failed_app = agent4.execute_submission(
            db=db_session,
            application_id=app.id,
            simulate_failure=True,
        )

    assert failed_app.status == "Failed"
    assert failed_app.submission_result == "failed"
    assert failed_app.retry_count == 1
    assert failed_app.error_message is not None
    assert failed_app.applied_at is None


# ===========================================================================
# TEST 8: Failed application can be safely retried and succeed
# ===========================================================================


def test_08_failed_application_can_safely_retry_submission(
    db_session: Session, sample_preference: JobPreference
):
    resume, ver = create_approved_resume_and_version(db_session)
    job, match, route = create_sample_job_match_and_route(db_session, sample_preference)

    agent4 = ApplicationExecutionAgent()
    settings = AutomationSettings(id=uuid.uuid4(), approval_mode="manual")

    apps = agent4.process_shortlisted_jobs(
        db=db_session,
        preference=sample_preference,
        shortlisted_matches=[match],
        routes=[route],
        automation_settings=settings,
        preferred_resume_version_id=ver.id,
    )
    app = apps[0]
    agent4.approve_application(db_session, app.id)

    # 1. First attempt fails
    agent4.execute_submission(db_session, app.id, simulate_failure=True)
    assert app.status == "Failed"
    assert app.retry_count == 1

    # 2. Retry succeeds with valid confirmation receipt
    with patch.object(telegram_service, "_send_telegram_http", return_value=(True, None)):
        retried_app = agent4.execute_submission(
            db=db_session,
            application_id=app.id,
            explicit_confirmation_evidence="PORTAL-CONFIRM-RETRY-OK",
        )

    assert retried_app.status == "Submitted"
    assert retried_app.submission_result == "success"
    assert retried_app.confirmation_evidence == "PORTAL-CONFIRM-RETRY-OK"
    assert retried_app.applied_at is not None

    # Verify complete status journey in audit history
    history = db_session.scalars(
        select(ApplicationStatusHistory)
        .where(ApplicationStatusHistory.application_id == app.id)
        .order_by(ApplicationStatusHistory.created_at.asc())
    ).all()
    journey = [h.new_status for h in history]
    assert journey == [
        "Prepared",
        "Awaiting Approval",
        "Approved",
        "Submission In Progress",
        "Failed",
        "Submission In Progress",
        "Submitted",
    ]


# ===========================================================================
# TEST 9: Duplicate submission blocked on already Submitted applications
# ===========================================================================


def test_09_duplicate_submission_blocked_on_submitted(
    db_session: Session, sample_preference: JobPreference
):
    resume, ver = create_approved_resume_and_version(db_session)
    job, match, route = create_sample_job_match_and_route(db_session, sample_preference)

    app = Application(
        id=uuid.uuid4(),
        preference_id=sample_preference.id,
        discovered_job_id=job.id,
        company=job.company,
        job_title=job.title,
        route_type=route.route_type,
        route_target=route.url_or_contact,
        status="Submitted",
        approved_by_user=True,
        applied_at=datetime.now(timezone.utc),
        confirmation_evidence="REAL-PORTAL-RECEIPT",
        resume_id=resume.id,
        resume_version_id=ver.id,
        idempotency_key="key-test-09",
    )
    db_session.add(app)
    db_session.commit()

    agent4 = ApplicationExecutionAgent()

    # Attempting to submit an already submitted application must be rejected
    with pytest.raises(ValueError, match="Application has already been submitted; duplicate submission is blocked"):
        agent4.execute_submission(db_session, app.id)

    # Attempting to approve an already submitted application must be rejected
    with pytest.raises(ValueError, match="Application has already been submitted"):
        agent4.approve_application(db_session, app.id)


# ===========================================================================
# TEST 10: Reconcile unconfirmed submission enforces real external evidence
# ===========================================================================


def test_10_reconcile_unconfirmed_submission(
    db_session: Session, sample_preference: JobPreference
):
    resume, ver = create_approved_resume_and_version(db_session)
    job, match, route = create_sample_job_match_and_route(db_session, sample_preference)

    app = Application(
        id=uuid.uuid4(),
        preference_id=sample_preference.id,
        discovered_job_id=job.id,
        company=job.company,
        job_title=job.title,
        route_type=route.route_type,
        route_target=route.url_or_contact,
        status="Submission Unconfirmed",
        approved_by_user=True,
        resume_id=resume.id,
        resume_version_id=ver.id,
        idempotency_key="key-test-10",
    )
    db_session.add(app)
    db_session.commit()

    agent5 = ApplicationTrackingAgent()

    # 1. Cannot reconcile to 'Submitted' without evidence
    with pytest.raises(ValueError, match="requires confirmation_evidence"):
        agent5.reconcile_unconfirmed_submission(db_session, app.id, resolution="Submitted", confirmation_evidence=None)

    # 2. Cannot reconcile to 'Submitted' using an internal approval token
    with pytest.raises(ValueError, match="Internal user approval reference cannot be used"):
        agent5.reconcile_unconfirmed_submission(
            db_session, app.id, resolution="Submitted", confirmation_evidence="USER-APPROVED-RECEIPT-FAKE"
        )

    # 3. Can reconcile to 'Approved' to re-enable submission
    agent5.reconcile_unconfirmed_submission(db_session, app.id, resolution="Approved")
    assert app.status == "Approved"
    assert app.retry_count == 1

    # 4. From Approved, can execute submission with genuine receipt
    agent4 = ApplicationExecutionAgent()
    agent4.execute_submission(db_session, app.id, explicit_confirmation_evidence="VERIFIED-PORTAL-RECEIPT-99")
    assert app.status == "Submitted"
    assert app.confirmation_evidence == "VERIFIED-PORTAL-RECEIPT-99"


# ===========================================================================
# TEST 11: Audit reconciliation of Finom and Emma (USER-APPROVED-RECEIPT) records
# ===========================================================================


def test_11_audit_reconciliation_of_finom_and_emma_records(
    db_session: Session, sample_preference: JobPreference
):
    resume, ver = create_approved_resume_and_version(db_session)

    # Simulate existing Finom record with fabricated USER-APPROVED-RECEIPT
    job1 = DiscoveredJob(
        id=uuid.uuid4(),
        source_name="External",
        canonical_url="https://finom.co/job-1",
        fingerprint="finom-1",
        title="Product Analyst",
        company="Finom",
        official_job_url="https://finom.co/job-1",
        description="Analyst role",
    )
    db_session.add(job1)

    # Simulate Emma record with fabricated USER-APPROVED-RECEIPT
    job2 = DiscoveredJob(
        id=uuid.uuid4(),
        source_name="External",
        canonical_url="https://emma.com/job-2",
        fingerprint="emma-2",
        title="BI Developer",
        company="Emma – The Sleep Company",
        official_job_url="https://emma.com/job-2",
        description="BI role",
    )
    db_session.add(job2)
    db_session.flush()

    app1 = Application(
        id=uuid.uuid4(),
        preference_id=sample_preference.id,
        discovered_job_id=job1.id,
        company="Finom",
        job_title="Product Analyst",
        route_type="official_company_portal",
        route_target="https://finom.co/job-1",
        status="Submitted",
        approved_by_user=True,
        confirmation_evidence="USER-APPROVED-RECEIPT-31AE405BD0",
        applied_at=datetime.now(timezone.utc),
        resume_id=resume.id,
        resume_version_id=ver.id,
        idempotency_key="key-finom",
    )
    app2 = Application(
        id=uuid.uuid4(),
        preference_id=sample_preference.id,
        discovered_job_id=job2.id,
        company="Emma – The Sleep Company",
        job_title="BI Developer",
        route_type="official_company_portal",
        route_target="https://emma.com/job-2",
        status="Submitted",
        approved_by_user=True,
        confirmation_evidence="USER-APPROVED-RECEIPT-7BB021E4CA",
        applied_at=datetime.now(timezone.utc),
        resume_id=resume.id,
        resume_version_id=ver.id,
        idempotency_key="key-emma",
    )
    db_session.add_all([app1, app2])
    db_session.commit()

    # Run the reconciliation script
    count = reconcile_applications(db_session)
    assert count == 2

    # Verify both records are now 'Submission Unconfirmed' without fabricated evidence
    db_session.refresh(app1)
    db_session.refresh(app2)

    for app, orig_ref in [(app1, "USER-APPROVED-RECEIPT-31AE405BD0"), (app2, "USER-APPROVED-RECEIPT-7BB021E4CA")]:
        assert app.status == "Submission Unconfirmed"
        assert app.confirmation_evidence is None, "Fabricated evidence must be cleared from external confirmation field!"
        assert app.approval_reference == orig_ref, "Internal approval proof must be retained in approval_reference!"
        assert app.submission_result == "unconfirmed"

        # Verify audit history row exists
        hist = db_session.scalars(
            select(ApplicationStatusHistory).where(
                ApplicationStatusHistory.application_id == app.id,
                ApplicationStatusHistory.source == "audit_reconciliation",
            )
        ).first()
        assert hist is not None
        assert hist.previous_status == "Submitted"
        assert hist.new_status == "Submission Unconfirmed"


# ===========================================================================
# TEST 12: Telegram notifications fired for distinct lifecycle events
# ===========================================================================


def test_12_telegram_notifications_lifecycle_distinction(
    db_session: Session, sample_preference: JobPreference
):
    resume, ver = create_approved_resume_and_version(db_session)
    job, match, route = create_sample_job_match_and_route(db_session, sample_preference)

    agent4 = ApplicationExecutionAgent()
    settings = AutomationSettings(
        id=uuid.uuid4(),
        approval_mode="manual",
        telegram_notifications_enabled=True,
    )

    apps = agent4.process_shortlisted_jobs(
        db=db_session,
        preference=sample_preference,
        shortlisted_matches=[match],
        routes=[route],
        automation_settings=settings,
        preferred_resume_version_id=ver.id,
    )
    app = apps[0]

    captured_events = []

    def mock_dispatch(db, event_type, title, **kwargs):
        captured_events.append(event_type)

    with patch.object(telegram_service, "record_and_dispatch", side_effect=mock_dispatch):
        # 1. Explicit user approval
        agent4.approve_application(db_session, app.id)
        assert "application_approved" in captured_events
        assert "application_submitted" not in captured_events
        assert "submission_confirmed" not in captured_events

        # 2. External submission with confirmation
        agent4.execute_submission(
            db_session,
            app.id,
            explicit_confirmation_evidence="PORTAL-CONFIRM-9988",
        )
        assert "submission_started" in captured_events
        assert "submission_confirmed" in captured_events
