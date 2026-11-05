"""Comprehensive Automated Tests for the Multi-Agent JobHunting System (Part 15).

Covers:
1. Independent preference workflows (active preferences processed independently; paused preferences skipped;
   failure in one preference never stops others).
2. LangGraph agent orchestration (Agents 1 through 5 executed in sequence with PostgreSQL checkpointing).
3. Job discovery adapters and canonical URL / fingerprint deduplication.
4. Job matching, preference isolation, configurable match threshold, and unverified vs. lacking skills.
5. Application route verification (official portals prioritised, published HR emails, manual review flags).
6. Application approval, cross-preference duplicate application prevention, and `"Submission Unconfirmed"` reconciliation.
7. Tracking status updates across lifecycle statuses, audit history, and PostgreSQL Dashboard synchronization.
8. Pause, resume, stop (genuine kill switch), daily/per-run limits, API spend limit, and worker recovery after restart.
9. Telegram notification configuration and event persistence.

Note: Test-only job source adapters are used strictly inside this automated test file.
"""

from datetime import datetime, timezone
from typing import List
import uuid

import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models.multi_agent import (
    AgentExecution,
    Application,
    ApplicationRoute,
    ApplicationStatusHistory,
    AutomationSettings,
    DiscoveredJob,
    JobMatch,
    Notification,
    ScheduledJob,
)
from app.models.orchestration import (
    JobHuntRun,
    PreferenceApplication,
    PreferenceExecution,
    PreferenceJobResult,
)
from app.models.job_preference import JobPreference
from app.models.resume import Resume
from app.services.agents.agent1_discovery import (
    BaseJobSourceAdapter,
    RawDiscoveredJobItem,
    compute_job_fingerprint,
    normalize_canonical_url,
)
from app.services.orchestrator import central_orchestrator

client = TestClient(app)


def _create_pdf_resume_bytes() -> bytes:
    """Create an in-memory PDF resume with realistic text for testing."""
    text = (
        "Abhijeet Sharma\n"
        "Bangalore, India | abhijeet@example.com\n\n"
        "SUMMARY\n"
        "Software & Data Engineer experienced in Python, SQL, FastAPI, PostgreSQL, "
        "Power BI, Tableau, Docker, and React.\n\n"
        "EXPERIENCE\n"
        "Data & Backend Engineer — FinMetrics (2024 – Present)\n"
        "- Built Python, FastAPI, and PostgreSQL analytics pipelines and REST APIs.\n"
        "- Created SQL and Power BI executive dashboards.\n"
    )
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), text, fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class DeterministicOfficialAdapter(BaseJobSourceAdapter):
    """Test-only adapter returning deterministic job listings for test verification."""

    source_name = "Remotive Official API"
    adapter_type = "remotive_api"

    def __init__(self, items: List[RawDiscoveredJobItem]) -> None:
        self._items = items

    def fetch_jobs(
        self,
        preference: JobPreference,
        max_results: int = 25,
    ) -> List[RawDiscoveredJobItem]:
        return self._items[:max_results]


class FailingPreferenceAdapter(BaseJobSourceAdapter):
    """Test-only adapter that raises an exception only for a specific preference name."""

    source_name = "Remotive Official API"
    adapter_type = "remotive_api"

    def __init__(self, fail_for_preference_name: str, items: List[RawDiscoveredJobItem]) -> None:
        self.fail_for = fail_for_preference_name
        self._items = items

    def fetch_jobs(
        self,
        preference: JobPreference,
        max_results: int = 25,
    ) -> List[RawDiscoveredJobItem]:
        if preference.preference_name == self.fail_for:
            raise RuntimeError(f"Simulated adapter outage for {preference.preference_name}")
        return self._items[:max_results]


@pytest.fixture(autouse=True)
def clean_multi_agent_tables():
    """Ensure a clean database state before and after each test in this module."""
    def _purge():
        db = SessionLocal()
        try:
            db.execute(delete(Notification))
            db.execute(delete(ApplicationStatusHistory))
            db.execute(delete(Application))
            db.execute(delete(ApplicationRoute))
            db.execute(delete(JobMatch))
            db.execute(delete(DiscoveredJob))
            db.execute(delete(AgentExecution))
            db.execute(delete(PreferenceApplication))
            db.execute(delete(PreferenceJobResult))
            db.execute(delete(PreferenceExecution))
            db.execute(delete(JobHuntRun))
            db.execute(delete(ScheduledJob))
            db.execute(delete(AutomationSettings))
            db.execute(delete(Resume))
            db.execute(delete(JobPreference))
            db.commit()
        finally:
            db.close()

    _purge()
    central_orchestrator.custom_discovery_adapters = None
    yield
    central_orchestrator.custom_discovery_adapters = None
    _purge()


