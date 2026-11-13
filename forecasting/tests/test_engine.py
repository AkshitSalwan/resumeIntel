from datetime import date

import pandas as pd
import pytest

from forecasting.engine.evaluation import rolling_origin_evaluate
from forecasting.engine.emerging import analyze_emerging_skills
from forecasting.engine.models import (
    exponential_smoothing_forecast,
    moving_average_forecast,
    seasonal_naive_forecast,
)


def test_baselines_return_bounded_estimates_and_intervals():
    values = [0.1, 0.2, 0.3, 0.4]
    assert moving_average_forecast(values, 2).values == (0.3, 0.3)
    estimate = exponential_smoothing_forecast(values, 2)
    assert estimate.lower and estimate.upper
    assert all(lower <= value <= upper for lower, value, upper in zip(estimate.lower, estimate.values, estimate.upper))


def test_seasonal_naive_requires_a_complete_season():
    with pytest.raises(ValueError, match="complete season"):
        seasonal_naive_forecast([1.0, 2.0], 1)


def test_rolling_origin_is_chronological_and_reports_insufficient_data():
    result = rolling_origin_evaluate([1.0, 2.0, 3.0], moving_average_forecast, horizon=2, minimum_train_size=2)
    assert result["status"] == "insufficient_data"
    evaluated = rolling_origin_evaluate([1.0, 2.0, 3.0, 4.0, 5.0], moving_average_forecast, horizon=1, minimum_train_size=3)
    assert evaluated["status"] == "evaluated"
    assert evaluated["mae"] is not None


def test_emerging_skills_require_independent_evidence():
    frame = pd.DataFrame([
        {"period": "2026-01-01", "skill_id": "python", "skill_name": "Python", "postings_requiring_skill": 1, "demand_share": 0.5, "company_count": 1, "source_count": 1},
        {"period": "2026-02-01", "skill_id": "python", "skill_name": "Python", "postings_requiring_skill": 2, "demand_share": 0.7, "company_count": 2, "source_count": 2},
    ])
    result = analyze_emerging_skills(frame)
    assert result.iloc[0]["classification"] == "insufficient-data"
