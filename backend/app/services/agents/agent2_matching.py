"""Agent 2: Job Matching (Part 4).

Responsibilities:
- Compare each DiscoveredJob against the active JobPreference AND its approved ResumeVersion.
- Evaluate role alignment, location/work-mode fit, employment type, experience level, salary range, and resume-derived skills/experience.
- Generate a 0–100 match score, matched skills, relevant experience, unverified/missing keywords (never treated as proof of lacking a skill), matching reasons, rejection reasons, and shortlisting decision.
- Store results separately per preference (`job_matches` table) to prevent cross-preference contamination.
- Only shortlist eligible jobs (`match_score >= threshold`) for Agent 3.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_preference import JobPreference
from app.models.multi_agent import DiscoveredJob, JobMatch
from app.models.orchestration import PreferenceJobResult
from app.models.resume_intelligence import ResumeAnalysis, ResumeVersion
from app.services.ai_provider import AIProviderClient
from app.services.experience_matcher import evaluate_experience_eligibility
from app.services.location_matcher import evaluate_location_eligibility
from app.services.role_synonyms import expand_job_roles

logger = logging.getLogger("jobhunter.agent2_matching")


class LLMJobMatchOutput(BaseModel):
    """Structured Pydantic model for AI-powered job matching evaluation."""

    match_score: int = Field(default=0, ge=0, le=100)
    skills_matched: List[str] = Field(default_factory=list)
    relevant_experience: List[str] = Field(default_factory=list)
    missing_or_unverified_requirements: List[str] = Field(default_factory=list)
    reasons_for_matching: List[str] = Field(default_factory=list)
    reasons_for_rejection: List[str] = Field(default_factory=list)
    shortlisted: bool = False

    @field_validator("match_score", mode="before")
    @classmethod
    def clamp_score(cls, v: int) -> int:
        return max(0, min(100, int(v)))


class JobMatchingAgent:
    """Agent 2: Evaluates discovered jobs against an independent JobPreference and its approved resume."""

    def __init__(self, ai_client: Optional[AIProviderClient] = None) -> None:
        self.ai_client = ai_client

    def evaluate_jobs_for_preference(
        self,
        db: Session,
        preference: JobPreference,
        discovered_jobs: List[DiscoveredJob],
        preference_run_id: Optional[UUID] = None,
        override_threshold: Optional[int] = None,
        allow_ai_calls: bool = True,
    ) -> tuple[List[JobMatch], float]:
        """Evaluate each discovered job for `preference`, persist `JobMatch`, and return `(matches, api_cost_usd)`."""
        threshold = (
            override_threshold
            if override_threshold is not None
            else preference.minimum_match_score
        )

        resume_version: Optional[ResumeVersion] = None
        resume_analysis: Optional[ResumeAnalysis] = None
        if preference.approved_resume_version_id:
            resume_version = db.get(ResumeVersion, preference.approved_resume_version_id)
        if preference.approved_resume_id:
            resume_analysis = db.scalars(
                select(ResumeAnalysis)
                .where(ResumeAnalysis.resume_id == preference.approved_resume_id)
                .order_by(ResumeAnalysis.created_at.desc())
                .limit(1)
            ).first()

        results: List[JobMatch] = []
        total_api_cost = 0.0

        for job in discovered_jobs:
            existing_match = db.scalars(
                select(JobMatch)
                .where(
                    JobMatch.preference_id == preference.id,
                    JobMatch.discovered_job_id == job.id,
                )
                .limit(1)
            ).first()

            evaluation, method_used, cost = self._evaluate_single_job(
                preference=preference,
                job=job,
                resume_version=resume_version,
                resume_analysis=resume_analysis,
                threshold=threshold,
                allow_ai_calls=allow_ai_calls,
            )
            total_api_cost += cost

            has_location_ineligibility = any(
                "Location Ineligible" in r for r in evaluation.reasons_for_rejection
            )
            has_experience_ineligibility = any(
                "Experience Ineligible" in r for r in evaluation.reasons_for_rejection
            )
            is_ineligible = has_location_ineligibility or has_experience_ineligibility

            is_matching = (
                evaluation.match_score >= max(50, threshold - 15)
                and not is_ineligible
            )
            is_shortlisted = bool(
                evaluation.match_score >= threshold
                and evaluation.shortlisted
                and not is_ineligible
            )

            if existing_match is not None:
                existing_match.preference_run_id = preference_run_id
                existing_match.resume_version_id = (
                    resume_version.id if resume_version else None
                )
                existing_match.match_score = evaluation.match_score
                existing_match.threshold_used = threshold
                existing_match.is_matching = is_matching
                existing_match.shortlisted = is_shortlisted
                existing_match.skills_matched = evaluation.skills_matched
                existing_match.relevant_experience = evaluation.relevant_experience
                existing_match.missing_or_unverified_requirements = (
                    evaluation.missing_or_unverified_requirements
                )
                existing_match.reasons_for_matching = evaluation.reasons_for_matching
                existing_match.reasons_for_rejection = evaluation.reasons_for_rejection
                existing_match.evaluation_method = method_used
                match_row = existing_match
            else:
                match_row = JobMatch(
                    preference_id=preference.id,
                    preference_run_id=preference_run_id,
                    discovered_job_id=job.id,
                    resume_version_id=resume_version.id if resume_version else None,
                    match_score=evaluation.match_score,
                    threshold_used=threshold,
                    is_matching=is_matching,
                    shortlisted=is_shortlisted,
                    skills_matched=evaluation.skills_matched,
                    relevant_experience=evaluation.relevant_experience,
                    missing_or_unverified_requirements=(
                        evaluation.missing_or_unverified_requirements
                    ),
                    reasons_for_matching=evaluation.reasons_for_matching,
                    reasons_for_rejection=evaluation.reasons_for_rejection,
                    evaluation_method=method_used,
                )
                db.add(match_row)
                db.flush()

            # Sync with PreferenceJobResult for Phase 2B compatibility
            existing_legacy = db.scalars(
                select(PreferenceJobResult)
                .where(
                    PreferenceJobResult.preference_id == preference.id,
                    PreferenceJobResult.job_url == job.official_job_url,
                )
                .limit(1)
            ).first()
            if existing_legacy is None:
                db.add(
                    PreferenceJobResult(
                        preference_id=preference.id,
                        execution_id=preference_run_id,
                        title=job.title[:200],
                        company=job.company[:150],
                        location=(job.location or "Not Specified")[:150],
                        work_mode=job.work_mode,
                        job_url=job.official_job_url[:500],
                        match_score=evaluation.match_score,
                        is_matching=is_matching,
                        is_shortlisted=is_shortlisted,
                    )
                )
            else:
                existing_legacy.execution_id = preference_run_id
                existing_legacy.match_score = evaluation.match_score
                existing_legacy.is_matching = is_matching
                existing_legacy.is_shortlisted = is_shortlisted

            results.append(match_row)

        db.commit()
        return results, total_api_cost

    def _evaluate_single_job(
        self,
        preference: JobPreference,
        job: DiscoveredJob,
        resume_version: Optional[ResumeVersion],
        resume_analysis: Optional[ResumeAnalysis],
        threshold: int,
        allow_ai_calls: bool,
    ) -> tuple[LLMJobMatchOutput, str, float]:
        """Use AI provider if configured and permitted; otherwise use deterministic rule scoring."""
        if (
            allow_ai_calls
            and self.ai_client is not None
            and self.ai_client.is_configured
        ):
            try:
                ai_out = self._evaluate_with_ai(
                    preference=preference,
                    job=job,
                    resume_version=resume_version,
                    resume_analysis=resume_analysis,
                    threshold=threshold,
                )
                return ai_out, "ai", 0.002
            except Exception as exc:
                logger.warning(
                    "AI matching fallback to deterministic rule (%s)",
                    type(exc).__name__,
                )

        rule_out = self._evaluate_deterministic(
            preference=preference,
            job=job,
            resume_version=resume_version,
            resume_analysis=resume_analysis,
            threshold=threshold,
        )
        return rule_out, "deterministic_rule", 0.0

    def _evaluate_with_ai(
        self,
        preference: JobPreference,
        job: DiscoveredJob,
        resume_version: Optional[ResumeVersion],
        resume_analysis: Optional[ResumeAnalysis],
        threshold: int,
    ) -> LLMJobMatchOutput:
        assert self.ai_client is not None
        system_prompt = (
            "You are Agent 2 (Job Matching Agent) in Project JobHunter.\n"
            "STRICT RULES:\n"
            "1. Compare the discovered job against the active Job Preference and the approved Resume.\n"
            "2. Never fabricate candidate qualifications.\n"
            "3. Location compliance is mandatory: Candidate is based in India. If the job is on-site "
            "or hybrid in an international location (e.g. Germany, USA, UK) or restricted to non-India residents, "
            "it is INELIGIBLE. Set match_score <= 25, shortlisted = false, and include 'Location Ineligible' in reasons_for_rejection.\n"
            f"4. Experience compliance is mandatory: Candidate experience level is '{preference.experience_level or 'Entry-level'}'. "
            "If the role requires lead, principal, senior, or significantly higher years of experience than candidate's level, "
            "it is INELIGIBLE. Set match_score <= 25, shortlisted = false, and include 'Experience Ineligible' in reasons_for_rejection.\n"
            "5. Never treat a missing keyword as proof that the candidate lacks a skill; list it in "
            "`missing_or_unverified_requirements` as an unverified requirement.\n"
            "6. Set `shortlisted` to true ONLY if `match_score` >= the configured threshold AND both location and experience are eligible.\n"
            "7. Return valid JSON matching the schema."
        )
        user_prompt = json.dumps(
            {
                "threshold": threshold,
                "preference": {
                    "name": preference.preference_name,
                    "target_roles": preference.job_roles,
                    "locations": preference.locations,
                    "location_mode": getattr(preference, "location_mode", "INDIA_ONLY") or "INDIA_ONLY",
                    "work_mode": preference.work_mode,
                    "employment_type": preference.employment_type,
                    "experience_level": preference.experience_level,
                    "min_salary": preference.min_salary,
                    "max_salary": preference.max_salary,
                    "skills": preference.skills,
                },
                "approved_resume_excerpt": (
                    (resume_version.content[:4000] if resume_version else "")
                ),
                "resume_extracted_skills": (
                    resume_analysis.technical_skills if resume_analysis else []
                ),
                "discovered_job": {
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "work_mode": job.work_mode,
                    "employment_type": job.employment_type,
                    "min_salary": job.min_salary,
                    "max_salary": job.max_salary,
                    "description": job.description[:4000],
                },
            },
            ensure_ascii=False,
        )
        result = self.ai_client.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema_cls=LLMJobMatchOutput,
            operation_label="agent2_job_matching",
        )
        loc_elig = evaluate_location_eligibility(
            job_location=job.location,
            job_work_mode=job.work_mode,
            preference_locations=preference.locations or [],
            location_mode=getattr(preference, "location_mode", "INDIA_ONLY") or "INDIA_ONLY",
            preference_work_mode=preference.work_mode,
            job_description=job.description,
            raw_metadata=job.raw_metadata,
        )
        exp_elig = evaluate_experience_eligibility(
            job_title=job.title,
            job_description=job.description,
            preference_experience_level=preference.experience_level or "Entry-level",
        )
        if not loc_elig.is_eligible:
            result.shortlisted = False
            result.match_score = min(result.match_score, 25)
            result.reasons_for_rejection.insert(
                0, f"Location Ineligible: {loc_elig.reason}"
            )
        if not exp_elig.is_eligible:
            result.shortlisted = False
            result.match_score = min(result.match_score, 25)
            result.reasons_for_rejection.insert(
                0, f"Experience Ineligible: {exp_elig.reason}"
            )
        if loc_elig.is_eligible and exp_elig.is_eligible:
            result.shortlisted = bool(result.match_score >= threshold)
        return result

    def _evaluate_deterministic(
        self,
        preference: JobPreference,
        job: DiscoveredJob,
        resume_version: Optional[ResumeVersion],
        resume_analysis: Optional[ResumeAnalysis],
        threshold: int,
    ) -> LLMJobMatchOutput:
        """Transparent, fact-based scoring comparing job fields against preference and approved resume."""
        job_title_lower = (job.title or "").lower()
        job_desc_lower = f"{job.title or ''} {job.description or ''}".lower()
        resume_text_lower = (resume_version.content if resume_version else "").lower()

        candidate_skills: List[str] = list(preference.skills or [])
        if resume_analysis and resume_analysis.technical_skills:
            for sk in resume_analysis.technical_skills:
                if sk not in candidate_skills:
                    candidate_skills.append(sk)

        reasons_for_matching: List[str] = []
        reasons_for_rejection: List[str] = []
        relevant_experience: List[str] = []

        # 1. Role alignment (up to 35 points)
        role_score = 0
        expanded_target_roles = expand_job_roles(preference.job_roles or [])
        matched_roles = [
            role
            for role in expanded_target_roles
            if role.lower() in job_title_lower
            or any(
                token in job_title_lower
                for token in role.lower().split()
                if len(token) > 3
            )
        ]
        if matched_roles:
            role_score = 35
            reasons_for_matching.append(
                f"Job title aligns with target role(s): {', '.join(matched_roles[:2])}."
            )
        elif any(role.lower() in job_desc_lower for role in expanded_target_roles):
            role_score = 22
            reasons_for_matching.append(
                "Target role responsibilities appear in the job description."
            )
        else:
            role_score = 8
            reasons_for_rejection.append(
                f"Job title '{job.title}' does not directly match target roles ({', '.join(preference.job_roles[:3])})."
            )

        # 2. Skills alignment (up to 40 points)
        skills_matched: List[str] = []
        missing_or_unverified: List[str] = []

        for skill in preference.skills or []:
            sk_lower = skill.lower()
            in_job = sk_lower in job_desc_lower
            in_resume = (not resume_text_lower) or (sk_lower in resume_text_lower)
            if in_job and in_resume:
                skills_matched.append(skill)
            elif in_job and not in_resume:
                missing_or_unverified.append(
                    f"{skill} (mentioned in job; unverified in approved resume text — not proof of lacking skill)"
                )

        # Also check any additional resume skills present in the job description
        for sk in candidate_skills:
            if sk not in skills_matched and sk.lower() in job_desc_lower:
                skills_matched.append(sk)

        total_pref_skills = max(1, len(preference.skills or []))
        skill_ratio = min(1.0, len(skills_matched) / total_pref_skills)
        skill_score = int(round(skill_ratio * 40))

        if skills_matched:
            reasons_for_matching.append(
                f"Matched {len(skills_matched)} relevant skill(s): {', '.join(skills_matched[:5])}."
            )
        else:
            reasons_for_rejection.append(
                "No direct overlap found between job description and preference skills."
            )

        # 3. Location & Work Mode alignment (Mandatory Eligibility Check)
        loc_elig = evaluate_location_eligibility(
            job_location=job.location,
            job_work_mode=job.work_mode,
            preference_locations=preference.locations or [],
            location_mode=getattr(preference, "location_mode", "INDIA_ONLY") or "INDIA_ONLY",
            preference_work_mode=preference.work_mode,
            job_description=job.description,
            raw_metadata=job.raw_metadata,
        )

        if not loc_elig.is_eligible:
            loc_score = 0
            reasons_for_rejection.append(f"Location Ineligible: {loc_elig.reason}")
        else:
            loc_score = 15
            reasons_for_matching.append(
                f"Location compatible: {loc_elig.matched_location or job.location or 'India/Remote'} ({loc_elig.reason})"
            )

        # 4. Experience alignment (Mandatory Eligibility Check)
        exp_elig = evaluate_experience_eligibility(
            job_title=job.title,
            job_description=job.description,
            preference_experience_level=preference.experience_level or "Entry-level",
        )
        if not exp_elig.is_eligible:
            reasons_for_rejection.append(f"Experience Ineligible: {exp_elig.reason}")
        else:
            reasons_for_matching.append(
                f"Experience compatible: {preference.experience_level or 'Entry-level'} (Detected: {exp_elig.detected_tier})"
            )

        # 5. Salary & Resume Verification (up to 10 points)
        qual_score = 5
        if resume_version is not None:
            qual_score = 10
            relevant_experience.append(
                f"Evaluated against approved resume version '{resume_version.title}'."
            )
        else:
            missing_or_unverified.append(
                "No approved resume version linked to this preference yet."
            )

        if (
            preference.min_salary is not None
            and job.max_salary is not None
            and job.max_salary < preference.min_salary
        ):
            qual_score = max(0, qual_score - 8)
            reasons_for_rejection.append(
                f"Offered maximum salary ({job.max_salary}) is below minimum preference ({preference.min_salary})."
            )

        raw_score = role_score + skill_score + loc_score + qual_score
        if not loc_elig.is_eligible or not exp_elig.is_eligible:
            # Enforce Mandatory Eligibility: Ineligible location or experience caps score at 25 and strictly prevents shortlisting.
            total_score = min(raw_score, 25)
            shortlisted = False
        else:
            total_score = max(0, min(100, raw_score))
            shortlisted = bool(total_score >= threshold)

        if not shortlisted and not reasons_for_rejection:
            reasons_for_rejection.append(
                f"Calculated match score ({total_score}/100) is below the configured threshold ({threshold}/100)."
            )

        return LLMJobMatchOutput(
            match_score=total_score,
            skills_matched=skills_matched,
            relevant_experience=relevant_experience,
            missing_or_unverified_requirements=missing_or_unverified,
            reasons_for_matching=reasons_for_matching,
            reasons_for_rejection=reasons_for_rejection,
            shortlisted=shortlisted,
        )

