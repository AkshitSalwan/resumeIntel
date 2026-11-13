from __future__ import annotations

from collections import Counter
from statistics import mean, median
from typing import Any

from .models import CollectionIssue, NormalizedJob


def role_bucket(title: str) -> str:
    lowered = title.lower()
    rules = (
        ("software/backend/frontend engineering", ("engineer", "developer")),
        ("data engineering", ("data engineer",)),
        ("data science", ("data scientist", "data science")),
        ("machine learning / AI", ("machine learning", "ml engineer", "ai ")),
        ("cloud / DevOps", ("devops", "dev ops", "cloud engineer", "site reliability")),
        ("cybersecurity", ("security engineer", "cybersecurity", "cyber security")),
        ("product management", ("product manager",)),
        ("business analytics", ("business analyst", "business analytics")),
    )
    for label, terms in rules:
        if any(term in lowered for term in terms):
            return label
    return "other / unclassified"


def quality_report(
    *,
    fetched: int,
    parsed: int,
    jobs: list[NormalizedJob],
    duplicate_count: int,
    issues: list[CollectionIssue],
    stage_accounting: dict[str, Any] | None = None,
    run_id: str | None = None,
    minimum_description_length: int = 300,
) -> dict[str, Any]:
    descriptions = [len(job.description) for job in jobs if job.description]
    return {
        "collection_run_id": run_id,
        "pilot_cap_audit": {
            "previous_default_max_records": 20,
            "scope": "global",
            "selection_behavior": "Each board was fetched in full, then the global budget was divided across registry entries and each parsed list was sliced.",
            "persistence_behavior": "Raw snapshots were retained; normalized jobs were previously rewritten as the current export. The scaled collector merges prior normalized jobs and writes run-specific raw snapshots.",
        },
        "status": "suitable_for_initial_llm_finetuning" if len(jobs) >= 500 else "requires_more_data",
        "total_records_fetched": fetched,
        "total_records_parsed": parsed,
        "records_discovered": sum(item.get("discovered", 0) for item in (stage_accounting or {}).get("boards", {}).values()),
        "records_rejected": sum((stage_accounting or {}).get("records_rejected", {}).values()),
        "unique_records": len(jobs),
        "records_with_usable_full_descriptions": sum(bool(job.description and len(job.description) >= minimum_description_length) for job in jobs),
        "missing_field_percentages": {
            field: round(sum(getattr(job, field) in (None, "") for job in jobs) / len(jobs) * 100, 2) if jobs else 0
            for field in ("location", "country", "department", "team", "employment_type", "workplace_type", "published_at", "job_url", "apply_url")
        },
        "duplicate_count": duplicate_count,
        "company_distribution": dict(Counter(job.company for job in jobs)),
        "ats_source_distribution": dict(Counter(job.source for job in jobs)),
        "country_distribution": dict(Counter(job.country or "unknown" for job in jobs)),
        "location_distribution": dict(Counter(job.location or "unknown" for job in jobs)),
        "job_role_distribution": dict(Counter(role_bucket(job.title) for job in jobs)),
        "publication_date_coverage": sum(job.published_at is not None for job in jobs) / len(jobs) * 100 if jobs else 0,
        "source_updated_date_coverage": sum(job.source_updated_at is not None for job in jobs) / len(jobs) * 100 if jobs else 0,
        "collection_date_coverage": sum(job.collection_timestamp is not None for job in jobs) / len(jobs) * 100 if jobs else 0,
        "description_length": {
            "count": len(descriptions),
            "min": min(descriptions) if descriptions else None,
            "median": median(descriptions) if descriptions else None,
            "mean": round(mean(descriptions), 2) if descriptions else None,
            "max": max(descriptions) if descriptions else None,
        },
        "http_failures_and_skipped_boards": [issue.model_dump() for issue in issues],
        "stage_accounting": stage_accounting or {},
        "description_minimum_length": minimum_description_length,
        "limitations": [
            "Public accessibility does not establish redistribution rights.",
            "The collection is ATS- and company-selection-biased.",
            "No human verification of skill labels is implied by collection.",
            "Publication dates are reported only when supplied by the source; Greenhouse updated_at is source_updated_at.",
        ],
    }
