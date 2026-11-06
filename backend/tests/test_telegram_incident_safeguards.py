"""Tests for MIORA 2.0 Telegram incident safeguards and multi-layered gating."""

from datetime import datetime, timezone
import os
import uuid
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.services.telegram_service as ts_module
from app.db.base import Base
from app.models.job_preference import JobPreference
from app.models.multi_agent import Application, ApplicationRoute, AutomationSettings, DiscoveredJob, JobMatch, Notification
from app.models.resume import Resume
from app.models.resume_intelligence import ResumeVersion
from app.services.agents.agent4_execution import agent4_execution
from app.services.telegram_service import telegram_service


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


def test_gate1_test_environment_blocks_telegram_dispatch(db_session: Session):
    """Gate 1: In test or development environments, Telegram dispatch is strictly blocked."""
    can_send, reason = telegram_service.should_send_telegram(
        db_session, event_type="job_approved", application_id=uuid.uuid4()
    )
    assert not can_send
    assert "suppressed in test/dev environment" in reason


def test_gate2_disabled_env_var_blocks_telegram_dispatch(db_session: Session, monkeypatch):
    """Gate 2: TELEGRAM_NOTIFICATIONS_ENABLED=false blocks dispatch even if not in test env."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(ts_module.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(ts_module.settings, "TELEGRAM_NOTIFICATIONS_ENABLED", False)

    can_send, reason = telegram_service.should_send_telegram(
        db_session, event_type="job_approved", application_id=uuid.uuid4()
    )
    assert not can_send
    assert "disabled globally via TELEGRAM_NOTIFICATIONS_ENABLED" in reason


def test_gate3_db_setting_disabled_blocks_telegram_dispatch(db_session: Session, monkeypatch):
    """Gate 3: automation_settings.telegram_notifications_enabled=False blocks dispatch."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(ts_module.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(ts_module.settings, "TELEGRAM_NOTIFICATIONS_ENABLED", True)

    settings = db_session.scalar(select(AutomationSettings).limit(1))
    if not settings:
        settings = AutomationSettings()
        db_session.add(settings)
    settings.telegram_notifications_enabled = False
    settings.is_kill_switch_engaged = False
    db_session.commit()

    can_send, reason = telegram_service.should_send_telegram(
        db_session, event_type="job_approved", application_id=uuid.uuid4()
    )
    assert not can_send
    assert "disabled in AutomationSettings" in reason


def test_gate4_kill_switch_blocks_telegram_dispatch(db_session: Session, monkeypatch):
    """Gate 4: Kill switch engaged blocks all Telegram dispatch immediately."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(ts_module.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(ts_module.settings, "TELEGRAM_NOTIFICATIONS_ENABLED", True)

    settings = db_session.scalar(select(AutomationSettings).limit(1))
    if not settings:
        settings = AutomationSettings()
        db_session.add(settings)
    settings.telegram_notifications_enabled = True
    settings.is_kill_switch_engaged = True
    db_session.commit()

    can_send, reason = telegram_service.should_send_telegram(
        db_session, event_type="job_approved", application_id=uuid.uuid4()
    )
    assert not can_send
    assert "Kill switch is engaged" in reason


def test_gate5_duplicate_suppression_blocks_repeated_events(db_session: Session, monkeypatch):
    """Gate 5: Identical event type for same application within 5 minutes is suppressed."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(ts_module.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(ts_module.settings, "TELEGRAM_NOTIFICATIONS_ENABLED", True)

    settings = db_session.scalar(select(AutomationSettings).limit(1))
    if not settings:
        settings = AutomationSettings()
        db_session.add(settings)
    settings.telegram_notifications_enabled = True
    settings.is_kill_switch_engaged = False
    settings.notify_on_application_submitted = True
    db_session.commit()

    pref = JobPreference(
        id=uuid.uuid4(),
        preference_name="Data Analyst India",
        job_roles=["Data Analyst"],
        locations=["Bengaluru"],
        location_mode="INDIA_ONLY",
        work_mode="Flexible",
        employment_type="Full-time",
        experience_level="Mid",
        min_salary=800000,
        currency="INR",
        skills=["Python", "SQL"],
        minimum_match_score=70,
        is_active=True,
    )
    db_session.add(pref)
    db_session.flush()

    job = DiscoveredJob(
        id=uuid.uuid4(),
        source_name="Greenhouse Official",
        canonical_url="https://boards.greenhouse.io/test/jobs/1",
        official_job_url="https://boards.greenhouse.io/test/jobs/1",
        fingerprint=uuid.uuid4().hex,
        title="Data Analyst",
        company="Test Corp",
        location="Bengaluru, India",
        description="Looking for Data Analyst with SQL and Python.",
    )
    db_session.add(job)
    db_session.flush()

    test_app = Application(
        id=uuid.uuid4(),
        preference_id=pref.id,
        discovered_job_id=job.id,
        job_title="Data Analyst",
        company="Test Corp",
        route_type="official_company_portal",
        route_target="https://boards.greenhouse.io/test/jobs/1",
        status="Approved",
        idempotency_key="idemp_12345",
    )
    db_session.add(test_app)
    db_session.commit()
    app_id = test_app.id

    # First check passes (no prior notification in DB)
    can_send_1, reason_1 = telegram_service.should_send_telegram(
        db_session, event_type="submission_started", application_id=app_id
    )
    assert can_send_1

    # Record notification as sent
    sent_notif = Notification(
        id=uuid.uuid4(),
        event_type="submission_started",
        title="Submission Started",
        message="Started",
        application_id=app_id,
        telegram_sent=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(sent_notif)
    db_session.commit()

    # Second check within 5 minutes is blocked
    can_send_2, reason_2 = telegram_service.should_send_telegram(
        db_session, event_type="submission_started", application_id=app_id
    )
    assert not can_send_2
    assert "Duplicate notification" in reason_2


def test_kill_switch_blocks_agent4_approval_and_execution(db_session: Session):
    """Verification that Agent 4 approve_application and execute_submission respect the kill switch."""
    settings = db_session.scalar(select(AutomationSettings).limit(1))
    if not settings:
        settings = AutomationSettings()
        db_session.add(settings)
    settings.is_kill_switch_engaged = True
    db_session.commit()

    # Attempt approve_application
    with pytest.raises(ValueError, match="Emergency kill switch is engaged"):
        agent4_execution.approve_application(db_session, uuid.uuid4())

    # Attempt execute_submission
    with pytest.raises(ValueError, match="Emergency kill switch is engaged"):
        agent4_execution.execute_submission(db_session, uuid.uuid4())
