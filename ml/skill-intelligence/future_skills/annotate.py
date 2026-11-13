from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .annotation import _safe_write, annotation_from_candidate, load_annotations, load_examples, save_annotation
from .schemas import ReviewStatus
from .validation import validate_annotation
from forecasting.taxonomy.skill_dictionary import INITIAL_SKILLS


def _correct_output(example, initial_output: dict | None = None) -> tuple[dict, list[str], list[str]]:
    selected: dict[str, dict[str, str]] = {
        str(item["canonical_id"]): dict(item)
        for item in (initial_output or {}).get("skills", [])
        if isinstance(item, dict) and item.get("canonical_id")
    }
    description = next((message["content"] for message in example.messages if message.get("role") == "user"), "")
    while True:
        query = input("Search taxonomy (or 'list', 'done'): ").strip()
        if query.lower() == "done":
            break
        if query.lower() == "list":
            matches = list(INITIAL_SKILLS)
        else:
            needle = query.casefold()
            matches = [skill for skill in INITIAL_SKILLS if needle in skill.skill_id.casefold() or needle in skill.canonical_name.casefold() or any(needle in alias.casefold() for alias in skill.aliases)]
        if not matches:
            print("No matching taxonomy skills. Try another name or alias.")
            continue
        for index, skill in enumerate(matches, 1):
            print(f"{index}. {skill.skill_id} | {skill.canonical_name} | aliases: {', '.join(skill.aliases) or '(none)'}")
        choice = input("Select number to add, 'remove ID', or search again: ").strip()
        if choice.startswith("remove "):
            selected.pop(choice.removeprefix("remove ").strip(), None)
            continue
        try:
            skill = matches[int(choice) - 1]
        except (ValueError, IndexError):
            print("Invalid selection.")
            continue
        if skill.skill_id in selected:
            print("Already selected.")
            continue
        print("Evidence must be quoted from the job description shown above.")
        evidence = input("Evidence quote: ").strip()
        if len(evidence) >= 2 and evidence[0] == evidence[-1] and evidence[0] in {"\"", "'", "“", "”", "‘", "’"}:
            evidence = evidence[1:-1].strip()
        if not evidence or evidence.casefold() not in description.casefold():
            print("That quote was not found in the displayed job description; skill not added.")
            continue
        selected[skill.skill_id] = {"name": skill.canonical_name, "canonical_id": skill.skill_id, "evidence": evidence}
    values = list(selected.values())
    return (
        {"skills": values, "unresolved_skills": []},
        [item["canonical_id"] for item in values],
        [item["name"] for item in values],
    )


