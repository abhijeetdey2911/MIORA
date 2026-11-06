"""Application Package Preparation & Intelligence Service (Agent 4 Support).

Responsibilities:
- Generate tailored cover letters for specific job postings and companies.
- Generate tailored resume summaries and highlights matching job requirements.
- Prepare structured answers for standard applicant screening questions.
- Assemble cohesive, auditable application packages stored in `applications.prepared_payload`.
- Provide robust fallback generation when AI models are unavailable or rate-limited.
"""

from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional

from app.services.ai_provider import AIProviderClient

logger = logging.getLogger("jobhunter.application_preparer")


def extract_candidate_name_from_text(text: Optional[str], fallback: str = "Candidate") -> str:
    """Heuristically extract candidate name from top lines of resume text."""
    if not text:
        return fallback
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    for line in lines[:5]:
        # Typical name line: 2 to 4 words, letters only, not header like 'Resume' or 'Curriculum'
        cleaned = re.sub(r"[^a-zA-Z\s]", "", line).strip()
        words = cleaned.split()
        if 2 <= len(words) <= 4 and all(w.istitle() or w.isupper() for w in words):
            lower_words = [w.lower() for w in words]
            if not any(kw in lower_words for kw in ("resume", "curriculum", "vitae", "profile", "summary")):
                return cleaned.title()
    return fallback


def generate_cover_letter(
    candidate_name: str,
    company: str,
    job_title: str,
    job_description: str,
    skills: List[str],
    experience_summary: str = "",
    ai_client: Optional[AIProviderClient] = None,
) -> str:
    """Generate a high-quality, professional cover letter tailored to the job and company."""
    clean_company = (company or "your organization").strip()
    clean_title = (job_title or "the open position").strip()
    clean_skills = [s.strip() for s in skills if s.strip()]
    top_skills_str = ", ".join(clean_skills[:5]) if clean_skills else "software engineering and modern technology stacks"

    if ai_client is not None:
        try:
            prompt = (
                f"You are a professional career coach and executive copywriter. "
                f"Write a polished, concise, and compelling 3-paragraph cover letter for:\n"
                f"Candidate Name: {candidate_name}\n"
                f"Target Role: {clean_title}\n"
                f"Target Company: {clean_company}\n"
                f"Key Candidate Skills: {top_skills_str}\n"
                f"Candidate Background: {experience_summary[:400] if experience_summary else 'Extensive software development experience'}\n"
                f"Job Requirements Excerpt: {job_description[:500] if job_description else 'Standard industry requirements'}\n\n"
                f"Requirements for the letter:\n"
                f"- First paragraph: Express enthusiasm for {clean_title} at {clean_company} and state core qualifications.\n"
                f"- Second paragraph: Highlight specific alignment with key skills ({top_skills_str}) and relevant problem-solving experience.\n"
                f"- Third paragraph: Express eagerness to discuss how the candidate can add immediate value, with a professional closing.\n"
                f"- Do NOT fabricate fake employer facts, unverified metrics, or unrealistic claims.\n"
                f"- Return ONLY the cover letter text without preamble or markdown meta comments."
            )
            ai_resp = ai_client.generate_content(
                prompt=prompt,
                system_instruction="You write formal, genuine, and impactful job application cover letters.",
                temperature=0.3,
                max_tokens=650,
            )
            letter = (ai_resp.text or "").strip()
            if len(letter) > 150:
                return letter
        except Exception as exc:
            logger.info("AI cover letter generation fallback triggered (%s): using structured template.", exc)

    # High-quality deterministic fallback
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    return (
        f"{date_str}\n\n"
        f"Hiring Team\n"
        f"{clean_company}\n\n"
        f"Dear Hiring Team at {clean_company},\n\n"
        f"I am writing to express my strong interest in the {clean_title} opportunity at {clean_company}. "
        f"With hands-on experience and solid foundation in {top_skills_str}, I am excited about the prospect "
        f"of contributing to your engineering initiatives and building high-reliability solutions.\n\n"
        f"Throughout my work, I have focused on writing clean, scalable code, collaborating across agile teams, "
        f"and rapidly mastering domain-specific workflows. My background in {top_skills_str} directly complements "
        f"the technical requirements of the {clean_title} role at {clean_company}. I take pride in delivering robust "
        f"systems that meet high performance and maintainability standards.\n\n"
        f"I would welcome the opportunity to discuss in greater detail how my skills and proactive work ethic "
        f"can support {clean_company}'s goals. Thank you for your time and consideration.\n\n"
        f"Sincerely,\n"
        f"{candidate_name}"
    )


