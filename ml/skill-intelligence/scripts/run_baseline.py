from __future__ import annotations

import json
from pathlib import Path

from _bootstrap import ROOT


def main() -> int:
    result = {
        "status": "unavailable",
        "model": "Qwen/Qwen3-4B-Instruct-2507",
        "gold_examples": 0,
        "message": "No human-reviewed gold evaluation set is available; base-model inference was not run.",
    }
    output = ROOT / "artifacts" / "evaluation"
    output.mkdir(parents=True, exist_ok=True)
    (output / "base_model_metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
