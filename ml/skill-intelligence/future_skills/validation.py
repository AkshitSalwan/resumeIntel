from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import ValidationError

from . import _bootstrap  # noqa: F401
from forecasting.taxonomy.skill_dictionary import INITIAL_SKILLS

from .schemas import AnnotationRecord, FutureSkillsExample, FutureSkillsOutput, ReviewStatus


def validate_example(value: dict[str, Any]) -> FutureSkillsExample:
    example = FutureSkillsExample.model_validate(value)
    if example.human_review_status in {ReviewStatus.REVIEWED, ReviewStatus.GOLD} and example.labeling_method == "weak_dictionary_match":
        raise ValueError("Weak dictionary labels cannot be marked reviewed or gold.")
    if example.human_review_status == ReviewStatus.GOLD and not example.provenance.get("reviewer"):
        raise ValueError("Gold examples require reviewer provenance.")
    if example.human_review_status == ReviewStatus.AI_ASSISTED:
        if example.labeling_method != "ai_assisted_pseudo_label":
            raise ValueError("AI-assisted examples must use the ai_assisted_pseudo_label labeling method.")
        ai_provenance = example.provenance.get("ai_assisted")
        if not isinstance(ai_provenance, dict) or ai_provenance.get("pseudo_label") is not True or ai_provenance.get("independent_human_review") is not False:
            raise ValueError("AI-assisted examples require explicit pseudo-label provenance and no human-review claim.")
    return example


def validate_annotation(record: AnnotationRecord, *, candidate_ids: set[str] | None = None) -> AnnotationRecord:
    if record.reviewer_decision in {ReviewStatus.REVIEWED, ReviewStatus.REJECTED, ReviewStatus.GOLD}:
        if not record.reviewer:
            raise ValueError("Reviewed, rejected, and gold records require reviewer identity.")
    if record.reviewer_decision == ReviewStatus.AI_ASSISTED:
        ai_provenance = record.provenance.get("ai_assisted")
        if record.reviewer is not None:
            raise ValueError("AI-assisted annotations cannot claim a human reviewer.")
        if not isinstance(ai_provenance, dict) or not all(ai_provenance.get(key) for key in ("system_id", "timestamp", "method")):
            raise ValueError("AI-assisted annotations require system_id, timestamp, and method provenance.")
        if ai_provenance.get("pseudo_label") is not True:
            raise ValueError("AI-assisted annotations must be identified as pseudo-labels.")
    if candidate_ids is not None and record.example_id not in candidate_ids:
        raise ValueError("Annotation does not reference a candidate example.")
    if len(record.canonical_skill_ids) != len(set(record.canonical_skill_ids)):
        raise ValueError("Duplicate canonical skill IDs are not allowed.")
    known_ids = {skill.skill_id for skill in INITIAL_SKILLS}
    unsupported = set(record.canonical_skill_ids) - known_ids
    if unsupported:
        raise ValueError(f"Unsupported canonical skill IDs: {sorted(unsupported)}")
    if record.corrected_output:
        if set(record.corrected_output) != {"skills", "unresolved_skills"}:
            raise ValueError("Corrected output must contain skills and unresolved_skills only.")
        if not isinstance(record.corrected_output.get("skills"), list) or not isinstance(record.corrected_output.get("unresolved_skills"), list):
            raise ValueError("Corrected output skills and unresolved_skills must be lists.")
        for item in record.corrected_output["skills"]:
            if not isinstance(item, dict) or set(item) != {"name", "canonical_id", "evidence"}:
                raise ValueError("Each corrected skill requires name, canonical_id, and evidence.")
            if not all(isinstance(item[field], str) and item[field].strip() for field in ("name", "canonical_id", "evidence")):
                raise ValueError("Corrected skill fields must be non-empty strings.")
        corrected_ids = {
            str(item.get("canonical_id"))
            for item in record.corrected_output.get("skills", [])
            if isinstance(item, dict) and item.get("canonical_id")
        }
        if len(corrected_ids) != sum(1 for item in record.corrected_output.get("skills", []) if isinstance(item, dict) and item.get("canonical_id")):
            raise ValueError("Corrected output contains duplicate canonical skill IDs.")
        unsupported_corrected = corrected_ids - known_ids
        if unsupported_corrected:
            raise ValueError(f"Unsupported corrected canonical skill IDs: {sorted(unsupported_corrected)}")
        if corrected_ids != set(record.canonical_skill_ids):
            raise ValueError("Corrected output canonical IDs must match annotation canonical_skill_ids.")
    if not record.source_job_id or not record.provenance:
        raise ValueError("Annotation provenance is required.")
    if record.provenance.get("source_job_id") and str(record.provenance["source_job_id"]) != record.source_job_id:
        raise ValueError("Annotation source job ID does not match provenance.")
    if record.task_type.value not in {"skill_extraction", "skill_relationship", "evidence_interpretation", "emerging_classification", "career_intelligence"}:
        raise ValueError("Unsupported annotation task type.")
    output = record.corrected_output or record.proposed_output
    if record.reviewer_decision in {ReviewStatus.REVIEWED, ReviewStatus.GOLD, ReviewStatus.AI_ASSISTED} and record.task_type.value == "skill_extraction" and record.provenance.get("user_content"):
        if set(output) != {"skills", "unresolved_skills"}:
            raise ValueError("Reviewed skill extraction output must contain skills and unresolved_skills only.")
        if not isinstance(output.get("skills"), list) or not isinstance(output.get("unresolved_skills"), list):
            raise ValueError("Reviewed output skills and unresolved_skills must be lists.")
        content = str(record.provenance["user_content"])
        ids: list[str] = []
        for item in output["skills"]:
            if not isinstance(item, dict) or set(item) != {"name", "canonical_id", "evidence"}:
                raise ValueError("Each skill requires name, canonical_id, and evidence.")
            if not all(isinstance(item[field], str) and item[field].strip() for field in ("name", "canonical_id", "evidence")):
                raise ValueError("Skill fields must be non-empty strings.")
            if item["evidence"] not in content:
                raise ValueError("Skill evidence is not an exact substring of the candidate job description.")
            ids.append(item["canonical_id"])
        if len(ids) != len(set(ids)):
            raise ValueError("Reviewed output contains duplicate canonical skill IDs.")
        if set(ids) != set(record.canonical_skill_ids):
            raise ValueError("Reviewed output canonical IDs must match annotation canonical_skill_ids.")
    return record


