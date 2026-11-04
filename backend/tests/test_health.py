"""Tests for Project JobHunter Health Endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_health_endpoint() -> None:
    """Test GET /health returns 200 and required fields."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "degraded"]
    assert data["project"] == "Project JobHunter"
    assert data["version"] == "0.1.0"
    assert "services" in data
    assert "database" in data["services"]
    assert "api" in data["services"]
    assert data["services"]["api"]["status"] == "operational"


def test_api_v1_health_endpoint() -> None:
    """Test GET /api/v1/health returns 200 and matches root health format."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["services"]["api"]["status"] == "operational"


def test_root_meta_endpoint() -> None:
    """Test GET / returns metadata and documentation links."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "Project JobHunter"
    assert "docs" in data
    assert "health" in data

