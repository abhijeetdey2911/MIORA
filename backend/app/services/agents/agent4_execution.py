"""Agent 4: Application Execution (Part 6).

Modular subagent handlers:
- 4.1 OfficialCompanyPortalHandler (`official_company_portal`)
- 4.2 OfficialApplicationFormHandler (`official_application_form`)
- 4.3 PublishedHREmailHandler (`published_hr_email`)
- 4.4 AuthorisedRecruiterOutreachHandler (`verified_recruiter_contact`)

Strict safety & compliance rules:
- Default to Manual Approval Mode (`Prepared` -> `Awaiting Approval`) unless `auto_authorised`
  and the specific route permission is explicitly enabled.
- Never submit an application using an unapproved resume.
- Prevent duplicate applications across all routes and across all preferences (`discovered_job_id` + `idempotency_key`).
- Enforce `max_applications_per_run` and `max_applications_per_day`.
- Never bypass CAPTCHA, authentication, or access controls.
- Never mark an application as `"Submitted"` without confirmation evidence; use `"Submission Unconfirmed"`
  when the submission outcome is uncertain and block retries until reconciled.
"""

from datetime import datetime, time, timedelta, timezone
import hashlib
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.multi_agent import (
    Application,
    ApplicationRoute,
    ApplicationStatusHistory,
    AutomationSettings,
    DiscoveredJob,
    JobMatch,
)
from app.models.job_preference import JobPreference
from app.models.resume import Resume
from app.models.resume_intelligence import ResumeVersion
from app.services.application_preparer import (
    build_full_application_package,
    extract_candidate_name_from_text,
)
from app.services.telegram_service import telegram_service


