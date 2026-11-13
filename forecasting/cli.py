import argparse
import json
from pathlib import Path

from forecasting.pipelines.pipeline import export_result, process_source
from forecasting.reports.eda_report import add_visualizations, build_eda_report, write_eda_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Process historical job-market source data.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    process = subparsers.add_parser("process", help="Validate, clean, deduplicate, normalize, aggregate, and export a source.")
    process.add_argument("input", type=Path, help="CSV or JSON source file.")
    process.add_argument("--source-id", help="Stable source registry identifier.")
    process.add_argument("--output-dir", type=Path, required=True)
    process.add_argument("--format", choices=("parquet", "csv"), default="parquet")
    eda = subparsers.add_parser("eda", help="Generate data-driven EDA and readiness reports.")
    eda.add_argument("--input", type=Path, help="Genuine CSV or JSON source. Omit only to document unavailable data.")
    eda.add_argument("--report", type=Path, default=Path("docs/phase-2b-eda-report.md"))
    eda.add_argument("--json-report", type=Path, default=Path("forecasting/data/exports/phase-2b-eda.json"))
    eda.add_argument("--charts-dir", type=Path, default=Path("forecasting/data/exports/phase-2b-charts"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "process":
        result = process_source(args.input, source_id=args.source_id)
        export_result(result, args.output_dir, format=args.format)
        print(json.dumps(result["quality_report"], indent=2))
    elif args.command == "eda":
        result = process_source(args.input) if args.input else {"postings": [], "mentions": [], "quality_report": {
            "records_received": 0, "valid_records": 0, "rejected_records": 0, "duplicate_records": 0,
            "missing_posting_dates": 0, "missing_job_descriptions": 0, "missing_locations": 0,
        }}
        report = build_eda_report(result["postings"], result["mentions"], result["quality_report"])
        add_visualizations(report, args.charts_dir)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        write_eda_report(report, args.report)
        args.json_report.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"dataset_status": report["dataset_status"], "report": str(args.report), "visualizations": report.get("visualizations", [])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
