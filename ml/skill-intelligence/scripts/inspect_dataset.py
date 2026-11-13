from __future__ import annotations

import json
from pathlib import Path

from _bootstrap import ROOT


def main() -> int:
    data_root = ROOT / "data"
    files = [str(path.relative_to(ROOT)) for path in data_root.rglob("*") if path.is_file() and path.name != ".gitkeep"]
    report = {
        "status": "available" if files else "unavailable",
        "files": files,
        "message": "No genuine dataset files found; synthetic fixtures are excluded." if not files else "Inspect provenance before preparation.",
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
