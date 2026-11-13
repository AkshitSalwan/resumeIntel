from __future__ import annotations

from pydantic import BaseModel, Field

from src.contracts import ExtractionOutput


class ExtractSkillsRequest(BaseModel):
    job_description: str = Field(min_length=1, max_length=100_000)
    industry: str | None = None
    role: str | None = None


class ExtractSkillsResponse(ExtractionOutput):
    pass
