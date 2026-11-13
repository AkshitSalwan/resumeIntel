from __future__ import annotations

from collections.abc import Callable

import numpy as np

from .models import ForecastEstimate


def rolling_origin_evaluate(
    values: list[float],
    forecast: Callable[[list[float], int], ForecastEstimate],
    *,
    horizon: int,
    minimum_train_size: int = 6,
) -> dict[str, float | int | None]:
    if horizon < 1 or minimum_train_size < 2:
        raise ValueError("horizon and minimum_train_size must be positive")
    if len(values) < minimum_train_size + horizon:
        return {"status": "insufficient_data", "observations": len(values), "mae": None, "rmse": None, "wape": None, "mase": None}
    actual: list[float] = []
    predicted: list[float] = []
    for origin in range(minimum_train_size, len(values) - horizon + 1):
        estimate = forecast(values[:origin], horizon)
        actual.extend(values[origin:origin + horizon])
        predicted.extend(estimate.values)
    errors = np.asarray(actual) - np.asarray(predicted)
    naive_errors = np.asarray(actual[1:]) - np.asarray(actual[:-1]) if len(actual) > 1 else np.asarray([])
    return {
        "status": "evaluated",
        "observations": len(values),
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "wape": float(np.sum(np.abs(errors)) / np.sum(np.abs(actual))) if np.sum(np.abs(actual)) else None,
        "mase": float(np.mean(np.abs(errors)) / np.mean(np.abs(naive_errors))) if naive_errors.size and np.mean(np.abs(naive_errors)) else None,
    }
