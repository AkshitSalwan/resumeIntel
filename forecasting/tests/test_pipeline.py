from datetime import UTC, datetime

import pandas as pd

from forecasting.analytics.demand_aggregation import aggregate_skill_demand
from forecasting.preprocessing.cleaning import clean_record
from forecasting.preprocessing.deduplication import deduplicate_postings
from forecasting.taxonomy.skill_dictionary import INITIAL_SKILLS
from forecasting.taxonomy.skill_normalizer import SkillNormalizer


NOW = datetime(2026, 1, 2, tzinfo=UTC)


def posting(record_id: str, description: str, date: str = "2025-01-15"):
    return clean_record({
        "id": record_id,
        "title": "Data Engineer",
        "company": "Example",
        "description": description,
        "location": "Remote",
        "date_posted": date,
    }, source_id="fixture", now=NOW)


def test_cleaning_preserves_missing_date_and_normalizes_whitespace():
    result = clean_record({"title": "  Data   Engineer ", "description": "Python\nETL"}, source_id="fixture", now=NOW)
    assert result.job_title == "Data Engineer"
    assert result.job_description == "Python ETL"
    assert result.posting_date is None


def test_normalizer_distinguishes_java_from_javascript():
    normalizer = SkillNormalizer(INITIAL_SKILLS)
    mentions = normalizer.extract("p1", "Built JavaScript services and Java integrations.")
    assert {mention.skill_id for mention in mentions} == {"javascript", "java"}


def test_go_match_requires_programming_context_and_ignores_gtm():
    normalizer = SkillNormalizer(INITIAL_SKILLS)
    assert "go" not in {mention.skill_id for mention in normalizer.extract("p1", "Led go-to-market strategy and GTM campaigns.")}
    assert "go" in {mention.skill_id for mention in normalizer.extract("p2", "Built backend services in Go programming language.")}
    assert "go" in {mention.skill_id for mention in normalizer.extract("p3", "Experience with Golang services.")}


def test_commercial_taxonomy_skills_and_aliases_are_unique_and_extractable():
    normalizer = SkillNormalizer(INITIAL_SKILLS)
    ids = {skill.skill_id for skill in INITIAL_SKILLS}
    assert len(ids) == len(INITIAL_SKILLS)
    mentions = normalizer.extract("p1", "Sales account executive owning retention, upsell, and new business development.")
    assert {mention.skill_id for mention in mentions} == {"sales", "account-management", "customer-retention", "revenue-growth", "business-development"}


def test_deduplication_is_auditable():
    first = posting("a", "Python ETL")
    duplicate = posting("a", "Python ETL")
    result = deduplicate_postings([first, duplicate])
    assert len(result.unique) == 1
    assert result.duplicates[0]["kept_id"] == first.id


def test_demand_uses_unique_skill_postings_and_explicit_denominator():
    postings = [posting("a", "Python Python"), posting("b", "Docker"), posting("c", "Python")]
    mentions = [mention for item in postings for mention in SkillNormalizer(INITIAL_SKILLS).extract(item.id, item.job_description)]
    result = aggregate_skill_demand(postings, mentions, frequency="month")
    python = result[result.skill_id == "python"].iloc[0]
    assert python.postings_requiring_skill == 2
    assert python.eligible_postings == 3
    assert python.demand_percentage == 2 / 3 * 100
    assert isinstance(result, pd.DataFrame)


def test_ml_infrastructure_taxonomy_skills_are_extractable():
    normalizer = SkillNormalizer(INITIAL_SKILLS)
    mentions = normalizer.extract(
        "p1",
        (
            "Reinforcement Learning, PyTorch, JAX, model evaluation, "
            "model inference optimization, GPU computing, "
            "high-performance computing, virtualization, and sandboxing."
        ),
    )
    assert {mention.skill_id for mention in mentions} == {
        "reinforcement-learning",
        "pytorch",
        "jax",
        "model-evaluation",
        "model-inference-optimization",
        "gpu-computing",
        "high-performance-computing",
        "virtualization",
        "sandboxing",
    }


def test_ml_infrastructure_aliases_are_case_insensitive():
    normalizer = SkillNormalizer(INITIAL_SKILLS)
    mentions = normalizer.extract(
        "p1",
        "PYTORCH, JAX, HPC, virtual machines, and sandbox.",
    )
    assert {mention.skill_id for mention in mentions} == {
        "pytorch",
        "jax",
        "high-performance-computing",
        "virtualization",
        "sandboxing",
    }


def test_ml_infrastructure_taxonomy_avoids_ambiguous_short_aliases():
    normalizer = SkillNormalizer(INITIAL_SKILLS)
    mentions = normalizer.extract(
        "p1",
        "We will use RL as a project label, GPU-related products, "
        "and sandboxing in the testing environment.",
    )
    ids = {mention.skill_id for mention in mentions}
    assert "reinforcement-learning" not in ids
    assert "gpu-computing" not in ids
    assert "sandboxing" in ids
