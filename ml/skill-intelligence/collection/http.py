from __future__ import annotations

import json
import time
from collections.abc import Callable
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class PublicApiError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, retryable: bool = False) -> None:
        super().__init__(message)
        self.status = status
        self.retryable = retryable


def retry_after_seconds(value: str | None, default: float) -> float:
    if not value:
        return default
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            return max(0.0, (parsedate_to_datetime(value).timestamp() - time.time()))
        except (TypeError, ValueError, OverflowError):
            return default


def fetch_json(
    url: str,
    *,
    timeout: float = 20.0,
    attempts: int = 3,
    user_agent: str = "ResumeIntel-research-collector/1.0",
    opener: Callable[..., Any] = urlopen,
) -> Any:
    for attempt in range(attempts):
        request = Request(url, headers={"Accept": "application/json", "User-Agent": user_agent})
        try:
            with opener(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            retryable = error.code == 429 or 500 <= error.code < 600
            if not retryable or attempt == attempts - 1:
                raise PublicApiError(f"HTTP {error.code} from {url}", status=error.code, retryable=retryable) from error
            delay = retry_after_seconds(error.headers.get("Retry-After"), 2 ** attempt)
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            if attempt == attempts - 1:
                raise PublicApiError(f"Request failed for {url}: {error}", retryable=True) from error
            delay = 2 ** attempt
        time.sleep(min(delay, 30.0))
    raise AssertionError("unreachable")
