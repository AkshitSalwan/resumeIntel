from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SkillLabel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    canonical_id: str | None = None
    category: str | None = None
    evidence: str
    confidence: None = None


class ExtractionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: list[SkillLabel] = Field(default_factory=list)
    unresolved_skills: list[str] = Field(default_factory=list)
    model_version: str


class ChatRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[dict[str, str]]
    provenance: dict[str, Any]
    label_source: str
