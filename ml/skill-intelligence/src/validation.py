from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from .contracts import ChatRecord, ExtractionOutput
from .taxonomy import resolve_skill


def validate_chat_record(value: dict[str, Any]) -> ChatRecord:
    return ChatRecord.model_validate(value)


def parse_model_output(raw: str) -> ExtractionOutput:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("Model output is not valid JSON.") from error
    result = ExtractionOutput.model_validate(payload)
    for skill in result.skills:
        if skill.canonical_id is not None and resolve_skill(skill.canonical_id) is None:
            raise ValueError(f"Unknown taxonomy id: {skill.canonical_id}")
    return result
