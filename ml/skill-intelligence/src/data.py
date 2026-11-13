from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .contracts import ChatRecord

SYSTEM_PROMPT = "Extract skills from job descriptions. Use only the supplied taxonomy. Return valid JSON with evidence."


def source_fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def to_chat_record(posting: dict[str, Any], mentions: list[dict[str, Any]]) -> ChatRecord:
    description = posting.get("job_description") or ""
    skills = [
        {
            "name": mention["canonical_name"],
            "canonical_id": mention["skill_id"],
            "evidence": mention["evidence"],
        }
        for mention in mentions
    ]
    return ChatRecord(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Job description: {description}"},
            {"role": "assistant", "content": json.dumps({"skills": skills, "unresolved_skills": []}, ensure_ascii=False)},
        ],
        provenance={"posting_id": posting["id"], "source_id": posting["source_id"]},
        label_source="weak_dictionary_match",
    )