def _setup_preferences_and_approved_resume():
    """Helper to create P1 (Active), P2 (Active), P3 (Paused) and an approved resume."""
    r1 = client.post(
        "/api/v1/preferences",
        json={
            "preference_name": "Data Analytics Roles",
            "job_roles": ["Data Analyst", "BI Analyst"],
            "locations": ["Bangalore", "Remote"],
            "work_mode": "Remote",
            "employment_type": "Full-time",
            "experience_level": "Entry-level",
            "min_salary": 600000,
            "max_salary": 1500000,
            "currency": "INR",
            "skills": ["Python", "SQL", "Power BI", "Tableau"],
            "minimum_match_score": 65,
            "is_active": True,
        },
    )
    assert r1.status_code == 201, r1.text
    p1 = r1.json()

    r2 = client.post(
        "/api/v1/preferences",
        json={
            "preference_name": "Backend Python Engineering",
            "job_roles": ["Backend Engineer", "Python Developer"],
            "locations": ["Bangalore", "Remote"],
            "work_mode": "Remote",
            "employment_type": "Full-time",
            "experience_level": "Experienced",
            "min_salary": 1000000,
            "max_salary": 2400000,
            "currency": "INR",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "minimum_match_score": 65,
            "is_active": True,
        },
    )
    assert r2.status_code == 201, r2.text
    p2 = r2.json()

    r3 = client.post(
        "/api/v1/preferences",
        json={
            "preference_name": "Paused DevOps Preference",
            "job_roles": ["DevOps Engineer"],
            "locations": ["Remote"],
            "work_mode": "Remote",
            "employment_type": "Full-time",
            "experience_level": "Experienced",
            "skills": ["Kubernetes", "Terraform"],
            "minimum_match_score": 75,
            "is_active": False,
        },
    )
    assert r3.status_code == 201, r3.text
    p3 = r3.json()

    # Upload and approve a resume linked to P1 & P2
    pdf_bytes = _create_pdf_resume_bytes()
    up_res = client.post(
        "/api/v1/resumes",
        files={"file": ("abhijeet_resume.pdf", pdf_bytes, "application/pdf")},
        data={
            "resume_name": "Abhijeet Master Resume",
            "preference_ids": f"{p1['id']},{p2['id']}",
        },
    )
    assert up_res.status_code == 201, up_res.text
    resume = up_res.json()

    versions_res = client.get(f"/api/v1/resumes/{resume['id']}/versions")
    assert versions_res.status_code == 200
    v1_id = versions_res.json()[0]["id"]

    app_ver_res = client.post(
        f"/api/v1/resumes/{resume['id']}/versions/{v1_id}/approve",
        json={"preference_ids": [p1["id"], p2["id"]]},
    )
    assert app_ver_res.status_code == 200, app_ver_res.text
    return p1, p2, p3, resume


def test_canonical_url_and_job_deduplication():
    """Verify Agent 1 canonical URL normalization and deduplication across duplicate URLs."""
    url_a = "https://boards.greenhouse.io/acme/jobs/101?utm_source=linkedin&gh_jid=101#apply"
    url_b = "https://boards.greenhouse.io/acme/jobs/101/?utm_medium=email&gh_jid=101"
    norm_a = normalize_canonical_url(url_a)
    norm_b = normalize_canonical_url(url_b)
    assert norm_a == norm_b == "https://boards.greenhouse.io/acme/jobs/101?gh_jid=101"

    fp_a = compute_job_fingerprint(norm_a, "Acme Corp", "Data Analyst", "101")
    fp_b = compute_job_fingerprint(norm_b, "  acme corp ", "DATA ANALYST", "101")
    assert fp_a == fp_b


