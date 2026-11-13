from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from . import _bootstrap  # noqa: F401
from .schemas import AnnotationRecord, FutureSkillsExample, ReviewStatus
from forecasting.taxonomy.skill_dictionary import INITIAL_SKILLS


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Dataset file not found: {source}")

    records = []
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{source}:{line_number}: invalid JSON: {error}") from error
        if not isinstance(value, dict):
            raise ValueError(f"{source}:{line_number}: each JSONL record must be an object")
        records.append(value)
    return records


def _validate_training_data(path: str | Path, *, expected_split: str = "train") -> tuple[list[FutureSkillsExample], list[str]]:
    errors: list[str] = []
    examples: list[FutureSkillsExample] = []

    try:
        rows = _read_jsonl(path)
    except (OSError, ValueError) as error:
        return [], [str(error)]

    seen_ids: set[str] = set()
    seen_jobs: set[str] = set()
    taxonomy = {skill.skill_id: skill.canonical_name for skill in INITIAL_SKILLS}
    expected_roles = ["system", "user", "assistant"]

    for index, row in enumerate(rows, 1):
        try:
            example = FutureSkillsExample.model_validate(row)
        except ValidationError as error:
            errors.append(f"Training row {index}: schema validation failed: {error.error_count()} error(s)")
            continue

        if example.example_id in seen_ids:
            errors.append(f"Training row {index}: duplicate example_id {example.example_id}")
            continue
        seen_ids.add(example.example_id)
        if example.source_job_id:
            if example.source_job_id in seen_jobs:
                errors.append(f"Training row {index}: duplicate source_job_id {example.source_job_id}")
            seen_jobs.add(example.source_job_id)

        if example.split != expected_split:
            errors.append(f"Training row {index}: split must be '{expected_split}'")
        if example.human_review_status != ReviewStatus.REVIEWED:
            errors.append(f"Training row {index}: label is not human-reviewed")
        if example.labeling_method != "human_reviewed":
            errors.append(f"Training row {index}: labeling_method must be 'human_reviewed'")
        if not example.source_job_id:
            errors.append(f"Training row {index}: source_job_id provenance is missing")
        provenance = example.provenance
        if not provenance.get("reviewer"):
            errors.append(f"Training row {index}: human reviewer provenance is missing")
        if not example.source_record_ids:
            errors.append(f"Training row {index}: source_record_ids are missing")
        if not provenance.get("source_job_id"):
            errors.append(f"Training row {index}: provenance source_job_id is missing")
        elif str(provenance["source_job_id"]) != str(example.source_job_id):
            errors.append(f"Training row {index}: source_job_id does not match provenance")
        if not example.source_companies:
            errors.append(f"Training row {index}: source company provenance is missing")

        roles = [message.get("role") for message in example.messages]
        if roles != expected_roles:
            errors.append(f"Training row {index}: expected system/user/assistant messages in that order")
            continue

        try:
            target = json.loads(example.messages[-1].get("content", ""))
        except (TypeError, json.JSONDecodeError):
            errors.append(f"Training row {index}: assistant target is not valid JSON")
            continue

        if not isinstance(target, dict) or not isinstance(target.get("skills"), list) or not isinstance(target.get("unresolved_skills"), list):
            errors.append(f"Training row {index}: assistant target must contain skills and unresolved_skills lists")
            continue

        user_content = example.messages[1].get("content", "")
        if not isinstance(target, dict) or not isinstance(target.get("skills"), list) or not isinstance(target.get("unresolved_skills"), list):
            errors.append(f"Training row {index}: assistant target must contain skills and unresolved_skills lists")
            continue
        target_ids = []
        for skill in target["skills"]:
            if not isinstance(skill, dict):
                errors.append(f"Training row {index}: skill entry must be an object")
                continue
            name = skill.get("name")
            canonical_id = skill.get("canonical_id")
            evidence = skill.get("evidence")
            if not all(isinstance(value, str) and value.strip() for value in (name, canonical_id, evidence)):
                errors.append(f"Training row {index}: each skill needs non-empty name, canonical_id, and evidence")
                continue
            if evidence not in user_content:
                errors.append(f"Training row {index}: evidence is not an exact substring of the user message")
            expected_name = taxonomy.get(canonical_id)
            if expected_name is None:
                errors.append(f"Training row {index}: unsupported canonical skill ID {canonical_id}")
            elif name != expected_name:
                errors.append(f"Training row {index}: skill name does not match canonical taxonomy ID {canonical_id}")
            target_ids.append(canonical_id)

        if len(target_ids) != len(set(target_ids)):
            errors.append(f"Training row {index}: duplicate canonical skill IDs")
        if set(target_ids) != set(example.canonical_skill_ids):
            errors.append(f"Training row {index}: target skill IDs differ from canonical_skill_ids")
        examples.append(example)

    return examples, errors


