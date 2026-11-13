from collections.abc import Iterable

import pandas as pd

from forecasting.schemas.job_posting import JobPosting
from forecasting.schemas.skill import SkillMention


def skill_distribution(
    postings: Iterable[JobPosting],
    mentions: Iterable[SkillMention],
    *,
    industry: str | None = None,
    region: str | None = None,
) -> pd.DataFrame:
    posting_frame = pd.DataFrame([
        {
            "posting_id": posting.id,
            "industry": posting.industry,
            "region": posting.region,
            "role": posting.normalized_job_title or posting.job_title,
        }
        for posting in postings
        if (industry is None or posting.industry == industry)
        and (region is None or posting.region == region)
    ])
    if posting_frame.empty:
        return pd.DataFrame(columns=["skill_id", "skill_name", "occurrences", "postings_requiring_skill", "demand_percentage", "job_roles", "industries", "regions"])
    mention_frame = pd.DataFrame([mention.model_dump() for mention in mentions])
    if mention_frame.empty:
        return pd.DataFrame(columns=["skill_id", "skill_name", "occurrences", "postings_requiring_skill", "demand_percentage", "job_roles", "industries", "regions"])
    joined = mention_frame[["posting_id", "skill_id", "canonical_name"]].drop_duplicates(["posting_id", "skill_id"]).merge(posting_frame, on="posting_id", how="inner")
    result = joined.groupby(["skill_id", "canonical_name"], as_index=False).agg(
        occurrences=("skill_id", "size"),
        postings_requiring_skill=("posting_id", "nunique"),
        job_roles=("role", "nunique"),
        industries=("industry", "nunique"),
        regions=("region", "nunique"),
    )
    result["demand_percentage"] = result["postings_requiring_skill"] / posting_frame["posting_id"].nunique() * 100
    return result.rename(columns={"canonical_name": "skill_name"}).sort_values("demand_percentage", ascending=False).reset_index(drop=True)
