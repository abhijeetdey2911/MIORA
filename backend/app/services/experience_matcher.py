"""Experience Level Normalization, Matching, and Eligibility Service.

Enforces strict candidate experience requirements during Job Matching (Agent 2)
and Job Discovery (Agent 1).
"""

from dataclasses import dataclass
import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger("jobhunter.experience_matcher")

SENIORITY_EXECUTIVE = "EXECUTIVE"
SENIORITY_LEAD_PRINCIPAL = "LEAD_PRINCIPAL"
SENIORITY_SENIOR = "SENIOR"
SENIORITY_ENTRY = "ENTRY"
SENIORITY_MID_UNSPECIFIED = "MID_UNSPECIFIED"

# Seniority keyword patterns for titles
EXECUTIVE_PATTERNS = [
    r"\bvice\s+president\b",
    r"\bvp\b",
    r"\bdirector\b",
    r"\bhead\s+of\b",
    r"\bchief\b",
    r"\bgeneral\s+manager\b",
]

LEAD_PRINCIPAL_PATTERNS = [
    r"\bprincipal\b",
    r"\bstaff\b",
    r"\barchitect\b",
    r"\blead\b",
    r"\btech\s+lead\b",
    r"\bteam\s+lead\b",
    r"\bmanager\b",
    r"\bmanagement\b",
]

SENIOR_PATTERNS = [
    r"\bsenior\b",
    r"\bsr\.\b",
    r"\bsr\b",
    r"\bsde\s*(?:iii|iv|3|4)\b",
    r"\blevel\s*(?:iii|iv|3|4)\b",
    r"\banalyst\s*(?:iii|iv|3|4)\b",
    r"\bspecialist\s*(?:iii|iv|3|4)\b",
    r"\bexpert\b",
]

ENTRY_FRESHER_PATTERNS = [
    r"\bfresher\b",
    r"\bentry\s*level\b",
    r"\bjunior\b",
    r"\bjr\.\b",
    r"\bjr\b",
    r"\bgraduate\b",
    r"\btrainee\b",
    r"\bintern\b",
    r"\binternship\b",
    r"\bassociate\b",
    r"\bapprentice\b",
    r"\bco-op\b",
    r"\b0\s*-\s*1\s*year\b",
    r"\b0\s*-\s*2\s*year\b",
    r"\bentry\b",
]

# Numeric experience regex: e.g. "5+ years", "3-5 years", "min 4 yrs"
NUMERIC_EXP_PATTERN = re.compile(
    r"(?:(?:requires?|minimum|at\s+least|with)?\s*(\d+(?:\.\d+)?)\s*(?:-|to|\+)\s*(\d+(?:\.\d+)?)?\s*(?:years?|yrs?))|"
    r"(?:(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?))",
    re.IGNORECASE,
)


@dataclass
class ExperienceEligibility:
    """Detailed evaluation of a job listing's experience requirements against user preference."""

    is_eligible: bool
    reason: str
    detected_tier: str
    required_years: Optional[str] = None
    min_years_detected: Optional[float] = None
    max_years_detected: Optional[float] = None


