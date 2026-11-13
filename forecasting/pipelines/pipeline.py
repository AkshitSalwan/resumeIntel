import json
from pathlib import Path
from typing import Any

import pandas as pd

from forecasting.analytics.demand_aggregation import aggregate_skill_demand
from forecasting.ingestion.loaders import load_source_records
from forecasting.preprocessing.cleaning import clean_record
from forecasting.preprocessing.deduplication import deduplicate_postings
from forecasting.reports.quality import build_quality_report
from forecasting.taxonomy.skill_dictionary import INITIAL_SKILLS
from forecasting.taxonomy.skill_normalizer import SkillNormalizer


def process_source(path: str | Path, source_id: str | None = None) -> dict[str, Any]:
    records = list(load_source_records(path))
    valid = []
    rejected: list[dict[str, str]] = []
    for index, record in enumerate(records):
        try:
            valid.append(clean_record(record, source_id=source_id))
        except (TypeError, ValueError) as error:
            rejected.append({"record_index": str(index), "reason": str(error)})
    deduped = deduplicate_postings(valid)
    normalizer = SkillNormalizer(INITIAL_SKILLS)
    mentions = [
        mention
        for posting in deduped.unique
        for mention in normalizer.extract(posting.id, posting.job_description)
    ]
    report = build_quality_report(len(records), deduped.unique, rejected, deduped.duplicates, mentions)
    return {
        "postings": deduped.unique,
        "mentions": mentions,
        "demand": aggregate_skill_demand(deduped.unique, mentions),
        "quality_report": report,
    }


def export_result(result: dict[str, Any], output_dir: str | Path, format: str = "parquet") -> None:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    postings = pd.DataFrame([posting.model_dump(mode="json") for posting in result["postings"]])
    mentions = pd.DataFrame([mention.model_dump() for mention in result["mentions"]])
    demand = result["demand"]
    for name, frame in (("postings", postings), ("skill_mentions", mentions), ("skill_demand", demand)):
        if format == "parquet":
            try:
                frame.to_parquet(destination / f"{name}.parquet", index=False)
            except ImportError as error:
                raise RuntimeError("Parquet export requires an optional parquet engine such as pyarrow; use --format csv or install pyarrow.") from error
        elif format == "csv":
            frame.to_csv(destination / f"{name}.csv", index=False)
        else:
            raise ValueError("format must be parquet or csv")
    (destination / "quality_report.json").write_text(json.dumps(result["quality_report"], indent=2), encoding="utf-8")
