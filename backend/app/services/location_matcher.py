"""Location Normalization, Matching, and Eligibility Service.

Enforces strict candidate location requirements during Job Discovery (Agent 1)
and Job Matching (Agent 2).
"""

from dataclasses import dataclass, field
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("jobhunter.location_matcher")

# Canonical aliases for Indian cities and metropolitan hubs
INDIAN_CITY_ALIASES: Dict[str, str] = {
    # Bangalore / Bengaluru
    "bangalore": "bangalore",
    "bengaluru": "bangalore",
    "blr": "bangalore",
    "bangalore urban": "bangalore",
    "bangalore rural": "bangalore",
    # Hyderabad
    "hyderabad": "hyderabad",
    "hyd": "hyderabad",
    "secunderabad": "hyderabad",
    "cyberabad": "hyderabad",
    # Mumbai
    "mumbai": "mumbai",
    "bombay": "mumbai",
    "navi mumbai": "mumbai",
    "thane": "mumbai",
    # Pune
    "pune": "pune",
    "poona": "pune",
    "pimpri-chinchwad": "pune",
    # Delhi NCR
    "delhi": "delhi ncr",
    "new delhi": "delhi ncr",
    "delhi ncr": "delhi ncr",
    "ncr": "delhi ncr",
    "gurgaon": "delhi ncr",
    "gurugram": "delhi ncr",
    "noida": "delhi ncr",
    "greater noida": "delhi ncr",
    "ghaziabad": "delhi ncr",
    "faridabad": "delhi ncr",
    # Chennai
    "chennai": "chennai",
    "madras": "chennai",
    # Kolkata
    "kolkata": "kolkata",
    "calcutta": "kolkata",
    # Jamshedpur
    "jamshedpur": "jamshedpur",
    "tatanagar": "jamshedpur",
    # Ahmedabad
    "ahmedabad": "ahmedabad",
    "amdavad": "ahmedabad",
    "gandhinagar": "ahmedabad",
    # Kochi / Kerala
    "kochi": "kochi",
    "cochin": "kochi",
    "ernakulam": "kochi",
    "thiruvananthapuram": "thiruvananthapuram",
    "trivandrum": "thiruvananthapuram",
    # Chandigarh Tricity
    "chandigarh": "chandigarh",
    "mohali": "chandigarh",
    "panchkula": "chandigarh",
    # Others
    "jaipur": "jaipur",
    "lucknow": "lucknow",
    "indore": "indore",
    "coimbatore": "coimbatore",
    "visakhapatnam": "visakhapatnam",
    "vizag": "visakhapatnam",
    "bhubaneswar": "bhubaneswar",
    "patna": "patna",
    "nagpur": "nagpur",
    "bhopal": "bhopal",
    "surat": "surat",
    "vadodara": "vadodara",
    "mysore": "mysore",
    "mysuru": "mysore",
    "mangalore": "mangalore",
    "mangaluru": "mangalore",
    "dehradun": "dehradun",
    "ranchi": "ranchi",
}

# Indian states and union territories
INDIAN_STATES: Set[str] = {
    "karnataka",
    "telangana",
    "maharashtra",
    "tamil nadu",
    "west bengal",
    "jharkhand",
    "uttar pradesh",
    "haryana",
    "kerala",
    "gujarat",
    "rajasthan",
    "punjab",
    "andhra pradesh",
    "odisha",
    "bihar",
    "madhya pradesh",
    "delhi",
    "chandigarh",
    "goa",
    "assam",
    "uttarakhand",
    "himachal pradesh",
    "jammu and kashmir",
    "chhattisgarh",
}

# Known foreign countries, territories, and hubs
FOREIGN_COUNTRIES: Set[str] = {
    "germany",
    "deutschland",
    "united states",
    "usa",
    "u.s.a.",
    "united kingdom",
    "uk",
    "u.k.",
    "canada",
    "australia",
    "netherlands",
    "france",
    "spain",
    "italy",
    "poland",
    "sweden",
    "switzerland",
    "austria",
    "belgium",
    "ireland",
    "brazil",
    "mexico",
    "japan",
    "singapore",
    "new zealand",
    "portugal",
    "czech republic",
    "denmark",
    "norway",
    "finland",
    "israel",
    "uae",
    "united arab emirates",
    "philippines",
}

