from collections.abc import Iterable

import pandas as pd

from forecasting.analytics.demand_aggregation import aggregate_skill_demand
from forecasting.schemas.job_posting import JobPosting
from forecasting.schemas.skill import SkillMention


def temporal_skill_demand(
    postings: Iterable[JobPosting],
    mentions: Iterable[SkillMention],
    frequency: str = "year",
) -> pd.DataFrame:
    """Return descriptive historical demand and period-over-period changes."""
    demand = aggregate_skill_demand(postings, mentions, frequency)
    if demand.empty:
        return demand.assign(absolute_change=pd.Series(dtype="float64"), percentage_change=pd.Series(dtype="float64"))
    demand = demand.sort_values(["skill_id", "period"]).copy()
    demand["absolute_change"] = demand.groupby("skill_id")["demand_percentage"].diff()
    demand["percentage_change"] = demand.groupby("skill_id")["demand_percentage"].pct_change() * 100
    return demand.reset_index(drop=True)


def demand_consistency(trends: pd.DataFrame) -> pd.DataFrame:
    if trends.empty:
        return pd.DataFrame(columns=["skill_id", "observed_periods", "mean_demand", "demand_std", "consistent_across_periods"])
    result = trends.groupby("skill_id")["demand_percentage"].agg(
        observed_periods="count", mean_demand="mean", demand_std="std"
    ).reset_index()
    result["demand_std"] = result["demand_std"].fillna(0)
    result["consistent_across_periods"] = result["observed_periods"] >= 2
    return result
