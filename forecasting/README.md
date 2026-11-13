# Historical job-market data engineering

This package is an isolated Phase 2A foundation for ResumeIntel. It processes
manually acquired CSV or JSON job-posting datasets into validated canonical
postings, auditable skill mentions, historical demand aggregates, and quality
reports. It does **not** forecast, train a model, call an LLM, or write to
Supabase.

## Setup

From the repository root:

```bash
.venv/bin/pip install -r requirements.txt
```

The package targets Python 3.11+ and uses Pydantic for contracts, pandas for
aggregation, and Parquet or CSV for exports. Parquet requires an optional
engine such as `pyarrow`; CSV remains available without that native dependency.

## Run

```bash
.venv/bin/python -m forecasting.cli process path/to/jobs.csv \
  --source-id kaggle-example \
  --output-dir forecasting/data/processed/example \
  --format parquet
```

The output contains `postings`, `skill_mentions`, `skill_demand`, and a
machine-readable `quality_report.json`. Original source files are never
overwritten. Invalid records and deduplication decisions are retained in the
quality report.

## Exploratory analysis

Generate the Phase 2B report from a genuine source without mixing in unit
fixtures:

```bash
.venv/bin/python -m forecasting.cli eda \
  --input path/to/jobs.csv \
  --report docs/phase-2b-eda-report.md \
  --json-report forecasting/data/exports/phase-2b-eda.json \
  --charts-dir forecasting/data/exports/phase-2b-charts
```

Omit `--input` to generate an explicit unavailable-data report. Charts are
created only when genuine postings are present. Role grouping uses the
documented deterministic rules in `forecasting/docs/role-mapping.md`.

## Data semantics

Demand percentage is calculated per period and cohort:

`postings requiring skill / eligible dated postings * 100`

Postings without a posting date are retained in the canonical output and
reported as missing, but excluded from time-based aggregates rather than being
assigned to an arbitrary period. Each posting contributes at most once per
skill. These are historical descriptive metrics, not predictions or growth
claims.

The initial taxonomy is versioned and extensible in
`forecasting/taxonomy/skill_dictionary.py`. Dictionary extraction records
matched text and evidence; it does not claim semantic completeness and should
be replaced or supplemented by reviewed extraction methods later.

## Forecasting readiness and models

Build an auditable report from the public ATS collection:

```bash
.venv/bin/python -m forecasting.scripts.run_forecast_audit
```

This writes the monthly skill-demand observations, emerging-skill analysis, and
readiness report under
`ml/skill-intelligence/data/job-postings/reports/forecasting/`. The report
excludes source-update timestamps and collection timestamps from historical
demand, preserves missing periods, and blocks future estimates when reliable
publication-date coverage is insufficient. Moving-average, seasonal-naive, and
exponential-smoothing implementations plus chronological rolling-origin
evaluation are available in `forecasting/engine/`; they do not use Qwen or an
LLM for numeric forecasts.
