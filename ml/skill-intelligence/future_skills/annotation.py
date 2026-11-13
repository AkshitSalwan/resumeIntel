from __future__ import annotations

import csv
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schemas import AnnotationRecord, FutureSkillsExample, ReviewStatus
from .validation import validate_annotation
from forecasting.taxonomy.skill_dictionary import INITIAL_SKILLS
from forecasting.taxonomy.skill_normalizer import SkillNormalizer


def _safe_write(path: str | Path, content: str, *, backup_suffix: str = ".before-export.bak") -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup = destination.with_name(destination.name + backup_suffix)
    if destination.exists() and not backup.exists():
        shutil.copy2(destination, backup)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, destination)


def annotation_from_candidate(example: FutureSkillsExample) -> AnnotationRecord:
    skills = example.proposed_output.get("skills", [])
    return AnnotationRecord(
        example_id=example.example_id,
        source_job_id=example.source_job_id or str(example.provenance.get("source_job_id", "")),
        company=example.source_companies[0] if example.source_companies else "",
        title=example.source_title or "",
        task_type=example.task_type,
        original_evidence=example.original_evidence,
        extracted_skills=[str(item.get("name", "")) for item in skills if isinstance(item, dict)],
        canonical_skill_ids=list(example.canonical_skill_ids),
        proposed_output=example.proposed_output,
        split=example.split,
        provenance={
            **example.provenance,
            "source_record_ids": example.source_record_ids,
            "source_ids": example.source_ids,
            "user_content": next((message.get("content", "") for message in example.messages if message.get("role") == "user"), ""),
        },
    )


