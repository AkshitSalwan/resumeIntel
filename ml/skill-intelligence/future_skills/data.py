from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from . import _bootstrap  # noqa: F401
from forecasting.taxonomy.skill_dictionary import INITIAL_SKILLS
from forecasting.taxonomy.skill_normalizer import SkillNormalizer

from .schemas import FutureSkillsExample, ReviewStatus, TaskType


def _record_fingerprint(row: dict[str, Any]) -> str:
    return hashlib.sha256(f"{row['source']}:{row['source_job_id']}".encode()).hexdigest()[:16]


def _chat(system: str, user: str, assistant: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
        {"role": "assistant", "content": json.dumps(assistant, ensure_ascii=False)},
    ]


def build_candidate_examples(input_path: str | Path) -> list[FutureSkillsExample]:
    normalizer = SkillNormalizer(INITIAL_SKILLS)
    examples: list[FutureSkillsExample] = []
    for line in Path(input_path).read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        record_id = row["record_id"]
        mentions = normalizer.extract(record_id, row.get("description"))
        skills = [
            {"name": mention.canonical_name, "canonical_id": mention.skill_id, "evidence": mention.evidence}
            for mention in mentions
        ]
        examples.append(FutureSkillsExample(
            example_id=f"extract-{_record_fingerprint(row)}",
            task_type=TaskType.SKILL_EXTRACTION,
            messages=_chat(
                "Extract only skills explicitly supported by the supplied job description and canonical taxonomy.",
                f"Job description:\n{row.get('description', '')}",
                {"skills": skills, "unresolved_skills": []},
            ),
            source_record_ids=[record_id],
            source_companies=[row["company"]],
            source_ids=[row["source"]],
            source_job_id=row["source_job_id"],
            source_title=row["title"],
            original_evidence=[mention.evidence for mention in mentions],
            proposed_output={"skills": skills, "unresolved_skills": []},
            canonical_skill_ids=sorted({mention.skill_id for mention in mentions}),
            labeling_method="weak_dictionary_match",
            human_review_status=ReviewStatus.CANDIDATE,
            provenance={
                "source_job_id": row["source_job_id"],
                "source_url": row.get("job_url"),
                "collection_timestamp": row.get("collection_timestamp"),
                "taxonomy": "forecasting.taxonomy.skill_dictionary.INITIAL_SKILLS",
            },
        ))
    return examples


def write_jsonl(examples: list[FutureSkillsExample], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(example.model_dump_json() + "\n" for example in examples), encoding="utf-8")


def split_by_company(examples: list[FutureSkillsExample], *, seed: int = 42) -> dict[str, list[FutureSkillsExample]]:
    del seed
    groups: dict[str, list[FutureSkillsExample]] = defaultdict(list)
    for example in examples:
        groups[example.source_companies[0] if example.source_companies else example.example_id].append(example)
    ordered = sorted(groups.items(), key=lambda item: item[0])
    result = {"train": [], "validation": [], "test": []}
    group_count = len(ordered)
    train_cutoff = max(1, round(group_count * 0.6))
    validation_cutoff = max(train_cutoff + 1, round(group_count * 0.8)) if group_count > 1 else train_cutoff
    for index, (_, group) in enumerate(ordered):
        split = "train" if index < train_cutoff else "validation" if index < validation_cutoff else "test"
        result[split].extend(group)
    for split, items in result.items():
        for item in items:
            item.split = split
    return result
