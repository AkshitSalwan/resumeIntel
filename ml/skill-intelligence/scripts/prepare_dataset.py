from __future__ import annotations

import json
from pathlib import Path

from _bootstrap import ROOT
from src.data import to_chat_record


def main() -> int:
    output = ROOT / "data" / "processed"
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "unavailable",
        "genuine_postings": 0,
        "labeled_examples": 0,
        "weak_label_count": 0,
        "human_reviewed_label_count": 0,
        "unique_canonical_skills": 0,
        "unresolved_skill_count": 0,
        "duplicate_count": 0,
        "message": "No genuine Phase 2A output is available. No training records were generated.",
    }
    (output / "dataset_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for split in ("train", "validation", "test"):
        (output / f"{split}.jsonl").write_text("", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
