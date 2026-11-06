"""Celery & Redis Background Execution Service (Part 8).

Provides:
- Configured `Celery` instance with task isolation, retry backoff, and safe serialization.
- Isolated per-preference Celery task `execute_preference_workflow_task`.
- Scheduled automation task `run_scheduled_jobhunter_task`.
- Crash/restart recovery task `recover_interrupted_workflows_task`.
- Fast broker health check (`is_redis_broker_available`) with automatic in-process fallback
  when Redis is not running locally.
"""

import socket
from urllib.parse import urlparse
import uuid

from celery import Celery

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.orchestrator import central_orchestrator

settings = get_settings()

broker_url = settings.CELERY_BROKER_URL or settings.REDIS_URL
result_backend = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL

celery_app = Celery(
    "jobhunter_orchestrator",
    broker=broker_url,
    backend=result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_always_eager=bool(settings.CELERY_TASK_ALWAYS_EAGER),
)


def is_redis_broker_available(timeout_seconds: float = 0.25) -> bool:
    """Perform a fast TCP socket check to verify whether the Redis broker is reachable."""
    try:
        parsed = urlparse(settings.CELERY_BROKER_URL or settings.REDIS_URL)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 6379
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


@celery_app.task(
    name="jobhunter.execute_preference_workflow",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
)
def execute_preference_workflow_task(self, preference_run_id_str: str) -> dict:
    """Execute the 5-agent LangGraph workflow for a single `PreferenceExecution` in an isolated worker task."""
    db = SessionLocal()
    try:
        pr_id = uuid.UUID(preference_run_id_str)
        pref_run = central_orchestrator.execute_preference_workflow(db, pr_id)
        return {
            "preference_run_id": str(pref_run.id),
            "status": pref_run.status,
            "jobs_discovered": pref_run.jobs_discovered,
            "matching_jobs": pref_run.matching_jobs,
            "shortlisted_jobs": pref_run.shortlisted_jobs,
            "applications_submitted": pref_run.applications_submitted,
        }
    finally:
        db.close()


@celery_app.task(name="jobhunter.run_scheduled_jobhunter")
def run_scheduled_jobhunter_task() -> dict:
    """Triggered by Celery Beat or scheduler to run JobHunter across all active preferences."""
    db = SessionLocal()
    try:
        wf_run = central_orchestrator.start_jobhunter_workflow(
            db,
            trigger_source="scheduled",
            execute_synchronously=True,
        )
        return {
            "workflow_run_id": str(wf_run.id),
            "status": wf_run.status,
            "active_preferences": wf_run.active_preferences,
        }
    finally:
        db.close()


@celery_app.task(name="jobhunter.recover_interrupted_workflows")
def recover_interrupted_workflows_task() -> dict:
    """Recover any interrupted `PreferenceExecution` rows after a worker or server restart."""
    db = SessionLocal()
    try:
        recovered = central_orchestrator.recover_interrupted_runs(
            db, execute_synchronously=True
        )
        return {
            "recovered_count": len(recovered),
            "preference_run_ids": [str(pr.id) for pr in recovered],
        }
    finally:
        db.close()
