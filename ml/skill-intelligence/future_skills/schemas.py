from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskType(StrEnum):
    SKILL_EXTRACTION = "skill_extraction"
    SKILL_RELATIONSHIP = "skill_relationship"
    EVIDENCE_INTERPRETATION = "evidence_interpretation"
    EMERGING_CLASSIFICATION = "emerging_classification"
    CAREER_INTELLIGENCE = "career_intelligence"


class ReviewStatus(StrEnum):
    CANDIDATE = "candidate"
    AI_ASSISTED = "ai_assisted"
    REVIEWED = "reviewed"
    REJECTED = "rejected"
    GOLD = "gold"


class FutureSkillsExample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    example_id: str
    task_type: TaskType
    messages: list[dict[str, str]]
    source_record_ids: list[str] = Field(default_factory=list)
    source_companies: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    source_job_id: str | None = None
    source_title: str | None = None
    original_evidence: list[str] = Field(default_factory=list)
    proposed_output: dict[str, Any] = Field(default_factory=dict)
    canonical_skill_ids: list[str] = Field(default_factory=list)
    labeling_method: str
    human_review_status: ReviewStatus
    split: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)


class AnnotationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    example_id: str
    source_job_id: str
    company: str
    title: str
    task_type: TaskType
    original_evidence: list[str] = Field(default_factory=list)
    extracted_skills: list[str] = Field(default_factory=list)
    canonical_skill_ids: list[str] = Field(default_factory=list)
    proposed_output: dict[str, Any] = Field(default_factory=dict)
    reviewer_decision: ReviewStatus = ReviewStatus.CANDIDATE
    corrected_output: dict[str, Any] | None = None
    review_notes: str | None = None
    reviewer: str | None = None
    split: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_model: str = "Qwen/Qwen3-4B-Instruct-2507"
    adapter_path: str | None = None
    model_version: str = "untrained"
    enabled: bool = False
    inference_timeout_seconds: float = Field(default=30.0, gt=0)
    ollama_endpoint: str | None = None


class EvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_record_id: str
    field: str
    quote: str = Field(min_length=1)


class FutureSkillsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_type: TaskType
    observed_evidence: list[EvidenceReference] = Field(default_factory=list)
    future_hypotheses: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    insufficient_evidence: bool = False
    model_version: str
