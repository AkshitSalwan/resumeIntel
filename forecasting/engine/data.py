from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

from forecasting.schemas.job_posting import JobPosting
from forecasting.taxonomy.skill_dictionary import INITIAL_SKILLS
from forecasting.taxonomy.skill_normalizer import SkillNormalizer


def _date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _datetime(value: Any, fallback: datetime) -> datetime:
    if value:
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            pass
    return fallback
def load_normalized_postings(path: str | Path) -> tuple[list[JobPosting], list[Any]]:
    postings: list[JobPosting] = []
    mentions: list[Any] = []
    normalizer = SkillNormalizer(INITIAL_SKILLS)
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        description = row.get("description") or ""
        collected = datetime.fromisoformat(row["collection_timestamp"].replace("Z", "+00:00"))
        posting = JobPosting(
            id=row["record_id"],
            source_id=row["source"],
            external_id=row.get("source_job_id"),
            job_title=row["title"],
            company_name=row.get("company"),
            job_description=description,
            location=row.get("location"),
            country=row.get("country"),
            posting_date=_date(row.get("published_at")),
            source_url=row.get("job_url"),
            collected_at=collected,
            content_hash=hashlib.sha256(description.encode("utf-8")).hexdigest(),
            created_at=_datetime(row.get("first_seen_at"), collected),
        )
        postings.append(posting)
        mentions.extend(normalizer.extract(posting.id, description))
    return postings, mentions


def build_readiness_report(postings: list[JobPosting], mentions: list[Any]) -> dict[str, Any]:
    dated = [item for item in postings if item.posting_date is not None]
    months = Counter(item.posting_date.strftime("%Y-%m") for item in dated)
    dates = [item.posting_date for item in dated]
    source_updates = len(postings) - len(dated)
    return {
        "status": "insufficient_data_for_validated_forecasting" if len(dated) < len(postings) or len(months) < 24 else "ready_for_backtesting",
        "total_records": len(postings),
        "unique_records": len({item.id for item in postings}),
        "usable_descriptions": sum(bool(item.job_description and len(item.job_description) >= 300) for item in postings),
        "records_with_extracted_skills": len({item.posting_id for item in mentions}),
        "records_with_reliable_publication_dates": len(dated),
        "records_with_only_source_update_dates": source_updates,
        "records_with_unknown_dates": 0,
        "date_range": {"start": min(dates).isoformat() if dates else None, "end": max(dates).isoformat() if dates else None},
        "monthly_record_distribution": dict(sorted(months.items())),
        "distinct_months": len(months),
        "missing_months": _missing_months(dates),
        "distinct_sources": len({item.source_id for item in postings}),
        "distinct_companies": len({item.company_name for item in postings if item.company_name}),
        "distinct_roles": len({item.normalized_job_title or item.job_title for item in postings}),
        "country_coverage": Counter(item.country or "unknown" for item in postings),
        "location_coverage": Counter(item.location or "unknown" for item in postings),
        "skill_count": len({item.skill_id for item in mentions}),
        "limitations": [
            "Greenhouse source_updated_at values are excluded from temporal demand.",
            "Collection timestamps are not publication dates.",
            "Sparse, cross-sectional dated observations do not establish stable historical seasonality.",
        ],
    }


def _missing_months(dates: list[date | None]) -> list[str]:
    if not dates:
        return []
    start = date(min(item for item in dates if item).year, min(item for item in dates if item).month, 1)
    end = date(max(item for item in dates if item).year, max(item for item in dates if item).month, 1)
    missing: list[str] = []
    cursor = start
    while cursor <= end:
        if cursor.strftime("%Y-%m") not in {item.strftime("%Y-%m") for item in dates if item}:
            missing.append(cursor.strftime("%Y-%m"))
        cursor = date(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1)
    return missing
