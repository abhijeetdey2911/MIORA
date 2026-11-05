"""Role Synonym and Keyword Expansion Service for Job Discovery and Matching."""

from typing import List, Set

ROLE_SYNONYMS = {
    "data analyst": [
        "data analyst",
        "business analyst",
        "bi analyst",
        "business intelligence analyst",
        "analytics engineer",
        "product analyst",
        "reporting analyst",
        "junior data analyst",
        "data operations analyst",
        "sql analyst",
        "data analytics",
        "analyst",
    ],
    "business analyst": [
        "business analyst",
        "data analyst",
        "product analyst",
        "systems analyst",
        "operations analyst",
        "bi analyst",
    ],
    "data engineer": [
        "data engineer",
        "analytics engineer",
        "big data engineer",
        "etl developer",
        "data platform engineer",
    ],
    "software engineer": [
        "software engineer",
        "software developer",
        "backend developer",
        "backend engineer",
        "full stack engineer",
        "full-stack developer",
        "python developer",
        "sde",
    ],
    "backend developer": [
        "backend developer",
        "backend engineer",
        "python developer",
        "software engineer",
        "api developer",
    ],
    "ai engineer": [
        "ai engineer",
        "machine learning engineer",
        "ml engineer",
        "data scientist",
        "genai engineer",
        "llm engineer",
    ],
    "devops engineer": [
        "devops engineer",
        "cloud engineer",
        "site reliability engineer",
        "sre",
        "platform engineer",
    ],
}


def expand_job_roles(primary_roles: List[str]) -> List[str]:
    """Expand user's primary target roles into a deduplicated list of search keywords and titles."""
    expanded: Set[str] = set()
    for role in primary_roles or []:
        role_cleaned = role.strip()
        if not role_cleaned:
            continue
        expanded.add(role_cleaned)
        role_lower = role_cleaned.lower()
        for key, synonyms in ROLE_SYNONYMS.items():
            if key in role_lower or role_lower in key:
                for syn in synonyms:
                    expanded.add(syn.title())

    # Return preserving primary roles first
    result = list(primary_roles or [])
    for item in expanded:
        if item not in result and item.lower() not in [r.lower() for r in result]:
            result.append(item)
    return result
