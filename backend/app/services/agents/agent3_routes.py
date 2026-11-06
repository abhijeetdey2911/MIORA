"""Agent 3: Application Route Discovery (Part 5).

Responsibilities:
- Discover and verify legitimate application routes for shortlisted jobs:
  1. Official company careers portal (`official_company_portal`)
  2. Official application form (`official_application_form`)
  3. Publicly published HR application email (`published_hr_email`)
  4. Verified recruiter professional contact (`verified_recruiter_contact`)
- Prioritise official company application portals.
- Never guess email addresses or invent recruiter contacts.
- Never use private or unlawfully obtained personal information.
- Mark unverified routes as `manual_review_required` (`requires_manual_review = True`).
"""

from datetime import datetime, timezone
import re
from typing import List
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.multi_agent import ApplicationRoute, DiscoveredJob, JobMatch

OFFICIAL_ATS_DOMAINS = (
    "greenhouse.io",
    "lever.co",
    "myworkdayjobs.com",
    "workable.com",
    "ashbyhq.com",
    "smartrecruiters.com",
    "bamboohr.com",
    "remotive.com",
    "arbeitnow.com",
    "jobicy.com",
)

# Matches only explicitly published application emails in job descriptions (never guessed)
PUBLISHED_EMAIL_PATTERN = re.compile(
    r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b"
)


class ApplicationRouteDiscoveryAgent:
    """Agent 3: Discovers and verifies legitimate application routes for shortlisted jobs."""

    def discover_routes_for_shortlisted_matches(
        self,
        db: Session,
        shortlisted_matches: List[JobMatch],
    ) -> List[ApplicationRoute]:
        """Inspect each shortlisted job and persist verified/unverified ApplicationRoute rows."""
        discovered_routes: List[ApplicationRoute] = []
        now = datetime.now(timezone.utc)

        for match in shortlisted_matches:
            if not match.shortlisted:
                continue

            job: DiscoveredJob = match.discovered_job
            existing_routes = list(
                db.scalars(
                    select(ApplicationRoute).where(
                        ApplicationRoute.discovered_job_id == job.id,
                        ApplicationRoute.preference_id == match.preference_id,
                    )
                ).all()
            )
            if existing_routes:
                discovered_routes.extend(existing_routes)
                continue

            raw_meta = job.raw_metadata or {}

            # 1. Primary Official Portal / Application Form Route from official_job_url
            official_url = (job.official_job_url or "").strip()
            parsed = urlparse(official_url)
            domain = parsed.netloc.lower()

            if parsed.scheme in ("http", "https") and domain:
                is_linkedin = "linkedin.com" in domain
                is_known_portal = any(
                    ats in domain for ats in OFFICIAL_ATS_DOMAINS
                ) or bool(raw_meta.get("verified_portal"))
                route_type = (
                    "official_application_form"
                    if raw_meta.get("is_application_form")
                    else "official_company_portal"
                )
                if is_linkedin:
                    verification_status = "manual_review_required"
                    confidence = 65
                    requires_manual = True
                    notes = (
                        "LinkedIn job posting identified. Automated login bypass/scraping is prohibited; "
                        "assisted manual application workflow enabled with tailored package."
                    )
                else:
                    verification_status = (
                        "verified" if is_known_portal else "manual_review_required"
                    )
                    confidence = 92 if is_known_portal else 70
                    requires_manual = not is_known_portal
                    notes = (
                        f"Verified official portal URL on {domain}."
                        if is_known_portal
                        else f"Official job URL on {domain}; marked for manual verification before automated submission."
                    )

                primary_route = ApplicationRoute(
                    discovered_job_id=job.id,
                    preference_id=match.preference_id,
                    route_type=route_type,
                    url_or_contact=official_url[:600],
                    source=job.source_name,
                    verification_status=verification_status,
                    last_verified_at=now,
                    confidence_level=confidence,
                    requires_manual_review=requires_manual,
                    verification_notes=notes,
                )
                db.add(primary_route)
                db.flush()
                discovered_routes.append(primary_route)

            # 2. Explicitly published HR email (only if present in raw_metadata or job description)
            published_email = raw_meta.get("published_hr_email")
            if not published_email and job.description:
                email_matches = PUBLISHED_EMAIL_PATTERN.findall(job.description)
                for candidate_email in email_matches:
                    local_part = candidate_email.split("@")[0].lower()
                    if any(
                        prefix in local_part
                        for prefix in ("careers", "jobs", "hr", "talent", "recruiting", "apply")
                    ):
                        published_email = candidate_email
                        break

            if published_email and isinstance(published_email, str):
                email_route = ApplicationRoute(
                    discovered_job_id=job.id,
                    preference_id=match.preference_id,
                    route_type="published_hr_email",
                    url_or_contact=published_email.strip()[:600],
                    source=f"Published in {job.source_name} job listing",
                    verification_status="verified",
                    last_verified_at=now,
                    confidence_level=85,
                    requires_manual_review=False,
                    verification_notes="Explicitly published HR/careers application email in listing.",
                )
                db.add(email_route)
                db.flush()
                discovered_routes.append(email_route)

            # 3. Explicitly verified recruiter contact (only if provided in official source metadata)
            verified_recruiter = raw_meta.get("verified_recruiter_contact")
            if verified_recruiter and isinstance(verified_recruiter, str):
                recruiter_route = ApplicationRoute(
                    discovered_job_id=job.id,
                    preference_id=match.preference_id,
                    route_type="verified_recruiter_contact",
                    url_or_contact=verified_recruiter.strip()[:600],
                    source=f"Official listing metadata ({job.source_name})",
                    verification_status="verified",
                    last_verified_at=now,
                    confidence_level=80,
                    requires_manual_review=True,
                    verification_notes="Verified professional recruiter contact from listing; requires user review prior to outreach.",
                )
                db.add(recruiter_route)
                db.flush()
                discovered_routes.append(recruiter_route)

        db.commit()
        return discovered_routes

