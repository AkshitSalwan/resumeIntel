from __future__ import annotations

from .inference.schemas import ExtractSkillsRequest, ExtractSkillsResponse


def extract_skills(request: ExtractSkillsRequest) -> ExtractSkillsResponse:
    """Framework-neutral service boundary for a future authenticated API."""
    raise RuntimeError("Skill model service is unavailable until a validated adapter is exported.")