def _validate_sft_data(path: str | Path, *, split: str) -> tuple[list[FutureSkillsExample], list[str]]:
    examples, errors = _validate_training_data(path, expected_split=split)
    errors = [error.replace("Training row", f"{split.title()} row") for error in errors]
    return examples, errors


def _source_job_ids(records: list[Any]) -> set[str]:
    return {str(record.source_job_id) for record in records if record.source_job_id}


def _companies(records: list[Any]) -> set[str]:
    values = set()
    for record in records:
        companies = getattr(record, "source_companies", [])
        company = getattr(record, "company", None)
        values.update(str(item) for item in companies if item)
        if company:
            values.add(str(company))
    return values


def _validate_gold_data(path: str | Path) -> tuple[list[AnnotationRecord], list[str]]:
    errors: list[str] = []
    records: list[AnnotationRecord] = []

    try:
        rows = _read_jsonl(path)
    except (OSError, ValueError) as error:
        return [], [str(error)]

    seen_ids: set[str] = set()
    seen_jobs: set[str] = set()
    taxonomy = {skill.skill_id: skill.canonical_name for skill in INITIAL_SKILLS}
    for index, row in enumerate(rows, 1):
        try:
            record = AnnotationRecord.model_validate(row)
        except ValidationError as error:
            errors.append(f"Gold row {index}: schema validation failed: {error.error_count()} error(s)")
            continue

        if record.example_id in seen_ids:
            errors.append(f"Gold row {index}: duplicate example_id {record.example_id}")
            continue
        seen_ids.add(record.example_id)
        if record.source_job_id in seen_jobs:
            errors.append(f"Gold row {index}: duplicate source_job_id {record.source_job_id}")
        seen_jobs.add(record.source_job_id)

        if record.reviewer_decision not in {ReviewStatus.REVIEWED, ReviewStatus.GOLD}:
            errors.append(
                f"Gold row {index}: reviewer_decision must be 'reviewed' or 'gold'"
            )
        if record.split != "test":
            errors.append(f"Gold row {index}: split must be 'test'")
        if not record.reviewer:
            errors.append(f"Gold row {index}: reviewer identity is missing")
        if not record.company:
            errors.append(f"Gold row {index}: company provenance is missing")
        if not record.provenance.get("source_record_ids"):
            errors.append(f"Gold row {index}: source_record_ids provenance is missing")
        if not record.provenance.get("source_job_id"):
            errors.append(f"Gold row {index}: provenance source_job_id is missing")
        elif str(record.provenance["source_job_id"]) != str(record.source_job_id):
            errors.append(f"Gold row {index}: source_job_id does not match provenance")
        output = record.corrected_output or record.proposed_output
        skills = output.get("skills", []) if isinstance(output, dict) else []
        ids = [skill.get("canonical_id") for skill in skills if isinstance(skill, dict)]
        if len(ids) != len(skills) or len(ids) != len(set(ids)) or set(ids) != set(record.canonical_skill_ids):
            errors.append(f"Gold row {index}: skill IDs do not match the reviewed canonical_skill_ids")
        for skill in skills:
            if not isinstance(skill, dict):
                continue
            canonical_id = skill.get("canonical_id")
            if canonical_id not in taxonomy:
                errors.append(f"Gold row {index}: unsupported canonical skill ID {canonical_id}")
            elif skill.get("name") != taxonomy[canonical_id]:
                errors.append(f"Gold row {index}: skill name does not match canonical taxonomy ID {canonical_id}")

        records.append(record)

    return records, errors