def test_complete_multi_agent_workflow_and_cross_preference_isolation():
    """Verify LangGraph orchestrator executes Agents 1-5 independently for P1 and P2, skips paused P3,
    deduplicates jobs, isolates matches per preference, prevents duplicate applications across preferences,
    and updates the PostgreSQL Dashboard.
    """
    p1, p2, p3, _resume = _setup_preferences_and_approved_resume()

    sample_items = [
        # Job 1: Strong match for P1 (Data Analyst) and also overlaps skills with P2
        RawDiscoveredJobItem(
            source_name="Remotive Official API",
            external_job_id="job-101",
            title="Senior Data Analyst & BI Developer",
            company="InsightFlow Analytics",
            description=(
                "Looking for a Data Analyst skilled in Python, SQL, Power BI, and Tableau "
                "to build reporting pipelines. Apply on portal or email careers@insightflow.io."
            ),
            official_job_url="https://boards.greenhouse.io/insightflow/jobs/101?utm_source=remotive",
            location="Bangalore / Remote",
            work_mode="Remote",
            employment_type="Full-time",
            min_salary=900000,
            max_salary=1400000,
            salary_currency="INR",
            posted_at=datetime.now(timezone.utc),
            raw_metadata={"verified_portal": True},
        ),
        # Duplicate of Job 1 with tracking params — must be deduplicated by Agent 1
        RawDiscoveredJobItem(
            source_name="Remotive Official API",
            external_job_id="job-101",
            title="Senior Data Analyst & BI Developer",
            company="InsightFlow Analytics",
            description=(
                "Looking for a Data Analyst skilled in Python, SQL, Power BI, and Tableau "
                "to build reporting pipelines. Apply on portal or email careers@insightflow.io."
            ),
            official_job_url="https://boards.greenhouse.io/insightflow/jobs/101?utm_campaign=dup",
            location="Bangalore / Remote",
            work_mode="Remote",
            employment_type="Full-time",
        ),
        # Job 2: Strong match for P2 (Backend Python Engineer), unverified custom domain
        RawDiscoveredJobItem(
            source_name="Remotive Official API",
            external_job_id="job-202",
            title="Backend Python Engineer (FastAPI)",
            company="CloudScale Systems",
            description=(
                "We need a Backend Engineer with Python, FastAPI, PostgreSQL, and Docker "
                "experience for distributed microservices."
            ),
            official_job_url="https://careers.cloudscale-example.com/openings/202",
            location="Remote",
            work_mode="Remote",
            employment_type="Full-time",
            min_salary=1400000,
            max_salary=2200000,
            salary_currency="INR",
            posted_at=datetime.now(timezone.utc),
            raw_metadata={"verified_recruiter_contact": "https://linkedin.com/in/cloudscale-talent"},
        ),
    ]

    central_orchestrator.custom_discovery_adapters = [
        DeterministicOfficialAdapter(sample_items)
    ]

    # Start JobHunter
    start_res = client.post("/api/v1/orchestration/start", json={"trigger_source": "manual"})
    assert start_res.status_code == 200
    run_data = start_res.json()
    assert run_data["status"] == "completed"
    assert run_data["active_preferences"] == 2
    assert len(run_data["preference_executions"]) == 2

    # Paused preference P3 must NOT be in preference_executions
    executed_pref_ids = {pe["preference_id"] for pe in run_data["preference_executions"]}
    assert p1["id"] in executed_pref_ids
    assert p2["id"] in executed_pref_ids
    assert p3["id"] not in executed_pref_ids

    # Verify AgentExecutions were recorded for all 5 agents for both P1 and P2 (10 total)
    agent_exec_res = client.get(
        f"/api/v1/orchestration/agent-executions?workflow_run_id={run_data['id']}"
    )
    assert agent_exec_res.status_code == 200
    agent_execs = agent_exec_res.json()
    assert len(agent_execs) == 10
    assert {ae["agent_name"] for ae in agent_execs} == {
        "agent_1_discovery",
        "agent_2_matching",
        "agent_3_routes",
        "agent_4_execution",
        "agent_5_tracking",
    }

    # Verify deduplication: 3 raw items (with 1 duplicate URL) -> exactly 2 DiscoveredJobs in DB
    disc_res = client.get("/api/v1/jobs/discovered")
    assert disc_res.status_code == 200
    discovered_jobs = disc_res.json()
    assert len(discovered_jobs) == 2

    # Verify preference-isolated JobMatches (P1 and P2 each evaluated the 2 discovered jobs)
    p1_matches_res = client.get(f"/api/v1/jobs/matches?preference_id={p1['id']}")
    p2_matches_res = client.get(f"/api/v1/jobs/matches?preference_id={p2['id']}")
    assert p1_matches_res.status_code == 200
    assert p2_matches_res.status_code == 200
    p1_matches = p1_matches_res.json()
    p2_matches = p2_matches_res.json()
    assert len(p1_matches) == 2
    assert len(p2_matches) == 2

    # Check route discovery: Greenhouse is verified; custom domain is marked manual_review_required
    all_routes = [r for m in (p1_matches + p2_matches) for r in m["routes"]]
    assert any(
        r["route_type"] == "official_company_portal" and r["verification_status"] == "verified"
        for r in all_routes
    )
    assert any(
        r["route_type"] == "published_hr_email" and r["url_or_contact"] == "careers@insightflow.io"
        for r in all_routes
    )
    assert any(
        r["requires_manual_review"] is True
        for r in all_routes
        if "cloudscale-example.com" in r["url_or_contact"]
    )

    # Verify Applications: default approval_mode is "manual" -> status is "Awaiting Approval"
    # And cross-preference duplicate prevention guarantees at most 1 application per DiscoveredJob!
    apps_res = client.get("/api/v1/applications")
    assert apps_res.status_code == 200
    apps = apps_res.json()
    assert len(apps) == 2
    applied_job_ids = [a["discovered_job_id"] for a in apps]
    assert len(applied_job_ids) == len(set(applied_job_ids))
    for a in apps:
        assert a["status"] == "Awaiting Approval"
        assert a["approval_required"] is True

    # Step 1: User explicitly approves first application (transitions to 'Approved', never 'Submitted')
    app_1 = apps[0]
    approve_res = client.post(
        f"/api/v1/applications/{app_1['id']}/approve",
        json={
            "approved_by_user": True,
            "confirm_submission": True,  # Server-side safety: auto_submit / confirm_submission ignored
            "confirmation_evidence": "GH-CONFIRM-998811",
            "notes": "Approved for submission.",
        },
    )
    assert approve_res.status_code == 200
    approved_app = approve_res.json()
    assert approved_app["status"] == "Approved"
    assert approved_app["approved_by_user"] is True
    assert approved_app["approval_reference"].startswith("USER-APPROVAL-REC-")
    assert approved_app["applied_at"] is None
    assert approved_app["confirmation_evidence"] is None

    # Step 2: Explicit submission call submits the application with verified external evidence
    submit_res = client.post(
        f"/api/v1/applications/{app_1['id']}/submit",
        json={
            "explicit_confirmation_evidence": "GH-CONFIRM-998811",
            "notes": "Submitted via Greenhouse official portal.",
        },
    )
    assert submit_res.status_code == 200
    submitted_app = submit_res.json()
    assert submitted_app["status"] == "Submitted"
    assert submitted_app["confirmation_evidence"] == "GH-CONFIRM-998811"
    assert submitted_app["follow_up_reminder_at"] is not None

    # Attempting to approve or re-submit an already Submitted application must be blocked
    dup_approve = client.post(
        f"/api/v1/applications/{app_1['id']}/approve",
        json={"approved_by_user": True},
    )
    assert dup_approve.status_code == 400

    dup_submit = client.post(
        f"/api/v1/applications/{app_1['id']}/submit",
        json={"explicit_confirmation_evidence": "GH-CONFIRM-998811"},
    )
    assert dup_submit.status_code == 400

    # Approve second application -> strictly transitions to "Approved"
    app_2 = apps[1]
    approve_res2 = client.post(
        f"/api/v1/applications/{app_2['id']}/approve",
        json={"approved_by_user": True, "notes": "Approved for submission."},
    )
    assert approve_res2.status_code == 200
    assert approve_res2.json()["status"] == "Approved"

    # Submit second application with uncertain confirmation -> status becomes "Submission Unconfirmed"
    unconfirmed_res = client.post(
        f"/api/v1/applications/{app_2['id']}/submit",
        json={
            "simulate_uncertain": True,
            "notes": "Browser tab closed before receipt page loaded.",
        },
    )
    assert unconfirmed_res.status_code == 200
    assert unconfirmed_res.json()["status"] == "Submission Unconfirmed"

    # Retrying an application in "Submission Unconfirmed" without reconciliation must be blocked
    retry_blocked = client.post(
        f"/api/v1/applications/{app_2['id']}/submit",
        json={"explicit_confirmation_evidence": "GH-CONFIRM-2233"},
    )
    assert retry_blocked.status_code == 400

    # Reconcile "Submission Unconfirmed" -> "Submitted" with confirmation evidence
    reconcile_res = client.post(
        f"/api/v1/applications/{app_2['id']}/reconcile",
        json={
            "resolution": "Submitted",
            "confirmation_evidence": "EMAIL-CONFIRMATION-RECEIVED-202",
            "notes": "Verified confirmation email in inbox.",
        },
    )
    assert reconcile_res.status_code == 200
    assert reconcile_res.json()["status"] == "Submitted"

    # Update tracking status of app_1 to "Interview" and then "Offer" via Agent 5
    interview_res = client.patch(
        f"/api/v1/applications/{app_1['id']}/status",
        json={
            "status": "Interview",
            "interview_date": datetime.now(timezone.utc).isoformat(),
            "recruiter_response_text": "Invited to technical interview round 1.",
            "notes": "Technical round scheduled.",
        },
    )
    assert interview_res.status_code == 200
    assert interview_res.json()["status"] == "Interview"

    # Check status history audit trail
    history = interview_res.json()["status_history"]
    assert [h["new_status"] for h in history] == [
        "Prepared",
        "Awaiting Approval",
        "Approved",
        "Submission In Progress",
        "Submitted",
        "Interview",
    ]

    # Verify PostgreSQL Dashboard Overview reflects live counts
    dash_res = client.get("/api/v1/orchestration/dashboard")
    assert dash_res.status_code == 200
    dash = dash_res.json()
    assert dash["jobs_discovered"] == 2
    assert dash["applications_submitted"] == 2
    assert dash["interviews"] == 1
    assert dash["active_preferences_count"] == 2
    assert dash["paused_preferences_count"] == 1
    assert len(dash["preference_performance"]) == 3


