"""Tests for Project JobHunter Job Preferences CRUD Endpoints."""

import uuid
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _sample_payload(**overrides):
    payload = {
        "preference_name": "Full-Stack Product Engineer",
        "job_roles": ["Full-Stack Engineer", "Backend Developer", "Software Engineer"],
        "locations": ["Bengaluru", "Hyderabad", "Remote"],
        "work_mode": "Hybrid",
        "employment_type": "Full-time",
        "experience_level": "Entry-level",
        "min_salary": 1200000,
        "max_salary": 2400000,
        "currency": "INR",
        "skills": ["Python", "FastAPI", "React", "TypeScript", "PostgreSQL"],
        "minimum_match_score": 80,
        "is_active": True,
    }
    payload.update(overrides)
    return payload


def test_preferences_crud_lifecycle() -> None:
    """Test creating, listing, retrieving, updating, toggling status, and deleting a preference."""
    # 1. Create preference (POST /api/v1/preferences)
    create_res = client.post("/api/v1/preferences", json=_sample_payload())
    assert create_res.status_code == 201, create_res.text
    created = create_res.json()
    pref_id = created["id"]
    assert created["preference_name"] == "Full-Stack Product Engineer"
    assert created["job_roles"] == ["Full-Stack Engineer", "Backend Developer", "Software Engineer"]
    assert created["locations"] == ["Bengaluru", "Hyderabad", "Remote"]
    assert created["work_mode"] == "Hybrid"
    assert created["employment_type"] == "Full-time"
    assert created["experience_level"] == "Entry-level"
    assert created["min_salary"] == 1200000
    assert created["max_salary"] == 2400000
    assert created["currency"] == "INR"
    assert len(created["skills"]) == 5
    assert created["minimum_match_score"] == 80
    assert created["is_active"] is True
    assert "created_at" in created
    assert "updated_at" in created

    try:
        # 2. List preferences (GET /api/v1/preferences)
        list_res = client.get("/api/v1/preferences")
        assert list_res.status_code == 200
        items = list_res.json()
        assert any(item["id"] == pref_id for item in items)

        # 3. Get single preference (GET /api/v1/preferences/{id})
        get_res = client.get(f"/api/v1/preferences/{pref_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == pref_id

        # 4. Update preference (PUT /api/v1/preferences/{id})
        updated_payload = _sample_payload(
            preference_name="AI Engineer — Remote",
            work_mode="Remote",
            experience_level="Experienced",
            min_salary=2000000,
            max_salary=3500000,
            minimum_match_score=85,
        )
        put_res = client.put(f"/api/v1/preferences/{pref_id}", json=updated_payload)
        assert put_res.status_code == 200
        updated = put_res.json()
        assert updated["preference_name"] == "AI Engineer — Remote"
        assert updated["work_mode"] == "Remote"
        assert updated["experience_level"] == "Experienced"
        assert updated["min_salary"] == 2000000
        assert updated["max_salary"] == 3500000
        assert updated["minimum_match_score"] == 85

        # 5. Pause preference via PATCH /api/v1/preferences/{id}/status with explicit status
        patch_res = client.patch(
            f"/api/v1/preferences/{pref_id}/status",
            json={"is_active": False},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["is_active"] is False

        # 6. Toggle preference status via PATCH /api/v1/preferences/{id}/status without body
        toggle_res = client.patch(f"/api/v1/preferences/{pref_id}/status")
        assert toggle_res.status_code == 200
        assert toggle_res.json()["is_active"] is True
    finally:
        # 7. Delete preference (DELETE /api/v1/preferences/{id})
        del_res = client.delete(f"/api/v1/preferences/{pref_id}")
        assert del_res.status_code == 200
        assert del_res.json()["id"] == pref_id

    # 8. Confirm 404 after deletion
    missing_res = client.get(f"/api/v1/preferences/{pref_id}")
    assert missing_res.status_code == 404


def test_preference_validation_errors() -> None:
    """Test validation rules for salary ranges, required lists, and enums."""
    # Max salary less than min salary
    bad_salary = _sample_payload(min_salary=2500000, max_salary=1500000)
    res_salary = client.post("/api/v1/preferences", json=bad_salary)
    assert res_salary.status_code == 422

    # Empty job_roles list
    empty_roles = _sample_payload(job_roles=[])
    res_roles = client.post("/api/v1/preferences", json=empty_roles)
    assert res_roles.status_code == 422

    # Invalid work_mode enum
    bad_mode = _sample_payload(work_mode="Anywhere")
    res_mode = client.post("/api/v1/preferences", json=bad_mode)
    assert res_mode.status_code == 422

    # Match score > 100
    bad_score = _sample_payload(minimum_match_score=110)
    res_score = client.post("/api/v1/preferences", json=bad_score)
    assert res_score.status_code == 422


def test_preference_not_found() -> None:
    """Test 404 responses for non-existent preference UUID."""
    random_id = str(uuid.uuid4())
    assert client.get(f"/api/v1/preferences/{random_id}").status_code == 404
    assert client.delete(f"/api/v1/preferences/{random_id}").status_code == 404


def test_orchestration_readiness_and_independent_toggles() -> None:
    """Test that two preferences can be toggled independently and orchestration readiness reflects it."""
    res_p1 = client.post(
        "/api/v1/preferences",
        json=_sample_payload(preference_name="P1 — Data Analytics", is_active=True),
    )
    res_p2 = client.post(
        "/api/v1/preferences",
        json=_sample_payload(preference_name="P2 — Software Development", is_active=True),
    )
    assert res_p1.status_code == 201
    assert res_p2.status_code == 201
    p1_id = res_p1.json()["id"]
    p2_id = res_p2.json()["id"]

    try:
        # Pause P2 while keeping P1 active
        patch_p2 = client.patch(
            f"/api/v1/preferences/{p2_id}/status",
            json={"is_active": False},
        )
        assert patch_p2.status_code == 200
        assert patch_p2.json()["is_active"] is False

        # Verify P1 is still active
        get_p1 = client.get(f"/api/v1/preferences/{p1_id}")
        assert get_p1.status_code == 200
        assert get_p1.json()["is_active"] is True

        # Check orchestration readiness endpoint
        orch_res = client.get("/api/v1/orchestration/readiness")
        assert orch_res.status_code == 200
        orch_data = orch_res.json()
        assert orch_data["engine_connected"] is False
        assert orch_data["automation_state"] == "ready"
        assert len(orch_data["workflow_steps"]) == 7

        by_id = {item["preference_id"]: item for item in orch_data["preferences"]}
        assert by_id[p1_id]["is_active"] is True
        assert by_id[p1_id]["eligible_for_discovery"] is True
        assert by_id[p2_id]["is_active"] is False
        assert by_id[p2_id]["eligible_for_discovery"] is False
    finally:
        client.delete(f"/api/v1/preferences/{p1_id}")
        client.delete(f"/api/v1/preferences/{p2_id}")


