from __future__ import annotations

import re
from collections.abc import Iterable

from .models import NormalizedJob


def deduplicate_jobs(jobs: Iterable[NormalizedJob]) -> tuple[list[NormalizedJob], int]:
    by_source: dict[tuple[str, str], NormalizedJob] = {}
    cross_source: dict[tuple[str, str, str], NormalizedJob] = {}
    duplicate_count = 0
    for job in jobs:
        source_key = (job.source, job.source_job_id)
        if source_key in by_source:
            previous = by_source[source_key]
            by_source[source_key] = previous.model_copy(update={"last_seen_at": max(previous.last_seen_at, job.last_seen_at)})
            duplicate_count += 1
            continue
        cross_key = (re.sub(r"\W+", "", job.company.lower()), re.sub(r"\W+", "", job.title.lower()), re.sub(r"\W+", "", (job.location or "").lower()))
        if cross_key in cross_source and cross_key != ("", "", "") and cross_source[cross_key].source != job.source:
            duplicate_count += 1
            continue
        by_source[source_key] = job
        cross_source[cross_key] = job
    return list(by_source.values()), duplicate_count
