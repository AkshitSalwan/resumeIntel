from dataclasses import dataclass

from forecasting.schemas.job_posting import JobPosting


@dataclass(frozen=True)
class DeduplicationResult:
    unique: list[JobPosting]
    duplicates: list[dict[str, str]]


def deduplicate_postings(postings: list[JobPosting]) -> DeduplicationResult:
    seen: dict[tuple[str, str], JobPosting] = {}
    unique: list[JobPosting] = []
    duplicates: list[dict[str, str]] = []
    for posting in postings:
        key = (
            f"{posting.source_id}:{posting.external_id}" if posting.external_id else posting.content_hash,
            posting.posting_date.isoformat() if posting.posting_date else "",
        )
        if key in seen:
            duplicates.append({"duplicate_id": posting.id, "kept_id": seen[key].id, "reason": "source/date or content hash match"})
            continue
        seen[key] = posting
        unique.append(posting)
    return DeduplicationResult(unique=unique, duplicates=duplicates)