def training_gate(
    report_path: str | Path,
    *,
    training_data_path: str | Path = "future_skills/data/train_sft.jsonl",
    gold_data_path: str | Path = "future_skills/data/gold.jsonl",
    validation_data_path: str | Path = "future_skills/data/validation_sft.jsonl",
    minimum_reviewed_training_examples: int = 50,
    minimum_reviewed_validation_examples: int = 10,
    minimum_gold_evaluation_examples: int = 20,
) -> dict[str, object]:
    try:
        report = json.loads(Path(report_path).read_text(encoding="utf-8"))
        if not isinstance(report, dict):
            raise ValueError("Report must contain a JSON object")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        return {"status": "blocked", "reason": f"Cannot read annotation report: {error}"}

    training, training_errors = _validate_training_data(training_data_path)
    validation, validation_errors = _validate_sft_data(validation_data_path, split="validation")
    gold, gold_errors = _validate_gold_data(gold_data_path)
    errors = training_errors + validation_errors + gold_errors

    training_ids = {item.example_id for item in training}
    gold_ids = {item.example_id for item in gold}
    overlap = training_ids & gold_ids
    if overlap:
        errors.append(f"Training/gold ID overlap: {len(overlap)} example(s)")
    validation_ids = {item.example_id for item in validation}
    for name, left, right in (("training/validation", training_ids, validation_ids), ("validation/gold", validation_ids, gold_ids)):
        shared = left & right
        if shared:
            errors.append(f"{name.title()} ID overlap: {len(shared)} example(s)")
    for left_name, left, right_name, right in (
        ("training", training, "validation", validation),
        ("training", training, "gold", gold),
        ("validation", validation, "gold", gold),
    ):
        shared_jobs = _source_job_ids(left) & _source_job_ids(right)
        if shared_jobs:
            errors.append(f"{left_name}/{right_name} source_job_id overlap: {len(shared_jobs)} job(s)")
        shared_companies = _companies(left) & _companies(right)
        if shared_companies:
            errors.append(f"{left_name}/{right_name} company leakage: {sorted(shared_companies)}")
    if report.get("gold_overlaps_training"):
        errors.append("Annotation report flags gold/training overlap")

    warnings = []
    reported_training = int(report.get("reviewed_training_examples", report.get("human_reviewed", 0)))
    reported_gold = int(report.get("gold_evaluation_examples", report.get("gold_evaluation", 0)))
    if reported_training != len(training):
        warnings.append(
            f"Report says {reported_training} reviewed training examples; validated SFT file contains {len(training)}."
        )
    reported_validation = int(report.get("reviewed_validation_examples", 0))
    if reported_validation != len(validation):
        warnings.append(f"Report says {reported_validation} reviewed validation examples; validated SFT file contains {len(validation)}.")
    if reported_gold != len(gold):
        warnings.append(
            f"Report says {reported_gold} gold examples; validated gold file contains {len(gold)}."
        )

    if len(training) < minimum_reviewed_training_examples:
        errors.append(
            f"Need at least {minimum_reviewed_training_examples} valid reviewed training examples; found {len(training)}."
        )
    if len(validation) < minimum_reviewed_validation_examples:
        errors.append(f"Need at least {minimum_reviewed_validation_examples} valid reviewed validation examples; found {len(validation)}.")
    if len(gold) < minimum_gold_evaluation_examples:
        errors.append(
            f"Need at least {minimum_gold_evaluation_examples} separate gold evaluation examples; found {len(gold)}."
        )

    gold_readiness_errors = list(gold_errors)
    if len(gold) < minimum_gold_evaluation_examples:
        gold_readiness_errors.append(f"Need at least {minimum_gold_evaluation_examples} gold examples; found {len(gold)}.")
    if training_ids & gold_ids:
        gold_readiness_errors.append("Training/gold example ID overlap.")
    if _source_job_ids(training) & _source_job_ids(gold):
        gold_readiness_errors.append("Training/gold source_job_id overlap.")
    if _companies(training) & _companies(gold):
        gold_readiness_errors.append("Training/gold company leakage.")

    result: dict[str, object] = {
        "status": "blocked" if errors else "ready_for_gpu_runtime",
        "training_readiness": "blocked" if errors else "ready_for_training",
        "final_evaluation_readiness": "ready_for_final_evaluation" if not gold_readiness_errors else "blocked",
        "final_evaluation_errors": gold_readiness_errors,
        "training_examples": len(training),
        "validation_examples": len(validation),
        "gold_examples": len(gold),
        "split_companies": {"train": sorted(_companies(training)), "validation": sorted(_companies(validation)), "gold": sorted(_companies(gold))},
        "reported_training_examples": reported_training,
        "reported_gold_examples": reported_gold,
        "warnings": warnings,
        "errors": errors,
    }
    result["reason"] = (
        "; ".join(errors) if errors
        else "Training, validation, and gold JSONL files passed split checks; an NVIDIA GPU runtime is still required."
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Future Skills QLoRA training readiness.")
    parser.add_argument("--dataset-report", type=Path, default=Path("future_skills/data/annotation_report.json"))
    parser.add_argument("--training-data", type=Path, default=Path("future_skills/data/train_sft.jsonl"))
    parser.add_argument("--gold-data", type=Path, default=Path("future_skills/data/gold.jsonl"))
    parser.add_argument("--validation-data", type=Path, default=Path("future_skills/data/validation_sft.jsonl"))
    parser.add_argument("--min-reviewed-training", type=int, default=50)
    parser.add_argument("--min-gold-evaluation", type=int, default=20)
    parser.add_argument("--min-reviewed-validation", type=int, default=10)
    args = parser.parse_args()

    result = training_gate(
        args.dataset_report,
        training_data_path=args.training_data,
        gold_data_path=args.gold_data,
        validation_data_path=args.validation_data,
        minimum_reviewed_training_examples=args.min_reviewed_training,
        minimum_reviewed_validation_examples=args.min_reviewed_validation,
        minimum_gold_evaluation_examples=args.min_gold_evaluation,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["status"] != "blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())
