import re
from collections.abc import Iterable

from forecasting.schemas.job_posting import JobPosting

ROLE_RULES: dict[str, tuple[str, ...]] = {
    "Software Engineering": ("software engineer", "software developer"),
    "Backend Development": ("backend", "back-end"),
    "Frontend Development": ("frontend", "front-end", "ui developer"),
    "Full Stack Development": ("full stack", "fullstack"),
    "AI/ML Engineering": ("machine learning engineer", "ml engineer", "ai engineer"),
    "Data Engineering": ("data engineer",),
    "Data Science": ("data scientist", "data science"),
    "Cybersecurity": ("security engineer", "cybersecurity", "cyber security"),
    "Cloud/DevOps Engineering": ("devops", "dev ops", "cloud engineer", "site reliability"),
}


def classify_role(title: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
    matches = [role for role, terms in ROLE_RULES.items() if any(term in normalized for term in terms)]
    return matches[0] if len(matches) == 1 else None


def role_assignments(postings: Iterable[JobPosting]) -> dict[str, list[str]]:
    assignments: dict[str, list[str]] = {}
    for posting in postings:
        role = classify_role(posting.normalized_job_title or posting.job_title)
        if role:
            assignments.setdefault(role, []).append(posting.id)
    return assignments