def review(
    candidates_path: str | Path,
    annotations_path: str | Path,
    *,
    candidate_ids: list[str] | None = None,
) -> None:
    examples = load_examples(candidates_path)
    candidate_by_id = {example.example_id: example for example in examples}
    if len(candidate_by_id) != len(examples):
        raise ValueError("Duplicate candidate IDs in candidates file")
    candidate_id_set = set(candidate_by_id)
    selected_ids: list[str] | None = None
    if candidate_ids is not None:
        selected_ids = list(dict.fromkeys(candidate_ids))
        unknown_ids = [example_id for example_id in selected_ids if example_id not in candidate_id_set]
        if unknown_ids:
            raise ValueError(
                "Unknown candidate ID(s) not present in the supplied candidates file: "
                + ", ".join(unknown_ids)
            )

    annotations_file = Path(annotations_path)
    if not annotations_file.exists():
        initial = [annotation_from_candidate(example) for example in examples]
        _safe_write(annotations_file, "".join(item.model_dump_json() + "\n" for item in initial), backup_suffix=".before-human-review.bak")
    existing = load_annotations(annotations_path)
    review_examples = (
        [candidate_by_id[example_id] for example_id in selected_ids]
        if selected_ids is not None
        else examples
    )
    for example in review_examples:
        current = existing.get(example.example_id)
        if selected_ids is None:
            if current and current.reviewer_decision != ReviewStatus.CANDIDATE:
                continue
        elif current and current.reviewer_decision not in {ReviewStatus.CANDIDATE, ReviewStatus.AI_ASSISTED}:
            # Explicit targeting can reopen AI pseudo-labels, but never silently
            # replace a saved human decision.
            print(f"Skipping {example.example_id}: existing {current.reviewer_decision.value} decision is preserved.")
            continue

        base = current or annotation_from_candidate(example)
        print(f"\n{example.example_id} | {example.source_title} | {example.source_companies}")
        user_message = next((message.get("content", "") for message in example.messages if message.get("role") == "user"), "")
        print(user_message)
        displayed_output = (base.corrected_output or base.proposed_output) if base.reviewer_decision == ReviewStatus.AI_ASSISTED else example.proposed_output
        displayed_skills = displayed_output.get("skills", []) if isinstance(displayed_output, dict) else []
        if base.reviewer_decision == ReviewStatus.AI_ASSISTED:
            print("AI-assisted suggested skills (pseudo-labels):")
        else:
            print("Extracted skills:")
        print(", ".join(str(item.get("name", "")) for item in displayed_skills if isinstance(item, dict)) or "(none)")
        print("Canonical IDs:", ", ".join(base.canonical_skill_ids if base.reviewer_decision == ReviewStatus.AI_ASSISTED else example.canonical_skill_ids) or "(none)")
        print("Evidence snippets:")
        for snippet in example.original_evidence:
            print(f"  - {snippet}")
        print("Review the full job text and each evidence quote before deciding.")
        decision = input("Decision [a]ccept/[r]eject/[c]orrect/[s]kip/[q]uit: ").strip().lower()
        if decision == "q":
            break
        if decision == "s":
            continue
        status = {"a": ReviewStatus.REVIEWED, "r": ReviewStatus.REJECTED, "c": ReviewStatus.REVIEWED}.get(decision)
        if status is None:
            continue
        reviewer = input("Reviewer ID: ").strip()
        if not reviewer:
            print("Review not saved: reviewer ID is required.")
            continue
        notes = input("Review notes (optional): ").strip()
        corrected = None
        canonical_skill_ids = None
        extracted_skills = None
        if decision == "c":
            initial_output = (base.corrected_output or base.proposed_output) if base.reviewer_decision == ReviewStatus.AI_ASSISTED else None
            corrected, canonical_skill_ids, extracted_skills = _correct_output(example, initial_output)
        action = {"a": "accept", "r": "reject", "c": "correct"}[decision]
        human_review = {
            "reviewer": reviewer,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision": action,
            "notes": notes,
        }
        if base.reviewer_decision == ReviewStatus.AI_ASSISTED:
            human_review["ai_assisted_snapshot"] = {
                "output": base.corrected_output or base.proposed_output,
                "canonical_skill_ids": list(base.canonical_skill_ids),
                "extracted_skills": list(base.extracted_skills),
                "review_notes": base.review_notes,
            }
        prior_notes = base.review_notes
        combined_notes = []
        if prior_notes:
            combined_notes.append(f"Prior annotation notes: {prior_notes}")
        if notes:
            combined_notes.append(f"Human review notes: {notes}")
        record = base.model_copy(update={
            "reviewer_decision": status,
            "corrected_output": corrected if corrected is not None else base.corrected_output,
            "review_notes": "\n".join(combined_notes) or None,
            "reviewer": reviewer,
            "canonical_skill_ids": canonical_skill_ids if canonical_skill_ids is not None else base.canonical_skill_ids,
            "extracted_skills": extracted_skills if extracted_skills is not None else base.extracted_skills,
            "proposed_output": base.proposed_output,
            "provenance": {**base.provenance, "user_content": user_message, "human_review": human_review},
        })
        try:
            validate_annotation(record, candidate_ids=candidate_id_set)
        except ValueError as error:
            print(f"Review not saved: {error}")
            continue
        save_annotation(record, annotations_path, candidate_ids=candidate_id_set)
        existing[record.example_id] = record


def main() -> int:
    parser = argparse.ArgumentParser(description="Review Future Skills candidate examples and resume later.")
    parser.add_argument("--candidates", type=Path, default=Path("future_skills/data/train.jsonl"))
    parser.add_argument("--annotations", type=Path, default=Path("future_skills/data/train_reviews.jsonl"))
    args = parser.parse_args()
    review(args.candidates, args.annotations)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
