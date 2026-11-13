from __future__ import annotations

import re
from datetime import UTC, datetime
from html import unescape
from typing import Any


def text(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(str(value)))).strip()
    return cleaned or None


def timestamp(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000 if value > 10_000_000_000 else value, tz=UTC)
    raw = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def first_text(value: Any) -> str | None:
    if isinstance(value, list):
        return text(value[0]) if value else None
    if isinstance(value, dict):
        return text(value.get("name") or value.get("title") or value.get("text"))
    return text(value)