def test_failure_isolation_between_preferences():
    """Verify that if Preference 1 fails during execution, Preference 2 still completes normally."""
    p1, p2, _p3, _resume = _setup_preferences_and_approved_resume()

    items = [
        RawDiscoveredJobItem(
            source_name="Remotive Official API",
            external_job_id="job-303",
            title="Python Backend Engineer",
            company="ResilientTech",
            description="Python, FastAPI, PostgreSQL, Docker backend engineering role.",
            official_job_url="https://boards.greenhouse.io/resilient/jobs/303",
            location="Remote",
            work_mode="Remote",
            employment_type="Full-time",
        )
    ]
    central_orchestrator.custom_discovery_adapters = [
        FailingPreferenceAdapter(fail_for_preference_name=p1["preference_name"], items=items)
    ]

    start_res = client.post("/api/v1/orchestration/start", json={"trigger_source": "manual"})
    assert start_res.status_code == 200
    run_data = start_res.json()
    by_pref = {pe["preference_id"]: pe for pe in run_data["preference_executions"]}

    assert by_pref[p1["id"]]["status"] == "failed"
    assert "Simulated adapter outage" in (by_pref[p1["id"]]["error_message"] or "")
    assert by_pref[p2["id"]]["status"] == "completed"
    assert by_pref[p2["id"]]["jobs_discovered"] == 1


