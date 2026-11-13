from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RegistryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str
    provider: str
    board: str
    website: str
    source_url: str
    country: str | None = None
    industry: str | None = None


class NormalizedJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    source: str
    source_job_id: str
    company: str
    title: str
    description: str
    location: str | None = None
    location_raw: str | None = None
    country: str | None = None
    country_resolution_method: str | None = None
    country_confidence: str | None = None
    department: str | None = None
    team: str | None = None
    employment_type: str | None = None
    workplace_type: str | None = None
    published_at: datetime | None = None
    source_updated_at: datetime | None = None
    first_seen_at: datetime
    last_seen_at: datetime
    job_url: str | None = None
    apply_url: str | None = None
    compensation: Any = None
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    collection_timestamp: datetime


class CollectionIssue(BaseModel):
    source: str
    board: str
    status: int | None = None
    error: str
    retryable: bool = False


class CollectionResult(BaseModel):
    fetched: int
    normalized: list[NormalizedJob]
    issues: list[CollectionIssue]
    raw_files: list[str]
    report: dict[str, Any] = Field(default_factory=dict)
