from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    location = Path(path or Path(__file__).resolve().parents[2] / "config" / "training.json")
    return json.loads(location.read_text(encoding="utf-8"))
