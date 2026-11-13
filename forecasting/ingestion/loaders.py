import csv
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def load_source_records(path: str | Path) -> Iterator[dict[str, Any]]:
    """Yield source records without modifying the input file."""
    source = Path(path)
    if source.suffix.lower() == ".csv":
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            yield from csv.DictReader(handle)
        return
    if source.suffix.lower() == ".json":
        with source.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, list):
            yield from payload
        elif isinstance(payload, dict) and isinstance(payload.get("records"), list):
            yield from payload["records"]
        else:
            raise ValueError("JSON source must be a list of records or an object with a records list.")
        return
    raise ValueError(f"Unsupported source format: {source.suffix or 'missing extension'}; use CSV or JSON.")
