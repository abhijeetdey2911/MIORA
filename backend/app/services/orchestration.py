"""Central orchestration readiness, dashboard aggregation, settings, and scheduling service."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.multi_agent import (
    AgentExecution,
    Application,
    AutomationSettings,
    DiscoveredJob,
    JobMatch,
    Notification,
    ScheduledJob,
)
from app.models.orchestration import JobHuntRun, PreferenceExecution
from app.models.job_preference import JobPreference
from app.schemas.multi_agent import (
    AgentExecutionResponse,
    AutomationSettingsResponse,
    AutomationSettingsUpdate,
    DashboardOverviewResponse,
    DashboardPreferenceCardItem,
    NotificationResponse,
    PreferenceRunSummaryResponse,
    ScheduledJobResponse,
    ScheduledJobUpdate,
    WorkflowRunSummaryResponse,
)
from app.schemas.orchestration import (
    OrchestrationPreferenceSummary,
    OrchestrationReadinessResponse,
)
from app.services.agents.agent5_tracking import (
    SUBMITTED_EQUIVALENT_STATUSES,
    agent5_tracking,
)
from app.services.job_preference import JobPreferenceService
from app.services.orchestrator import central_orchestrator
from app.services.telegram_service import telegram_service

USER_CENTRIC_WORKFLOW_STEPS: List[str] = [
    "1. User creates one or more job preferences.",
    "2. User uploads and approves a resume.",
    "3. User presses the central Start JobHunter button.",
    "4. The system processes every active preference independently.",
    "5. Agents execute their assigned workflow.",
    "6. Results are stored separately for each preference.",
    "7. Dashboard displays overall and preference-wise results.",
]


class OrchestrationService:
    """Central orchestration, Automation Control Centre, and PostgreSQL Dashboard service."""

    @staticmethod
    def get_readiness(db: Session) -> OrchestrationReadinessResponse:
        """Inspect persisted preferences and report central orchestration readiness."""
        preferences = JobPreferenceService.list_preferences(db)
        summaries: List[OrchestrationPreferenceSummary] = []
        active_count = 0

        for pref in preferences:
            if pref.is_active:
                active_count += 1
            summaries.append(
                OrchestrationPreferenceSummary(
                    preference_id=pref.id,
                    preference_name=pref.preference_name,
                    is_active=pref.is_active,
                    eligible_for_discovery=pref.is_active,
                    has_approved_resume=pref.has_approved_resume,
                    approved_resume_id=pref.approved_resume_id,
                    approved_resume_version_id=pref.approved_resume_version_id,
                    eligible_for_applications=pref.eligible_for_applications,
                    job_roles=pref.job_roles,
                    locations=pref.locations,
                    work_mode=pref.work_mode,
                    minimum_match_score=pref.minimum_match_score,
                )
            )

        total_count = len(preferences)
        paused_count = total_count - active_count

        return OrchestrationReadinessResponse(
            engine_connected=False,
            automation_state="ready",
            message=(
                "Automation engine is not connected yet. Active preferences are "
                "prepared for independent processing; paused preferences are excluded "
                "from future job discovery runs."
            ),
            total_preferences=total_count,
            active_preferences=active_count,
            paused_preferences=paused_count,
            workflow_steps=USER_CENTRIC_WORKFLOW_STEPS,
            preferences=summaries,
        )

    @staticmethod
    def serialize_workflow_run(
        db: Session,
        wf_run: JobHuntRun,
    ) -> WorkflowRunSummaryResponse:
        """Serialize a `JobHuntRun` with its `PreferenceExecution` records."""
        pref_names = {
            p.id: p.preference_name
            for p in db.scalars(select(JobPreference)).all()
        }
        pref_summaries: List[PreferenceRunSummaryResponse] = []
        for pr in wf_run.preference_executions:
            pref_summaries.append(
                PreferenceRunSummaryResponse(
                    id=pr.id,
                    run_id=pr.run_id,
                    preference_id=pr.preference_id,
                    preference_name=pref_names.get(pr.preference_id, "Job Preference"),
                    status=pr.status,
                    current_agent=pr.current_agent,
                    approved_resume_version_id=pr.approved_resume_version_id,
                    jobs_discovered=pr.jobs_discovered,
                    matching_jobs=pr.matching_jobs,
                    shortlisted_jobs=pr.shortlisted_jobs,
                    applications_submitted=pr.applications_submitted,
                    interviews_scheduled=pr.interviews_scheduled,
                    offers_received=pr.offers_received,
                    error_message=pr.error_message,
                    started_at=pr.started_at,
                    completed_at=pr.completed_at,
                    created_at=pr.created_at,
                    updated_at=pr.updated_at,
                )
            )
        return WorkflowRunSummaryResponse(
            id=wf_run.id,
            status=wf_run.status,
            trigger_source=wf_run.trigger_source,
            current_stage=wf_run.current_stage,
            approval_mode=wf_run.approval_mode,
            total_preferences=wf_run.total_preferences,
            active_preferences=wf_run.active_preferences,
            max_jobs_per_run=wf_run.max_jobs_per_run,
            max_applications_per_run=wf_run.max_applications_per_run,
            api_spend_usd=wf_run.api_spend_usd,
            error_message=wf_run.error_message,
            started_at=wf_run.started_at,
            paused_at=wf_run.paused_at,
            stopped_at=wf_run.stopped_at,
            completed_at=wf_run.completed_at,
            created_at=wf_run.created_at,
            updated_at=wf_run.updated_at,
            preference_executions=pref_summaries,
        )

    @classmethod
    def get_dashboard_overview(cls, db: Session) -> DashboardOverviewResponse:
        """Compute the complete Part 10 Dashboard Overview directly from PostgreSQL."""
        settings = central_orchestrator.get_or_create_settings(db)
        preferences = JobPreferenceService.list_preferences(db)

        total_discovered = int(
            db.scalar(select(func.count(DiscoveredJob.id))) or 0
        )
        total_matching = int(
            db.scalar(
                select(func.count(JobMatch.id)).where(JobMatch.is_matching.is_(True))
            )
            or 0
        )
        total_shortlisted = int(
            db.scalar(
                select(func.count(JobMatch.id)).where(JobMatch.shortlisted.is_(True))
            )
            or 0
        )
        total_submitted = int(
            db.scalar(
                select(func.count(Application.id)).where(
                    Application.status.in_(SUBMITTED_EQUIVALENT_STATUSES)
                )
            )
            or 0
        )
        total_interviews = int(
            db.scalar(
                select(func.count(Application.id)).where(
                    Application.status == "Interview"
                )
            )
            or 0
        )
        total_offers = int(
            db.scalar(
                select(func.count(Application.id)).where(Application.status == "Offer")
            )
            or 0
        )

        active_count = sum(1 for p in preferences if p.is_active)
        paused_count = len(preferences) - active_count
        eligible_count = sum(1 for p in preferences if p.eligible_for_applications)

        last_wf_run = db.scalars(
            select(JobHuntRun).order_by(JobHuntRun.created_at.desc()).limit(1)
        ).first()
        last_run_summary = (
            cls.serialize_workflow_run(db, last_wf_run) if last_wf_run else None
        )

        preference_cards: List[DashboardPreferenceCardItem] = []
        for idx, pref in enumerate(preferences, start=1):
            latest_pref_run = db.scalars(
                select(PreferenceExecution)
                .where(PreferenceExecution.preference_id == pref.id)
                .order_by(PreferenceExecution.created_at.desc())
                .limit(1)
            ).first()

            pref_matches = list(
                db.scalars(
                    select(JobMatch)
                    .where(JobMatch.preference_id == pref.id)
                    .order_by(JobMatch.match_score.desc(), JobMatch.created_at.desc())
                ).all()
            )
            pref_discovered_count = (
                latest_pref_run.jobs_discovered
                if latest_pref_run and latest_pref_run.jobs_discovered > 0
                else len(pref_matches)
            )
            pref_matching_count = sum(1 for m in pref_matches if m.is_matching)
            pref_shortlisted_count = sum(1 for m in pref_matches if m.shortlisted)

            tracking_metrics = agent5_tracking.compute_preference_tracking_metrics(
                db, pref.id
            )

            if not pref.is_active:
                wf_status = "paused"
            elif latest_pref_run:
                wf_status = latest_pref_run.status
            else:
                wf_status = "ready"

            recent_matches_payload: List[Dict[str, Any]] = []
            for m in pref_matches[:6]:
                job = m.discovered_job
                recent_matches_payload.append(
                    {
                        "match_id": str(m.id),
                        "job_id": str(job.id) if job else None,
                        "title": job.title if job else "Job Listing",
                        "company": job.company if job else "",
                        "location": job.location if job else "",
                        "work_mode": job.work_mode if job else "",
                        "match_score": m.match_score,
                        "shortlisted": m.shortlisted,
                        "official_job_url": job.official_job_url if job else "",
                        "skills_matched": m.skills_matched,
                    }
                )

            preference_cards.append(
                DashboardPreferenceCardItem(
                    preference_id=pref.id,
                    code=f"P{idx}",
                    preference_name=pref.preference_name,
                    target_roles=pref.job_roles,
                    locations=pref.locations,
                    work_mode=pref.work_mode,
                    is_active=pref.is_active,
                    has_approved_resume=pref.has_approved_resume,
                    eligible_for_applications=pref.eligible_for_applications,
                    workflow_status=wf_status,
                    jobs_discovered=pref_discovered_count,
                    matching_jobs=pref_matching_count,
                    shortlisted_jobs=pref_shortlisted_count,
                    applications_submitted=tracking_metrics["applications_submitted"],
                    interviews=tracking_metrics["interviews_scheduled"],
                    offers=tracking_metrics["offers_received"],
                    recent_matches=recent_matches_payload,
                )
            )

        notifications = list(
            db.scalars(
                select(Notification)
                .order_by(Notification.created_at.desc())
                .limit(10)
            ).all()
        )
        recent_updates = [
            NotificationResponse.model_validate(n) for n in notifications
        ]

        # Build 7-day activity series from PostgreSQL
        now_utc = datetime.now(timezone.utc)
        activity_series: List[Dict[str, Any]] = []
        for day_offset in range(6, -1, -1):
            target_day = (now_utc - timedelta(days=day_offset)).date()
            day_start = datetime.combine(
                target_day, datetime.min.time(), tzinfo=timezone.utc
            )
            day_end = day_start + timedelta(days=1)
            disc_c = int(
                db.scalar(
                    select(func.count(DiscoveredJob.id)).where(
                        DiscoveredJob.discovered_at >= day_start,
                        DiscoveredJob.discovered_at < day_end,
                    )
                )
                or 0
            )
            app_c = int(
                db.scalar(
                    select(func.count(Application.id)).where(
                        Application.created_at >= day_start,
                        Application.created_at < day_end,
                    )
                )
                or 0
            )
            activity_series.append(
                {
                    "day": target_day.strftime("%a"),
                    "date": target_day.isoformat(),
                    "discovered": disc_c,
                    "applications": app_c,
                }
            )

        return DashboardOverviewResponse(
            jobs_discovered=total_discovered,
            matching_jobs=total_matching,
            shortlisted_jobs=total_shortlisted,
            applications_submitted=total_submitted,
            interviews=total_interviews,
            offers=total_offers,
            automation_state=settings.automation_state,
            is_kill_switch_engaged=settings.is_kill_switch_engaged,
            approval_mode=settings.approval_mode,
            active_preferences_count=active_count,
            paused_preferences_count=paused_count,
            eligible_preferences_count=eligible_count,
            last_run=last_run_summary,
            preference_performance=preference_cards,
            recent_updates=recent_updates,
            activity_series=activity_series,
        )

    @staticmethod
    def get_settings(db: Session) -> AutomationSettingsResponse:
        settings = central_orchestrator.get_or_create_settings(db)
        resp = AutomationSettingsResponse.model_validate(settings)
        resp.telegram_configured = telegram_service.is_configured()
        return resp

    @staticmethod
    def update_settings(
        db: Session,
        payload: AutomationSettingsUpdate,
    ) -> AutomationSettingsResponse:
        settings = central_orchestrator.get_or_create_settings(db)
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(settings, field, value)
        db.commit()
        db.refresh(settings)
        resp = AutomationSettingsResponse.model_validate(settings)
        resp.telegram_configured = telegram_service.is_configured()
        return resp

    @staticmethod
    def get_or_create_schedule(db: Session) -> ScheduledJob:
        sched = db.scalars(select(ScheduledJob).limit(1)).first()
        if sched is None:
            sched = ScheduledJob(
                name="Daily JobHunter Run",
                is_enabled=False,
                cron_expression="0 9 * * *",
                daily_time="09:00",
                timezone="Asia/Kolkata",
                max_jobs_per_run=50,
                max_applications_per_run=10,
            )
            db.add(sched)
            db.commit()
            db.refresh(sched)
        return sched

    @classmethod
    def get_schedule(cls, db: Session) -> ScheduledJobResponse:
        sched = cls.get_or_create_schedule(db)
        return ScheduledJobResponse.model_validate(sched)

    @classmethod
    def update_schedule(
        cls,
        db: Session,
        payload: ScheduledJobUpdate,
    ) -> ScheduledJobResponse:
        sched = cls.get_or_create_schedule(db)
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(sched, field, value)

        if "daily_time" in update_data and update_data["daily_time"]:
            hr, mn = update_data["daily_time"].split(":")
            sched.cron_expression = f"{int(mn)} {int(hr)} * * *"

        if sched.is_enabled:
            now = datetime.now(timezone.utc)
            hr, mn = (sched.daily_time or "09:00").split(":")
            candidate = now.replace(
                hour=int(hr), minute=int(mn), second=0, microsecond=0
            )
            if candidate <= now:
                candidate = candidate + timedelta(days=1)
            sched.next_run_at = candidate
        else:
            sched.next_run_at = None

        db.commit()
        db.refresh(sched)
        return ScheduledJobResponse.model_validate(sched)

    @classmethod
    def list_workflow_runs(
        cls,
        db: Session,
        limit: int = 20,
    ) -> List[WorkflowRunSummaryResponse]:
        runs = list(
            db.scalars(
                select(JobHuntRun)
                .order_by(JobHuntRun.created_at.desc())
                .limit(limit)
            ).all()
        )
        return [cls.serialize_workflow_run(db, r) for r in runs]

    @staticmethod
    def list_agent_executions(
        db: Session,
        workflow_run_id: Optional[uuid.UUID] = None,
        limit: int = 50,
    ) -> List[AgentExecutionResponse]:
        stmt = select(AgentExecution).order_by(AgentExecution.started_at.desc())
        if workflow_run_id:
            stmt = stmt.where(AgentExecution.workflow_run_id == workflow_run_id)
        rows = list(db.scalars(stmt.limit(limit)).all())
        return [AgentExecutionResponse.model_validate(r) for r in rows]
