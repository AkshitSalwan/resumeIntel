from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CountryResolution:
    country: str | None
    method: str | None
    confidence: str | None


COUNTRY_NAMES = {
    "australia": "Australia",
    "brazil": "Brazil",
    "canada": "Canada",
    "france": "France",
    "germany": "Germany",
    "india": "India",
    "ireland": "Ireland",
    "israel": "Israel",
    "japan": "Japan",
    "netherlands": "Netherlands",
    "singapore": "Singapore",
    "spain": "Spain",
    "switzerland": "Switzerland",
    "united kingdom": "United Kingdom",
    "united states": "United States",
    "usa": "United States",
}

ALIASES = {
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "us": "United States",
    "u.s.": "United States",
    "usa": "United States",
    "u.s.a.": "United States",
}

ISO_CODES = {
    "au": "Australia",
    "br": "Brazil",
    "ca": "Canada",
    "de": "Germany",
    "fr": "France",
    "gb": "United Kingdom",
    "ie": "Ireland",
    "il": "Israel",
    "jp": "Japan",
    "nl": "Netherlands",
    "sg": "Singapore",
    "es": "Spain",
    "ch": "Switzerland",
    "us": "United States",
}


def resolve_country(location: str | None) -> CountryResolution:
    """Resolve only explicit country evidence; cities and employer country are ignored."""
    if not location:
        return CountryResolution(None, None, None)
    value = location.strip().lower()
    candidates: set[tuple[str, str, str]] = set()
    for raw, country in COUNTRY_NAMES.items():
        if re.search(rf"(?<![a-z]){re.escape(raw)}(?![a-z])", value):
            candidates.add((country, "exact_country_name", "high"))
    for raw, country in ALIASES.items():
        if re.search(rf"(?<![a-z]){re.escape(raw)}(?![a-z])", value):
            candidates.add((country, "curated_alias", "medium"))
    for raw, country in ISO_CODES.items():
        if re.search(rf"(?<![a-z]){re.escape(raw)}(?![a-z])", value):
            candidates.add((country, "iso_country_code", "medium"))
    if len({candidate[0] for candidate in candidates}) != 1:
        return CountryResolution(None, "ambiguous" if candidates else None, None)
    country, method, confidence = next(iter(candidates))
    return CountryResolution(country, method, confidence)
