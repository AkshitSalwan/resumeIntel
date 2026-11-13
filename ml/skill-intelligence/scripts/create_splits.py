from __future__ import annotations

import json
from pathlib import Path

from _bootstrap import ROOT


def main() -> int:
    report_path = ROOT / "data" / "processed" / "dataset_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {"labeled_examples": 0}
    result = {
        "status": "unavailable" if not report.get("labeled_examples") else "pending",
        "strategy": "temporal when posting dates are sufficient; otherwise deterministic grouped split",
        "leakage_group": "source posting or company where available",
        "split_sizes": {"train": 0, "validation": 0, "test": 0},
    }
    path = ROOT / "data" / "processed" / "split_report.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
