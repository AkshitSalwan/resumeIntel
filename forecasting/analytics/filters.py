from collections.abc import Iterable

from forecasting.schemas.job_posting import JobPosting
from forecasting.schemas.skill import SkillMention


def filter_postings(
    postings: Iterable[JobPosting],
    *,
    industry: str | None = None,
    region: str | None = None,
) -> list[JobPosting]:
    return [
        posting for posting in postings
        if (industry is None or posting.industry == industry)
        and (region is None or posting.region == region)
    ]
