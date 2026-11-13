from __future__ import annotations

import argparse
import json
from pathlib import Path

from forecasting.engine.data import build_readiness_report, load_normalized_postings
from forecasting.engine.emerging import analyze_emerging_skills
from forecasting.engine.timeseries import build_skill_timeseries


def run(input_path: str | Path, output_dir: str | Path) -> dict:
    postings, mentions = load_normalized_postings(input_path)
    readiness = build_readiness_report(postings, mentions)
    monthly = build_skill_timeseries(postings, mentions, "month")
    emerging = analyze_emerging_skills(monthly)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(destination / "monthly_skill_demand.csv", index=False)
    emerging.to_csv(destination / "emerging_skills.csv", index=False)
    report = {
        "readiness": readiness,
        "forecast_support": {
            "status": "blocked" if readiness["status"] != "ready_for_backtesting" else "requires_backtesting",
            "supported_horizons_months": [],
            "models_implemented": ["moving_average", "seasonal_naive", "exponential_smoothing"],
            "evaluation": "not_run_on_production_data",
            "reason": "Insufficient reliable publication-date coverage and sparse periods; no future estimates are emitted.",
        },
        "timeseries": {
            "frequency": "month",
            "observations": len(monthly),
            "skills": int(monthly["skill_id"].nunique()) if not monthly.empty else 0,
            "missing_periods_not_filled": True,
        },
        "emerging_skill_summary": emerging.to_dict(orient="records"),
    }
    (destination / "forecast_readiness.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build auditable skill-demand readiness and descriptive reports.")
    parser.add_argument("--input", type=Path, default=Path("ml/skill-intelligence/data/job-postings/normalized/jobs.jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path("ml/skill-intelligence/data/job-postings/reports/forecasting"))
    args = parser.parse_args()
    print(json.dumps(run(args.input, args.output_dir), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
