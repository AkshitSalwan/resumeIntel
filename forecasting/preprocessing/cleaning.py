import hashlib
import re
from datetime import UTC, date, datetime
from typing import Any

from forecasting.schemas.job_posting import JobPosting

FIELD_ALIASES = {
    "source_id": ("source_id", "source", "dataset"),
    "external_id": ("external_id", "id", "job_id", "jobId"),
    "job_title": ("job_title", "title", "jobTitle"),
    "company_name": ("company_name", "company", "companyName"),
    "job_description": ("job_description", "description", "jobDescription", "requirements"),
    "location": ("location", "job_location", "city"),
    "country": ("country",),
    "region": ("region", "state", "market"),
    "posting_date": ("posting_date", "date_posted", "posted_date", "date"),
    "industry": ("industry",),
    "employment_type": ("employment_type", "employmentType", "type"),
    "experience_level": ("experience_level", "experienceLevel", "seniority"),
    "source_url": ("source_url", "url", "link"),
}


def _value(record: dict[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        if name in record:
            return record[name]
    return None


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", str(value)).strip()
    return cleaned or None


def parse_date(value: Any) -> date | None:
    if value is None or not str(value).strip():
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw[:10], pattern).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError as exc:
        raise ValueError(f"Unsupported posting date: {raw!r}") from exc


def clean_record(record: dict[str, Any], source_id: str | None = None, now: datetime | None = None) -> JobPosting:
    title = normalize_text(_value(record, FIELD_ALIASES["job_title"]))
    if not title:
        raise ValueError("job_title is required")
    description = normalize_text(_value(record, FIELD_ALIASES["job_description"]))
    company = normalize_text(_value(record, FIELD_ALIASES["company_name"]))
    location = normalize_text(_value(record, FIELD_ALIASES["location"]))
    external_id = normalize_text(_value(record, FIELD_ALIASES["external_id"]))
    resolved_source = normalize_text(source_id) or normalize_text(_value(record, FIELD_ALIASES["source_id"])) or "manual"
    posting_date = parse_date(_value(record, FIELD_ALIASES["posting_date"]))
    collected_at = now or datetime.now(UTC)
    content_basis = "|".join((title.lower(), company or "", location or "", description or "", str(posting_date or "")))
    content_hash = hashlib.sha256(content_basis.encode("utf-8")).hexdigest()
    posting_id = f"{resolved_source}:{external_id}" if external_id else f"{resolved_source}:{content_hash[:20]}"
    return JobPosting(
        id=posting_id,
        source_id=resolved_source,
        external_id=external_id,
        job_title=title,
        normalized_job_title=re.sub(r"[^a-z0-9]+", " ", title.lower()).strip() or None,
        company_name=company,
        industry=normalize_text(_value(record, FIELD_ALIASES["industry"])),
        job_description=description,
        location=location,
        country=normalize_text(_value(record, FIELD_ALIASES["country"])),
        region=normalize_text(_value(record, FIELD_ALIASES["region"])),
        posting_date=posting_date,
        employment_type=normalize_text(_value(record, FIELD_ALIASES["employment_type"])),
        experience_level=normalize_text(_value(record, FIELD_ALIASES["experience_level"])),
        source_url=normalize_text(_value(record, FIELD_ALIASES["source_url"])),
        collected_at=collected_at,
        content_hash=content_hash,
        created_at=collected_at,
    )
