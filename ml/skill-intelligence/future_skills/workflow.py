from __future__ import annotations

import argparse
import json
from pathlib import Path

from .annotation import (
    export_candidates,
    ai_pre_review_validation,
    export_ai_assisted_data,
    export_csv,
    export_gold,
    export_training_data,
    load_annotations,
    load_examples,
    _safe_write,
    quality_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Future Skills annotation and gold-data workflow.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export-annotations")
    export_parser.add_argument("--candidates", type=Path, default=Path("future_skills/data/train.jsonl"))
    export_parser.add_argument("--output", type=Path, default=Path("future_skills/data/annotations.jsonl"))
    export_parser.add_argument("--csv", type=Path)

    training_parser = subparsers.add_parser("export-training")
    training_parser.add_argument("--candidates", type=Path, default=Path("future_skills/data/train.jsonl"))
    training_parser.add_argument("--annotations", type=Path, default=Path("future_skills/data/train_reviews.jsonl"))
    training_parser.add_argument("--output", type=Path, default=Path("future_skills/data/train_sft.jsonl"))

    validation_parser = subparsers.add_parser("export-validation")
    validation_parser.add_argument("--candidates", type=Path, default=Path("future_skills/data/validation.jsonl"))
    validation_parser.add_argument("--annotations", type=Path, default=Path("future_skills/data/validation_annotations.jsonl"))
    validation_parser.add_argument("--output", type=Path, default=Path("future_skills/data/validation_sft.jsonl"))
    validation_parser.add_argument("--training", type=Path, default=Path("future_skills/data/train_sft.jsonl"))
    validation_parser.add_argument("--gold", type=Path, default=Path("future_skills/data/gold.jsonl"))

    ai_review_parser = subparsers.add_parser("ai-pre-review-validation")
    ai_review_parser.add_argument("--candidates", type=Path, default=Path("future_skills/data/validation.jsonl"))
    ai_review_parser.add_argument("--annotations", type=Path, default=Path("future_skills/data/validation_annotations.jsonl"))
    ai_review_parser.add_argument("--system-id", default="codex-ai-assistant (model identifier unavailable)")

    ai_export_parser = subparsers.add_parser("export-validation-ai")
    ai_export_parser.add_argument("--candidates", type=Path, default=Path("future_skills/data/validation.jsonl"))
    ai_export_parser.add_argument("--annotations", type=Path, default=Path("future_skills/data/validation_annotations.jsonl"))
    ai_export_parser.add_argument("--output", type=Path, default=Path("future_skills/data/validation_ai_sft.jsonl"))
    ai_export_parser.add_argument("--training", type=Path, default=Path("future_skills/data/train_sft.jsonl"))
    ai_export_parser.add_argument("--gold", type=Path, default=Path("future_skills/data/gold.jsonl"))

    review_parser = subparsers.add_parser("review")
    review_parser.add_argument("--candidates", type=Path, default=Path("future_skills/data/validation.jsonl"))
    review_parser.add_argument("--annotations", type=Path, default=Path("future_skills/data/validation_annotations.jsonl"))
    review_parser.add_argument(
        "--candidate-id",
        action="append",
        dest="candidate_ids",
        help="Review only this candidate ID; may be supplied multiple times. Explicitly selected AI-assisted records are eligible for human review.",
    )

    gold_parser = subparsers.add_parser("export-gold")
    gold_parser.add_argument("--annotations", type=Path, default=Path("future_skills/data/annotations.jsonl"))
    gold_parser.add_argument("--output", type=Path, default=Path("future_skills/data/gold.jsonl"))
    gold_parser.add_argument("--training", type=Path, default=Path("future_skills/data/train.jsonl"))
    gold_parser.add_argument("--validation", type=Path, default=Path("future_skills/data/validation.jsonl"))
    gold_parser.add_argument("--candidates", type=Path, default=Path("future_skills/data/test.jsonl"))

    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--candidates", type=Path, default=Path("future_skills/data/train.jsonl"))
    report_parser.add_argument("--annotations", type=Path, default=Path("future_skills/data/annotations.jsonl"))
    report_parser.add_argument("--output", type=Path, default=Path("future_skills/data/annotation_report.json"))
    report_parser.add_argument("--gold", type=Path)
    report_parser.add_argument("--training", type=Path)
    report_parser.add_argument("--validation", type=Path)

    args = parser.parse_args()
    if args.command == "export-annotations":
        count = export_candidates(args.candidates, args.output)
        if args.csv:
            export_csv(args.output, args.csv)
        print(json.dumps({"exported_candidates": count, "output": str(args.output)}))
        return 0
    if args.command == "export-training":
        result = export_training_data(args.candidates, args.annotations, args.output)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "export-validation":
        train_rows = load_examples(args.training)
        gold_rows = load_annotations(args.gold) if args.gold.exists() else {}
        train_keys = {value for row in train_rows for value in (row.example_id, row.source_job_id) if value}
        gold_keys = {value for row in gold_rows.values() for value in (row.example_id, row.source_job_id) if value}
        result = export_training_data(args.candidates, args.annotations, args.output, split="validation", excluded_ids=train_keys | gold_keys)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "ai-pre-review-validation":
        result = ai_pre_review_validation(args.candidates, args.annotations, system_id=args.system_id)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "export-validation-ai":
        train_rows = load_examples(args.training)
        gold_rows = load_annotations(args.gold) if args.gold.exists() else {}
        excluded_ids = {value for row in train_rows for value in (row.example_id, row.source_job_id) if value}
        excluded_ids.update(value for row in gold_rows.values() for value in (row.example_id, row.source_job_id) if value)
        excluded_companies = {company for row in train_rows for company in row.source_companies if company}
        excluded_companies.update(row.company for row in gold_rows.values() if row.company)
        result = export_ai_assisted_data(args.candidates, args.annotations, args.output, excluded_ids=excluded_ids, excluded_companies=excluded_companies)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "review":
        from .annotate import review
        try:
            review(args.candidates, args.annotations, candidate_ids=args.candidate_ids)
        except ValueError as error:
            parser.error(str(error))
        return 0
    if args.command == "export-gold":
        training_ids = {example.example_id for example in load_examples(args.training)}
        validation_ids = {example.example_id for example in load_examples(args.validation)} if args.validation.exists() else set()
        candidate_ids = {example.example_id for example in load_examples(args.candidates)} if args.candidates.exists() else None
        result = export_gold(args.annotations, args.output, training_ids=training_ids, validation_ids=validation_ids, candidate_ids=candidate_ids)
        print(json.dumps(result, indent=2))
        return 0
    result = quality_report(args.annotations, len(load_examples(args.candidates)), split="train" if "train" in args.candidates.name else None)
    if args.gold and args.gold.exists():
        result["gold_evaluation_examples"] = sum(1 for line in args.gold.read_text(encoding="utf-8").splitlines() if line.strip())
    if args.training and args.gold and args.gold.exists():
        training_ids = {example.example_id for example in load_examples(args.training)}
        gold_ids = {json.loads(line)["example_id"] for line in args.gold.read_text(encoding="utf-8").splitlines() if line.strip()}
        result["gold_overlaps_training"] = bool(training_ids & gold_ids)
    if args.validation and args.validation.exists() and args.gold and args.gold.exists():
        validation_ids = {example.example_id for example in load_examples(args.validation)}
        gold_ids = {json.loads(line)["example_id"] for line in args.gold.read_text(encoding="utf-8").splitlines() if line.strip()}
        result["gold_overlaps_validation"] = bool(validation_ids & gold_ids)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    _safe_write(args.output, json.dumps(result, indent=2), backup_suffix=".before-report-refresh.bak")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