def validate_annotation_json(raw: str, *, candidate_ids: set[str] | None = None) -> AnnotationRecord:
    try:
        record = AnnotationRecord.model_validate_json(raw)
    except (ValueError, ValidationError) as error:
        raise ValueError("Invalid annotation JSON.") from error
    return validate_annotation(record, candidate_ids=candidate_ids)


def validate_dataset(examples: list[FutureSkillsExample]) -> dict[str, Any]:
    failures: list[str] = []
    for example in examples:
        try:
            validate_example(example.model_dump())
        except (ValidationError, ValueError) as error:
            failures.append(f"{example.example_id}: {error}")
    return {
        "valid": not failures,
        "count": len(examples),
        "failures": failures,
        "by_task": dict(Counter(example.task_type.value for example in examples)),
        "by_review_status": dict(Counter(example.human_review_status.value for example in examples)),
        "gold_count": sum(example.human_review_status == ReviewStatus.GOLD for example in examples),
    }


def parse_model_output(raw: str) -> FutureSkillsOutput:
    try:
        return FutureSkillsOutput.model_validate_json(raw)
    except (ValueError, ValidationError) as error:
        raise ValueError("Model output is not valid Future Skills JSON.") from error


def require_evidence(output: FutureSkillsOutput) -> None:
    factual = output.observed_evidence or output.insufficient_evidence
    if not factual:
        raise ValueError("Factual output requires source evidence or an explicit insufficient-evidence response.")
