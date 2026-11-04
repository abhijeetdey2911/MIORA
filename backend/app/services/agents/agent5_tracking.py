"""Agent 5: Application Tracking (Part 7).

Responsibilities:
- Track every application across all 11 lifecycle statuses:
  - Prepared
  - Awaiting Approval
  - Submitted
  - Submission Unconfirmed
  - Under Review
  - Recruiter Response
  - Interview
  - Rejected
  - Offer
  - Withdrawn
  - No Response
- Maintain an immutable audit trail (`ApplicationStatusHistory`) for every status transition.
- Manage interview dates, recruiter responses, notes, and follow-up reminders.
- Safely reconcile `"Submission Unconfirmed"` applications before any retry.
- Synchronize preference-level and run-level counters (`PreferenceExecution`, `JobHuntRun`).
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.multi_agent import Application, ApplicationStatusHistory
from app.models.orchestration import JobHuntRun, PreferenceExecution
from app.services.telegram_service import telegram_service

VALID_APPLICATION_STATUSES = (
    "Prepared",
    "Awaiting Approval",
    "Submitted",
    "Submission Unconfirmed",
    "Under Review",
    "Recruiter Response",
    "Interview",
    "Rejected",
    "Offer",
    "Withdrawn",
    "No Response",
)

SUBMITTED_EQUIVALENT_STATUSES = (
    "Submitted",
    "Under Review",
    "Recruiter Response",
    "Interview",
    "Rejected",
    "Offer",
    "No Response",
)


class ApplicationTrackingAgent:
    """Agent 5: Tracks application lifecycle, follow-up reminders, status transitions, and metrics."""

    def sync_preference_applications(
        self,
        db: Session,
        preference_id: uuid.UUID,
        preference_run_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, int]:
        """Inspect all applications for a preference, set default follow-up reminders on newly
        submitted applications, and compute live tracking counts.
        """
        now = datetime.now(timezone.utc)
        apps = list(
            db.scalars(
                select(Application).where(Application.preference_id == preference_id)
            ).all()
        )

        for app_record in apps:
            if (
                app_record.status == "Submitted"
                and app_record.applied_at is not None
                and app_record.follow_up_reminder_at is None
            ):
                app_record.follow_up_reminder_at = app_record.applied_at + timedelta(days=7)

        db.flush()

        metrics = self.compute_preference_tracking_metrics(db, preference_id)

        if preference_run_id:
            pref_run = db.get(PreferenceExecution, preference_run_id)
            if pref_run:
                pref_run.applications_submitted = metrics["applications_submitted"]
                pref_run.interviews_scheduled = metrics["interviews_scheduled"]
                pref_run.offers_received = metrics["offers_received"]
                db.flush()

        db.commit()
        return metrics

    @staticmethod
    def compute_preference_tracking_metrics(
        db: Session,
        preference_id: uuid.UUID,
    ) -> Dict[str, int]:
        """Compute accurate status breakdown for a given preference from PostgreSQL."""
        apps = list(
            db.scalars(
                select(Application).where(Application.preference_id == preference_id)
            ).all()
        )
        submitted_count = sum(
            1 for a in apps if a.status in SUBMITTED_EQUIVALENT_STATUSES
        )
        awaiting_approval = sum(
            1 for a in apps if a.status in ("Prepared", "Awaiting Approval")
        )
        unconfirmed = sum(1 for a in apps if a.status == "Submission Unconfirmed")
        interviews = sum(1 for a in apps if a.status == "Interview")
        offers = sum(1 for a in apps if a.status == "Offer")
        rejections = sum(1 for a in apps if a.status == "Rejected")
        responses = sum(
            1
            for a in apps
            if a.status in ("Recruiter Response", "Interview", "Offer", "Rejected")
            or bool(a.recruiter_response_text)
        )
        return {
            "total_applications": len(apps),
            "applications_submitted": submitted_count,
            "awaiting_approval": awaiting_approval,
            "submission_unconfirmed": unconfirmed,
            "interviews_scheduled": interviews,
            "offers_received": offers,
            "rejections_received": rejections,
            "responses_received": responses,
        }

    def update_application_status(
        self,
        db: Session,
        application_id: uuid.UUID,
        new_status: str,
        *,
        source: str = "user_or_agent_5",
        notes: Optional[str] = None,
        evidence: Optional[str] = None,
        interview_date: Optional[datetime] = None,
        recruiter_response_text: Optional[str] = None,
        follow_up_reminder_at: Optional[datetime] = None,
    ) -> Application:
        """Transition an application to a validated status and record an audit trail entry."""
        if new_status not in VALID_APPLICATION_STATUSES:
            raise ValueError(
                f"Invalid status '{new_status}'. Allowed statuses: {', '.join(VALID_APPLICATION_STATUSES)}"
            )

        app_record = db.get(Application, application_id)
        if not app_record:
            raise ValueError("Application not found.")

        now = datetime.now(timezone.utc)
        previous_status = app_record.status

        if new_status == "Submitted" and not (evidence or app_record.confirmation_evidence):
            raise ValueError(
                "Cannot mark application as 'Submitted' without confirmation evidence. "
                "Use 'Submission Unconfirmed' when confirmation receipt is unavailable."
            )

        app_record.status = new_status
        if evidence:
            app_record.confirmation_evidence = evidence
        if new_status == "Submitted" and app_record.applied_at is None:
            app_record.applied_at = now
            if app_record.follow_up_reminder_at is None:
                app_record.follow_up_reminder_at = now + timedelta(days=7)

        if interview_date is not None:
            app_record.interview_date = interview_date
        if recruiter_response_text is not None:
            app_record.recruiter_response_text = recruiter_response_text
        if follow_up_reminder_at is not None:
            app_record.follow_up_reminder_at = follow_up_reminder_at
        if notes is not None:
            app_record.notes = notes

        history_entry = ApplicationStatusHistory(
            application_id=app_record.id,
            previous_status=previous_status,
            new_status=new_status,
            source=source,
            notes=notes or f"Status updated from '{previous_status}' to '{new_status}'.",
            evidence=evidence or app_record.confirmation_evidence,
        )
        db.add(history_entry)
        db.commit()
        db.refresh(app_record)

        # Synchronize PreferenceExecution / JobHuntRun counters
        self.sync_preference_applications(
            db,
            preference_id=app_record.preference_id,
            preference_run_id=app_record.preference_run_id,
        )

        # Dispatch notification for key milestones
        milestone_event_map = {
            "Submitted": ("application_submitted", f"Application Submitted: {app_record.job_title}"),
            "Submission Unconfirmed": (
                "submission_unconfirmed",
                f"Submission Unconfirmed: {app_record.job_title}",
            ),
            "Recruiter Response": (
                "recruiter_response",
                f"Recruiter Response from {app_record.company}",
            ),
            "Interview": (
                "interview_update",
                f"Interview Scheduled: {app_record.job_title} at {app_record.company}",
            ),
            "Offer": (
                "offer_received",
                f"Offer Received: {app_record.job_title} at {app_record.company}",
            ),
            "Rejected": (
                "application_update",
                f"Application Update ({app_record.company}): Rejected",
            ),
            "Under Review": (
                "application_update",
                f"Application Under Review: {app_record.job_title} at {app_record.company}",
            ),
        }
        if new_status in milestone_event_map and new_status != previous_status:
            event_type, title = milestone_event_map[new_status]
            telegram_service.record_and_dispatch(
                db,
                event_type=event_type,
                title=title,
                message=notes
                or recruiter_response_text
                or f"{app_record.job_title} at {app_record.company} is now '{new_status}'.",
                preference_id=app_record.preference_id,
                application_id=app_record.id,
                company=app_record.company,
                job_title=app_record.job_title,
                status_badge=new_status,
            )

        return app_record

    def reconcile_unconfirmed_submission(
        self,
        db: Session,
        application_id: uuid.UUID,
        resolution: str,
        confirmation_evidence: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Application:
        """Reconcile an application in `'Submission Unconfirmed'` status before any retry.

        `resolution` must be one of:
        - `'Submitted'` (requires `confirmation_evidence`)
        - `'Awaiting Approval'` (clears unconfirmed lock so user/agent can safely retry)
        - `'Withdrawn'`
        """
        app_record = db.get(Application, application_id)
        if not app_record:
            raise ValueError("Application not found.")
        if app_record.status != "Submission Unconfirmed":
            raise ValueError(
                f"Application status is '{app_record.status}', not 'Submission Unconfirmed'."
            )
        if resolution not in ("Submitted", "Awaiting Approval", "Withdrawn"):
            raise ValueError(
                "Reconciliation resolution must be 'Submitted', 'Awaiting Approval', or 'Withdrawn'."
            )
        if resolution == "Submitted" and not confirmation_evidence:
            raise ValueError(
                "Reconciling to 'Submitted' requires confirmation_evidence (e.g. email or portal receipt)."
            )

        if resolution == "Awaiting Approval":
            app_record.retry_count = (app_record.retry_count or 0) + 1

        return self.update_application_status(
            db,
            application_id=application_id,
            new_status=resolution,
            source="reconciliation",
            notes=notes
            or f"Reconciled Submission Unconfirmed -> {resolution}.",
            evidence=confirmation_evidence,
        )


agent5_tracking = ApplicationTrackingAgent()
