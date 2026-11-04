"""Application configuration management using Pydantic Settings."""

from pathlib import Path
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_ROOT_DIR = _BACKEND_DIR.parent


class Settings(BaseSettings):
    """JobHunter application settings loaded from environment or defaults."""

    # Project metadata
    PROJECT_NAME: str = "Project JobHunter"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS Origins (allow list or comma-delimited string)
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return [str(item) for item in v]
        return ["http://localhost:5174", "http://localhost:5173"]

    # PostgreSQL Database configuration
    POSTGRES_SERVER: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "replace_with_secure_password"
    POSTGRES_DB: str = "jobhunter"
    DATABASE_URL: Optional[str] = None

    # Connection pool configuration
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_PRE_PING: bool = True
    DB_CONNECT_TIMEOUT: float = 2.0

    # Resume storage configuration (prepared for local or cloud storage backends)
    STORAGE_BACKEND: str = "local"
    RESUME_STORAGE_DIR: str = str(_BACKEND_DIR / "storage" / "resumes")
    MAX_RESUME_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

    # Phase 3B — AI Provider Configuration (Backend-only; never exposed to frontend)
    AI_PROVIDER: str = "openai"
    AI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    AI_MODEL: str = "gpt-4o-mini"
    AI_FALLBACK_MODEL: Optional[str] = None
    GEMINI_FALLBACK_MODEL: Optional[str] = "gemini-1.5-flash"
    OPENAI_FALLBACK_MODEL: Optional[str] = None
    AI_BASE_URL: Optional[str] = None
    AI_TIMEOUT_SECONDS: float = 150.0
    AI_MAX_RETRIES: int = 3
    AI_INITIAL_BACKOFF_SECONDS: float = 1.0

    # Multi-Agent Background Execution (Celery & Redis)
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # Telegram Bot Notification Configuration (Backend-only; never exposed to frontend)
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    TELEGRAM_NOTIFICATIONS_ENABLED: bool = False

    # Automation Control Centre & Safety Defaults
    DEFAULT_MAX_JOBS_PER_RUN: int = 50
    DEFAULT_MAX_APPLICATIONS_PER_RUN: int = 10
    DEFAULT_MAX_APPLICATIONS_PER_DAY: int = 25
    DEFAULT_MAX_RUNTIME_SECONDS: int = 1800
    DEFAULT_MAX_API_SPEND_USD: float = 5.0
    DEFAULT_MIN_MATCH_SCORE: int = 70
    DEFAULT_RETRY_LIMIT: int = 2
    DEFAULT_APPROVAL_MODE: str = "manual"
    PLAYWRIGHT_ENABLED: bool = False
    PLAYWRIGHT_HEADLESS: bool = True

    def is_telegram_configured(self) -> bool:
        """Return True if a valid Telegram Bot token and Chat ID are configured."""
        token = (self.TELEGRAM_BOT_TOKEN or "").strip()
        chat_id = (self.TELEGRAM_CHAT_ID or "").strip()
        placeholders = {"", "your_bot_token_here", "replace_with_bot_token", "none", "null"}
        return bool(token and chat_id and token.lower() not in placeholders)

    def get_effective_ai_api_key(self) -> Optional[str]:
        """Return the configured LLM API key from environment variables, or None if unset."""
        candidates = [
            self.AI_API_KEY,
            self.OPENAI_API_KEY,
            self.GEMINI_API_KEY,
            self.GROQ_API_KEY,
            self.ANTHROPIC_API_KEY,
        ]
        placeholders = {
            "",
            "your_api_key_here",
            "replace_with_your_api_key",
            "replace_with_api_key",
            "none",
            "null",
        }
        for key in candidates:
            if key is not None:
                cleaned = key.strip()
                if cleaned and cleaned.lower() not in placeholders:
                    return cleaned
        return None

    def get_effective_fallback_model(self) -> Optional[str]:
        """Return the configured fallback model for the active AI provider, if different from primary."""
        primary = (self.AI_MODEL or "").strip()
        candidates: List[Optional[str]] = []

        if self.AI_FALLBACK_MODEL:
            candidates.append(self.AI_FALLBACK_MODEL)

        provider = (self.AI_PROVIDER or "").lower().strip()
        if provider == "gemini":
            candidates.append(self.GEMINI_FALLBACK_MODEL)
            # Default to gemini-1.5-flash if primary is gemini-2.5-flash or gemini-2.0-flash
            if primary in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"):
                candidates.append("gemini-1.5-flash")
            elif primary == "gemini-1.5-flash":
                candidates.append("gemini-2.0-flash")
        elif provider == "openai":
            candidates.append(self.OPENAI_FALLBACK_MODEL)
            if primary == "gpt-4o":
                candidates.append("gpt-4o-mini")

        for cand in candidates:
            if cand:
                cleaned = cand.strip()
                if cleaned and cleaned != primary:
                    return cleaned
        return None

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Construct or return standard SQLAlchemy database connection URI."""
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            # Normalize PostgreSQL scheme to modern psycopg v3 driver if not explicitly specified
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg://", 1)
            elif url.startswith("postgresql://") and "+psycopg" not in url:
                url = url.replace("postgresql://", "postgresql+psycopg://", 1)
            return url

        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=(str(_ROOT_DIR / ".env"), str(_BACKEND_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()


def get_settings() -> Settings:
    """Return the singleton Settings instance."""
    return settings
