"""SQLAlchemy models package."""

from app.models.job_preference import JobPreference
from app.models.multi_agent import (
    AgentExecution,
    Application,
    ApplicationRoute,
    ApplicationStatusHistory,
    AutomationSettings,
    DiscoveredJob,
    JobMatch,
    JobSource,
    Notification,
    ScheduledJob,
)
from app.models.orchestration import (
    JobHuntRun,
    PreferenceApplication,
    PreferenceExecution,
    PreferenceJobResult,
    PreferenceRun,
    WorkflowRun,
)
from app.models.resume import Resume, resume_preferences
from app.models.resume_intelligence import (
    ResumeAnalysis,
    ResumeSuggestion,
    ResumeVersion,
)

__all__ = [
    "JobPreference",
    "JobHuntRun",
    "WorkflowRun",
    "PreferenceExecution",
    "PreferenceRun",
    "PreferenceJobResult",
    "PreferenceApplication",
    "Resume",
    "resume_preferences",
    "ResumeAnalysis",
    "ResumeSuggestion",
    "ResumeVersion",
    "JobSource",
    "DiscoveredJob",
    "JobMatch",
    "ApplicationRoute",
    "Application",
    "ApplicationStatusHistory",
    "AgentExecution",
    "AutomationSettings",
    "ScheduledJob",
    "Notification",
]