def extract_experience_years(text: Optional[str]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """Extract numeric experience requirement (min_years, max_years, raw_str) from text."""
    if not text:
        return None, None, None

    match = NUMERIC_EXP_PATTERN.search(text)
    if not match:
        return None, None, None

    # Group 1 & 2: "3-5 years" or "3 to 5 years"
    if match.group(1):
        min_y = float(match.group(1))
        max_y = float(match.group(2)) if match.group(2) else None
        raw_str = match.group(0).strip()
        return min_y, max_y, raw_str

    # Group 3: "5+ years"
    if match.group(3):
        min_y = float(match.group(3))
        raw_str = match.group(0).strip()
        return min_y, None, raw_str

    return None, None, None


def detect_seniority_tier(job_title: Optional[str], description: Optional[str] = None) -> str:
    """Classify the seniority tier of the job: EXECUTIVE, LEAD_PRINCIPAL, SENIOR, ENTRY, or MID_UNSPECIFIED."""
    title_norm = (job_title or "").lower().strip()

    for pat in EXECUTIVE_PATTERNS:
        if re.search(pat, title_norm, re.IGNORECASE):
            return "EXECUTIVE"

    for pat in LEAD_PRINCIPAL_PATTERNS:
        if re.search(pat, title_norm, re.IGNORECASE):
            return "LEAD_PRINCIPAL"

    for pat in SENIOR_PATTERNS:
        if re.search(pat, title_norm, re.IGNORECASE):
            return "SENIOR"

    for pat in ENTRY_FRESHER_PATTERNS:
        if re.search(pat, title_norm, re.IGNORECASE):
            return "ENTRY"

    return "MID_UNSPECIFIED"


classify_seniority_tier = detect_seniority_tier


def evaluate_experience_eligibility(
    job_title: Optional[str],
    job_description: Optional[str] = None,
    experience_requirement: Optional[str] = None,
    preference_experience_level: str = "Entry-level",
) -> ExperienceEligibility:
    """Evaluate whether a job listing is compatible with user experience preference.

    Supported preferences:
    - "Fresher": Strictly entry-level, graduate, intern, 0-1 years. Senior/Lead/Principal roles are rejected.
    - "Entry-level": 0-2 years, junior, associate, or standard analyst/developer roles. Executive/Staff/Lead roles are rejected.
    - "Experienced": 3+ years, senior, lead, staff roles are welcomed and prioritised.
    """
    pref_level = (preference_experience_level or "Entry-level").strip()
    tier = detect_seniority_tier(job_title, job_description)

    # Extract numeric experience from explicit requirement or description excerpt
    combined_text = f"{experience_requirement or ''} {(job_description or '')[:3000]}"
    min_years, max_years, raw_exp = extract_experience_years(combined_text)

    # 1. Candidate is a "Fresher"
    if pref_level.lower() == "fresher":
        if tier in {"EXECUTIVE", "LEAD_PRINCIPAL"}:
            return ExperienceEligibility(
                is_eligible=False,
                reason=f"Role seniority ({tier.replace('_', ' ').title()}) is incompatible with 'Fresher' preference.",
                detected_tier=tier,
                required_years=raw_exp,
                min_years_detected=min_years,
                max_years_detected=max_years,
            )

        if tier == "SENIOR":
            return ExperienceEligibility(
                is_eligible=False,
                reason="Senior role is incompatible with 'Fresher' experience preference.",
                detected_tier=tier,
                required_years=raw_exp,
                min_years_detected=min_years,
                max_years_detected=max_years,
            )

        if min_years is not None and min_years >= 2.0:
            return ExperienceEligibility(
                is_eligible=False,
                reason=f"Role explicitly requires {raw_exp or f'{int(min_years)}+ years'}, which exceeds 'Fresher' experience level.",
                detected_tier=tier,
                required_years=raw_exp,
                min_years_detected=min_years,
                max_years_detected=max_years,
            )

        if tier == "ENTRY" or (min_years is not None and min_years <= 1.0):
            return ExperienceEligibility(
                is_eligible=True,
                reason="Role specifically targets entry-level, graduate, or fresher candidates.",
                detected_tier=tier,
                required_years=raw_exp,
                min_years_detected=min_years,
                max_years_detected=max_years,
            )

        # Standard role without senior keywords is eligible for fresher
        return ExperienceEligibility(
            is_eligible=True,
            reason="Standard role without mandatory senior experience barriers.",
            detected_tier=tier,
            required_years=raw_exp,
            min_years_detected=min_years,
            max_years_detected=max_years,
        )

    # 2. Candidate is "Entry-level"
    elif pref_level.lower() in {"entry-level", "entry level"}:
        if tier == "EXECUTIVE":
            return ExperienceEligibility(
                is_eligible=False,
                reason="Executive/Director position is incompatible with 'Entry-level' preference.",
                detected_tier=tier,
                required_years=raw_exp,
                min_years_detected=min_years,
                max_years_detected=max_years,
            )

        if tier == "LEAD_PRINCIPAL":
            return ExperienceEligibility(
                is_eligible=False,
                reason="Lead/Principal role is incompatible with 'Entry-level' preference.",
                detected_tier=tier,
                required_years=raw_exp,
                min_years_detected=min_years,
                max_years_detected=max_years,
            )

        if min_years is not None and min_years >= 4.0:
            return ExperienceEligibility(
                is_eligible=False,
                reason=f"Role requires {raw_exp or f'{int(min_years)}+ years'}, which is outside 'Entry-level' scope.",
                detected_tier=tier,
                required_years=raw_exp,
                min_years_detected=min_years,
                max_years_detected=max_years,
            )

        return ExperienceEligibility(
            is_eligible=True,
            reason="Role is compatible with 'Entry-level' experience.",
            detected_tier=tier,
            required_years=raw_exp,
            min_years_detected=min_years,
            max_years_detected=max_years,
        )

    # 3. Candidate is "Experienced"
    else:
        return ExperienceEligibility(
            is_eligible=True,
            reason=f"Role matches candidate's 'Experienced' profile (Seniority: {tier.replace('_', ' ').title()}).",
            detected_tier=tier,
            required_years=raw_exp,
            min_years_detected=min_years,
            max_years_detected=max_years,
        )
