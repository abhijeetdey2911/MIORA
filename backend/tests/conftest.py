import os
from unittest.mock import MagicMock, patch
import pytest

# Ensure safe test environment defaults
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("TELEGRAM_NOTIFICATIONS_ENABLED", "false")


@pytest.fixture(autouse=True)
def prevent_external_telegram_calls():
    """Autouse fixture ensuring no tests ever dispatch real HTTP requests to Telegram API."""
    with patch(
        "app.services.telegram_service.TelegramNotificationService._send_telegram_http",
        return_value={"ok": True, "result": {"message_id": 999999, "chat": {"id": -1000000000000}}},
    ) as mock_send:
        yield mock_send


@pytest.fixture(autouse=True)
def guard_production_database():
    """Safety guard: Abort immediately if any test attempts to run against a production database."""
    from app.core.config import get_settings
    settings = get_settings()
    if settings.ENVIRONMENT.lower() in ("production", "prod"):
        raise RuntimeError(
            "CRITICAL SAFETY VIOLATION: Test suite execution is strictly prohibited in PRODUCTION environment!"
        )
