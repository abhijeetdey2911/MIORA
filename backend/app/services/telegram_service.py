"""Telegram Bot API Notification Service (Part 12).

Security Guarantees:
- Reads `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` strictly from backend environment variables.
- Never exposes bot tokens in logs or API responses.
- Stores every notification in PostgreSQL (`notifications` table) and optionally dispatches via Telegram Bot API.
"""

import logging
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.multi_agent import AutomationSettings, Notification

logger = logging.getLogger("jobhunter.telegram")


class TelegramNotificationService:
    """Manages persistent application/workflow notifications and optional Telegram Bot delivery."""

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
        """Persist a Notification in PostgreSQL and dispatch via Telegram if enabled and configured."""
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
            event_type=event_type,
            automation_settings=automation_settings,
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
    def _should_send_telegram(
        event_type: str,
        automation_settings: Optional[AutomationSettings],
    ) -> bool:
        """Check whether Telegram delivery is enabled for the given event_type."""
        if not (
            settings.TELEGRAM_NOTIFICATIONS_ENABLED
            or (
                automation_settings is not None
                and automation_settings.telegram_notifications_enabled
            )
        ):
            return False

        if automation_settings is None:
            return True

        mapping = {
            "workflow_started": automation_settings.notify_on_workflow_start,
            "workflow_completed": automation_settings.notify_on_workflow_complete,
            "important_error": automation_settings.notify_on_errors,
            "application_approved": automation_settings.notify_on_application_submitted,
            "submission_started": automation_settings.notify_on_application_submitted,
            "submission_confirmed": automation_settings.notify_on_application_submitted,
            "application_submitted": automation_settings.notify_on_application_submitted,
            "submission_unconfirmed": automation_settings.notify_on_submission_unconfirmed,
            "submission_failed": automation_settings.notify_on_errors,
            "interview_invitation": automation_settings.notify_on_interview,
            "interview_update": automation_settings.notify_on_interview,
            "recruiter_response": automation_settings.notify_on_recruiter_response,
            "offer": automation_settings.notify_on_offer,
            "offer_received": automation_settings.notify_on_offer,
            "daily_summary": automation_settings.notify_daily_summary,
        }
        return mapping.get(event_type, True)

    @staticmethod
    def _send_telegram_http(title: str, message: str) -> tuple[bool, Optional[str]]:
        """Send message via official Telegram Bot API (`sendMessage`). Never logs token."""
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
