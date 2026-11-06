"""Telegram Bot API Notification Service (Part 12).

Security & Reliability Guarantees:
- Reads `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` strictly from backend environment variables.
- Never exposes bot tokens in logs, exceptions, or API responses.
- Stores every notification in PostgreSQL (`notifications` table) for an immutable audit trail.
- Strict Test & Development Barrier: Never dispatches live HTTP messages in `test` or `development`
  environments, or when running under `pytest`.
- Central Double-Opt-In: Requires both `TELEGRAM_NOTIFICATIONS_ENABLED=true` in environment AND
  `automation_settings.telegram_notifications_enabled=true` in the database.
- Emergency Kill Switch Guard: Immediately suppresses all Telegram dispatches if `is_kill_switch_engaged=True`.
- Duplicate Event Suppression: Suppresses duplicate dispatches for the same application and event within 5 minutes.
"""

from datetime import datetime, timedelta, timezone
import logging
import os
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.multi_agent import AutomationSettings, Notification

logger = logging.getLogger("jobhunter.telegram")


class TelegramNotificationService:
    """Manages persistent application/workflow notifications and guarded Telegram Bot delivery."""

    @staticmethod
    def is_configured() -> bool:
        """Return True if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are configured on the backend."""
        return settings.is_telegram_configured()

    @staticmethod
    def create_and_dispatch(
        db: Session,
        event_type: str,
        title: str,
        message: str,
        preference_id: Optional[UUID] = None,
        application_id: Optional[UUID] = None,
        workflow_run_id: Optional[UUID] = None,
        company: Optional[str] = None,
        job_title: Optional[str] = None,
        status_badge: Optional[str] = None,
        automation_settings: Optional[AutomationSettings] = None,
    ) -> Notification:
        """Persist a Notification in PostgreSQL and dispatch via Telegram if enabled and verified."""
        notification = Notification(
            preference_id=preference_id,
            application_id=application_id,
            workflow_run_id=workflow_run_id,
            event_type=event_type,
            title=title[:250],
            message=message,
            company=company[:200] if company else None,
            job_title=job_title[:250] if job_title else None,
            status_badge=status_badge[:50] if status_badge else None,
            is_read=False,
            telegram_sent=False,
        )
        db.add(notification)
        db.flush()

        should_send = TelegramNotificationService._should_send_telegram(
            db=db,
            event_type=event_type,
            automation_settings=automation_settings,
            application_id=application_id,
        )

        if should_send and TelegramNotificationService.is_configured():
            ok, err = TelegramNotificationService._send_telegram_http(
                title=title,
                message=message,
            )
            notification.telegram_sent = ok
            notification.telegram_error = err

        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    def should_send_telegram(
        db: Optional[Session] = None,
        *,
        event_type: str,
        automation_settings: Optional[AutomationSettings] = None,
        application_id: Optional[UUID] = None,
    ) -> tuple[bool, str]:
        """Central verification check enforcing all environment, database, kill switch,
        and duplicate suppression rules. Returns (can_send, reason).
        """
        # 1. Test & Development Environment Barrier
        if (
            os.environ.get("PYTEST_CURRENT_TEST")
            or settings.ENVIRONMENT.lower() in ("test", "testing", "development")
            or getattr(settings, "TESTING", False)
        ):
            return False, "Telegram HTTP dispatch suppressed in test/dev environment."

        # 2. Global environment toggle must be enabled
        if not settings.TELEGRAM_NOTIFICATIONS_ENABLED:
            return False, "Telegram notifications disabled globally via TELEGRAM_NOTIFICATIONS_ENABLED."

        # 3. Resolve central AutomationSettings
        current_settings = automation_settings
        if current_settings is None and db is not None:
            try:
                current_settings = db.scalars(select(AutomationSettings).limit(1)).first()
            except Exception as exc:
                logger.warning("Could not load AutomationSettings for Telegram check: %s", exc)

        if current_settings is None:
            return False, "AutomationSettings record not found in database."

        # 4. Emergency Kill Switch Guard
        if current_settings.is_kill_switch_engaged:
            return False, "Kill switch is engaged."

        # 5. Central Automation Settings toggle must be enabled
        if not current_settings.telegram_notifications_enabled:
            return False, "Telegram notifications disabled in AutomationSettings."

        # 6. Event-specific notification category toggle
        mapping = {
            "workflow_started": current_settings.notify_on_workflow_start,
            "workflow_completed": current_settings.notify_on_workflow_complete,
            "workflow_start": current_settings.notify_on_workflow_start,
            "workflow_complete": current_settings.notify_on_workflow_complete,
            "important_error": current_settings.notify_on_errors,
            "workflow_error": current_settings.notify_on_errors,
            "application_approved": current_settings.notify_on_application_submitted,
            "submission_started": current_settings.notify_on_application_submitted,
            "submission_confirmed": current_settings.notify_on_application_submitted,
            "application_submitted": current_settings.notify_on_application_submitted,
            "submission_unconfirmed": current_settings.notify_on_submission_unconfirmed,
            "submission_failed": current_settings.notify_on_errors,
            "interview_invitation": current_settings.notify_on_interview,
            "interview_update": current_settings.notify_on_interview,
            "recruiter_response": current_settings.notify_on_recruiter_response,
            "offer": current_settings.notify_on_offer,
            "offer_received": current_settings.notify_on_offer,
            "daily_summary": current_settings.notify_daily_summary,
        }
        if not mapping.get(event_type, True):
            return False, f"Notification disabled for event type: {event_type}"

        # 7. Duplicate event suppression (5-minute window for same application & event)
        if db is not None and application_id is not None:
            try:
                cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
                recent_dup = db.scalars(
                    select(Notification).where(
                        Notification.event_type == event_type,
                        Notification.application_id == application_id,
                        Notification.telegram_sent.is_(True),
                        Notification.created_at >= cutoff,
                    ).limit(1)
                ).first()
                if recent_dup is not None:
                    return False, f"Duplicate notification for application {application_id} within 5 minutes."
            except Exception as exc:
                logger.debug("Duplicate check skipped due to query error: %s", exc)

        return True, "Telegram dispatch allowed."

    @staticmethod
    def _should_send_telegram(
        *,
        db: Optional[Session] = None,
        event_type: str,
        automation_settings: Optional[AutomationSettings] = None,
        application_id: Optional[UUID] = None,
    ) -> bool:
        can_send, _ = TelegramNotificationService.should_send_telegram(
            db,
            event_type=event_type,
            automation_settings=automation_settings,
            application_id=application_id,
        )
        return can_send

    @staticmethod
    def _send_telegram_http(title: str, message: str) -> tuple[bool, Optional[str]]:
        """Send message via official Telegram Bot API (`sendMessage`). Never logs tokens or sensitive keys."""
        token = (settings.TELEGRAM_BOT_TOKEN or "").strip()
        chat_id = (settings.TELEGRAM_CHAT_ID or "").strip()
        if not token or not chat_id:
            return False, "Telegram Bot token or Chat ID is not configured."

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": f"*{title}*\n{message}",
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, json=payload)
                if 200 <= res.status_code < 300:
                    return True, None
                return False, f"Telegram API returned HTTP {res.status_code}"
        except Exception as exc:
            logger.warning("Telegram notification delivery failed: %s", type(exc).__name__)
            return False, f"Telegram delivery error: {type(exc).__name__}"

    record_and_dispatch = create_and_dispatch


telegram_service = TelegramNotificationService()
