from collections import Counter
from datetime import date
from typing import Any

from forecasting.schemas.job_posting import JobPosting
from forecasting.schemas.skill import SkillMention


def build_quality_report(
    received: int,
    valid: list[JobPosting],
    rejected: list[dict[str, str]],
    duplicates: list[dict[str, str]],
    mentions: list[SkillMention],
    unmapped_skills: list[str] | None = None,
) -> dict[str, Any]:
    dates = [posting.posting_date for posting in valid if posting.posting_date]
    return {
        "records_received": received,
        "valid_records": len(valid),
        "rejected_records": len(rejected),
        "duplicate_records": len(duplicates),
        "missing_posting_dates": sum(posting.posting_date is None for posting in valid),
        "missing_job_descriptions": sum(not posting.job_description for posting in valid),
        "missing_locations": sum(not posting.location for posting in valid),
        "skills_extracted": len(mentions),
        "unique_skills_extracted": len({mention.skill_id for mention in mentions}),
        "unmapped_skills": unmapped_skills or [],
        "source_distribution": dict(Counter(posting.source_id for posting in valid)),
        "date_range": {
            "start": min(dates).isoformat() if dates else None,
            "end": max(dates).isoformat() if dates else None,
        },
        "rejected": rejected,
        "duplicates": duplicates,
    }