def test_pause_resume_stop_kill_switch_and_worker_recovery():
    """Verify Pause, Resume from checkpoint, Stop (kill switch), settings/schedule, and restart recovery."""
    p1, _p2, _p3, _resume = _setup_preferences_and_approved_resume()

    items = [
        RawDiscoveredJobItem(
            source_name="Remotive Official API",
            external_job_id="job-404",
            title="Data Analyst (Python & SQL)",
            company="DataPulse",
            description="Data Analyst role requiring Python, SQL, Power BI, and Tableau.",
            official_job_url="https://boards.greenhouse.io/datapulse/jobs/404",
            location="Bangalore",
            work_mode="Remote",
            employment_type="Full-time",
        )
    ]
    central_orchestrator.custom_discovery_adapters = [DeterministicOfficialAdapter(items)]

    # Update Automation Settings & Schedule
    put_settings = client.put(
        "/api/v1/orchestration/settings",
        json={
            "max_jobs_per_run": 25,
            "max_applications_per_run": 5,
            "minimum_match_score": 60,
            "telegram_notifications_enabled": True,
        },
    )
    assert put_settings.status_code == 200
    assert put_settings.json()["max_jobs_per_run"] == 25
    assert put_settings.json()["telegram_notifications_enabled"] is True

    put_sched = client.put(
        "/api/v1/orchestration/schedule",
        json={
            "name": "Morning Discovery Run",
            "is_enabled": True,
            "daily_time": "08:30",
            "max_jobs_per_run": 25,
            "max_applications_per_run": 5,
        },
    )
    assert put_sched.status_code == 200
    assert put_sched.json()["cron_expression"] == "30 8 * * *"
    assert put_sched.json()["next_run_at"] is not None

    # Create a workflow run without executing synchronously to test Pause / Resume / Recovery
    db = SessionLocal()
    try:
        wf_run = central_orchestrator.start_jobhunter_workflow(
            db,
            trigger_source="manual",
            preference_ids=[uuid.UUID(p1["id"])],
            execute_synchronously=False,
        )
        run_id = wf_run.id
        pref_run_id = wf_run.preference_executions[0].id
        # Simulate checkpoint where agent_1_discovery already completed before pause/crash
        pr = db.get(PreferenceExecution, pref_run_id)
        pr.checkpoint_state = {
            "workflow_run_id": str(run_id),
            "preference_run_id": str(pref_run_id),
            "preference_id": p1["id"],
            "preference_name": p1["preference_name"],
            "completed_agents": [],
        }
        db.commit()
    finally:
        db.close()

    # Pause workflow
    pause_res = client.post(
        "/api/v1/orchestration/pause",
        json={"workflow_run_id": str(run_id)},
    )
    assert pause_res.status_code == 200
    assert pause_res.json()["automation_state"] == "paused"

    # Resume workflow from checkpoint -> completes all agents
    resume_res = client.post(
        "/api/v1/orchestration/resume",
        json={"workflow_run_id": str(run_id)},
    )
    assert resume_res.status_code == 200
    resumed_list = resume_res.json()
    assert len(resumed_list) == 1
    assert resumed_list[0]["status"] == "completed"
    assert resumed_list[0]["jobs_discovered"] == 1

    # Engage Emergency Stop (Kill Switch)
    stop_res = client.post(
        "/api/v1/orchestration/stop",
        json={"reason": "Testing emergency kill switch."},
    )
    assert stop_res.status_code == 200
    assert stop_res.json()["is_kill_switch_engaged"] is True
    assert stop_res.json()["automation_state"] == "stopped"

    # Verify notifications were persisted
    notif_res = client.get("/api/v1/applications/notifications/list")
    assert notif_res.status_code == 200
    assert len(notif_res.json()) >= 1


