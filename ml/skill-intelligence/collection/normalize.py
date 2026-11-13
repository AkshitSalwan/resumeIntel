from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid5, NAMESPACE_URL

from .country import resolve_country
from .models import NormalizedJob, RegistryEntry


def normalize_job(raw: dict[str, Any], entry: RegistryEntry, collected_at: datetime, previous: NormalizedJob | None = None) -> NormalizedJob:
    first_seen = previous.first_seen_at if previous else collected_at
    location_raw = raw.get("location_raw") or raw.get("location")
    resolution = resolve_country(location_raw)
    return NormalizedJob(
        record_id=str(uuid5(NAMESPACE_URL, f"{raw['source']}:{raw['source_job_id']}")),
        source=raw["source"],
        source_job_id=raw["source_job_id"],
        company=raw["company"],
        title=raw["title"],
        description=raw["description"],
        location=raw.get("location"),
        location_raw=location_raw,
        country=raw.get("country") or resolution.country,
        country_resolution_method=raw.get("country_resolution_method") or resolution.method,
        country_confidence=raw.get("country_confidence") or resolution.confidence,
        department=raw.get("department"),
        team=raw.get("team"),
        employment_type=raw.get("employment_type"),
        workplace_type=raw.get("workplace_type"),
        published_at=raw.get("published_at"),
        source_updated_at=raw.get("source_updated_at"),
        first_seen_at=first_seen,
        last_seen_at=collected_at,
        job_url=raw.get("job_url"),
        apply_url=raw.get("apply_url"),
        compensation=raw.get("compensation"),
        source_metadata={**raw.get("source_metadata", {}), "collection_run_id": raw.get("collection_run_id")},
        collection_timestamp=collected_at,
    )
