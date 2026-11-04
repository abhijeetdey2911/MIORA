"""Health check schema definitions."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DatabaseHealth(BaseModel):
    """Database connection status schema."""
    status: str = Field(description="Database connectivity status: 'connected' or 'disconnected'")
    latency_ms: Optional[float] = Field(default=None, description="Database ping latency in milliseconds")
    dialect: str = Field(default="postgresql", description="Database SQL dialect")
    error: Optional[str] = Field(default=None, description="Error message if disconnected")


class ApiHealth(BaseModel):
    """API service status schema."""
    status: str = Field(default="operational", description="Core API service status")
    uptime_seconds: float = Field(description="Uptime in seconds since process startup")


class SystemInfo(BaseModel):
    """Host system runtime information."""
    python_version: str
    environment: str


class ServiceHealthMap(BaseModel):
    """Aggregated services health map."""
    database: DatabaseHealth
    api: ApiHealth


class HealthResponse(BaseModel):
    """Top-level health response model."""
    status: str = Field(description="Overall platform status: 'healthy', 'degraded', or 'unhealthy'")
    project: str = Field(description="Project name")
    version: str = Field(description="Application version")
    environment: str = Field(description="Runtime environment")
    timestamp: datetime = Field(description="Current UTC timestamp")
    services: ServiceHealthMap = Field(description="Status of individual sub-services")
    system: SystemInfo = Field(description="System runtime metrics")

