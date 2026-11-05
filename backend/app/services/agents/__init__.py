"""Multi-Agent JobHunting System Agents Package (Agents 1 through 5)."""

from app.services.agents.agent1_discovery import (
    ArbeitnowPublicAPIAdapter,
    BaseJobSourceAdapter,
    GreenhouseOfficialCompanyAdapter,
    JobDiscoveryAgent,
    JobicyRemoteAPIAdapter,
    RawDiscoveredJobItem,
    RemotiveOfficialAPIAdapter,
    compute_job_fingerprint,
    normalize_canonical_url,
)
from app.services.agents.agent2_matching import JobMatchingAgent
from app.services.agents.agent3_routes import ApplicationRouteDiscoveryAgent
from app.services.agents.agent4_execution import ApplicationExecutionAgent, agent4_execution
from app.services.agents.agent5_tracking import ApplicationTrackingAgent, agent5_tracking

agent1_discovery = JobDiscoveryAgent()
agent2_matching = JobMatchingAgent()
agent3_routes = ApplicationRouteDiscoveryAgent()

__all__ = [
    "BaseJobSourceAdapter",
    "RawDiscoveredJobItem",
    "GreenhouseOfficialCompanyAdapter",
    "JobicyRemoteAPIAdapter",
    "RemotiveOfficialAPIAdapter",
    "ArbeitnowPublicAPIAdapter",
    "JobDiscoveryAgent",
    "JobMatchingAgent",
    "ApplicationRouteDiscoveryAgent",
    "ApplicationExecutionAgent",
    "ApplicationTrackingAgent",
    "normalize_canonical_url",
    "compute_job_fingerprint",
    "agent1_discovery",
    "agent2_matching",
    "agent3_routes",
    "agent4_execution",
    "agent5_tracking",
]
