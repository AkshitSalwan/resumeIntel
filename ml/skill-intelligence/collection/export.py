from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import NormalizedJob


def export_jobs(jobs: list[NormalizedJob], report: dict, output_root: str | Path) -> list[str]:
    root = Path(output_root)
    normalized = root / "normalized"
    reports = root / "reports"
    normalized.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    jsonl = normalized / "jobs.jsonl"
    jsonl.write_text("\n".join(job.model_dump_json() for job in jobs) + ("\n" if jobs else ""), encoding="utf-8")
    paths.append(str(jsonl))
    csv_path = normalized / "jobs.csv"
    fields = list(NormalizedJob.model_fields)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for job in jobs:
            row = job.model_dump(mode="json")
            row["source_metadata"] = json.dumps(row["source_metadata"], ensure_ascii=False)
            row["compensation"] = json.dumps(row["compensation"], ensure_ascii=False)
            writer.writerow(row)
    paths.append(str(csv_path))
    try:
        import pandas as pd
        pd.DataFrame([job.model_dump(mode="json") for job in jobs]).to_parquet(root / "normalized" / "jobs.parquet", index=False)
        paths.append(str(root / "normalized" / "jobs.parquet"))
    except (ImportError, ValueError):
        pass
    report_path = reports / "collection_quality.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    paths.append(str(report_path))
    return paths
