"""Agent 1: Job Discovery (Part 3).

Responsibilities:
- Discover relevant jobs for a specific active JobPreference using a modular source adapter architecture.
- Search permitted job sources (official public APIs, feeds, and configured company career endpoints).
- Deduplicate jobs using canonical URLs and stable SHA-256 identifiers (`fingerprint`).
- Clearly distinguish unavailable information (`None`) from present data.
- Never invent fake jobs or fake job URLs, and never scrape sites in violation of their terms.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_preference import JobPreference
from app.models.multi_agent import DiscoveredJob, JobSource

logger = logging.getLogger("jobhunter.agent1_discovery")

TRACKING_QUERY_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "gh_src",
    "source",
}


def normalize_canonical_url(raw_url: str) -> str:
    """Normalize a job URL by stripping tracking query parameters and fragments."""
    cleaned = (raw_url or "").strip()
    if not cleaned:
        raise ValueError("Job URL cannot be empty.")
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"Invalid official job URL: {cleaned}")

    filtered_query = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=False)
        if k.lower() not in TRACKING_QUERY_PARAMS
    ]
    normalized_path = parsed.path.rstrip("/") or "/"
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            normalized_path,
            "",
            urlencode(sorted(filtered_query)),
            "",
        )
    )


def compute_job_fingerprint(
    canonical_url: str,
    company: str,
    title: str,
    external_job_id: Optional[str] = None,
) -> str:
    """Compute a deterministic SHA-256 fingerprint for job deduplication."""
    base = f"{canonical_url.lower()}|{(company or '').strip().lower()}|{(title or '').strip().lower()}|{(external_job_id or '').strip().lower()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _strip_html(raw_html: str) -> str:
    """Convert HTML job descriptions from public APIs into clean plain text."""
    if not raw_html:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", raw_html, flags=re.IGNORECASE)
    text = re.sub(r"</p>|</li>|</div>|</h[1-6]>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


@dataclass
class RawDiscoveredJobItem:
    """Structured job record returned by a source adapter before DB deduplication."""

    source_name: str
    external_job_id: Optional[str]
    title: str
    company: str
    description: str
    official_job_url: str
    location: Optional[str] = None
    work_mode: Optional[str] = None
    employment_type: Optional[str] = None
    experience_requirement: Optional[str] = None
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    salary_currency: Optional[str] = None
    salary_raw: Optional[str] = None
    posted_at: Optional[datetime] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


class BaseJobSourceAdapter(ABC):
    """Abstract base class for permitted job discovery source adapters."""

    source_name: str = "Base Source"
    adapter_type: str = "base"
    base_url: str = ""

    @abstractmethod
    def fetch_jobs(
        self,
        preference: JobPreference,
        max_results: int = 25,
    ) -> List[RawDiscoveredJobItem]:
        """Fetch relevant jobs from the permitted source for the given preference."""
        raise NotImplementedError


class RemotiveOfficialAPIAdapter(BaseJobSourceAdapter):
    """Official Remotive Public API adapter (`https://remotive.com/api/remote-jobs`)."""

    source_name = "Remotive Official API"
    adapter_type = "remotive_api"
    base_url = "https://remotive.com/api/remote-jobs"

    def fetch_jobs(
        self,
        preference: JobPreference,
        max_results: int = 25,
    ) -> List[RawDiscoveredJobItem]:
        results: List[RawDiscoveredJobItem] = []
        search_term = (preference.job_roles[0] if preference.job_roles else "").strip()
        params: Dict[str, Any] = {"limit": max(10, min(max_results * 2, 50))}
        if search_term:
            params["search"] = search_term

        try:
            with httpx.Client(timeout=12.0) as client:
                response = client.get(self.base_url, params=params)
                if response.status_code != 200:
                    return []
                payload = response.json()
        except Exception as exc:
            logger.info(
                "Remotive Official API unreachable or timed out (%s); returning 0 items.",
                type(exc).__name__,
            )
            return []

        raw_jobs = payload.get("jobs") or []
        for item in raw_jobs[:max_results]:
            url = (item.get("url") or "").strip()
            title = (item.get("title") or "").strip()
            company = (item.get("company_name") or "").strip()
            description = _strip_html(item.get("description") or "")
            if not (url and title and company and description):
                continue

            posted_at: Optional[datetime] = None
            pub_date = item.get("publication_date")
            if isinstance(pub_date, str) and pub_date.strip():
                try:
                    posted_at = datetime.fromisoformat(
                        pub_date.replace("Z", "+00:00")
                    )
                except ValueError:
                    posted_at = None

            salary_raw = (item.get("salary") or "").strip() or None
            location = (item.get("candidate_required_location") or "").strip() or None
            job_type = (item.get("job_type") or "").strip()
            emp_type = (
                "Full-time"
                if "full_time" in job_type.lower()
                else "Contract"
                if "contract" in job_type.lower()
                else job_type or None
            )

            results.append(
                RawDiscoveredJobItem(
                    source_name=self.source_name,
                    external_job_id=str(item.get("id")) if item.get("id") else None,
                    title=title[:250],
                    company=company[:200],
                    description=description,
                    official_job_url=url,
                    location=location,
                    work_mode="Remote",
                    employment_type=emp_type,
                    experience_requirement=None,
                    min_salary=None,
                    max_salary=None,
                    salary_currency=None,
                    salary_raw=salary_raw,
                    posted_at=posted_at,
                    raw_metadata={
                        "category": item.get("category"),
                        "tags": item.get("tags") or [],
                    },
                )
            )
        return results


class ArbeitnowPublicAPIAdapter(BaseJobSourceAdapter):
    """Official Arbeitnow Public Job Board API adapter (`https://www.arbeitnow.com/api/job-board-api`)."""

    source_name = "Arbeitnow Public Job Board API"
    adapter_type = "arbeitnow_api"
    base_url = "https://www.arbeitnow.com/api/job-board-api"

    def fetch_jobs(
        self,
        preference: JobPreference,
        max_results: int = 25,
    ) -> List[RawDiscoveredJobItem]:
        results: List[RawDiscoveredJobItem] = []
        try:
            with httpx.Client(timeout=12.0) as client:
                response = client.get(self.base_url)
                if response.status_code != 200:
                    return []
                payload = response.json()
        except Exception as exc:
            logger.info(
                "Arbeitnow API unreachable or timed out (%s); returning 0 items.",
                type(exc).__name__,
            )
            return []

        raw_jobs = payload.get("data") or []
        role_keywords = [r.lower() for r in (preference.job_roles or [])]
        skill_keywords = [s.lower() for s in (preference.skills or [])]

        for item in raw_jobs:
            url = (item.get("url") or "").strip()
            title = (item.get("title") or "").strip()
            company = (item.get("company_name") or "").strip()
            description = _strip_html(item.get("description") or "")
            if not (url and title and company and description):
                continue

            haystack = f"{title} {description} {' '.join(item.get('tags') or [])}".lower()
            if role_keywords or skill_keywords:
                if not any(kw in haystack for kw in (role_keywords + skill_keywords)):
                    continue

            created_ts = item.get("created_at")
            posted_at = (
                datetime.fromtimestamp(int(created_ts), tz=timezone.utc)
                if isinstance(created_ts, (int, float))
                else None
            )

            results.append(
                RawDiscoveredJobItem(
                    source_name=self.source_name,
                    external_job_id=str(item.get("slug") or url),
                    title=title[:250],
                    company=company[:200],
                    description=description,
                    official_job_url=url,
                    location=(item.get("location") or "").strip() or None,
                    work_mode="Remote" if item.get("remote") else "On-site",
                    employment_type="Full-time",
                    experience_requirement=None,
                    posted_at=posted_at,
                    raw_metadata={"tags": item.get("tags") or []},
                )
            )
            if len(results) >= max_results:
                break

        return results


class JobDiscoveryAgent:
    """Agent 1: Coordinates job source adapters and deduplicates discovered jobs in PostgreSQL."""

    def __init__(
        self,
        adapters: Optional[List[BaseJobSourceAdapter]] = None,
    ) -> None:
        self.adapters: List[BaseJobSourceAdapter] = (
            adapters
            if adapters is not None
            else [
                RemotiveOfficialAPIAdapter(),
                ArbeitnowPublicAPIAdapter(),
            ]
        )

    @staticmethod
    def ensure_default_sources(db: Session) -> List[JobSource]:
        """Ensure default permitted job source rows exist in PostgreSQL."""
        defaults = [
            (
                "Remotive Official API",
                "remotive_api",
                "https://remotive.com/api/remote-jobs",
            ),
            (
                "Arbeitnow Public Job Board API",
                "arbeitnow_api",
                "https://www.arbeitnow.com/api/job-board-api",
            ),
        ]
        sources: List[JobSource] = []
        for name, adapter_type, base_url in defaults:
            existing = db.scalars(
                select(JobSource).where(JobSource.name == name).limit(1)
            ).first()
            if existing is None:
                existing = JobSource(
                    name=name,
                    adapter_type=adapter_type,
                    base_url=base_url,
                    is_enabled=True,
                    requires_credentials=False,
                )
                db.add(existing)
                db.flush()
            sources.append(existing)
        db.commit()
        return sources

    def discover_for_preference(
        self,
        db: Session,
        preference: JobPreference,
        max_jobs: int = 50,
    ) -> List[DiscoveredJob]:
        """Run all enabled adapters for `preference`, deduplicate, and persist in `discovered_jobs`."""
        self.ensure_default_sources(db)
        source_by_name = {
            s.name: s for s in db.scalars(select(JobSource)).all()
        }

        collected_raw: List[RawDiscoveredJobItem] = []
        per_adapter_limit = max(5, max_jobs // max(1, len(self.adapters)))

        for adapter in self.adapters:
            source_row = source_by_name.get(adapter.source_name)
            if source_row and not source_row.is_enabled:
                continue

            fetched = adapter.fetch_jobs(
                preference=preference,
                max_results=per_adapter_limit,
            )
            if source_row:
                source_row.last_synced_at = datetime.now(timezone.utc)
            collected_raw.extend(fetched)
            if len(collected_raw) >= max_jobs:
                break

        persisted_jobs: List[DiscoveredJob] = []
        seen_urls: set[str] = set()

        for raw in collected_raw[:max_jobs]:
            try:
                canonical_url = normalize_canonical_url(raw.official_job_url)
            except ValueError:
                continue

            if canonical_url in seen_urls:
                continue
            seen_urls.add(canonical_url)

            fingerprint = compute_job_fingerprint(
                canonical_url=canonical_url,
                company=raw.company,
                title=raw.title,
                external_job_id=raw.external_job_id,
            )

            existing = db.scalars(
                select(DiscoveredJob)
                .where(
                    (DiscoveredJob.canonical_url == canonical_url)
                    | (DiscoveredJob.fingerprint == fingerprint)
                )
                .limit(1)
            ).first()

            if existing is not None:
                persisted_jobs.append(existing)
                continue

            source_row = source_by_name.get(raw.source_name)
            new_job = DiscoveredJob(
                source_id=source_row.id if source_row else None,
                source_name=raw.source_name,
                external_job_id=raw.external_job_id,
                canonical_url=canonical_url,
                fingerprint=fingerprint,
                title=raw.title[:250],
                company=raw.company[:200],
                location=raw.location[:200] if raw.location else None,
                work_mode=raw.work_mode[:50] if raw.work_mode else None,
                employment_type=raw.employment_type[:60] if raw.employment_type else None,
                experience_requirement=(
                    raw.experience_requirement[:120]
                    if raw.experience_requirement
                    else None
                ),
                description=raw.description,
                min_salary=raw.min_salary,
                max_salary=raw.max_salary,
                salary_currency=raw.salary_currency,
                salary_raw=raw.salary_raw,
                posted_at=raw.posted_at,
                official_job_url=raw.official_job_url[:600],
                raw_metadata=raw.raw_metadata or {},
            )
            db.add(new_job)
            db.flush()
            persisted_jobs.append(new_job)

        db.commit()
        return persisted_jobs

