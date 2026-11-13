from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from forecasting.schemas.job_posting import JobPosting
from forecasting.schemas.skill import SkillMention


def build_skill_timeseries(
    postings: Iterable[JobPosting],
    mentions: Iterable[SkillMention],
    frequency: str = "month",
) -> pd.DataFrame:
    if frequency not in {"week", "month"}:
        raise ValueError("frequency must be week or month")
    dated = [item for item in postings if item.posting_date is not None]
    periods = [pd.Period(item.posting_date, freq="W-MON" if frequency == "week" else "M").start_time.date().isoformat() for item in dated]
    if not dated:
        return pd.DataFrame(columns=["period", "skill_id", "skill_name", "postings_requiring_skill", "eligible_postings", "demand_share", "company_count", "source_count"])
    posting_frame = pd.DataFrame({"posting_id": [item.id for item in dated], "period": periods, "company": [item.company_name for item in dated], "source": [item.source_id for item in dated]})
    mention_frame = pd.DataFrame([item.model_dump() for item in mentions])
    if mention_frame.empty:
        return pd.DataFrame(columns=["period", "skill_id", "skill_name", "postings_requiring_skill", "eligible_postings", "demand_share", "company_count", "source_count"])
    joined = mention_frame[["posting_id", "skill_id", "canonical_name"]].drop_duplicates(["posting_id", "skill_id"]).merge(posting_frame, on="posting_id", how="inner")
    denominator = posting_frame.groupby("period")["posting_id"].nunique().rename("eligible_postings")
    result = joined.groupby(["period", "skill_id", "canonical_name"]).agg(
        postings_requiring_skill=("posting_id", "nunique"),
        company_count=("company", "nunique"),
        source_count=("source", "nunique"),
    ).reset_index()
    result["eligible_postings"] = result["period"].map(denominator)
    result["demand_share"] = result["postings_requiring_skill"] / result["eligible_postings"]
    return result.rename(columns={"canonical_name": "skill_name"}).sort_values(["skill_id", "period"]).reset_index(drop=True)
