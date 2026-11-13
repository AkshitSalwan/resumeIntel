from collections import Counter
from itertools import combinations
from typing import Any

import pandas as pd

from forecasting.schemas.skill import SkillMention


def skill_cooccurrence(mentions: list[SkillMention], eligible_postings: int | None = None) -> pd.DataFrame:
    by_posting: dict[str, set[str]] = {}
    names: dict[str, str] = {}
    for mention in mentions:
        by_posting.setdefault(mention.posting_id, set()).add(mention.skill_id)
        names[mention.skill_id] = mention.canonical_name
    total = eligible_postings or len(by_posting)
    if not by_posting or total == 0:
        return pd.DataFrame(columns=["skill_a", "skill_b", "skill_a_name", "skill_b_name", "cooccurrence_count", "support", "confidence_a_to_b", "confidence_b_to_a", "lift"])
    singletons = Counter(skill for skills in by_posting.values() for skill in skills)
    pairs = Counter(pair for skills in by_posting.values() for pair in combinations(sorted(skills), 2))
    rows: list[dict[str, Any]] = []
    for (skill_a, skill_b), count in pairs.items():
        support = count / total
        rows.append({
            "skill_a": skill_a,
            "skill_b": skill_b,
            "skill_a_name": names[skill_a],
            "skill_b_name": names[skill_b],
            "cooccurrence_count": count,
            "support": support,
            "confidence_a_to_b": count / singletons[skill_a],
            "confidence_b_to_a": count / singletons[skill_b],
            "lift": support / ((singletons[skill_a] / total) * (singletons[skill_b] / total)),
        })
    return pd.DataFrame(rows).sort_values(["cooccurrence_count", "lift"], ascending=False).reset_index(drop=True)