def load_examples(path: str | Path) -> list[FutureSkillsExample]:
    return [FutureSkillsExample.model_validate_json(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def load_annotations(path: str | Path) -> dict[str, AnnotationRecord]:
    annotation_path = Path(path)
    if not annotation_path.exists():
        return {}
    records: dict[str, AnnotationRecord] = {}
    for line in annotation_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = AnnotationRecord.model_validate_json(line)
            if record.example_id in records:
                raise ValueError(f"Duplicate annotation candidate ID: {record.example_id}")
            records[record.example_id] = record
    return records


def export_candidates(input_path: str | Path, output_path: str | Path) -> int:
    candidates = load_examples(input_path)
    records = [annotation_from_candidate(example) for example in candidates]
    path = Path(output_path)
    _safe_write(path, "".join(record.model_dump_json() + "\n" for record in records))
    return len(records)


def save_annotation(record: AnnotationRecord, path: str | Path, *, candidate_ids: set[str]) -> None:
    validate_annotation(record, candidate_ids=candidate_ids)
    existing = load_annotations(path)
    existing[record.example_id] = record
    _safe_write(path, "".join(item.model_dump_json() + "\n" for item in sorted(existing.values(), key=lambda item: item.example_id)), backup_suffix=".before-human-review.bak")


_ROLE_SECTION = re.compile(
    r"\b(?:about (?:the )?role|your role|in this role|what you(?:'|’)ll do|what you will do|responsibilities|requirements|qualifications|what we(?:'|’)re looking for|what we are looking for|your impact|what you(?:'|’)ll bring|what you will bring|you might thrive)\b",
    re.IGNORECASE,
)
_BOILERPLATE = re.compile(r"\b(?:about openai|equal employment opportunity|equal opportunity|our commitment to inclusion|reasonable accommodations|compensation and benefits)\b", re.IGNORECASE)
_DIRECT_RELEVANCE = re.compile(
    r"\b(?:experience|proficien(?:t|cy)|expertise|knowledge|ability|familiar(?:ity)?|skill(?:s)?|you will|you'll|you’ll|build|develop|design|operate|manage|lead|deploy|implement|maintain|debug|architect|work with|responsible|support|drive|create|write|own|using|use|programming|technical)\b",
    re.IGNORECASE,
)
_MISSION_ONLY = re.compile(r"\b(?:our mission|company dedicated|dedicated to ensuring|benefits of ai|ai research and deployment company)\b", re.IGNORECASE)


def _sentence_for_match(text: str, matched: str) -> str | None:
    match = re.search(rf"(?<![\w+#]){re.escape(matched)}(?![\w+#])", text, re.IGNORECASE)
    if not match:
        return None
    for sentence_match in re.finditer(r"[^.!?\n]+(?:[.!?]+|$)", text):
        if sentence_match.start() <= match.start() < sentence_match.end():
            sentence = sentence_match.group(0).strip()
            return sentence if sentence and len(sentence) <= 500 else None
    return None


def ai_pre_review_validation(
    candidates_path: str | Path,
    annotations_path: str | Path,
    *,
    system_id: str = "codex-ai-assistant (model identifier unavailable)",
) -> dict[str, Any]:
    """Create explicitly AI-assisted pseudo-labels for pending validation rows.

    Existing human-reviewed records are never changed. Labels are extracted only
    from canonical taxonomy matches in role-specific sections and remain excluded
    from the human-reviewed exporter.
    """
    candidates = load_examples(candidates_path)
    annotations = load_annotations(annotations_path)
    candidate_by_id = {item.example_id: item for item in candidates}
    if len(candidate_by_id) != len(candidates):
        raise ValueError("Duplicate candidate IDs in validation candidates")
    if not annotations and Path(annotations_path).exists():
        raise ValueError("Validation annotations file exists but contains no records")

    matcher = SkillNormalizer(INITIAL_SKILLS)
    updated = dict(annotations)
    processed = 0
    uncertain_count = 0
    skills_added = 0
    skills_removed = 0
    timestamp = datetime.now(timezone.utc).isoformat()

    for candidate in candidates:
        current = annotations.get(candidate.example_id)
        if current and current.reviewer_decision != ReviewStatus.CANDIDATE:
            continue
        if candidate.split != "validation":
            raise ValueError(f"Candidate {candidate.example_id} is not in the validation split")
        user_content = next((message.get("content", "") for message in candidate.messages if message.get("role") == "user"), "")
        if not user_content:
            raise ValueError(f"Candidate {candidate.example_id} has no full job description")

        original_ids = set(candidate.canonical_skill_ids)
        role_match = _ROLE_SECTION.search(user_content)
        uncertain_reasons: list[str] = []
        retained: list[dict[str, str]] = []
        if not role_match:
            uncertain_reasons.append("No recognizable role requirements/responsibilities heading; no labels inferred.")
            role_text = ""
        else:
            role_text = user_content[role_match.start():]
            boilerplate = _BOILERPLATE.search(role_text)
            if boilerplate:
                role_text = role_text[:boilerplate.start()]
        role_matches = matcher.extract(candidate.example_id, role_text)
        for mention in role_matches:
            sentence = _sentence_for_match(role_text, mention.matched_text)
            if not sentence:
                uncertain_reasons.append(f"Could not isolate complete evidence for {mention.skill_id}.")
                continue
            if _MISSION_ONLY.search(sentence):
                continue
            if not _DIRECT_RELEVANCE.search(sentence):
                uncertain_reasons.append(f"Role-section mention of {mention.skill_id} lacks direct requirement/responsibility context.")
                continue
            retained.append({"name": mention.canonical_name, "canonical_id": mention.skill_id, "evidence": sentence})

        retained_ids = {item["canonical_id"] for item in retained}
        skills_added += len(retained_ids - original_ids)
        skills_removed += len(original_ids - retained_ids)
        output = {"skills": retained, "unresolved_skills": []}
        notes = (
            "AI-assisted taxonomy pre-review; pseudo-label only, not human-reviewed. "
            f"Retained {len(retained)} direct taxonomy matches from the full job description's role section. "
            f"Removed {len(original_ids - retained_ids)} candidate weak matches outside relevant role evidence."
        )
        if uncertain_reasons:
            notes += " Uncertain: " + " ".join(uncertain_reasons)
            uncertain_count += 1
        base = current or annotation_from_candidate(candidate)
        updated[candidate.example_id] = base.model_copy(update={
            "reviewer_decision": ReviewStatus.AI_ASSISTED,
            "reviewer": None,
            "corrected_output": output,
            "review_notes": notes,
            "extracted_skills": [item["name"] for item in retained],
            "original_evidence": [item["evidence"] for item in retained],
            "canonical_skill_ids": sorted(retained_ids),
            "split": "validation",
            "provenance": {
                **base.provenance,
                "user_content": user_content,
                "ai_assisted": {
                    "system_id": system_id,
                    "timestamp": timestamp,
                    "method": "canonical taxonomy extraction filtered to role-specific sections and direct evidence sentences",
                    "pseudo_label": True,
                    "uncertain": bool(uncertain_reasons),
                    "uncertain_reasons": uncertain_reasons,
                    "skills_added": sorted(retained_ids - original_ids),
                    "skills_removed": sorted(original_ids - retained_ids),
                    "independent_human_review": False,
                },
            },
        })
        validate_annotation(updated[candidate.example_id], candidate_ids=set(candidate_by_id))
        processed += 1

    _safe_write(annotations_path, "".join(item.model_dump_json() + "\n" for item in sorted(updated.values(), key=lambda item: item.example_id)), backup_suffix=".before-ai-assisted-review.bak")
    return {
        "processed": processed,
        "preserved_human_reviewed": sum(item.reviewer_decision == ReviewStatus.REVIEWED for item in annotations.values()),
        "ai_assisted_total": sum(item.reviewer_decision == ReviewStatus.AI_ASSISTED for item in updated.values()),
        "uncertain": uncertain_count,
        "skills_added": skills_added,
        "skills_removed": skills_removed,
        "pseudo_labels_not_human_reviewed": True,
        "output": str(annotations_path),
    }


def export_gold(
    annotation_path: str | Path,
    output_path: str | Path,
    *,
    training_ids: set[str] | None = None,
    validation_ids: set[str] | None = None,
    candidate_ids: set[str] | None = None,
) -> dict[str, Any]:
    records = load_annotations(annotation_path)
    eligible: list[AnnotationRecord] = []
    excluded: list[dict[str, str]] = []
    for record in records.values():
        reason = None
        if record.reviewer_decision == ReviewStatus.REJECTED:
            reason = "rejected_by_reviewer"
        elif record.reviewer_decision != ReviewStatus.REVIEWED and record.reviewer_decision != ReviewStatus.GOLD:
            reason = "not_reviewed"
        elif record.split != "test":
            reason = "not_test_split"
        elif training_ids and record.example_id in training_ids:
            reason = "training_overlap"
        elif validation_ids and record.example_id in validation_ids:
            reason = "validation_overlap"
        elif candidate_ids is not None and record.example_id not in candidate_ids:
            reason = "unknown_candidate_id"
        else:
            try:
                validate_annotation(record, candidate_ids=candidate_ids)
            except ValueError as error:
                reason = f"invalid_annotation: {error}"
        if reason:
            excluded.append({"example_id": record.example_id, "reason": reason})
        else:
            eligible.append(record)

    # Duplicate source jobs and near duplicate postings are excluded with a reason.
    grouped: dict[str, list[AnnotationRecord]] = {}
    for record in eligible:
        grouped.setdefault(record.source_job_id, []).append(record)
    kept: list[AnnotationRecord] = []
    for group in grouped.values():
        if len(group) > 1:
            excluded.extend({"example_id": item.example_id, "reason": "duplicate_source_job_id"} for item in group)
        else:
            kept.extend(group)
    eligible = kept
    # Companies may repeat within one split, but may not cross train/validation/test.
    splits_by_company: dict[str, set[str]] = {}
    for record in eligible:
        splits_by_company.setdefault(record.company, set()).add(record.split or "")
    leakage_companies = {company for company, splits in splits_by_company.items() if len(splits) > 1}
    if leakage_companies:
        leaked = [record for record in eligible if record.company in leakage_companies]
        eligible = [record for record in eligible if record.company not in leakage_companies]
        excluded.extend({"example_id": record.example_id, "reason": "company_cross_split_leakage"} for record in leaked)
    destination = Path(output_path)
    _safe_write(destination, "".join(record.model_dump_json() + "\n" for record in sorted(eligible, key=lambda item: item.example_id)))
    return {
        "gold_count": len(eligible), "eligible_count": len(eligible), "excluded_count": len(excluded),
        "excluded": excluded, "exclusion_counts": _counts_by_reason(excluded),
        "by_task": _counts(eligible, lambda item: item.task_type.value),
        "splits": sorted({record.split for record in eligible if record.split}), "output": str(destination),
    }


def _counts_by_reason(excluded: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in excluded:
        counts[item["reason"]] = counts.get(item["reason"], 0) + 1
    return counts


def quality_report(annotation_path: str | Path, candidate_count: int, *, split: str | None = None, gold_count: int | None = None, gold_overlaps_training: bool = False) -> dict[str, Any]:
    records = list(load_annotations(annotation_path).values())
    if split:
        records = [record for record in records if record.split == split]
    reviewed = [record for record in records if record.reviewer_decision in {ReviewStatus.REVIEWED, ReviewStatus.REJECTED, ReviewStatus.GOLD}]
    accepted = [record for record in records if record.reviewer_decision in {ReviewStatus.REVIEWED, ReviewStatus.GOLD}]
    ai_assisted = [record for record in records if record.reviewer_decision == ReviewStatus.AI_ASSISTED]
    candidates = [record for record in records if record.reviewer_decision == ReviewStatus.CANDIDATE]
    return {
        "total_candidates": candidate_count,
        "candidate_examples": len(candidates),
        "ai_assisted_examples": len(ai_assisted),
        "human_reviewed_examples": sum(record.reviewer_decision == ReviewStatus.REVIEWED for record in records),
        "ai_assisted_uncertain_examples": sum(bool(record.provenance.get("ai_assisted", {}).get("uncertain")) for record in ai_assisted),
        "ai_assisted_skills_added": sum(len(record.provenance.get("ai_assisted", {}).get("skills_added", [])) for record in ai_assisted),
        "ai_assisted_skills_removed": sum(len(record.provenance.get("ai_assisted", {}).get("skills_removed", [])) for record in ai_assisted),
        "ai_assisted_system_ids": sorted({str(record.provenance.get("ai_assisted", {}).get("system_id")) for record in ai_assisted if record.provenance.get("ai_assisted", {}).get("system_id")}),
        "ai_assisted_timestamps": sorted({str(record.provenance.get("ai_assisted", {}).get("timestamp")) for record in ai_assisted if record.provenance.get("ai_assisted", {}).get("timestamp")}),
        "decision_counts": _counts(records, lambda item: item.reviewer_decision.value),
        "reviewed_examples": len(reviewed),
        "accepted_examples": len(accepted),
        "rejected_examples": sum(record.reviewer_decision == ReviewStatus.REJECTED for record in records),
        "gold_examples": gold_count if gold_count is not None else sum(record.reviewer_decision == ReviewStatus.GOLD for record in records),
        "counts_per_task": _counts(records, lambda item: item.task_type.value),
        "canonical_mapping_accuracy": None,
        "missing_evidence_count": sum(
            1
            for record in accepted
            if (
                skills := (
                    record.corrected_output or record.proposed_output or {}
                ).get("skills", [])
            )
            and any(
                not isinstance(item, dict)
                or not isinstance(item.get("evidence"), str)
                or not item["evidence"].strip()
                for item in skills
            )
        ),
        "unsupported_skill_count": sum(1 for record in reviewed if any(not item for item in record.canonical_skill_ids)),
        "reviewer_completion_percentage": round(len(reviewed) / candidate_count * 100, 2) if candidate_count else 0,
        "reviewed_training_examples": sum(record.reviewer_decision == ReviewStatus.REVIEWED and record.split == "train" for record in records),
        "gold_evaluation_examples": gold_count if gold_count is not None else sum(record.reviewer_decision == ReviewStatus.GOLD and record.split == "test" for record in records),
        "gold_overlaps_training": gold_overlaps_training,
        "ai_assisted_labels_are_pseudo_labels": True,
        "ai_assisted_labels_are_human_verified": False,
        "note": "AI-assisted labels are pseudo-labels, not independent ground truth; do not compute human-verified evaluation metrics against them. Mapping accuracy is unavailable without an independent corrected reference.",
    }


def _counts(records: list[AnnotationRecord], key) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = key(record)
        counts[value] = counts.get(value, 0) + 1
    return counts


def export_csv(annotation_path: str | Path, output_path: str | Path) -> None:
    records = list(load_annotations(annotation_path).values())
    fields = ["example_id", "source_job_id", "company", "title", "task_type", "original_evidence", "extracted_skills", "canonical_skill_ids", "proposed_output", "reviewer_decision", "corrected_output", "review_notes", "reviewer", "split", "provenance"]
    import io
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    for record in records:
        row = record.model_dump(mode="json")
        for field in ("original_evidence", "extracted_skills", "canonical_skill_ids", "proposed_output", "corrected_output", "provenance"):
            row[field] = json.dumps(row[field], ensure_ascii=False)
        writer.writerow(row)
    _safe_write(output_path, handle.getvalue())


def export_training_data(
    candidates_path: str | Path,
    annotations_path: str | Path,
    output_path: str | Path,
    *,
    split: str = "train",
    excluded_ids: set[str] | None = None,
    excluded_companies: set[str] | None = None,
    required_status: ReviewStatus = ReviewStatus.REVIEWED,
    labeling_method: str = "human_reviewed",
) -> dict[str, Any]:
    """Export validated annotations for a split and explicitly selected status."""
    candidates = load_examples(candidates_path)
    annotations = load_annotations(annotations_path)

    candidate_by_id = {example.example_id: example for example in candidates}
    if len(candidate_by_id) != len(candidates):
        raise ValueError("Duplicate candidate IDs in candidate dataset")

    candidate_ids = set(candidate_by_id)
    exported: list[FutureSkillsExample] = []
    excluded: list[dict[str, str]] = []

    for record in annotations.values():
        if record.reviewer_decision != required_status:
            excluded.append({"example_id": record.example_id, "reason": "not_reviewed"})
            continue
        if record.split != split:
            excluded.append({"example_id": record.example_id, "reason": f"not_{split}_split"})
            continue

        candidate = candidate_by_id.get(record.example_id)
        if candidate is None:
            excluded.append({"example_id": record.example_id, "reason": "candidate_not_found"})
            continue
        if candidate.split != split:
            excluded.append({"example_id": record.example_id, "reason": f"candidate_not_{split}_split"})
            continue
        candidate_companies = set(candidate.source_companies)
        if excluded_companies and (record.company in excluded_companies or candidate_companies & excluded_companies):
            excluded.append({"example_id": record.example_id, "reason": "cross_split_company_leakage"})
            continue
        if excluded_ids and (record.example_id in excluded_ids or record.source_job_id in excluded_ids):
            excluded.append({"example_id": record.example_id, "reason": "cross_split_overlap"})
            continue

        try:
            record = record.model_copy(update={"provenance": {**record.provenance, "user_content": next((message.get("content", "") for message in candidate.messages if message.get("role") == "user"), "")}})
            validate_annotation(record, candidate_ids=candidate_ids)
            final_output = record.corrected_output or record.proposed_output
            if not isinstance(final_output, dict):
                raise ValueError("Missing final output")

            skills = final_output.get("skills")
            unresolved = final_output.get("unresolved_skills")
            if not isinstance(skills, list) or not isinstance(unresolved, list):
                raise ValueError("Output must contain skills and unresolved_skills lists")

            user_messages = [message for message in candidate.messages if message.get("role") == "user"]
            assistant_indices = [index for index, message in enumerate(candidate.messages) if message.get("role") == "assistant"]
            if len(user_messages) != 1 or len(assistant_indices) != 1:
                raise ValueError("Expected exactly one user and one assistant message")

            job_description = user_messages[0].get("content", "")
            final_ids = []
            for skill in skills:
                if not isinstance(skill, dict):
                    raise ValueError("Invalid skill entry")
                name, canonical_id, evidence = skill.get("name"), skill.get("canonical_id"), skill.get("evidence")
                if not all(isinstance(value, str) and value.strip() for value in (name, canonical_id, evidence)):
                    raise ValueError("Skill name, canonical_id, and evidence must be non-empty")
                if evidence not in job_description:
                    raise ValueError(f"Evidence is not an exact substring of the job description: {evidence!r}")
                final_ids.append(canonical_id)

            if len(final_ids) != len(set(final_ids)):
                raise ValueError("Duplicate canonical skill IDs in final output")
            if set(final_ids) != set(record.canonical_skill_ids):
                raise ValueError("Final output IDs do not match reviewed canonical_skill_ids")

            messages = [dict(message) for message in candidate.messages]
            messages[assistant_indices[0]]["content"] = json.dumps(final_output, ensure_ascii=False)
            exported.append(candidate.model_copy(update={
                "messages": messages,
                "proposed_output": final_output,
                "canonical_skill_ids": sorted(final_ids),
                "original_evidence": [skill["evidence"] for skill in skills],
                "human_review_status": required_status,
                "labeling_method": labeling_method,
                "split": split,
                "provenance": {
                    **candidate.provenance,
                    "reviewer": record.reviewer,
                    "annotation_review_notes": record.review_notes,
                    **({"ai_assisted": record.provenance["ai_assisted"]} if required_status == ReviewStatus.AI_ASSISTED else {}),
                },
            }))
        except ValueError as error:
            excluded.append({"example_id": record.example_id, "reason": str(error)})

    destination = Path(output_path)
    ids = [example.example_id for example in exported]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate exported {split} example IDs")
    jobs = [example.source_job_id for example in exported if example.source_job_id]
    if len(jobs) != len(set(jobs)):
        raise ValueError(f"Duplicate exported {split} source job IDs")
    _safe_write(destination, "".join(example.model_dump_json() + "\n" for example in exported))
    return {
        "exported": len(exported),
        "excluded": len(excluded),
        "exclusion_reasons": _counts_from_reasons(excluded),
        "output": str(destination),
        "split": split,
        "excluded_examples": excluded,
    }


def export_ai_assisted_data(
    candidates_path: str | Path,
    annotations_path: str | Path,
    output_path: str | Path,
    *,
    excluded_ids: set[str] | None = None,
    excluded_companies: set[str] | None = None,
) -> dict[str, Any]:
    """Export AI pseudo-labels separately from human-reviewed SFT data."""
    return export_training_data(
        candidates_path,
        annotations_path,
        output_path,
        split="validation",
        excluded_ids=excluded_ids,
        excluded_companies=excluded_companies,
        required_status=ReviewStatus.AI_ASSISTED,
        labeling_method="ai_assisted_pseudo_label",
    )


def _counts_from_reasons(excluded: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in excluded:
        reason = item["reason"]
        counts[reason] = counts.get(reason, 0) + 1
    return counts