# Known foreign cities
FOREIGN_CITIES: Set[str] = {
    # Germany / DACH
    "hamburg",
    "berlin",
    "munich",
    "münchen",
    "frankfurt",
    "cologne",
    "köln",
    "stuttgart",
    "düsseldorf",
    "dusseldorf",
    "leipzig",
    "dresden",
    "bonn",
    "bremen",
    "hannover",
    "nuremberg",
    "nürnberg",
    # UK / Ireland
    "london",
    "manchester",
    "birmingham",
    "edinburgh",
    "dublin",
    # US / Canada
    "new york",
    "san francisco",
    "austin",
    "seattle",
    "boston",
    "chicago",
    "los angeles",
    "toronto",
    "vancouver",
    "montreal",
    # Europe
    "paris",
    "madrid",
    "barcelona",
    "amsterdam",
    "rotterdam",
    "zurich",
    "geneva",
    "vienna",
    "stockholm",
    "warsaw",
    "krakow",
    # Others
    "sydney",
    "melbourne",
    "tokyo",
}

# Regional / timezone restriction indicators that exclude Indian candidates
FOREIGN_REGIONAL_RESTRICTIONS: List[str] = [
    "europe",
    "emea",
    "eu only",
    "eu",
    "north america",
    "latam",
    "americas",
    "us only",
    "usa only",
    "uk only",
    "cet only",
    "est only",
    "pst only",
    "cst only",
    "germany only",
]

WORLDWIDE_REMOTE_INDICATORS: List[str] = [
    "worldwide",
    "global",
    "anywhere in the world",
    "work from anywhere",
    "remote - anywhere",
    "100% remote worldwide",
    "all countries",
    "anywhere",
]

INDIA_REMOTE_INDICATORS: List[str] = [
    "remote (india)",
    "remote - india",
    "india remote",
    "anywhere in india",
    "pan india",
    "india-wide",
    "india wide",
    "remote in india",
]


@dataclass
class LocationEligibility:
    """Detailed evaluation of a job listing's location against user preference."""

    is_eligible: bool
    reason: str
    matched_location: Optional[str] = None
    is_india: bool = False
    is_remote: bool = False
    is_worldwide_remote: bool = False
    foreign_location: Optional[str] = None


