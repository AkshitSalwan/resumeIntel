from __future__ import annotations

import argparse
import json
from pathlib import Path

from .data import build_candidate_examples, split_by_company, write_jsonl
from .validation import validate_dataset


def prepare(input_path: str | Path, output_dir: str | Path) -> dict:
    examples = build_candidate_examples(input_path)
    splits = split_by_company(examples)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    for split, items in splits.items():
        write_jsonl(items, output / f"{split}.jsonl")
    report = {"status": "candidate_labels_only", "dataset_version": "weak-dictionary-v1", "total": len(examples), "splits": {key: len(value) for key, value in splits.items()}, "validation": validate_dataset(examples), "human_reviewed": 0, "gold_evaluation": 0, "future_outcome_training": "disabled_insufficient_historical_outcomes"}
    (output / "dataset_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Future Skills candidate datasets.")
    parser.add_argument("--input", type=Path, default=Path("ml/skill-intelligence/data/job-postings/normalized/jobs.jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path("ml/skill-intelligence/future-skills/data"))
    args = parser.parse_args()
    print(json.dumps(prepare(args.input, args.output_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