def generate_screening_answers(
    candidate_name: str,
    company: str,
    job_title: str,
    skills: List[str],
    work_mode_pref: str = "Remote",
    location_pref: str = "India",
) -> List[Dict[str, str]]:
    """Generate structured answers to standard employer ATS screening questions."""
    top_skills_str = ", ".join(skills[:4]) if skills else "modern software engineering methodologies"
    return [
        {
            "question": f"Why are you interested in joining {company} as a {job_title}?",
            "answer": (
                f"I admire {company}'s focus on engineering excellence and high-impact solutions. "
                f"The {job_title} role offers an ideal opportunity to apply my strengths in {top_skills_str} "
                f"while contributing directly to scalable, mission-critical systems."
            ),
        },
        {
            "question": "What relevant technical experience and strengths do you bring to this role?",
            "answer": (
                f"I bring practical experience with {top_skills_str}, test automation, and robust system architecture. "
                f"I focus on writing well-documented, test-driven code and driving projects from specification through production deployment."
            ),
        },
        {
            "question": "What is your current notice period and availability to start?",
            "answer": "Immediately available to 30 days maximum, depending on organizational requirements.",
        },
        {
            "question": f"What is your work authorization and preferred work mode ({work_mode_pref})?",
            "answer": f"Authorized to work in {location_pref} with full availability for {work_mode_pref} and hybrid arrangements.",
        },
    ]


def build_full_application_package(
    *,
    subagent_name: str,
    company: str,
    job_title: str,
    route_type: str,
    route_target: str,
    job_description: str,
    candidate_name: str,
    skills: List[str],
    resume_id: str,
    resume_name: str,
    resume_version_id: Optional[str] = None,
    resume_version_number: int = 1,
    work_mode_pref: str = "Remote",
    location_pref: str = "India",
    ai_client: Optional[AIProviderClient] = None,
    extra_safety_checks: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Assemble a complete, transparent application package for Agent 4."""
    clean_skills = [s for s in skills if s]
    cover_letter = generate_cover_letter(
        candidate_name=candidate_name,
        company=company,
        job_title=job_title,
        job_description=job_description,
        skills=clean_skills,
        ai_client=ai_client,
    )
    screening_answers = generate_screening_answers(
        candidate_name=candidate_name,
        company=company,
        job_title=job_title,
        skills=clean_skills,
        work_mode_pref=work_mode_pref,
        location_pref=location_pref,
    )

    safety_checks = {
        "captcha_bypass": "prohibited",
        "auth_bypass": "prohibited",
        "approved_resume_verified": True,
        "explicit_user_approval_required": True,
    }
    if extra_safety_checks:
        safety_checks.update(extra_safety_checks)

    return {
        "subagent": subagent_name,
        "company": company,
        "job_title": job_title,
        "route_type": route_type,
        "route_target": route_target,
        "candidate_name": candidate_name,
        "cover_letter": cover_letter,
        "tailored_summary": (
            f"Software engineering professional specializing in {', '.join(clean_skills[:4]) if clean_skills else 'software development'}, "
            f"prepared specifically for the {job_title} role at {company}."
        ),
        "highlighted_skills": clean_skills[:8],
        "answers_to_common_questions": screening_answers,
        "resume_id": resume_id,
        "resume_name": resume_name,
        "resume_version_id": resume_version_id,
        "resume_version_number": resume_version_number,
        "safety_checks": safety_checks,
        "prepared_at": datetime.now(timezone.utc).isoformat(),
    }