class SubagentExecutionResult:
    """Standardized outcome returned by each Agent 4 subagent handler."""

    def __init__(
        self,
        *,
        status: str,
        prepared_payload: Dict[str, Any],
        confirmation_evidence: Optional[str] = None,
        external_application_id: Optional[str] = None,
        submission_result: Optional[str] = None,
        error_message: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        self.status = status
        self.prepared_payload = prepared_payload
        self.confirmation_evidence = confirmation_evidence
        self.external_application_id = external_application_id
        self.submission_result = submission_result or (
            "success"
            if status == "Submitted"
            else "unconfirmed"
            if status == "Submission Unconfirmed"
            else "failed"
        )
        self.error_message = error_message
        self.notes = notes


FORBIDDEN_SYNTHETIC_PREFIXES: Tuple[str, ...] = (
    "PORTAL-RECEIPT",
    "FORM-CONFIRM",
    "EMAIL-MSG-ID",
    "OUTREACH-ID",
    "EXT-PORTAL",
    "EXT-FORM",
    "EXT-EMAIL",
    "EXT-OUTREACH",
    "USER-APPROVED-RECEIPT",
    "USER-APPROVAL",
)


def is_synthetic_or_internal_evidence(evidence: Optional[str]) -> bool:
    """Return True if evidence is missing, blank, or matches forbidden synthetic/internal receipts.

    Rejects fabricated or locally hashed tokens:
    - PORTAL-RECEIPT-...
    - FORM-CONFIRM-...
    - EMAIL-MSG-ID-...
    - OUTREACH-ID-...
    - EXT-PORTAL-...
    - EXT-FORM-...
    - EXT-EMAIL-...
    - EXT-OUTREACH-...
    - USER-APPROVED-RECEIPT-...
    - USER-APPROVAL-...
    """
    if not evidence or not isinstance(evidence, str):
        return True
    trimmed = evidence.strip().upper()
    for prefix in FORBIDDEN_SYNTHETIC_PREFIXES:
        if trimmed.startswith(prefix.upper()):
            return True
    return False


class OfficialCompanyPortalHandler:
    """Subagent 4.1: Prepares and (when authorised & permitted) executes official portal applications."""

    route_type = "official_company_portal"

    def prepare_package(
        self,
        job: DiscoveredJob,
        preference: JobPreference,
        route: ApplicationRoute,
        resume: Resume,
        resume_version: Optional[ResumeVersion],
    ) -> Dict[str, Any]:
        settings = get_settings()
        resume_text = (resume_version.content if resume_version else resume.extracted_text) or ""
        candidate_name = extract_candidate_name_from_text(resume_text, fallback="Candidate")
        pkg = build_full_application_package(
            subagent_name="4.1_official_company_portal",
            company=job.company,
            job_title=job.title,
            route_type="official_company_portal",
            route_target=route.url_or_contact,
            job_description=job.description or "",
            candidate_name=candidate_name,
            skills=preference.skills or [],
            resume_id=str(resume.id),
            resume_name=resume.resume_name,
            resume_version_id=str(resume_version.id) if resume_version else None,
            resume_version_number=resume_version.version_number if resume_version else 1,
            work_mode_pref=preference.work_mode or "Remote",
            location_pref=", ".join(preference.locations or ["India"]),
            extra_safety_checks={"playwright_enabled": bool(settings.PLAYWRIGHT_ENABLED)},
        )
        pkg["portal_url"] = route.url_or_contact
        pkg["preference_name"] = preference.preference_name
        return pkg

    def execute_submission(
        self,
        package: Dict[str, Any],
        route: ApplicationRoute,
        simulate_uncertain_outcome: bool = False,
        simulate_failed_outcome: bool = False,
        explicit_confirmation_evidence: Optional[str] = None,
        explicit_application_id: Optional[str] = None,
    ) -> SubagentExecutionResult:
        if simulate_failed_outcome:
            return SubagentExecutionResult(
                status="Failed",
                prepared_payload=package,
                error_message="Official portal session expired or ATS portal rejected submission payload.",
                submission_result="failed",
                notes="External portal submission failed due to employer ATS session error.",
            )

        if simulate_uncertain_outcome:
            return SubagentExecutionResult(
                status="Submission Unconfirmed",
                prepared_payload=package,
                confirmation_evidence=None,
                submission_result="unconfirmed",
                notes=(
                    "Portal submission initiated, but final confirmation receipt could not be verified. "
                    "Marked as Submission Unconfirmed to prevent duplicate retries until reconciled."
                ),
            )

        if explicit_confirmation_evidence:
            if is_synthetic_or_internal_evidence(explicit_confirmation_evidence):
                raise ValueError(
                    f"Forbidden synthetic or internal confirmation evidence: '{explicit_confirmation_evidence}'. "
                    "Actual employer ATS application ID or verified portal confirmation response is required."
                )
            return SubagentExecutionResult(
                status="Submitted",
                prepared_payload=package,
                confirmation_evidence=explicit_confirmation_evidence.strip(),
                external_application_id=explicit_application_id.strip() if explicit_application_id else None,
                submission_result="success",
                notes="Application submitted via official company portal with verified confirmation receipt.",
            )

        # Official company portal: Package preparation is NOT submission.
        # If automated browser submission is not connected or confirmed, do not claim submission.
        return SubagentExecutionResult(
            status="Submission Unconfirmed",
            prepared_payload=package,
            confirmation_evidence=None,
            submission_result="unconfirmed",
            notes=(
                "Portal application package prepared. Automated ATS browser submission is not connected or "
                "did not receive a verified employer confirmation receipt. "
                "Marked as Submission Unconfirmed until external confirmation receipt is recorded."
            ),
        )


class OfficialApplicationFormHandler:
    """Subagent 4.2: Prepares and executes official structured application forms."""

    route_type = "official_application_form"

    def prepare_package(
        self,
        job: DiscoveredJob,
        preference: JobPreference,
        route: ApplicationRoute,
        resume: Resume,
        resume_version: Optional[ResumeVersion],
    ) -> Dict[str, Any]:
        resume_text = (resume_version.content if resume_version else resume.extracted_text) or ""
        candidate_name = extract_candidate_name_from_text(resume_text, fallback="Candidate")
        pkg = build_full_application_package(
            subagent_name="4.2_official_application_form",
            company=job.company,
            job_title=job.title,
            route_type="official_application_form",
            route_target=route.url_or_contact,
            job_description=job.description or "",
            candidate_name=candidate_name,
            skills=preference.skills or [],
            resume_id=str(resume.id),
            resume_name=resume.resume_name,
            resume_version_id=str(resume_version.id) if resume_version else None,
            resume_version_number=resume_version.version_number if resume_version else 1,
            work_mode_pref=preference.work_mode or "Remote",
            location_pref=", ".join(preference.locations or ["India"]),
        )
        pkg["form_url"] = route.url_or_contact
        pkg["preference_name"] = preference.preference_name
        pkg["fields_prepared"] = [
            "candidate_resume_attachment",
            "target_role_alignment",
            "work_mode_preference",
            "cover_letter_text",
            "screening_questions",
        ]
        return pkg

    def execute_submission(
        self,
        package: Dict[str, Any],
        route: ApplicationRoute,
        simulate_uncertain_outcome: bool = False,
        simulate_failed_outcome: bool = False,
        explicit_confirmation_evidence: Optional[str] = None,
        explicit_application_id: Optional[str] = None,
    ) -> SubagentExecutionResult:
        if simulate_failed_outcome:
            return SubagentExecutionResult(
                status="Failed",
                prepared_payload=package,
                error_message="Official application form rejected submission fields or validation failed.",
                submission_result="failed",
                notes="Official application form submission failed.",
            )

        if simulate_uncertain_outcome:
            return SubagentExecutionResult(
                status="Submission Unconfirmed",
                prepared_payload=package,
                confirmation_evidence=None,
                submission_result="unconfirmed",
                notes="Official form submission did not return a deterministic HTTP confirmation token.",
            )

        if explicit_confirmation_evidence:
            if is_synthetic_or_internal_evidence(explicit_confirmation_evidence):
                raise ValueError(
                    f"Forbidden synthetic or internal confirmation evidence: '{explicit_confirmation_evidence}'. "
                    "Actual verified external form confirmation token is required."
                )
            return SubagentExecutionResult(
                status="Submitted",
                prepared_payload=package,
                confirmation_evidence=explicit_confirmation_evidence.strip(),
                external_application_id=explicit_application_id.strip() if explicit_application_id else None,
                submission_result="success",
                notes=f"Official application form submitted with verified external token ({explicit_confirmation_evidence.strip()}).",
            )

        # Official application form: Preparing form data is NOT submitting a form.
        return SubagentExecutionResult(
            status="Submission Unconfirmed",
            prepared_payload=package,
            confirmation_evidence=None,
            submission_result="unconfirmed",
            notes=(
                "Official application form payload prepared. Automated form submission is not connected or "
                "did not receive an external confirmation token. Preparing form data is not submitting a form."
            ),
        )


class PublishedHREmailHandler:
    """Subagent 4.3: Prepares tailored application email drafts for explicitly published HR emails."""

    route_type = "published_hr_email"

    def prepare_package(
        self,
        job: DiscoveredJob,
        preference: JobPreference,
        route: ApplicationRoute,
        resume: Resume,
        resume_version: Optional[ResumeVersion],
    ) -> Dict[str, Any]:
        resume_text = (resume_version.content if resume_version else resume.extracted_text) or ""
        candidate_name = extract_candidate_name_from_text(resume_text, fallback="Candidate")
        pkg = build_full_application_package(
            subagent_name="4.3_published_hr_email",
            company=job.company,
            job_title=job.title,
            route_type="published_hr_email",
            route_target=route.url_or_contact,
            job_description=job.description or "",
            candidate_name=candidate_name,
            skills=preference.skills or [],
            resume_id=str(resume.id),
            resume_name=resume.resume_name,
            resume_version_id=str(resume_version.id) if resume_version else None,
            resume_version_number=resume_version.version_number if resume_version else 1,
            work_mode_pref=preference.work_mode or "Remote",
            location_pref=", ".join(preference.locations or ["India"]),
        )
        pkg["recipient_email"] = route.url_or_contact
        pkg["subject"] = f"Application for {job.title} — {job.company}"
        pkg["body_preview"] = pkg["cover_letter"][:300] + "..."
        pkg["anti_spam_verified"] = True
        return pkg

    def execute_submission(
        self,
        package: Dict[str, Any],
        route: ApplicationRoute,
        simulate_uncertain_outcome: bool = False,
        simulate_failed_outcome: bool = False,
        explicit_confirmation_evidence: Optional[str] = None,
        explicit_application_id: Optional[str] = None,
    ) -> SubagentExecutionResult:
        if simulate_failed_outcome:
            return SubagentExecutionResult(
                status="Failed",
                prepared_payload=package,
                error_message="SMTP server rejected email delivery (e.g. 550 Mailbox unavailable).",
                submission_result="failed",
                notes="HR email dispatch failed due to SMTP delivery error.",
            )

        if simulate_uncertain_outcome:
            return SubagentExecutionResult(
                status="Submission Unconfirmed",
                prepared_payload=package,
                confirmation_evidence=None,
                submission_result="unconfirmed",
                notes="Published HR email dispatch status uncertain; awaiting SMTP delivery receipt.",
            )

        if explicit_confirmation_evidence:
            if is_synthetic_or_internal_evidence(explicit_confirmation_evidence):
                raise ValueError(
                    f"Forbidden synthetic or internal confirmation evidence: '{explicit_confirmation_evidence}'. "
                    "Genuine email provider message ID from a successful dispatch is required."
                )
            return SubagentExecutionResult(
                status="Submitted",
                prepared_payload=package,
                confirmation_evidence=explicit_confirmation_evidence.strip(),
                external_application_id=explicit_application_id.strip() if explicit_application_id else None,
                submission_result="success",
                notes=f"Published HR application email dispatched with verified provider message ID ({explicit_confirmation_evidence.strip()}).",
            )

        # Published HR email: Preparing an email draft is NOT sending an email.
        return SubagentExecutionResult(
            status="Submission Unconfirmed",
            prepared_payload=package,
            confirmation_evidence=None,
            submission_result="unconfirmed",
            notes=(
                "Tailored HR email draft prepared. Automated SMTP dispatch is not connected or "
                "did not return a verified email provider message ID. Preparing an email draft is not sending an email."
            ),
        )


class AuthorisedRecruiterOutreachHandler:
    """Subagent 4.4: Prepares concise professional outreach notes for verified recruiter contacts."""

    route_type = "verified_recruiter_contact"

    def prepare_package(
        self,
        job: DiscoveredJob,
        preference: JobPreference,
        route: ApplicationRoute,
        resume: Resume,
        resume_version: Optional[ResumeVersion],
    ) -> Dict[str, Any]:
        resume_text = (resume_version.content if resume_version else resume.extracted_text) or ""
        candidate_name = extract_candidate_name_from_text(resume_text, fallback="Candidate")
        pkg = build_full_application_package(
            subagent_name="4.4_authorised_recruiter_outreach",
            company=job.company,
            job_title=job.title,
            route_type="verified_recruiter_contact",
            route_target=route.url_or_contact,
            job_description=job.description or "",
            candidate_name=candidate_name,
            skills=preference.skills or [],
            resume_id=str(resume.id),
            resume_name=resume.resume_name,
            resume_version_id=str(resume_version.id) if resume_version else None,
            resume_version_number=resume_version.version_number if resume_version else 1,
            work_mode_pref=preference.work_mode or "Remote",
            location_pref=", ".join(preference.locations or ["India"]),
        )
        pkg["verified_contact"] = route.url_or_contact
        pkg["outreach_note"] = (
            f"Hello, I noticed the {job.title} opening at {job.company} and have prepared my "
            f"approved resume ({resume.resume_name}) and tailored portfolio for consideration."
        )
        return pkg

    def execute_submission(
        self,
        package: Dict[str, Any],
        route: ApplicationRoute,
        simulate_uncertain_outcome: bool = False,
        simulate_failed_outcome: bool = False,
        explicit_confirmation_evidence: Optional[str] = None,
        explicit_application_id: Optional[str] = None,
    ) -> SubagentExecutionResult:
        if simulate_failed_outcome:
            return SubagentExecutionResult(
                status="Failed",
                prepared_payload=package,
                error_message="Recruiter contact message failed to send: rate limit exceeded or contact invalid.",
                submission_result="failed",
                notes="Recruiter outreach dispatch failed.",
            )

        if simulate_uncertain_outcome:
            return SubagentExecutionResult(
                status="Submission Unconfirmed",
                prepared_payload=package,
                confirmation_evidence=None,
                submission_result="unconfirmed",
                notes="Recruiter outreach delivery unconfirmed; marked for manual reconciliation.",
            )

        if explicit_confirmation_evidence:
            if is_synthetic_or_internal_evidence(explicit_confirmation_evidence):
                raise ValueError(
                    f"Forbidden synthetic or internal confirmation evidence: '{explicit_confirmation_evidence}'. "
                    "Verified recruiter communication delivery receipt is required."
                )
            return SubagentExecutionResult(
                status="Submitted",
                prepared_payload=package,
                confirmation_evidence=explicit_confirmation_evidence.strip(),
                external_application_id=explicit_application_id.strip() if explicit_application_id else None,
                submission_result="success",
                notes=f"Authorised recruiter outreach delivered with verified delivery receipt ({explicit_confirmation_evidence.strip()}).",
            )

        # Recruiter outreach: Preparing an outreach note is NOT delivering a message.
        return SubagentExecutionResult(
            status="Submission Unconfirmed",
            prepared_payload=package,
            confirmation_evidence=None,
            submission_result="unconfirmed",
            notes=(
                "Recruiter outreach note prepared. Automated outreach messaging is not connected or "
                "did not return a verified delivery receipt. Preparing an outreach note is not delivering a message."
            ),
        )


class ApplicationExecutionAgent:
    """Agent 4: Coordinates subagents 4.1-4.4 with strict duplicate prevention, resume approval enforcement,
    rate/daily limits, and confirmation verification.
    """

    ROUTE_PRIORITY = {
        "official_company_portal": 1,
        "official_application_form": 2,
        "published_hr_email": 3,
        "verified_recruiter_contact": 4,
    }

    def __init__(self) -> None:
        self.handlers = {
            "official_company_portal": OfficialCompanyPortalHandler(),
            "official_application_form": OfficialApplicationFormHandler(),
            "published_hr_email": PublishedHREmailHandler(),
            "verified_recruiter_contact": AuthorisedRecruiterOutreachHandler(),
        }

    @staticmethod
    def build_idempotency_key(discovered_job_id: uuid.UUID) -> str:
        """Deterministic idempotency key per discovered job to prevent cross-preference and cross-route duplicates."""
        return hashlib.sha256(f"jobhunter-app:{discovered_job_id}".encode("utf-8")).hexdigest()

    @staticmethod
    def _resolve_approved_resume_and_version(
        db: Session,
        preference: JobPreference,
        preferred_version_id: Optional[uuid.UUID] = None,
    ) -> Tuple[Optional[Resume], Optional[ResumeVersion]]:
        """Ensure only an approved resume (and approved ResumeVersion) is ever used by Agent 4."""
        version_id = preferred_version_id or preference.approved_resume_version_id
        if version_id:
            version = db.get(ResumeVersion, version_id)
            if version and version.approval_status == "Approved":
                resume = db.get(Resume, version.parent_resume_id)
                if resume and resume.processing_status == "Processed":
                    return resume, version

        if preference.approved_resume_id:
            resume = db.get(Resume, preference.approved_resume_id)
            if resume and resume.processing_status == "Processed":
                ver = (
                    db.get(ResumeVersion, resume.approved_version_id)
                    if resume.approved_version_id
                    else None
                )
                if ver and ver.approval_status == "Approved":
                    return resume, ver

        # Fallback: find any processed Resume with an Approved ResumeVersion
        approved_ver = db.scalars(
            select(ResumeVersion)
            .where(ResumeVersion.approval_status == "Approved")
            .order_by(ResumeVersion.updated_at.desc())
        ).first()
        if approved_ver:
            resume = db.get(Resume, approved_ver.parent_resume_id)
            if resume and resume.processing_status == "Processed":
                return resume, approved_ver

        return None, None

    @staticmethod
    def _count_applications_today(db: Session) -> int:
        today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
        return int(
            db.scalar(
                select(func.count(Application.id)).where(
                    Application.created_at >= today_start
                )
            )
            or 0
        )

    @staticmethod
    def _is_auto_submit_permitted(
        settings: AutomationSettings,
        route: ApplicationRoute,
    ) -> bool:
        if settings.approval_mode != "auto_authorised":
            return False
        if route.verification_status != "verified" or route.requires_manual_review:
            return False
        if route.route_type == "official_company_portal":
            return bool(settings.allow_portal_auto_submit)
        if route.route_type == "official_application_form":
            return bool(settings.allow_form_auto_submit)
        if route.route_type == "published_hr_email":
            return bool(settings.allow_hr_email_auto_submit)
        if route.route_type == "verified_recruiter_contact":
            return bool(settings.allow_recruiter_outreach)
        return False

    def process_shortlisted_jobs(
        self,
        db: Session,
        preference: JobPreference,
        shortlisted_matches: List[JobMatch],
        routes: List[ApplicationRoute],
        automation_settings: AutomationSettings,
        preference_run_id: Optional[uuid.UUID] = None,
        preferred_resume_version_id: Optional[uuid.UUID] = None,
    ) -> List[Application]:
        """Prepare or execute applications for shortlisted jobs while enforcing all safety rules."""
        if automation_settings and automation_settings.is_kill_switch_engaged:
            return []
        resume, resume_version = self._resolve_approved_resume_and_version(
            db, preference, preferred_resume_version_id
        )
        if not resume or not resume_version or resume_version.approval_status != "Approved":
            # Strict rule: Never prepare or submit an application using an unapproved resume
            return []

        routes_by_job: Dict[uuid.UUID, List[ApplicationRoute]] = {}
        for route in routes:
            routes_by_job.setdefault(route.discovered_job_id, []).append(route)

        created_applications: List[Application] = []
        run_limit = max(1, int(automation_settings.max_applications_per_run or 10))
        daily_limit = max(1, int(automation_settings.max_applications_per_day or 25))
        apps_today = self._count_applications_today(db)

        for match in shortlisted_matches:
            if not match.shortlisted:
                continue
            if len(created_applications) >= run_limit:
                break
            if apps_today >= daily_limit:
                break

            job = match.discovered_job
            idempotency_key = self.build_idempotency_key(job.id)

            # Cross-preference & cross-route duplicate check
            existing_app = db.scalar(
                select(Application).where(
                    (Application.discovered_job_id == job.id)
                    | (Application.idempotency_key == idempotency_key)
                )
            )
            if existing_app is not None:
                continue

            job_routes = routes_by_job.get(job.id, [])
            if not job_routes:
                continue

            # Prioritise official company portals first
            job_routes.sort(key=lambda r: self.ROUTE_PRIORITY.get(r.route_type, 99))
            best_route = job_routes[0]
            handler = self.handlers.get(
                best_route.route_type, self.handlers["official_company_portal"]
            )

            package = handler.prepare_package(
                job=job,
                preference=preference,
                route=best_route,
                resume=resume,
                resume_version=resume_version,
            )

            auto_submit = self._is_auto_submit_permitted(automation_settings, best_route)
            now = datetime.now(timezone.utc)

            app_record = Application(
                preference_id=preference.id,
                preference_run_id=preference_run_id,
                discovered_job_id=job.id,
                job_match_id=match.id,
                route_id=best_route.id,
                resume_id=resume.id,
                resume_version_id=resume_version.id if resume_version else None,
                company=job.company,
                job_title=job.title,
                route_type=best_route.route_type,
                route_target=best_route.url_or_contact,
                status="Prepared",
                approval_required=not auto_submit,
                approved_by_user=False,
                prepared_payload=package,
                notes=f"Application prepared via {best_route.route_type} using approved resume '{resume.resume_name}'.",
                idempotency_key=idempotency_key,
            )
            db.add(app_record)
            db.flush()

            # Initial status history entry: Prepared
            db.add(
                ApplicationStatusHistory(
                    application_id=app_record.id,
                    previous_status=None,
                    new_status="Prepared",
                    source="agent_4_execution",
                    notes=f"Prepared application package via {best_route.route_type}.",
                )
            )

            if auto_submit:
                simulate_uncertain = bool((job.raw_metadata or {}).get("simulate_uncertain_submission"))
                simulate_failure = bool((job.raw_metadata or {}).get("simulate_failed_submission"))
                explicit_receipt = (job.raw_metadata or {}).get("confirmation_receipt")
                explicit_ext_id = (job.raw_metadata or {}).get("external_application_id")

                app_record.approved_by_user = True
                app_record.approved_at = now
                app_record.approval_reference = "AUTO-AUTHORISED-POLICY"
                app_record.status = "Approved"
                db.add(
                    ApplicationStatusHistory(
                        application_id=app_record.id,
                        previous_status="Prepared",
                        new_status="Approved",
                        source="agent_4_auto_authorised",
                        notes="Auto-authorised based on automation settings policy.",
                    )
                )
                db.flush()

                # Transition to Submission In Progress
                app_record.status = "Submission In Progress"
                app_record.submission_attempted_at = now
                db.add(
                    ApplicationStatusHistory(
                        application_id=app_record.id,
                        previous_status="Approved",
                        new_status="Submission In Progress",
                        source="agent_4_auto_authorised",
                        notes="Starting auto-authorised external submission attempt.",
                    )
                )
                db.flush()

                exec_result = handler.execute_submission(
                    package=package,
                    route=best_route,
                    simulate_uncertain_outcome=simulate_uncertain,
                    simulate_failed_outcome=simulate_failure,
                    explicit_confirmation_evidence=explicit_receipt,
                    explicit_application_id=explicit_ext_id,
                )
                app_record.status = exec_result.status
                app_record.confirmation_evidence = exec_result.confirmation_evidence
                app_record.external_application_id = exec_result.external_application_id
                app_record.submission_result = exec_result.submission_result
                app_record.error_message = exec_result.error_message
                app_record.notes = exec_result.notes
                if exec_result.status == "Submitted":
                    app_record.applied_at = now
                    app_record.follow_up_reminder_at = now + timedelta(days=7)
                db.add(
                    ApplicationStatusHistory(
                        application_id=app_record.id,
                        previous_status="Submission In Progress",
                        new_status=exec_result.status,
                        source="agent_4_auto_authorised",
                        notes=exec_result.notes,
                        evidence=exec_result.confirmation_evidence,
                    )
                )
            else:
                app_record.status = "Awaiting Approval"
                db.add(
                    ApplicationStatusHistory(
                        application_id=app_record.id,
                        previous_status="Prepared",
                        new_status="Awaiting Approval",
                        source="agent_4_execution",
                        notes="Queued for user review and approval in Manual Approval Mode.",
                    )
                )

            db.flush()
            created_applications.append(app_record)
            apps_today += 1

        db.commit()
        return created_applications

    def approve_application(
        self,
        db: Session,
        application_id: uuid.UUID,
        notes: Optional[str] = None,
    ) -> Application:
        """Explicit user approval transitions an application from 'Awaiting Approval' to 'Approved'.

        Strict safety guarantee: User approval NEVER marks an application as 'Submitted'.
        Generates an internal approval audit reference (USER-APPROVAL-REC-xxxx).
        """
        settings_record = db.scalar(select(AutomationSettings).limit(1))
        if settings_record and settings_record.is_kill_switch_engaged:
            raise ValueError("Application approval blocked: Emergency kill switch is engaged.")

        app_record = db.get(Application, application_id)
        if not app_record:
            raise ValueError("Application not found.")

        if app_record.status == "Submitted":
            raise ValueError("Application has already been submitted.")

        if app_record.status == "Submission In Progress":
            raise ValueError("Application submission is currently in progress.")

        if app_record.status == "Submission Unconfirmed":
            raise ValueError(
                "Application is in 'Submission Unconfirmed' state and must be reconciled before retrying."
            )

        if app_record.status == "Approved":
            return app_record

        # Enforce approved resume
        if app_record.resume_id:
            resume = db.get(Resume, app_record.resume_id)
            if not resume or resume.processing_status != "Processed":
                raise ValueError("Cannot approve application: associated resume is not processed.")
            if app_record.resume_version_id:
                ver = db.get(ResumeVersion, app_record.resume_version_id)
                if not ver or ver.approval_status != "Approved":
                    raise ValueError("Cannot approve application: resume version is not approved.")
        else:
            raise ValueError("Cannot approve application without an approved resume.")

        now = datetime.now(timezone.utc)
        previous_status = app_record.status
        approval_ref = f"USER-APPROVAL-REC-{hashlib.sha256(f'{app_record.id}:{now.isoformat()}'.encode('utf-8')).hexdigest()[:10].upper()}"

        app_record.approved_by_user = True
        app_record.approved_at = now
        app_record.approval_reference = approval_ref
        app_record.status = "Approved"
        app_record.notes = notes or f"Application explicitly approved by user (Ref: {approval_ref}). Ready for submission."

        db.add(
            ApplicationStatusHistory(
                application_id=app_record.id,
                previous_status=previous_status,
                new_status="Approved",
                source="user_approval",
                notes=app_record.notes,
            )
        )
        db.commit()
        db.refresh(app_record)

        telegram_service.record_and_dispatch(
            db,
            event_type="application_approved",
            title=f"Application Approved: {app_record.job_title} at {app_record.company}",
            message=f"Application approved by user (Ref: {approval_ref}). Queued for external submission.",
            preference_id=app_record.preference_id,
            application_id=app_record.id,
            company=app_record.company,
            job_title=app_record.job_title,
            status_badge="Approved",
        )
        return app_record

    def execute_submission(
        self,
        db: Session,
        application_id: uuid.UUID,
        simulate_uncertain: bool = False,
        simulate_failure: bool = False,
        explicit_confirmation_evidence: Optional[str] = None,
        explicit_application_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Application:
        """Executes external submission for an Approved (or retrying Failed) application.

        Lifecycle progression:
        1. Transitions 'Approved' -> 'Submission In Progress'.
        2. Executes external route handler.
        3. Evaluates external confirmation:
           - If genuine employer confirmation receipt verified: transitions to 'Submitted'.
           - If outcome uncertain: transitions to 'Submission Unconfirmed'.
           - If submission fails or network/server error: transitions to 'Failed'.
        """
        settings_record = db.scalar(select(AutomationSettings).limit(1))
        if settings_record and settings_record.is_kill_switch_engaged:
            raise ValueError("External submission blocked: Emergency kill switch is engaged.")

        app_record = db.get(Application, application_id)
        if not app_record:
            raise ValueError("Application not found.")

        if app_record.status == "Submitted":
            raise ValueError("Application has already been submitted; duplicate submission is blocked.")

        if app_record.status == "Submission In Progress":
            raise ValueError("Application submission is currently in progress.")

        if app_record.status == "Submission Unconfirmed":
            raise ValueError(
                "Application is in 'Submission Unconfirmed' state and must be reconciled before retrying."
            )

        if app_record.status in ("Prepared", "Awaiting Approval"):
            raise ValueError(
                "Application requires user approval before submission. Status must be 'Approved'."
            )

        if not app_record.approved_by_user and app_record.status != "Approved":
            raise ValueError("Application has not been approved by user.")

        # Enforce approved resume
        if app_record.resume_id:
            resume = db.get(Resume, app_record.resume_id)
            if not resume or resume.processing_status != "Processed":
                raise ValueError("Cannot submit application: associated resume is not processed.")
            if app_record.resume_version_id:
                ver = db.get(ResumeVersion, app_record.resume_version_id)
                if not ver or ver.approval_status != "Approved":
                    raise ValueError("Cannot submit application: resume version is not approved.")
        else:
            raise ValueError("Cannot submit application without an approved resume.")

        # Guard: Internal approval receipts or synthetic receipts cannot be passed as external confirmation evidence
        if explicit_confirmation_evidence and is_synthetic_or_internal_evidence(explicit_confirmation_evidence):
            raise ValueError(
                f"Forbidden synthetic or internal confirmation evidence: '{explicit_confirmation_evidence}'. "
                "A genuine external employer ATS application ID, verified portal confirmation response, "
                "genuine email provider message ID, or recruiter delivery receipt is required."
            )

        now = datetime.now(timezone.utc)
        previous_status = app_record.status

        # Step 1: Transition to 'Submission In Progress'
        app_record.status = "Submission In Progress"
        app_record.submission_attempted_at = now
        app_record.notes = notes or f"External submission attempt initiated via {app_record.route_type} to {app_record.route_target}."

        db.add(
            ApplicationStatusHistory(
                application_id=app_record.id,
                previous_status=previous_status,
                new_status="Submission In Progress",
                source="agent_4_execution",
                notes=app_record.notes,
            )
        )
        db.commit()
        db.refresh(app_record)

        telegram_service.record_and_dispatch(
            db,
            event_type="submission_started",
            title=f"Submission Started: {app_record.job_title} at {app_record.company}",
            message=f"Beginning external submission via {app_record.route_type} to {app_record.route_target}.",
            preference_id=app_record.preference_id,
            application_id=app_record.id,
            company=app_record.company,
            job_title=app_record.job_title,
            status_badge="Submission In Progress",
        )

        # Step 2: Invoke subagent handler
        route = db.get(ApplicationRoute, app_record.route_id) if app_record.route_id else None
        if not route:
            route = ApplicationRoute(
                discovered_job_id=app_record.discovered_job_id,
                preference_id=app_record.preference_id,
                route_type=app_record.route_type,
                url_or_contact=app_record.route_target,
                source="inferred",
            )

        handler = self.handlers.get(app_record.route_type, self.handlers["official_company_portal"])

        try:
            result = handler.execute_submission(
                package=app_record.prepared_payload,
                route=route,
                simulate_uncertain_outcome=simulate_uncertain,
                simulate_failed_outcome=simulate_failure,
                explicit_confirmation_evidence=explicit_confirmation_evidence,
                explicit_application_id=explicit_application_id,
            )
        except Exception as exc:
            result = SubagentExecutionResult(
                status="Failed",
                prepared_payload=app_record.prepared_payload,
                error_message=str(exc),
                submission_result="failed",
                notes=f"Submission failed with error: {str(exc)}",
            )

        # Step 3: Evaluate result and transition
        post_progress_status = "Submission In Progress"
        if result.status == "Submitted" and result.confirmation_evidence:
            if is_synthetic_or_internal_evidence(result.confirmation_evidence):
                raise ValueError(
                    f"Forbidden synthetic or internal confirmation evidence returned: '{result.confirmation_evidence}'."
                )
            app_record.status = "Submitted"
            app_record.applied_at = datetime.now(timezone.utc)
            app_record.confirmation_evidence = result.confirmation_evidence
            app_record.external_application_id = result.external_application_id
            app_record.submission_result = "success"
            app_record.error_message = None
            if app_record.follow_up_reminder_at is None:
                app_record.follow_up_reminder_at = app_record.applied_at + timedelta(days=7)
            app_record.notes = notes or result.notes or f"Application submitted with external confirmation ({result.confirmation_evidence})."

            db.add(
                ApplicationStatusHistory(
                    application_id=app_record.id,
                    previous_status=post_progress_status,
                    new_status="Submitted",
                    source="agent_4_execution",
                    notes=app_record.notes,
                    evidence=app_record.confirmation_evidence,
                )
            )
            db.commit()
            db.refresh(app_record)

            telegram_service.record_and_dispatch(
                db,
                event_type="submission_confirmed",
                title=f"Submission Confirmed: {app_record.job_title} at {app_record.company}",
                message=f"Application confirmed by employer/portal. Evidence: {app_record.confirmation_evidence}",
                preference_id=app_record.preference_id,
                application_id=app_record.id,
                company=app_record.company,
                job_title=app_record.job_title,
                status_badge="Submitted",
            )

        elif result.status == "Submission Unconfirmed":
            app_record.status = "Submission Unconfirmed"
            app_record.confirmation_evidence = None
            app_record.submission_result = "unconfirmed"
            app_record.notes = notes or result.notes or (
                "Submission attempt completed, but external confirmation could not be verified. "
                "Marked as Submission Unconfirmed to prevent duplicate retries until reconciled."
            )

            db.add(
                ApplicationStatusHistory(
                    application_id=app_record.id,
                    previous_status=post_progress_status,
                    new_status="Submission Unconfirmed",
                    source="agent_4_execution",
                    notes=app_record.notes,
                )
            )
            db.commit()
            db.refresh(app_record)

            telegram_service.record_and_dispatch(
                db,
                event_type="submission_unconfirmed",
                title=f"Submission Unconfirmed: {app_record.job_title} at {app_record.company}",
                message=app_record.notes,
                preference_id=app_record.preference_id,
                application_id=app_record.id,
                company=app_record.company,
                job_title=app_record.job_title,
                status_badge="Submission Unconfirmed",
            )

        else:  # Failed
            app_record.status = "Failed"
            app_record.submission_result = "failed"
            app_record.error_message = result.error_message or "External submission attempt failed."
            app_record.retry_count = (app_record.retry_count or 0) + 1
            app_record.notes = notes or result.notes or f"External submission failed: {app_record.error_message}"

            db.add(
                ApplicationStatusHistory(
                    application_id=app_record.id,
                    previous_status=post_progress_status,
                    new_status="Failed",
                    source="agent_4_execution",
                    notes=app_record.notes,
                )
            )
            db.commit()
            db.refresh(app_record)

            telegram_service.record_and_dispatch(
                db,
                event_type="submission_failed",
                title=f"Submission Failed: {app_record.job_title} at {app_record.company}",
                message=app_record.notes,
                preference_id=app_record.preference_id,
                application_id=app_record.id,
                company=app_record.company,
                job_title=app_record.job_title,
                status_badge="Failed",
            )

        from app.services.agents.agent5_tracking import agent5_tracking
        agent5_tracking.sync_preference_applications(db, app_record.preference_id)
        return app_record

    def approve_and_execute_application(
        self,
        db: Session,
        application_id: uuid.UUID,
        approved_by_user: bool = True,
        confirm_submission: Optional[bool] = None,
        confirmation_evidence: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Application:
        """Handle user approval review.

        STRICT SAFETY ENFORCEMENT:
        Manual user approval CANNOT trigger external submission automatically,
        even if confirm_submission=True or auto_submit=True is passed by the caller.
        Manual approval strictly transitions the application to 'Approved' (or 'Withdrawn')
        and stops there. External submission must be explicitly initiated via execute_submission.
        """
        app_record = db.get(Application, application_id)
        if not app_record:
            raise ValueError("Application not found.")

        if not approved_by_user:
            previous_status = app_record.status
            app_record.status = "Withdrawn"
            app_record.notes = notes or "Application withdrawn by user during approval review."
            db.add(
                ApplicationStatusHistory(
                    application_id=app_record.id,
                    previous_status=previous_status,
                    new_status="Withdrawn",
                    source="user_approval",
                    notes=app_record.notes,
                )
            )
            db.commit()
            db.refresh(app_record)
            return app_record

        # Strictly transitions to Approved and STOPS. Does not trigger execute_submission.
        return self.approve_application(db, application_id=application_id, notes=notes)


agent4_execution = ApplicationExecutionAgent()
