from __future__ import annotations

from .schemas import ExtractSkillsRequest, ExtractSkillsResponse


def predict(request: ExtractSkillsRequest) -> ExtractSkillsResponse:
    raise RuntimeError("Model weights and adapter are not available. Run a validated training/export workflow first.")
