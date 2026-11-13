from collections.abc import Iterable

import pandas as pd

from forecasting.schemas.job_posting import JobPosting
from forecasting.schemas.skill import SkillMention


def aggregate_skill_demand(
    postings: Iterable[JobPosting],
    mentions: Iterable[SkillMention],
    frequency: str = "month",
) -> pd.DataFrame:
    """Aggregate historical demand; postings without dates are excluded, not assigned to a period."""
    if frequency not in {"month", "quarter", "year"}:
        raise ValueError("frequency must be month, quarter, or year")
    dated = [posting for posting in postings if posting.posting_date is not None]
    posting_frame = pd.DataFrame([
        {
            "posting_id": posting.id,
            "period": pd.Period(posting.posting_date, freq={"month": "M", "quarter": "Q", "year": "Y"}[frequency]).start_time.date().isoformat(),
            "industry": posting.industry,
            "region": posting.region,
            "normalized_job_title": posting.normalized_job_title,
        }
        for posting in dated
    ])
    if posting_frame.empty:
        return pd.DataFrame(columns=["period", "skill_id", "skill_name", "postings_requiring_skill", "eligible_postings", "demand_percentage", "industry", "region"])
    mention_frame = pd.DataFrame([mention.model_dump() for mention in mentions])
    if mention_frame.empty:
        return pd.DataFrame(columns=["period", "skill_id", "skill_name", "postings_requiring_skill", "eligible_postings", "demand_percentage", "industry", "region"])
    joined = mention_frame[["posting_id", "skill_id", "canonical_name"]].drop_duplicates(["posting_id", "skill_id"]).merge(posting_frame, on="posting_id", how="inner")
    denominator = posting_frame.groupby(["period", "industry", "region"], dropna=False)["posting_id"].nunique().rename("eligible_postings").reset_index()
    numerator = joined.groupby(["period", "skill_id", "canonical_name", "industry", "region"], dropna=False)["posting_id"].nunique().rename("postings_requiring_skill").reset_index()
    result = numerator.merge(denominator, on=["period", "industry", "region"], how="left")
    result["demand_percentage"] = result["postings_requiring_skill"] / result["eligible_postings"] * 100
    return result.rename(columns={"canonical_name": "skill_name"}).sort_values(["period", "skill_id"]).reset_index(drop=True)
