"""Tests for Project JobHunter Phase 3B — AI Resume Intelligence.

Note: Mocked LLM responses are used strictly inside this automated test module
via FastAPI dependency overrides, never in real user-facing application code.
"""

from typing import Any, Dict, List, Optional
import pymupdf
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.resume_intelligence import (
    CandidateProfileSummary,
    EducationItem,
    ExperienceItem,
    LLMRegenerateSuggestionPayload,
    LLMResumeAnalysisPayload,
    LLMResumeEnhancementPayload,
    PreferenceAnalysisItem,
    ProjectItem,
    ResumeScoreExplanations,
    SectionComparisonItem,
    SuggestionPayloadItem,
)
from app.services.ai_provider import AIProviderClient, get_ai_provider_client

client = TestClient(app)


def _create_pdf_resume_bytes() -> bytes:
    """Create an in-memory PDF resume with realistic text for testing."""
    text = (
        "Abhijeet Sharma\n"
        "Bangalore, India | abhijeet@example.com | github.com/abhijeet\n\n"
        "SUMMARY\n"
        "Full-Stack & Data Engineer with 2 years of experience building Python, SQL, "
        "FastAPI, and React applications.\n\n"
        "EDUCATION\n"
        "B.Tech in Computer Science — NIT Karnataka (2024)\n\n"
        "EXPERIENCE\n"
        "Software & Data Engineer — Acme Analytics (2024 – Present)\n"
        "- Built FastAPI microservices and SQL reporting pipelines.\n"
        "- Created interactive React dashboards for product metrics.\n\n"
        "INTERNSHIPS\n"
        "Data Analyst Intern — InsightCorp (Summer 2023)\n"
        "- Automated weekly SQL & Python ETL reports.\n\n"
        "PROJECTS\n"
        "JobHunter Platform — Python, FastAPI, PostgreSQL, React, TypeScript\n"
        "- Designed multi-preference job tracking and resume management system.\n\n"
        "CERTIFICATIONS\n"
        "AWS Certified Cloud Practitioner\n\n"
        "ACHIEVEMENTS\n"
        "Winner, National Hackathon 2023"
    )
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), text, fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class FakeConfiguredAIClient(AIProviderClient):
    """Test-only AIProviderClient double returning deterministic structured payloads."""

    def __init__(self) -> None:
        super().__init__(
            provider="openai",
            api_key="test-only-key-not-real",
            model="gpt-4o-mini",
        )

    def analyse_resume(
        self,
        resume_text: str,
        preferences_context: List[Dict[str, Any]],
    ) -> LLMResumeAnalysisPayload:
        pref_items: List[PreferenceAnalysisItem] = []
        for pref in preferences_context:
            pref_items.append(
                PreferenceAnalysisItem(
                    preference_id=pref["preference_id"],
                    preference_name=pref["preference_name"],
                    target_roles=pref.get("target_roles", []),
                    preference_relevance_score=84,
                    score_explanation=(
                        f"Strong alignment with {pref['preference_name']} via Python, SQL, and analytics/engineering projects."
                    ),
                    relevant_skills=["Python", "SQL", "FastAPI", "React"],
                    relevant_projects=["JobHunter Platform"],
                    experience_alignment="2 years of relevant engineering and analytics experience matches target level.",
                    missing_relevant_keywords=["Docker", "Power BI"],
                    strengths=["Hands-on Python & SQL production work", "Clear full-stack project ownership"],
                    weaknesses=["Could quantify latency or pipeline throughput metrics"],
                    improvement_opportunities=[
                        f"Highlight measurable outcomes tailored to {pref['preference_name']}."
                    ],
                )
            )

        return LLMResumeAnalysisPayload(
            candidate_profile=CandidateProfileSummary(
                full_name="Abhijeet Sharma",
                headline="Full-Stack & Data Engineer",
                location="Bangalore, India",
                years_of_experience="2 years",
                contact_channels_present=["Email", "GitHub"],
                summary_evaluation="Concise summary; can be strengthened with domain impact metrics.",
            ),
            education=[
                EducationItem(
                    degree="B.Tech in Computer Science",
                    institution="NIT Karnataka",
                    graduation_year="2024",
                    details="Computer Science curriculum",
                )
            ],
            technical_skills=["Python", "SQL", "FastAPI", "PostgreSQL", "React", "TypeScript"],
            soft_skills=["Problem Solving", "Cross-functional Collaboration"],
            work_experience=[
                ExperienceItem(
                    role="Software & Data Engineer",
                    company="Acme Analytics",
                    duration="2024 – Present",
                    key_contributions=[
                        "Built FastAPI microservices and SQL reporting pipelines.",
                        "Created interactive React dashboards for product metrics.",
                    ],
                )
            ],
            internships=[
                ExperienceItem(
                    role="Data Analyst Intern",
                    company="InsightCorp",
                    duration="Summer 2023",
                    key_contributions=["Automated weekly SQL & Python ETL reports."],
                )
            ],
            projects=[
                ProjectItem(
                    title="JobHunter Platform",
                    technologies=["Python", "FastAPI", "PostgreSQL", "React", "TypeScript"],
                    summary="Designed multi-preference job tracking and resume management system.",
                    impact="Streamlined preference-based resume organisation.",
                )
            ],
            certifications=["AWS Certified Cloud Practitioner"],
            achievements=["Winner, National Hackathon 2023"],
            tools_and_technologies=["Git", "PostgreSQL", "FastAPI", "React", "AWS"],
            preference_analyses=pref_items,
            overall_quality_score=82,
            preference_relevance_score=84,
            skills_alignment_score=86,
            experience_alignment_score=80,
            project_relevance_score=88,
            ats_readability_score=85,
            score_explanations=ResumeScoreExplanations(
                overall_quality="Well-structured sections covering experience, internships, projects, and education.",
                preference_relevance="Directly aligns with both Data Analytics and Software Development roles.",
                skills_alignment="Core technical stack (Python, SQL, FastAPI, React) matches target requirements.",
                experience_alignment="2 years of full-time and internship experience aligns with entry/mid roles.",
                project_relevance="JobHunter project demonstrates end-to-end production architecture.",
                ats_readability="Clean single-column text hierarchy with standard section headings.",
            ),
            overall_strengths=[
                "Strong combination of backend (Python/FastAPI/SQL) and frontend (React/TypeScript) skills.",
                "Includes full-time experience, internship, project, certification, and hackathon achievement.",
            ],
            overall_weaknesses=[
                "Experience bullet points lack specific scale or time-saved percentages.",
            ],
            missing_information_questions=[
                "What was the approximate dataset size or query volume handled in the Acme Analytics SQL pipelines?",
                "How many hours per week did the InsightCorp ETL automation save the team?",
            ],
            suggestions=[
                SuggestionPayloadItem(
                    section_name="Professional Summary",
                    current_content="Full-Stack & Data Engineer with 2 years of experience building Python, SQL, FastAPI, and React applications.",
                    suggested_improvement="Results-driven Full-Stack & Data Engineer with 2 years of experience designing scalable FastAPI microservices, automated SQL data pipelines, and responsive React analytics dashboards.",
                    reason="Uses stronger positioning and highlights core deliverables clearly.",
                    priority="High",
                ),
                SuggestionPayloadItem(
                    section_name="Experience Descriptions",
                    current_content="Built FastAPI microservices and SQL reporting pipelines.",
                    suggested_improvement="Engineered modular FastAPI microservices and automated SQL reporting pipelines supporting product analytics.",
                    reason="Replaces generic verbs with stronger action verbs while preserving factual accuracy.",
                    priority="High",
                    clarifying_question="Can you share the number of internal users or reports served by these pipelines?",
                ),
                SuggestionPayloadItem(
                    section_name="Project Descriptions",
                    current_content="Designed multi-preference job tracking and resume management system.",
                    suggested_improvement="Architected a full-stack job tracking and resume management platform using FastAPI, PostgreSQL, and React with preference-based workflow orchestration.",
                    reason="Clarifies technical architecture and scope without inventing facts.",
                    priority="Medium",
                ),
                SuggestionPayloadItem(
                    section_name="Skills Section",
                    current_content="Python, SQL, FastAPI, React",
                    suggested_improvement="Languages & Databases: Python, SQL, TypeScript, PostgreSQL | Frameworks & Cloud: FastAPI, React, AWS",
                    reason="Grouping skills by category improves ATS and recruiter scan speed.",
                    priority="Medium",
                ),
                SuggestionPayloadItem(
                    section_name="Education Section",
                    current_content="B.Tech in Computer Science — NIT Karnataka (2024)",
                    suggested_improvement="B.Tech in Computer Science — NIT Karnataka (Graduated 2024)",
                    reason="Clear graduation label for standard ATS date parsers.",
                    priority="Low",
                ),
                SuggestionPayloadItem(
                    section_name="Keywords",
                    current_content="FastAPI, SQL, React",
                    suggested_improvement="Include 'REST APIs', 'Data Modeling', and 'Relational Databases' where supported by your FastAPI and PostgreSQL work.",
                    reason="Aligns terminology with common job descriptions.",
                    priority="Medium",
                ),
                SuggestionPayloadItem(
                    section_name="Formatting and Readability",
                    current_content="Standard layout",
                    suggested_improvement="Keep consistent bullet punctuation and group technical skills into labeled sub-categories.",
                    reason="Enhances visual hierarchy for quick recruiter review.",
                    priority="Low",
                ),
            ],
        )

    def enhance_resume(
        self,
        resume_text: str,
        sections: Optional[List[str]],
        preferences_context: List[Dict[str, Any]],
        accepted_suggestions: List[Dict[str, Any]],
    ) -> LLMResumeEnhancementPayload:
        return LLMResumeEnhancementPayload(
            title="AI-Enhanced Resume Draft",
            improved_full_content=(
                "Abhijeet Sharma\n"
                "Bangalore, India | abhijeet@example.com | github.com/abhijeet\n\n"
                "PROFESSIONAL SUMMARY\n"
                "Results-driven Full-Stack & Data Engineer with 2 years of experience designing "
                "scalable FastAPI microservices, automated SQL data pipelines, and responsive React dashboards.\n\n"
                "EXPERIENCE\n"
                "Software & Data Engineer — Acme Analytics (2024 – Present)\n"
                "- Engineered modular FastAPI microservices and automated SQL reporting pipelines.\n"
                "- Developed interactive React dashboards for product metrics tracking.\n"
            ),
            section_changes=[
                SectionComparisonItem(
                    section_name="Professional Summary",
                    original_content="Full-Stack & Data Engineer with 2 years of experience building Python, SQL, FastAPI, and React applications.",
                    suggested_content="Results-driven Full-Stack & Data Engineer with 2 years of experience designing scalable FastAPI microservices, automated SQL data pipelines, and responsive React dashboards.",
                    reason="Improved clarity and professional phrasing while preserving all facts.",
                    status="Accepted",
                ),
                SectionComparisonItem(
                    section_name="Experience Descriptions",
                    original_content="Built FastAPI microservices and SQL reporting pipelines.",
                    suggested_content="Engineered modular FastAPI microservices and automated SQL reporting pipelines.",
                    reason="Stronger action verbs without fabricating numbers.",
                    status="Pending",
                ),
            ],
        )

    def regenerate_suggestion(
        self,
        resume_text: str,
        section_name: str,
        current_content: Optional[str],
        previous_suggestion: str,
        user_instruction: Optional[str],
        preferences_context: List[Dict[str, Any]],
    ) -> LLMRegenerateSuggestionPayload:
        return LLMRegenerateSuggestionPayload(
            section_name=section_name,
            current_content=current_content,
            suggested_improvement=(
                f"[Regenerated] {previous_suggestion} "
                f"({user_instruction or 'Refined for clarity and factual precision'})"
            ),
            reason="Regenerated phrasing per user request while keeping factual accuracy.",
            priority="High",
            clarifying_question=None,
        )


