from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobPosting(BaseModel):
    """Canonical representation of a source job posting.

    Missing source values remain ``None`` so downstream metrics can distinguish
    unknown coverage from zero demand.
    """

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    id: str
    source_id: str
    external_id: str | None = None
    job_title: str = Field(min_length=1)
    normalized_job_title: str | None = None
    company_name: str | None = None
    industry: str | None = None
    job_description: str | None = None
    location: str | None = None
    country: str | None = None
    region: str | None = None
    posting_date: date | None = None
    employment_type: str | None = None
    experience_level: str | None = None
    source_url: str | None = None
    collected_at: datetime
    content_hash: str
    created_at: datetime

    @field_validator(
        "external_id", "normalized_job_title", "company_name", "industry",
        "job_description", "location", "country", "region", "employment_type",
        "experience_level", "source_url",
        mode="before",
    )
    @classmethod
    def empty_strings_are_missing(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value
