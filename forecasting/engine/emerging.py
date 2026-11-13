from __future__ import annotations

import pandas as pd


def analyze_emerging_skills(
    timeseries: pd.DataFrame,
    *,
    minimum_postings: int = 3,
    minimum_companies: int = 2,
    minimum_persistent_periods: int = 3,
) -> pd.DataFrame:
    columns = ["skill_id", "skill_name", "classification", "recent_growth", "total_postings", "company_count", "source_count", "persistent_periods"]
    if timeseries.empty:
        return pd.DataFrame(columns=columns)
    rows: list[dict[str, object]] = []
    for (skill_id, skill_name), group in timeseries.groupby(["skill_id", "skill_name"]):
        ordered = group.sort_values("period")
        recent = float(ordered["demand_share"].iloc[-1] - ordered["demand_share"].iloc[max(0, len(ordered) - 3)])
        total = int(ordered["postings_requiring_skill"].sum())
        companies = int(ordered["company_count"].max())
        sources = int(ordered["source_count"].max())
        persistent = int((ordered["postings_requiring_skill"] > 0).sum())
        if total < minimum_postings or companies < minimum_companies or persistent < minimum_persistent_periods:
            classification = "insufficient-data"
        elif recent > 0 and persistent >= 2:
            classification = "rapidly-growing" if recent >= 0.10 else "emerging"
        elif recent < 0:
            classification = "declining"
        else:
            classification = "established"
        rows.append({"skill_id": skill_id, "skill_name": skill_name, "classification": classification, "recent_growth": recent, "total_postings": total, "company_count": companies, "source_count": sources, "persistent_periods": persistent})
    return pd.DataFrame(rows, columns=columns).sort_values(["classification", "recent_growth"], ascending=[True, False]).reset_index(drop=True)
