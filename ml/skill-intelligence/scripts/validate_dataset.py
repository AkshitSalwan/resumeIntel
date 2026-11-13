from __future__ import annotations

import json
from pathlib import Path

from _bootstrap import ROOT
from src.validation import validate_chat_record


def main() -> int:
    processed = ROOT / "data" / "processed"
    failures: list[str] = []
    counts: dict[str, int] = {}
    for path in sorted(processed.glob("*.jsonl")):
        count = 0
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                validate_chat_record(json.loads(line))
                count += 1
            except (json.JSONDecodeError, ValueError) as error:
                failures.append(f"{path.name}:{line_number}: {error}")
        counts[path.name] = count
    result = {"valid": not failures, "counts": counts, "failures": failures}
    print(json.dumps(result, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
