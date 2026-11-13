from __future__ import annotations

from typing import Any

from ..http import fetch_json
from ..models import RegistryEntry
from .common import first_text, text, timestamp


def fetch_ashby(entry: RegistryEntry, *, fetch=fetch_json) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{entry.board}"
    payload = fetch(url)
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    normalized = []
    for job in jobs:
        description = text(job.get("descriptionPlain") or job.get("descriptionHtml"))
        normalized.append({
            "source": "ashby",
            "source_job_id": str(job.get("id")),
            "company": entry.company,
            "title": text(job.get("title")) or "",
            "description": description,
            "location": first_text(job.get("location")),
            "location_raw": first_text(job.get("location")),
            "country": None,
            "department": first_text(job.get("department")),
            "team": first_text(job.get("team")),
            "employment_type": text(job.get("employmentType")),
            "workplace_type": text(job.get("workplaceType")),
            "published_at": timestamp(job.get("publishedAt")),
            "job_url": job.get("jobUrl"),
            "apply_url": job.get("applyUrl"),
            "compensation": job.get("compensation"),
            "source_updated_at": None,
            "source_metadata": {"description_html": job.get("descriptionHtml"), "department": job.get("department"), "team": job.get("team"), "published_at_raw": job.get("publishedAt"), "registry_country": entry.country},
        })
    return payload, normalized
