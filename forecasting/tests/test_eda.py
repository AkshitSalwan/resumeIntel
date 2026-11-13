from forecasting.analytics.cooccurrence import skill_cooccurrence
from forecasting.analytics.coverage import coverage_analysis
from forecasting.analytics.distributions import skill_distribution
from forecasting.analytics.roles import classify_role
from forecasting.analytics.trends import temporal_skill_demand
from forecasting.reports.eda_report import build_eda_report, render_markdown
from forecasting.schemas.skill import SkillMention
from forecasting.tests.test_pipeline import posting


def mentions(postings):
    return [
        SkillMention(
            posting_id=posting_id,
            skill_id=skill_id,
            canonical_name=skill_name,
            matched_text=skill_name,
            evidence=skill_name,
        )
        for posting_id, pairs in postings.items()
        for skill_id, skill_name in pairs
    ]


def test_coverage_reports_empty_dataset_as_unavailable():
    result = coverage_analysis([], [])
    assert result["status"] == "unavailable"
    assert result["temporal_comparison_sufficient"] is False


def test_temporal_demand_calculates_period_change_without_filling_missing_periods():
    items = [posting("a", "Python", "2024-01-15"), posting("b", "Python", "2025-01-15")]
    result = temporal_skill_demand(items, mentions({"fixture:a": [("python", "Python")], "fixture:b": [("python", "Python")]}), "year")
    assert list(result["period"]) == ["2024-01-01", "2025-01-01"]
    assert result.iloc[1]["absolute_change"] == 0


def test_cooccurrence_deduplicates_mentions_and_calculates_metrics():
    result = skill_cooccurrence(mentions({
        "p1": [("python", "Python"), ("machine-learning", "Machine Learning"), ("python", "Python")],
        "p2": [("python", "Python")],
    }))
    row = result[(result["skill_a"] == "machine-learning") & (result["skill_b"] == "python")].iloc[0]
    assert row["cooccurrence_count"] == 1
    assert row["support"] == 0.5
    assert row["confidence_a_to_b"] == 1
    assert row["confidence_b_to_a"] == 0.5


def test_industry_and_geographic_filters_change_distribution_denominator():
    items = [
        posting("a", "Python", "2024-01-15"),
        posting("b", "Docker", "2024-01-15"),
    ]
    items[0] = items[0].model_copy(update={"industry": "Technology", "region": "India"})
    items[1] = items[1].model_copy(update={"industry": "Finance", "region": "United States"})
    item_mentions = mentions({"fixture:a": [("python", "Python")], "fixture:b": [("docker", "Docker")]})
    india = skill_distribution(items, item_mentions, region="India")
    finance = skill_distribution(items, item_mentions, industry="Finance")
    assert india.iloc[0]["skill_id"] == "python"
    assert finance.iloc[0]["skill_id"] == "docker"


def test_role_mapping_requires_a_known_title_pattern():
    assert classify_role("Senior Data Engineer") == "Data Engineering"
    assert classify_role("Mystery Specialist") is None


def test_empty_eda_report_is_explicit_and_reproducible_in_content():
    report = build_eda_report([], [], {"missing_posting_dates": 0})
    markdown = render_markdown(report)
    assert report["dataset_status"] == "unavailable"
    assert "No genuine historical job-market dataset is present" in markdown
    assert "Not ready for forecasting" in markdown