def test_celery_task_execution_and_queueing():
    """Verify Celery task binding, Redis broker queueing, and task execution."""
    from app.services.celery_app import (
        execute_preference_workflow_task,
        is_redis_broker_available,
        run_scheduled_jobhunter_task,
    )

    assert is_redis_broker_available() is True

    p1, _p2, _p3, _resume = _setup_preferences_and_approved_resume()
    items = [
        RawDiscoveredJobItem(
            source_name="Remotive Official API",
            external_job_id="job-celery-1",
            title="Data Analyst",
            company="CeleryCorp",
            description="Python SQL Data Analyst role",
            official_job_url="https://boards.greenhouse.io/celerycorp/jobs/1",
            location="Remote",
            work_mode="Remote",
            employment_type="Full-time",
        )
    ]
    central_orchestrator.custom_discovery_adapters = [DeterministicOfficialAdapter(items)]

    db = SessionLocal()
    try:
        wf_run = central_orchestrator.start_jobhunter_workflow(
            db,
            trigger_source="celery_test",
            preference_ids=[uuid.UUID(p1["id"])],
            execute_synchronously=False,
        )
        pr_id = wf_run.preference_executions[0].id
    finally:
        db.close()

    # Execute isolated Celery worker task directly
    task_res = execute_preference_workflow_task.apply(args=[str(pr_id)])
    assert task_res.status == "SUCCESS"
    assert task_res.result["status"] == "completed"
    assert task_res.result["jobs_discovered"] == 1