def normalize_text(text: Optional[str]) -> str:
    """Clean and normalize a location or description string."""
    if not text:
        return ""
    cleaned = text.lower().strip()
    # Replace common punctuation with spaces
    cleaned = re.sub(r"[,/|;•\(\)\-\.]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def extract_canonical_city(raw_text: Optional[str]) -> Optional[str]:
    """Extract canonical Indian city name from text if present."""
    if not raw_text:
        return None
    normalized = normalize_text(raw_text)
    words = set(normalized.split())

    # Try multi-word city aliases first (e.g. "new delhi", "delhi ncr", "navi mumbai")
    for alias, canonical in INDIAN_CITY_ALIASES.items():
        if " " in alias and alias in normalized:
            return canonical

    # Try single word aliases
    for word in words:
        if word in INDIAN_CITY_ALIASES:
            return INDIAN_CITY_ALIASES[word]

    return None


def detect_foreign_location(raw_text: Optional[str]) -> Optional[str]:
    """Detect if raw text mentions a known foreign country, city, or restricted region."""
    if not raw_text:
        return None
    normalized = normalize_text(raw_text)
    words = set(normalized.split())

    # Check multi-word foreign countries/cities
    for country in FOREIGN_COUNTRIES:
        if " " in country and country in normalized:
            return country.title()
    for city in FOREIGN_CITIES:
        if " " in city and city in normalized:
            return city.title()

    # Check single word matches
    for word in words:
        if word in FOREIGN_COUNTRIES:
            return word.title()
        if word in FOREIGN_CITIES:
            return word.title()

    return None


def is_explicitly_india_eligible(text: Optional[str]) -> bool:
    """Check if the text explicitly confirms candidates based in India are eligible."""
    if not text:
        return False
    norm = normalize_text(text)
    if "india" in norm or "bengaluru" in norm or "bangalore" in norm or "hyderabad" in norm:
        return True
    for ind in INDIA_REMOTE_INDICATORS:
        if normalize_text(ind) in norm:
            return True
    return False


def is_worldwide_remote(text: Optional[str]) -> bool:
    """Check if the text indicates a true worldwide remote position."""
    if not text:
        return False
    norm = normalize_text(text)
    for indicator in WORLDWIDE_REMOTE_INDICATORS:
        if normalize_text(indicator) in norm:
            return True
    return False


def evaluate_location_eligibility(
    job_location: Optional[str],
    job_work_mode: Optional[str],
    preference_locations: List[str],
    location_mode: str = "INDIA_ONLY",
    preference_work_mode: str = "Remote",
    job_description: Optional[str] = None,
    raw_metadata: Optional[Dict[str, Any]] = None,
) -> LocationEligibility:
    """Evaluate whether a discovered job is compatible with user location preference.

    Location modes:
    - INDIA_ONLY (default): Restricts results to Indian locations & India-eligible remote.
    - SELECTED_LOCATIONS_ONLY: Strictly restricts results to preferred cities selected by user.
    - WORLDWIDE_REMOTE: Allows worldwide remote jobs + India locations. Excludes foreign on-site/hybrid.

    Mandatory rules:
    - Never assume a job labelled 'Remote' is available worldwide.
    - Exclude international on-site and hybrid jobs across all modes.
    - Include remote jobs only when listing explicitly confirms candidates in India are eligible,
      unless WORLDWIDE_REMOTE mode is enabled and the job is worldwide remote.
    - Missing or ambiguous locations are excluded in strict mode.
    """
    mode = (location_mode or "INDIA_ONLY").upper().strip()
    if mode not in {"INDIA_ONLY", "SELECTED_LOCATIONS_ONLY", "WORLDWIDE_REMOTE"}:
        mode = "INDIA_ONLY"

    raw_loc = (job_location or "").strip()
    work_mode_raw = (job_work_mode or "").strip().lower()
    meta_location = ""
    if raw_metadata and isinstance(raw_metadata, dict):
        meta_location = str(
            raw_metadata.get("candidate_required_location")
            or raw_metadata.get("location")
            or ""
        ).strip()

    combined_location_text = f"{raw_loc} {meta_location}".strip()
    norm_location = normalize_text(combined_location_text)

    # Determine if work mode is Remote
    is_remote_job = (
        work_mode_raw == "remote"
        or "remote" in norm_location
        or (raw_metadata and bool(raw_metadata.get("remote")))
    )

    # 1. Check for Missing or Ambiguous location data
    if not combined_location_text or norm_location in {
        "not specified",
        "flexible",
        "unknown",
        "n a",
        "na",
        "null",
        "none",
    }:
        if not is_remote_job:
            return LocationEligibility(
                is_eligible=False,
                reason="Missing or ambiguous location. Excluded under strict location preference.",
            )
        # If it's remote but has zero location context, do not assume worldwide
        if not is_explicitly_india_eligible(job_description) and not (
            mode == "WORLDWIDE_REMOTE" and is_worldwide_remote(job_description)
        ):
            return LocationEligibility(
                is_eligible=False,
                reason="Remote job has no specified eligible region. Candidates in India cannot be confirmed.",
                is_remote=True,
            )

    # 2. Check for Foreign Location (City / Country)
    foreign_match = detect_foreign_location(combined_location_text)

    # 3. Check for Explicit Foreign Regional Restrictions (e.g. EU only, US only)
    has_foreign_restriction = False
    foreign_restriction_label = ""
    for reg in FOREIGN_REGIONAL_RESTRICTIONS:
        if reg in norm_location:
            has_foreign_restriction = True
            foreign_restriction_label = reg.upper()
            break

    # 4. Check for India Presence / Eligibility
    canonical_indian_city = extract_canonical_city(combined_location_text)
    has_indian_state = any(st in norm_location for st in INDIAN_STATES)
    is_in_india = (
        canonical_indian_city is not None
        or has_indian_state
        or "india" in norm_location
        or any(normalize_text(ind) in norm_location for ind in INDIA_REMOTE_INDICATORS)
    )

    # Also check if description confirms India if location text has foreign or remote
    india_confirmed_in_desc = is_explicitly_india_eligible(job_description)
    is_ww_remote = is_worldwide_remote(combined_location_text) or is_worldwide_remote(
        job_description
    )

    # --- EVALUATION LOGIC ---

    # Case A: International On-site or Hybrid Job
    # If the job is located in a foreign country/city and is NOT remote:
    if foreign_match and not is_remote_job:
        return LocationEligibility(
            is_eligible=False,
            reason=f"International on-site job located in {foreign_match}. Incompatible with Indian candidate location preference.",
            foreign_location=foreign_match,
        )

    # If non-remote job has a foreign restriction:
    if has_foreign_restriction and not is_remote_job:
        return LocationEligibility(
            is_eligible=False,
            reason=f"On-site/hybrid job restricted to {foreign_restriction_label}. Candidates in India are not eligible.",
            foreign_location=foreign_restriction_label,
        )

    # If non-remote job is NOT in India and foreign match not yet triggered:
    if not is_remote_job and not is_in_india:
        # Check if it mentions any Indian location
        return LocationEligibility(
            is_eligible=False,
            reason=f"Job location '{raw_loc}' is outside India or not recognized as an eligible Indian location.",
            foreign_location=raw_loc or None,
        )

    # Case B: Foreign Remote Job (e.g. Germany remote, USA remote)
    if is_remote_job and (foreign_match or has_foreign_restriction):
        loc_label = foreign_match or foreign_restriction_label
        # Excluded unless India eligibility is explicitly confirmed in the listing
        if not is_in_india and not india_confirmed_in_desc:
            return LocationEligibility(
                is_eligible=False,
                reason=f"Remote job restricted to candidates in {loc_label}. Candidates based in India are not confirmed eligible.",
                is_remote=True,
                foreign_location=loc_label,
            )

    # Case C: Worldwide Remote Job
    if is_remote_job and is_ww_remote and not is_in_india:
        if mode == "WORLDWIDE_REMOTE":
            return LocationEligibility(
                is_eligible=True,
                reason="Worldwide remote job is eligible under WORLDWIDE_REMOTE mode.",
                matched_location="Worldwide Remote",
                is_remote=True,
                is_worldwide_remote=True,
            )
        else:
            return LocationEligibility(
                is_eligible=False,
                reason="Worldwide remote job excluded under strict India mode (requires explicit India confirmation or WORLDWIDE_REMOTE mode).",
                is_remote=True,
                is_worldwide_remote=True,
            )

    # Case D: India-wide Remote Job
    is_india_remote = is_remote_job and (
        is_in_india
        or india_confirmed_in_desc
        or any(normalize_text(ind) in norm_location for ind in INDIA_REMOTE_INDICATORS)
    )
    if is_india_remote:
        if mode in {"INDIA_ONLY", "WORLDWIDE_REMOTE"}:
            return LocationEligibility(
                is_eligible=True,
                reason="India-wide remote job is eligible.",
                matched_location="Remote (India)",
                is_india=True,
                is_remote=True,
            )
        elif mode == "SELECTED_LOCATIONS_ONLY":
            # Check if user selected remote in their preferences
            user_has_remote_loc = any(
                "remote" in normalize_text(loc) or "anywhere in india" in normalize_text(loc)
                for loc in preference_locations
            )
            pref_allows_remote = (
                preference_work_mode.lower() in {"remote", "hybrid"}
                or user_has_remote_loc
            )
            if pref_allows_remote:
                return LocationEligibility(
                    is_eligible=True,
                    reason="India-wide remote job is eligible under selected remote preferences.",
                    matched_location="Remote (India)",
                    is_india=True,
                    is_remote=True,
                )
            else:
                return LocationEligibility(
                    is_eligible=False,
                    reason="Remote job excluded because user strictly selected on-site work mode.",
                    is_india=True,
                    is_remote=True,
                )

    # Case D2: Remote Job where user explicitly opted into Remote in preferred locations
    if is_remote_job and not foreign_match and not has_foreign_restriction:
        user_explicitly_chose_remote = any(
            normalize_text(loc) == "remote" or "remote" in normalize_text(loc)
            for loc in preference_locations
        )
        if user_explicitly_chose_remote:
            return LocationEligibility(
                is_eligible=True,
                reason="Remote job is eligible under user's explicit Remote preference.",
                matched_location="Remote",
                is_remote=True,
            )

    # Case E: Indian On-site / Hybrid Job
    if is_in_india:
        # Check canonical Indian city
        job_city = canonical_indian_city
        user_canonical_cities: Set[str] = set()
        user_accepts_pan_india = False

        for loc in preference_locations:
            norm_pl = normalize_text(loc)
            if "anywhere in india" in norm_pl or "pan india" in norm_pl:
                user_accepts_pan_india = True
            c_city = extract_canonical_city(loc)
            if c_city:
                user_canonical_cities.add(c_city)
            elif norm_pl in INDIAN_STATES:
                user_canonical_cities.add(norm_pl)

        if mode == "INDIA_ONLY":
            display_loc = job_city.title() if job_city else raw_loc or "India"
            return LocationEligibility(
                is_eligible=True,
                reason=f"Job in {display_loc} aligns with India location preference.",
                matched_location=display_loc,
                is_india=True,
                is_remote=is_remote_job,
            )

        elif mode == "SELECTED_LOCATIONS_ONLY":
            if user_accepts_pan_india:
                return LocationEligibility(
                    is_eligible=True,
                    reason=f"Job in {raw_loc} matches user's 'Anywhere in India' preference.",
                    matched_location=raw_loc,
                    is_india=True,
                    is_remote=is_remote_job,
                )

            if job_city and job_city in user_canonical_cities:
                return LocationEligibility(
                    is_eligible=True,
                    reason=f"Job in {job_city.title()} matches selected location preference.",
                    matched_location=job_city.title(),
                    is_india=True,
                    is_remote=is_remote_job,
                )

            # Check substring matches against preference locations
            for pref_loc in preference_locations:
                norm_p = normalize_text(pref_loc)
                if norm_p and norm_p in norm_location:
                    return LocationEligibility(
                        is_eligible=True,
                        reason=f"Job location '{raw_loc}' matches selected location '{pref_loc}'.",
                        matched_location=pref_loc,
                        is_india=True,
                        is_remote=is_remote_job,
                    )

            selected_str = ", ".join(preference_locations[:3])
            display_loc = job_city.title() if job_city else raw_loc
            return LocationEligibility(
                is_eligible=False,
                reason=f"Job location '{display_loc}' does not match selected preferred locations ({selected_str}).",
                matched_location=None,
                is_india=True,
                is_remote=is_remote_job,
            )

        elif mode == "WORLDWIDE_REMOTE":
            display_loc = job_city.title() if job_city else raw_loc or "India"
            return LocationEligibility(
                is_eligible=True,
                reason=f"Job in {display_loc} is eligible.",
                matched_location=display_loc,
                is_india=True,
                is_remote=is_remote_job,
            )

    # Fallback default: exclude conservatively
    return LocationEligibility(
        is_eligible=False,
        reason=f"Job location '{raw_loc}' could not be verified for Indian candidate eligibility.",
        foreign_location=raw_loc or None,
    )