def test_missing_api_key_handling_and_ai_status() -> None:
    """Verify missing API key returns clear setup instructions and never substitutes mock data."""
    app.dependency_overrides[get_ai_provider_client] = lambda: AIProviderClient(
        provider="openai", api_key=""
    )
    pdf_bytes = _create_pdf_resume_bytes()
    upload_res = client.post(
        "/api/v1/resumes",
        files={"file": ("NoKey_Resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_res.status_code == 201
    resume_id = upload_res.json()["id"]

    try:
        status_res = client.get("/api/v1/resumes/ai-status")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["configured"] is False
        assert "AI_API_KEY" in (status_data["setup_message"] or "")

        # Attempting analysis without an API key must return 503 with setup instructions
        analyse_res = client.post(f"/api/v1/resumes/{resume_id}/analyse")
        assert analyse_res.status_code == 503
        assert "AI_API_KEY" in analyse_res.json()["message"]

        # Verify resume status remains 'Not Analysed' and no fake analysis was stored
        get_res = client.get(f"/api/v1/resumes/{resume_id}")
        assert get_res.json()["ai_status"] == "Not Analysed"
        assert client.get(f"/api/v1/resumes/{resume_id}/analysis").status_code == 404
    finally:
        app.dependency_overrides.pop(get_ai_provider_client, None)
        client.delete(f"/api/v1/resumes/{resume_id}")


def test_full_phase3b_ai_resume_intelligence_workflow() -> None:
    """Test analysis, preference evaluation, suggestions, draft enhancement, versioning, and approval."""
    app.dependency_overrides[get_ai_provider_client] = FakeConfiguredAIClient

    # 1. Create P1 (Data Analytics) and P2 (Software Development) preferences
    p1_res = client.post(
        "/api/v1/preferences",
        json={
            "preference_name": "P1 — Data Analytics",
            "job_roles": ["Data Analyst", "Business Analyst"],
            "locations": ["Bangalore"],
            "work_mode": "Hybrid",
            "employment_type": "Full-time",
            "experience_level": "Entry-level",
            "skills": ["Python", "SQL", "Power BI"],
            "minimum_match_score": 75,
            "is_active": True,
        },
    )
    p2_res = client.post(
        "/api/v1/preferences",
        json={
            "preference_name": "P2 — Software Development",
            "job_roles": ["Full Stack Developer", "Backend Developer"],
            "locations": ["Bangalore", "Remote (India)"],
            "work_mode": "Remote",
            "employment_type": "Full-time",
            "experience_level": "Experienced",
            "skills": ["Python", "FastAPI", "React", "Docker"],
            "minimum_match_score": 80,
            "is_active": True,
        },
    )
    assert p1_res.status_code == 201
    assert p2_res.status_code == 201
    p1_id = p1_res.json()["id"]
    p2_id = p2_res.json()["id"]

    # Verify neither preference is eligible for automated applications before resume approval
    assert p1_res.json()["has_approved_resume"] is False
    assert p1_res.json()["eligible_for_applications"] is False

    resume_id = None
    try:
        # 2. Upload resume linked to P1 and P2
        pdf_bytes = _create_pdf_resume_bytes()
        up_res = client.post(
            "/api/v1/resumes",
            files={"file": ("Abhijeet_Master_Resume.pdf", pdf_bytes, "application/pdf")},
            data={
                "resume_name": "Abhijeet Master Resume",
                "preference_ids": f'["{p1_id}", "{p2_id}"]',
            },
        )
        assert up_res.status_code == 201
        resume_data = up_res.json()
        resume_id = resume_data["id"]
        assert resume_data["ai_status"] == "Not Analysed"

        # Verify v1 (Original Uploaded) version was created automatically
        v_list_initial = client.get(f"/api/v1/resumes/{resume_id}/versions")
        assert v_list_initial.status_code == 200
        versions_initial = v_list_initial.json()
        assert len(versions_initial) == 1
        v1_id = versions_initial[0]["id"]
        assert versions_initial[0]["version_number"] == 1
        assert versions_initial[0]["version_type"] == "Original Uploaded"

        # Verify v1 cannot be overwritten
        patch_v1 = client.patch(
            f"/api/v1/resumes/{resume_id}/versions/{v1_id}",
            json={"content": "Attempt to overwrite original"},
        )
        assert patch_v1.status_code == 400

        # 3. Run AI Resume Analysis (POST /api/v1/resumes/{id}/analyse)
        analyse_res = client.post(f"/api/v1/resumes/{resume_id}/analyse")
        assert analyse_res.status_code == 200, analyse_res.text
        analysis = analyse_res.json()
        assert analysis["candidate_profile"]["full_name"] == "Abhijeet Sharma"
        assert "Python" in analysis["technical_skills"]
        assert len(analysis["preference_analyses"]) == 2
        assert analysis["overall_quality_score"] == 82
        assert analysis["ats_readability_score"] == 85
        assert "overall_quality" in analysis["score_explanations"]
        assert "estimates" in analysis["score_disclaimer"]
        assert len(analysis["missing_information_questions"]) == 2
        assert len(analysis["suggestions"]) == 7

        # Verify resume ai_status is now 'Analysis Complete'
        after_analyse = client.get(f"/api/v1/resumes/{resume_id}").json()
        assert after_analyse["ai_status"] == "Analysis Complete"
        assert after_analyse["overall_quality_score"] == 82

        # 4. Accept, Reject, Edit, and Regenerate Suggestions
        suggestions = client.get(f"/api/v1/resumes/{resume_id}/suggestions").json()
        assert len(suggestions) == 7
        first_sug_id = suggestions[0]["id"]
        second_sug_id = suggestions[1]["id"]
        third_sug_id = suggestions[2]["id"]

        # Accept + edit first suggestion
        accept_res = client.patch(
            f"/api/v1/resumes/{resume_id}/suggestions/{first_sug_id}",
            json={
                "status": "Accepted",
                "user_edited_content": "Custom user-refined professional summary preserving all facts.",
            },
        )
        assert accept_res.status_code == 200
        assert accept_res.json()["status"] == "Accepted"
        assert (
            accept_res.json()["effective_content"]
            == "Custom user-refined professional summary preserving all facts."
        )

        # Reject second suggestion
        reject_res = client.patch(
            f"/api/v1/resumes/{resume_id}/suggestions/{second_sug_id}",
            json={"status": "Rejected"},
        )
        assert reject_res.status_code == 200
        assert reject_res.json()["status"] == "Rejected"

        # Regenerate third suggestion
        regen_res = client.post(
            f"/api/v1/resumes/{resume_id}/suggestions/{third_sug_id}/regenerate",
            json={"user_instruction": "Emphasize PostgreSQL schema design"},
        )
        assert regen_res.status_code == 200
        assert "[Regenerated]" in regen_res.json()["suggested_improvement"]

        # 5. Improve My Resume — Generate AI Draft (POST /api/v1/resumes/{id}/enhance)
        enhance_res = client.post(
            f"/api/v1/resumes/{resume_id}/enhance",
            json={"apply_accepted_suggestions": True},
        )
        assert enhance_res.status_code == 201, enhance_res.text
        v2_draft = enhance_res.json()
        assert v2_draft["version_number"] == 2
        assert v2_draft["version_type"] == "AI-Generated Draft"
        assert v2_draft["approval_status"] == "Awaiting Approval"
        assert len(v2_draft["section_changes"]) == 2

        # 6. Create User-Edited Version (POST /api/v1/resumes/{id}/versions)
        user_v_res = client.post(
            f"/api/v1/resumes/{resume_id}/versions",
            json={
                "title": "v3 — User-Edited Final Resume",
                "content": v2_draft["content"] + "\nSKILLS\nPython, SQL, FastAPI, React, PostgreSQL",
                "section_changes": v2_draft["section_changes"],
            },
        )
        assert user_v_res.status_code == 201
        v3_user = user_v_res.json()
        assert v3_user["version_number"] == 3
        assert v3_user["version_type"] == "User-Edited Version"
        assert v3_user["approval_status"] == "Awaiting Approval"

        # Verify all 3 versions exist and v1 is untouched
        all_versions = client.get(f"/api/v1/resumes/{resume_id}/versions").json()
        assert len(all_versions) == 3
        assert all_versions[0]["version_type"] == "Original Uploaded"

        # 7. Approve Final Resume Version (POST /api/v1/resumes/{id}/versions/{v3}/approve)
        approve_res = client.post(
            f"/api/v1/resumes/{resume_id}/versions/{v3_user['id']}/approve",
            json={"preference_ids": [p1_id, p2_id]},
        )
        assert approve_res.status_code == 200, approve_res.text
        approved_payload = approve_res.json()
        assert approved_payload["ai_status"] == "Approved"
        assert approved_payload["approved_version"]["approval_status"] == "Approved"
        assert set(approved_payload["linked_preference_ids"]) == {p1_id, p2_id}

        # Verify preferences P1 and P2 now have approved_resume_version_id and eligible_for_applications == True
        p1_after = client.get(f"/api/v1/preferences/{p1_id}").json()
        p2_after = client.get(f"/api/v1/preferences/{p2_id}").json()
        assert p1_after["has_approved_resume"] is True
        assert p1_after["eligible_for_applications"] is True
        assert p1_after["approved_resume_version_id"] == v3_user["id"]
        assert p2_after["has_approved_resume"] is True
        assert p2_after["eligible_for_applications"] is True

        # Verify orchestration readiness reflects approved resume eligibility
        orch_data = client.get("/api/v1/orchestration/readiness").json()
        orch_by_id = {item["preference_id"]: item for item in orch_data["preferences"]}
        assert orch_by_id[p1_id]["has_approved_resume"] is True
        assert orch_by_id[p1_id]["eligible_for_applications"] is True

    finally:
        app.dependency_overrides.pop(get_ai_provider_client, None)
        if resume_id:
            client.delete(f"/api/v1/resumes/{resume_id}")
        client.delete(f"/api/v1/preferences/{p1_id}")
        client.delete(f"/api/v1/preferences/{p2_id}")


class MalformedAIClient(AIProviderClient):
    """Test double that simulates invalid non-JSON output from an upstream LLM."""

    def __init__(self) -> None:
        super().__init__(provider="openai", api_key="test-key", model="gpt-4o-mini")

    def _call_provider(self, system_prompt: str, user_prompt: str) -> str:
        return "THIS IS NOT VALID JSON AT ALL"


def test_duplicate_analysis_and_malformed_llm_validation() -> None:
    """Verify malformed LLM responses fail cleanly with 502 and reset status from Analysing."""
    app.dependency_overrides[get_ai_provider_client] = MalformedAIClient
    pdf_bytes = _create_pdf_resume_bytes()
    up_res = client.post(
        "/api/v1/resumes",
        files={"file": ("Validation_Test.pdf", pdf_bytes, "application/pdf")},
    )
    assert up_res.status_code == 201
    resume_id = up_res.json()["id"]

    try:
        bad_res = client.post(f"/api/v1/resumes/{resume_id}/analyse")
        assert bad_res.status_code == 502

        # Verify status was restored to 'Not Analysed' (not stuck in 'Analysing')
        after_fail = client.get(f"/api/v1/resumes/{resume_id}").json()
        assert after_fail["ai_status"] == "Not Analysed"
    finally:
        app.dependency_overrides.pop(get_ai_provider_client, None)
        client.delete(f"/api/v1/resumes/{resume_id}")

