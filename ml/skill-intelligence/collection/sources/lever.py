from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from ..http import fetch_json
from ..models import RegistryEntry
from .common import first_text, text, timestamp


def fetch_lever(entry: RegistryEntry, *, fetch=fetch_json, page_size: int = 100, max_pages: int = 100) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw_pages: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []
    skip = 0
    for _ in range(max_pages):
        url = f"https://api.lever.co/v0/postings/{entry.board}?{urlencode({'mode': 'json', 'skip': skip, 'limit': page_size})}"
        payload = fetch(url)
        if not isinstance(payload, list):
            break
        raw_pages.append({"url": url, "jobs": payload})
        for job in payload:
            description = text(job.get("descriptionPlain") or job.get("description"))
            if not description:
                continue
            categories = job.get("categories") or {}
            normalized.append({
                "source": "lever",
                "source_job_id": str(job.get("id")),
                "company": entry.company,
                "title": text(job.get("text")) or "",
                "description": description,
                "location": first_text(categories.get("location")),
                "location_raw": first_text(categories.get("location")),
                "country": None,
                "department": first_text(categories.get("department")),
                "team": first_text(categories.get("team")),
                "employment_type": first_text(categories.get("commitment")),
                "published_at": timestamp(job.get("createdAt")),
                "source_updated_at": None,
                "job_url": job.get("hostedUrl"),
                "apply_url": job.get("applyUrl"),
                "source_metadata": {"categories": categories, "description_html": job.get("description"), "created_at_raw": job.get("createdAt"), "registry_country": entry.country},
            })
        if len(payload) < page_size:
            break
        skip += page_size
    return raw_pages, normalized
