from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import numpy as np


@dataclass(frozen=True)
class ForecastEstimate:
    model: str
    values: tuple[float, ...]
    lower: tuple[float, ...] | None = None
    upper: tuple[float, ...] | None = None


def _validate(values: list[float], horizon: int) -> None:
    if horizon < 1:
        raise ValueError("horizon must be positive")
    if len(values) < 2:
        raise ValueError("at least two observations are required")


def moving_average_forecast(values: list[float], horizon: int, window: int = 3) -> ForecastEstimate:
    _validate(values, horizon)
    if window < 1:
        raise ValueError("window must be positive")
    average = float(np.mean(values[-min(window, len(values)):]))
    return ForecastEstimate("moving_average", (average,) * horizon)


def seasonal_naive_forecast(values: list[float], horizon: int, season_length: int = 12) -> ForecastEstimate:
    _validate(values, horizon)
    if len(values) < season_length:
        raise ValueError("seasonal naive requires at least one complete season")
    return ForecastEstimate("seasonal_naive", tuple(float(values[-season_length + index % season_length]) for index in range(horizon)))


def exponential_smoothing_forecast(values: list[float], horizon: int, alpha: float = 0.3) -> ForecastEstimate:
    _validate(values, horizon)
    if not 0 < alpha <= 1:
        raise ValueError("alpha must be in (0, 1]")
    level = float(values[0])
    for value in values[1:]:
        level = alpha * float(value) + (1 - alpha) * level
    deviation = sqrt(float(np.mean([(value - level) ** 2 for value in values])))
    return ForecastEstimate("exponential_smoothing", (level,) * horizon, tuple(max(0.0, level - 1.96 * deviation) for _ in range(horizon)), tuple(level + 1.96 * deviation for _ in range(horizon)))
