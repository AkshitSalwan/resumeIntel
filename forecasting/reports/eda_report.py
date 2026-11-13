from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import pandas as pd

from forecasting.analytics.cooccurrence import skill_cooccurrence
from forecasting.analytics.coverage import coverage_analysis
from forecasting.analytics.distributions import skill_distribution
from forecasting.analytics.roles import role_assignments
from forecasting.analytics.trends import temporal_skill_demand
from forecasting.analytics.visualizations import generate_visualizations
from forecasting.reports.readiness import forecasting_readiness
from forecasting.schemas.job_posting import JobPosting
from forecasting.schemas.skill import SkillMention


def build_eda_report(
    postings: list[JobPosting],
    mentions: list[SkillMention],
    quality: dict[str, Any],
    source_inventory: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    coverage = coverage_analysis(postings, mentions, source_inventory)
    trends = temporal_skill_demand(postings, mentions, frequency="year")
    roles = role_assignments(postings)
    cooccurrence = skill_cooccurrence(mentions, len(postings))
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_status": "available" if postings else "unavailable",
        "coverage": coverage,
        "quality": quality,
        "role_assignments": {key: len(value) for key, value in roles.items()},
        "annual_skill_demand": trends.to_dict(orient="records"),
        "skill_distribution": skill_distribution(postings, mentions).to_dict(orient="records"),
        "industry_skill_distribution": {
            str(industry): skill_distribution(postings, mentions, industry=industry).to_dict(orient="records")
            for industry in sorted({item.industry for item in postings if item.industry})
        },
        "region_skill_distribution": {
            str(region): skill_distribution(postings, mentions, region=region).to_dict(orient="records")
            for region in sorted({item.region for item in postings if item.region})
        },
        "skill_cooccurrence": cooccurrence.to_dict(orient="records"),
        "readiness": forecasting_readiness(coverage, quality, {key: len(value) for key, value in roles.items()}),
    }


def render_markdown(report: dict[str, Any]) -> str:
    if report["dataset_status"] == "unavailable":
        return """# Phase 2B — Exploratory Data Analysis\n\n## Executive summary\n\nNo genuine historical job-market dataset is present in the repository. The `forecasting/data/` directories contain only placeholders, so no historical findings, trends, rankings, or visualizations are reported.\n\n## Dataset inventory\n\n- Research datasets analyzed: **none**.\n- Synthetic unit fixtures: excluded from research analysis.\n- Sources researched but not integrated: see [source registry](../forecasting/docs/source-registry.md).\n\n## Forecasting readiness\n\n**Not ready for forecasting.** Acquire and register a permitted posting-level dataset before interpreting historical demand or producing charts. The EDA modules and report generator are implemented and will remain data-driven when a real dataset is imported.\n\n## Next steps\n\n1. Import a permitted dataset through the Phase 2A CLI.\n2. Record source identifier, license, collection date, historical period, and geography.\n3. Run the EDA command against the processed output.\n4. Review missingness, source imbalance, role coverage, and temporal continuity before any Phase 3 modeling.\n"""
    coverage = report["coverage"]
    return "\n".join([
        "# Phase 2B — Exploratory Data Analysis",
        "",
        "## Executive summary",
        "",
        f"Analysis covers **{coverage['total_job_postings']}** genuine postings from **{coverage['earliest_posting_date']}** through **{coverage['latest_posting_date']}**. These are descriptive historical metrics, not predictions.",
        "",
        "## Dataset coverage",
        "",
        f"- Unique companies: {coverage['unique_companies']}",
        f"- Unique job titles: {coverage['unique_job_titles']}",
        f"- Normalized skills observed: {coverage['unique_normalized_skills']}",
        f"- Industries: {coverage['industries']}",
        f"- Geographic regions: {coverage['geographic_regions']}",
        f"- Postings by year: `{coverage['postings_by_year']}`",
        "",
        "## Data-quality assessment",
        "",
        f"- Missing posting dates: {report['quality'].get('missing_posting_dates', 0)}",
        f"- Missing descriptions: {report['quality'].get('missing_job_descriptions', 0)}",
        f"- Duplicate records: {report['quality'].get('duplicate_records', 0)}",
        "",
        "## Forecasting readiness",
        "",
        f"- Overall: **{report['readiness']['dimensions']['overall']}**",
        "- Readiness labels are rule-based and are not a confidence score.",
        "",
    ])


def write_eda_report(report: dict[str, Any], path: str | Path) -> None:
    Path(path).write_text(render_markdown(report), encoding="utf-8")


def add_visualizations(report: dict[str, Any], output_dir: str | Path) -> list[str]:
    trends = pd.DataFrame(report["annual_skill_demand"])
    cooccurrence = pd.DataFrame(report["skill_cooccurrence"])
    paths = generate_visualizations(report["coverage"], trends, cooccurrence, output_dir)
    report["visualizations"] = paths
    return paths
