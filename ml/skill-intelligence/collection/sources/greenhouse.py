from __future__ import annotations

from typing import Any

from ..http import fetch_json
from ..models import RegistryEntry
from .common import first_text, text, timestamp


def fetch_greenhouse(entry: RegistryEntry, *, fetch=fetch_json) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{entry.board}/jobs?content=true"
    payload = fetch(url)
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    normalized = []
    for job in jobs:
        content = text(job.get("content"))
        normalized.append({
            "source": "greenhouse",
            "source_job_id": str(job.get("id")),
            "company": entry.company,
            "title": text(job.get("title")) or "",
            "description": content,
            "location": first_text((job.get("location") or {}).get("name")),
            "location_raw": first_text((job.get("location") or {}).get("name")),
            "country": None,
            "department": first_text(job.get("departments")),
            "team": first_text(job.get("offices")),
            "published_at": None,
            "source_updated_at": timestamp(job.get("updated_at")),
            "job_url": job.get("absolute_url"),
            "apply_url": job.get("absolute_url"),
            "source_metadata": {"departments": job.get("departments"), "offices": job.get("offices"), "source_updated_at_raw": job.get("updated_at"), "registry_country": entry.country},
        })
    return payload, normalized
