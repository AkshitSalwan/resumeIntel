from collections.abc import Iterable
from typing import Any

import pandas as pd

from forecasting.schemas.job_posting import JobPosting
from forecasting.schemas.skill import SkillMention


def coverage_analysis(
    postings: Iterable[JobPosting],
    mentions: Iterable[SkillMention],
    source_inventory: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    records = list(postings)
    dated = [item.posting_date for item in records if item.posting_date is not None]
    years = pd.Series([item.year for item in dated], dtype="int64").value_counts().sort_index().to_dict() if dated else {}
    months = pd.Series([item.strftime("%Y-%m") for item in dated], dtype="string").value_counts().sort_index().to_dict() if dated else {}
    return {
        "status": "available" if records else "unavailable",
        "total_job_postings": len(records),
        "unique_companies": len({item.company_name for item in records if item.company_name}),
        "unique_job_titles": len({item.normalized_job_title or item.job_title for item in records}),
        "unique_normalized_skills": len({item.skill_id for item in mentions}),
        "industries": len({item.industry for item in records if item.industry}),
        "geographic_regions": len({item.region for item in records if item.region}),
        "earliest_posting_date": min(dated).isoformat() if dated else None,
        "latest_posting_date": max(dated).isoformat() if dated else None,
        "postings_by_year": {str(key): int(value) for key, value in years.items()},
        "postings_by_month": {str(key): int(value) for key, value in months.items()},
        "source_distribution": pd.Series([item.source_id for item in records], dtype="string").value_counts().to_dict() if records else {},
        "source_inventory": source_inventory or [],
        "missing_years": _missing_years(dated),
        "temporal_comparison_sufficient": len(set(item.year for item in dated)) >= 2,
    }


def _missing_years(dates: list[Any]) -> list[int]:
    if not dates:
        return []
    years = {item.year for item in dates}
    return [year for year in range(min(years), max(years) + 1) if year not in years]
