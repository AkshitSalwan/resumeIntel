import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = ROOT.parents[1]
sys.path.extend([str(ROOT), str(REPOSITORY)])

from future_skills.data import build_candidate_examples, split_by_company
from future_skills.annotation import ai_pre_review_validation, annotation_from_candidate, export_ai_assisted_data, export_gold, export_training_data, load_annotations, quality_report, save_annotation
from future_skills.inference import FutureSkillsUnavailable, InferenceRequest, infer
from future_skills.schemas import AnnotationRecord, ModelConfig, ReviewStatus, TaskType
from future_skills.validation import parse_model_output, require_evidence, validate_annotation, validate_example
from future_skills.train import training_gate
from future_skills.train import _validate_sft_data, _validate_training_data
from src.evaluation.metrics import extraction_metrics
from future_skills.annotate import _correct_output
from future_skills import workflow
from future_skills.annotate import review as review_candidates


def _input(path: Path) -> None:
    path.write_text(json.dumps({
        "record_id": "record-1",
        "source": "greenhouse",
        "source_job_id": "job-1",
        "company": "Example",
        "title": "Engineer",
        "description": "Python and Docker experience required.",
        "job_url": "https://example.test/jobs/1",
        "collection_timestamp": "2026-11-11T00:00:00Z",
    }) + "\n", encoding="utf-8")


def test_candidate_examples_preserve_provenance_and_weak_label_status(tmp_path):
    source = tmp_path / "jobs.jsonl"
    _input(source)
    examples = build_candidate_examples(source)
    assert len(examples) == 1
    assert examples[0].human_review_status.value == "candidate"
    assert examples[0].source_record_ids == ["record-1"]
    assert "python" in examples[0].canonical_skill_ids


def test_company_split_prevents_company_leakage():
    from future_skills.schemas import FutureSkillsExample, ReviewStatus
    rows = [
        FutureSkillsExample(example_id=str(i), task_type=TaskType.SKILL_EXTRACTION, messages=[], source_companies=[company], labeling_method="weak", human_review_status=ReviewStatus.CANDIDATE)
        for i, company in enumerate(["A", "A", "B", "B", "C"])
    ]
    splits = split_by_company(rows)
    memberships = {item.source_companies[0]: split for split, items in splits.items() for item in items}
    assert len(memberships) == 3
    assert all(sum(any(item.source_companies[0] == company for item in items) for items in splits.values()) == 1 for company in memberships)


def test_weak_labels_cannot_be_gold_and_missing_evidence_is_rejected():
    from future_skills.schemas import FutureSkillsExample, ReviewStatus
    example = FutureSkillsExample(example_id="x", task_type=TaskType.SKILL_EXTRACTION, messages=[], labeling_method="weak_dictionary_match", human_review_status=ReviewStatus.GOLD, provenance={"reviewer": "test"})
    with pytest.raises(ValueError, match="Weak dictionary"):
        validate_example(example.model_dump())
    output = parse_model_output('{"task_type":"evidence_interpretation","future_hypotheses":["x"],"model_version":"test"}')
    with pytest.raises(ValueError, match="source evidence"):
        require_evidence(output)


def test_inference_never_falls_back_to_unvalidated_model():
    with pytest.raises(FutureSkillsUnavailable, match="disabled"):
        infer(InferenceRequest(TaskType.SKILL_EXTRACTION, [], "test"), config=ModelConfig())


def test_training_requires_reviewed_gold_data(tmp_path):
    report = tmp_path / "report.json"
    training = tmp_path / "train_sft.jsonl"
    gold = tmp_path / "gold.jsonl"

    report.write_text(json.dumps({"human_reviewed": 0, "gold_evaluation": 0}))
    training.write_text("")
    gold.write_text("")

    result = training_gate(
        report,
        training_data_path=training,
        gold_data_path=gold,
    )
    assert result["status"] == "blocked"


def test_annotation_persists_and_resumes_with_review_metadata(tmp_path):
    source = tmp_path / "jobs.jsonl"
    _input(source)
    candidate = build_candidate_examples(source)[0]
    record = annotation_from_candidate(candidate).model_copy(update={
        "reviewer_decision": ReviewStatus.REVIEWED,
        "reviewer": "reviewer-1",
        "review_notes": "Evidence supports both listed skills.",
    })
    path = tmp_path / "reviews.jsonl"
    save_annotation(record, path, candidate_ids={candidate.example_id})
    assert load_annotations(path)[candidate.example_id].reviewer == "reviewer-1"
    assert quality_report(path, 1)["reviewed_examples"] == 1
    save_annotation(record.model_copy(update={"review_notes": "second save"}), path, candidate_ids={candidate.example_id})
    assert (tmp_path / "reviews.jsonl.before-human-review.bak").exists()


def test_annotation_rejects_bad_ids_duplicates_and_missing_provenance(tmp_path):
    candidate = AnnotationRecord(
        example_id="x", source_job_id="job", company="Example", title="Engineer",
        task_type=TaskType.SKILL_EXTRACTION, canonical_skill_ids=["python", "python"],
        provenance={"source_record_ids": ["record"]},
    )
    with pytest.raises(ValueError, match="Duplicate"):
        validate_annotation(candidate)
    bad = candidate.model_copy(update={"canonical_skill_ids": ["not-real"]})
    with pytest.raises(ValueError, match="Unsupported"):
        validate_annotation(bad)
    missing = candidate.model_copy(update={"canonical_skill_ids": [], "provenance": {}})
    with pytest.raises(ValueError, match="provenance"):
        validate_annotation(missing)


def test_gold_export_rejects_training_overlap_and_preserves_gold_only(tmp_path):
    source = tmp_path / "jobs.jsonl"
    _input(source)
    candidate = build_candidate_examples(source)[0]
    record = annotation_from_candidate(candidate).model_copy(update={
        "reviewer_decision": ReviewStatus.GOLD,
        "reviewer": "reviewer-1",
        "review_notes": "Approved gold example.",
    })
    annotations = tmp_path / "reviews.jsonl"
    save_annotation(record, annotations, candidate_ids={candidate.example_id})
    blocked = export_gold(annotations, tmp_path / "blocked.jsonl", training_ids={candidate.example_id})
    assert blocked["excluded"][0]["reason"] == "not_test_split"
    output = tmp_path / "gold.jsonl"
    record = record.model_copy(update={"split": "test"})
    save_annotation(record, annotations, candidate_ids={candidate.example_id})
    result = export_gold(annotations, output)
    assert result["gold_count"] == 1
    assert output.read_text().count("\n") == 1


def test_gold_export_accepts_reviewed_test_and_reports_exclusions(tmp_path):
    source = tmp_path / "jobs.jsonl"
    _input(source)
    candidate = build_candidate_examples(source)[0].model_copy(update={"split": "test"})
    reviewed = annotation_from_candidate(candidate).model_copy(update={"reviewer_decision": ReviewStatus.REVIEWED, "reviewer": "r1", "review_notes": None})
    rejected = reviewed.model_copy(update={"example_id": "rejected", "reviewer_decision": ReviewStatus.REJECTED, "review_notes": "not supported"})
    path = tmp_path / "reviews.jsonl"
    path.write_text("\n".join(item.model_dump_json() for item in (reviewed, rejected)) + "\n")
    output = tmp_path / "gold.jsonl"
    result = export_gold(path, output, candidate_ids={reviewed.example_id, rejected.example_id})
    assert result["eligible_count"] == 1
    assert result["excluded_count"] == 1
    assert result["excluded"][0]["reason"] == "rejected_by_reviewer"
    exported = json.loads(output.read_text().splitlines()[0])
    assert exported["proposed_output"] == reviewed.proposed_output
    assert exported["reviewer"] == "r1"


def test_gold_export_excludes_train_and_validation_and_duplicate_ids(tmp_path):
    source = tmp_path / "jobs.jsonl"
    _input(source)
    candidate = build_candidate_examples(source)[0].model_copy(update={"split": "test"})
    record = annotation_from_candidate(candidate).model_copy(update={"reviewer_decision": ReviewStatus.REVIEWED, "reviewer": "r1"})
    path = tmp_path / "reviews.jsonl"
    path.write_text(record.model_dump_json() + "\n" + record.model_dump_json() + "\n")
    with pytest.raises(ValueError, match="Duplicate annotation candidate ID"):
        export_gold(path, tmp_path / "gold.jsonl")
    path.write_text(record.model_dump_json() + "\n")
    result = export_gold(path, tmp_path / "gold.jsonl", training_ids={record.example_id})
    assert result["excluded"][0]["reason"] == "training_overlap"


def test_annotation_review_notes_optional_but_reviewer_required():
    record = AnnotationRecord(example_id="x", source_job_id="job", company="Example", title="Engineer", task_type=TaskType.SKILL_EXTRACTION, reviewer_decision=ReviewStatus.REVIEWED, reviewer="r1", provenance={"source_job_id": "job"})
    validate_annotation(record)
    with pytest.raises(ValueError, match="reviewer identity"):
        validate_annotation(record.model_copy(update={"reviewer": None}))


def test_correct_output_picker_resolves_alias_and_requires_description_evidence(monkeypatch, capsys):
    from future_skills.schemas import FutureSkillsExample
    example = FutureSkillsExample(
        example_id="x", task_type=TaskType.SKILL_EXTRACTION,
        messages=[{"role": "user", "content": "Job description: Own upsell and customer retention."}],
        labeling_method="weak_dictionary_match", human_review_status=ReviewStatus.CANDIDATE,
    )
    answers = iter(["upsell", "1", '"Own upsell"', "done"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    output, ids, names = _correct_output(example)
    assert output["skills"][0]["canonical_id"] == "revenue-growth"
    assert output["skills"][0]["evidence"] == "Own upsell"
    assert ids == ["revenue-growth"]
    assert names == ["Revenue Growth"]
    assert "revenue-growth" in capsys.readouterr().out


def test_export_training_uses_reviewed_labels_and_excludes_rejected(tmp_path):
    source = tmp_path / "jobs.jsonl"
    _input(source)
    candidate = build_candidate_examples(source)[0].model_copy(update={"split": "train"})
    candidates_path = tmp_path / "train.jsonl"
    candidates_path.write_text(candidate.model_dump_json() + "\n")
    reviewed = annotation_from_candidate(candidate).model_copy(update={
        "reviewer_decision": ReviewStatus.REVIEWED, "reviewer": "r1", "review_notes": "Checked evidence."
    })
    rejected = reviewed.model_copy(update={"example_id": "rejected", "reviewer_decision": ReviewStatus.REJECTED})
    annotations_path = tmp_path / "reviews.jsonl"
    annotations_path.write_text("\n".join(item.model_dump_json() for item in (reviewed, rejected)) + "\n")
    output_path = tmp_path / "training.jsonl"
    result = export_training_data(candidates_path, annotations_path, output_path)
    assert result["exported"] == 1
    assert result["excluded_examples"] == [{"example_id": "rejected", "reason": "not_reviewed"}]
    exported = json.loads(output_path.read_text().splitlines()[0])
    assert exported["labeling_method"] == "human_reviewed"
    assert exported["human_review_status"] == "reviewed"
    assert exported["provenance"]["reviewer"] == "r1"
    assert json.loads(exported["messages"][-1]["content"]) == reviewed.proposed_output


def test_validation_export_requires_explicit_review_and_exact_evidence(tmp_path):
    source = tmp_path / "validation.jsonl"
    _input(source)
    candidate = build_candidate_examples(source)[0].model_copy(update={"split": "validation"})
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text(candidate.model_dump_json() + "\n")
    pending = annotation_from_candidate(candidate)
    annotations = tmp_path / "annotations.jsonl"
    annotations.write_text(pending.model_dump_json() + "\n")
    output = tmp_path / "validation_sft.jsonl"
    result = export_training_data(candidates, annotations, output, split="validation")
    assert result["exported"] == 0
    reviewed = pending.model_copy(update={"reviewer_decision": ReviewStatus.REVIEWED, "reviewer": "human-1"})
    annotations.write_text(reviewed.model_dump_json() + "\n")
    result = export_training_data(candidates, annotations, output, split="validation")
    assert result["exported"] == 1
    assert json.loads(output.read_text().splitlines()[0])["provenance"]["reviewer"] == "human-1"
    bad_output = {"skills": [{"name": "Python", "canonical_id": "python", "evidence": "not in posting"}], "unresolved_skills": []}
    bad = reviewed.model_copy(update={"corrected_output": bad_output, "canonical_skill_ids": ["python"]})
    annotations.write_text(bad.model_dump_json() + "\n")
    result = export_training_data(candidates, annotations, output, split="validation")
    assert result["exported"] == 0
    assert "exact substring" in result["excluded_examples"][0]["reason"]


def test_training_gate_checks_validation_and_source_job_leakage(tmp_path):
    report = tmp_path / "report.json"
    report.write_text("{}")
    train = tmp_path / "train.jsonl"
    validation = tmp_path / "validation.jsonl"
    gold = tmp_path / "gold.jsonl"
    base = json.loads((Path(__file__).parent.parent / "data" / "train_sft.jsonl").read_text().splitlines()[0])
    # Small record counts exercise the gate's leakage checks before threshold checks.
    val = dict(base, example_id="validation-x", split="validation", source_job_id=base["source_job_id"])
    train.write_text(json.dumps(base) + "\n")
    validation.write_text(json.dumps(val) + "\n")
    gold.write_text("")
    result = training_gate(report, training_data_path=train, validation_data_path=validation, gold_data_path=gold)
    assert any("source_job_id overlap" in error for error in result["errors"])
    assert any("validation" in error.lower() for error in result["errors"])


def test_training_gate_rejects_ai_pseudo_labels_and_missing_reviewer_provenance(tmp_path):
    source = tmp_path / "jobs.jsonl"
    _input(source)
    candidate = build_candidate_examples(source)[0].model_copy(update={"split": "train"})
    ai_example = candidate.model_copy(update={
        "human_review_status": ReviewStatus.AI_ASSISTED,
        "labeling_method": "ai_assisted_pseudo_label",
        "provenance": {**candidate.provenance, "ai_assisted": {"pseudo_label": True}},
    })
    ai_path = tmp_path / "ai.jsonl"
    ai_path.write_text(ai_example.model_dump_json() + "\n")
    _, ai_errors = _validate_training_data(ai_path)
    assert any("not human-reviewed" in error for error in ai_errors)

    human_example = candidate.model_copy(update={
        "human_review_status": ReviewStatus.REVIEWED,
        "labeling_method": "human_reviewed",
        "provenance": {**candidate.provenance, "source_record_ids": ["record-1"]},
    })
    human_path = tmp_path / "human.jsonl"
    human_path.write_text(human_example.model_dump_json() + "\n")
    _, provenance_errors = _validate_training_data(human_path)
    assert any("human reviewer provenance is missing" in error for error in provenance_errors)


def test_validation_sft_missing_and_bad_split_are_reported(tmp_path):
    examples, errors = _validate_sft_data(tmp_path / "missing.jsonl", split="validation")
    assert examples == []
    assert errors


def test_extraction_metrics_canonical_ids_and_evidence_validity():
    result = extraction_metrics(
        [{"canonical_skill_ids": ["python", "docker"]}],
        [{"canonical_skill_ids": ["python", "aws"], "skills": [{"evidence": "Python"}, {"evidence": "AWS"}]}],
        ["Python and Docker"],
    )
    assert result["precision"] == 0.5
    assert result["recall"] == 0.5
    assert result["evidence_validity"] == 0.5


def test_workflow_cli_import_and_help(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["workflow", "--help"])
    with pytest.raises(SystemExit) as error:
        workflow.main()
    assert error.value.code == 0
    assert "export-validation" in capsys.readouterr().out


def test_validation_workflow_excludes_training_and_gold_id_or_job_leakage(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source.jsonl"
    _input(source)
    candidate = build_candidate_examples(source)[0].model_copy(update={"split": "validation"})
    ai_source = tmp_path / "ai_jobs.jsonl"
    ai_row = json.loads(source.read_text().splitlines()[0])
    ai_row.update({"record_id": "record-ai", "source_job_id": "job-ai"})
    ai_source.write_text(json.dumps(ai_row) + "\n")
    ai_candidate = build_candidate_examples(ai_source)[0].model_copy(update={"split": "validation"})
    candidates = tmp_path / "validation.jsonl"
    candidates.write_text(candidate.model_dump_json() + "\n" + ai_candidate.model_dump_json() + "\n")
    annotation = annotation_from_candidate(candidate).model_copy(update={
        "reviewer_decision": ReviewStatus.REVIEWED, "reviewer": "human-1",
    })
    annotations = tmp_path / "validation_annotations.jsonl"
    annotations.write_text(annotation.model_dump_json() + "\n")
    training = tmp_path / "train_sft.jsonl"
    train_overlap = candidate.model_copy(update={"split": "train", "human_review_status": ReviewStatus.REVIEWED, "labeling_method": "human_reviewed"})
    training.write_text(train_overlap.model_dump_json() + "\n")
    gold = tmp_path / "gold.jsonl"
    gold.write_text("")
    output = tmp_path / "validation_sft.jsonl"

    monkeypatch.setattr("sys.argv", ["workflow", "export-validation", "--candidates", str(candidates), "--annotations", str(annotations), "--output", str(output), "--training", str(training), "--gold", str(gold)])
    assert workflow.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["exported"] == 0
    assert report["excluded_examples"][0]["reason"] == "cross_split_overlap"

    # Gold annotations are schema-loaded and their source job IDs also block export.
    unrelated_train = candidate.model_copy(update={"example_id": "train-other", "source_job_id": "job-train", "split": "train"})
    training.write_text(unrelated_train.model_dump_json() + "\n")
    gold_record = annotation_from_candidate(candidate).model_copy(update={
        "example_id": "gold-other", "reviewer_decision": ReviewStatus.GOLD,
        "reviewer": "gold-reviewer", "split": "test",
    })
    gold.write_text(gold_record.model_dump_json() + "\n")
    monkeypatch.setattr("sys.argv", ["workflow", "export-validation", "--candidates", str(candidates), "--annotations", str(annotations), "--output", str(output), "--training", str(training), "--gold", str(gold)])
    assert workflow.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["exported"] == 0
    assert report["excluded_examples"][0]["reason"] == "cross_split_overlap"


def test_validation_export_duplicate_ids_and_schema_aware_gold_loading(tmp_path):
    source = tmp_path / "source.jsonl"
    _input(source)
    candidate = build_candidate_examples(source)[0].model_copy(update={"split": "validation"})
    candidates = tmp_path / "validation.jsonl"
    candidates.write_text(candidate.model_dump_json() + "\n" + candidate.model_dump_json() + "\n")
    with pytest.raises(ValueError, match="Duplicate candidate IDs"):
        export_training_data(candidates, tmp_path / "empty.jsonl", tmp_path / "out.jsonl", split="validation")

    # AnnotationRecord is the persisted gold schema; workflow must use its loader.
    gold_record = annotation_from_candidate(candidate).model_copy(update={"split": "test", "reviewer_decision": ReviewStatus.GOLD, "reviewer": "gold-reviewer"})
    gold = tmp_path / "gold.jsonl"
    gold.write_text(gold_record.model_dump_json() + "\n")
    assert load_annotations(gold)[candidate.example_id].source_job_id == candidate.source_job_id


def test_review_initializes_missing_file_and_preserves_existing_human_decisions(tmp_path, monkeypatch):
    source = tmp_path / "jobs.jsonl"
    _input(source)
    candidate = build_candidate_examples(source)[0]
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text(candidate.model_dump_json() + "\n")
    annotations = tmp_path / "reviews.jsonl"

    monkeypatch.setattr("builtins.input", lambda _: "q")
    review_candidates(candidates, annotations)
    initial = load_annotations(annotations)
    assert initial[candidate.example_id].reviewer_decision == ReviewStatus.CANDIDATE

    reviewed = initial[candidate.example_id].model_copy(update={"reviewer_decision": ReviewStatus.REVIEWED, "reviewer": "human-1", "review_notes": "kept"})
    save_annotation(reviewed, annotations, candidate_ids={candidate.example_id})
    before = annotations.read_text(encoding="utf-8")
    monkeypatch.setattr("builtins.input", lambda _: pytest.fail("reviewed record should be skipped"))
    review_candidates(candidates, annotations)
    assert annotations.read_text(encoding="utf-8") == before


def _ai_assisted_record(candidate):
    output = {
        "skills": [{"name": "Python", "canonical_id": "python", "evidence": "Python and Docker experience required."}],
        "unresolved_skills": [],
    }
    base = annotation_from_candidate(candidate)
    return base.model_copy(update={
        "reviewer_decision": ReviewStatus.AI_ASSISTED,
        "corrected_output": output,
        "canonical_skill_ids": ["python"],
        "extracted_skills": ["Python"],
        "review_notes": "AI pseudo-label note.",
        "provenance": {
            **base.provenance,
            "ai_assisted": {
                "system_id": "test-ai-system",
                "timestamp": "2026-01-01T00:00:00Z",
                "method": "test extraction",
                "pseudo_label": True,
                "independent_human_review": False,
            },
        },
    })


def test_targeted_review_cli_selects_only_requested_id_and_preserves_others(tmp_path, monkeypatch):
    source = tmp_path / "jobs.jsonl"
    _input(source)
    first = json.loads(source.read_text(encoding="utf-8").splitlines()[0])
    second = {**first, "record_id": "record-2", "source_job_id": "job-2", "title": "Engineer Two"}
    source.write_text(json.dumps(first) + "\n" + json.dumps(second) + "\n", encoding="utf-8")
    candidates_list = [item.model_copy(update={"split": "validation"}) for item in build_candidate_examples(source)]
    candidates = tmp_path / "validation.jsonl"
    candidates.write_text("\n".join(item.model_dump_json() for item in candidates_list) + "\n", encoding="utf-8")
    selected = annotation_from_candidate(candidates_list[0])
    unselected = _ai_assisted_record(candidates_list[1])
    annotations = tmp_path / "annotations.jsonl"
    annotations.write_text("\n".join(item.model_dump_json() for item in (selected, unselected)) + "\n", encoding="utf-8")

    answers = iter(["a", "human-1", "Reviewed selected record."])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr("sys.argv", [
        "workflow", "review", "--candidates", str(candidates), "--annotations", str(annotations),
        "--candidate-id", candidates_list[0].example_id,
    ])
    assert workflow.main() == 0

    after = load_annotations(annotations)
    assert after[candidates_list[0].example_id].reviewer_decision == ReviewStatus.REVIEWED
    assert after[candidates_list[1].example_id].model_dump() == unselected.model_dump()


def test_explicit_ai_review_preserves_pseudo_label_provenance_and_requires_human_decision(tmp_path, monkeypatch):
    source = tmp_path / "jobs.jsonl"
    _input(source)
    candidate = build_candidate_examples(source)[0].model_copy(update={"split": "validation"})
    candidates = tmp_path / "validation.jsonl"
    candidates.write_text(candidate.model_dump_json() + "\n", encoding="utf-8")
    ai_record = _ai_assisted_record(candidate)
    annotations = tmp_path / "annotations.jsonl"
    annotations.write_text(ai_record.model_dump_json() + "\n", encoding="utf-8")

    # AI pseudo-labels cannot enter the human-reviewed export before a saved decision.
    output = tmp_path / "validation_sft.jsonl"
    assert export_training_data(candidates, annotations, output, split="validation")["exported"] == 0

    answers = iter(["a", "human-reviewer", "Evidence checked against the full posting."])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    review_candidates(candidates, annotations, candidate_ids=[candidate.example_id])

    reviewed = load_annotations(annotations)[candidate.example_id]
    assert reviewed.reviewer_decision == ReviewStatus.REVIEWED
    assert reviewed.corrected_output == ai_record.corrected_output
    assert reviewed.provenance["ai_assisted"] == ai_record.provenance["ai_assisted"]
    assert reviewed.provenance["ai_assisted"]["independent_human_review"] is False
    assert reviewed.provenance["human_review"]["reviewer"] == "human-reviewer"
    assert reviewed.provenance["human_review"]["decision"] == "accept"
    assert "Evidence checked" in reviewed.provenance["human_review"]["notes"]
    assert "AI pseudo-label note." in reviewed.review_notes
    assert "Evidence checked" in reviewed.review_notes
    assert export_training_data(candidates, annotations, output, split="validation")["exported"] == 1


def test_ai_assisted_correction_preserves_original_pseudo_label_snapshot(tmp_path, monkeypatch):
    source = tmp_path / "jobs.jsonl"
    _input(source)
    candidate = build_candidate_examples(source)[0].model_copy(update={"split": "validation"})
    candidates = tmp_path / "validation.jsonl"
    candidates.write_text(candidate.model_dump_json() + "\n", encoding="utf-8")
    ai_record = _ai_assisted_record(candidate)
    annotations = tmp_path / "annotations.jsonl"
    annotations.write_text(ai_record.model_dump_json() + "\n", encoding="utf-8")
    corrected = {"skills": [{"name": "Docker", "canonical_id": "docker", "evidence": "Docker experience required."}], "unresolved_skills": []}
    monkeypatch.setattr("future_skills.annotate._correct_output", lambda example, initial_output=None: (corrected, ["docker"], ["Docker"]))
    answers = iter(["c", "human-reviewer", "Removed unsupported Python label."])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    review_candidates(candidates, annotations, candidate_ids=[candidate.example_id])
    reviewed = load_annotations(annotations)[candidate.example_id]
    assert reviewed.reviewer_decision == ReviewStatus.REVIEWED
    assert reviewed.corrected_output == corrected
    assert reviewed.proposed_output == ai_record.proposed_output
    assert reviewed.provenance["ai_assisted"] == ai_record.provenance["ai_assisted"]
    assert reviewed.provenance["human_review"]["decision"] == "correct"
    assert reviewed.provenance["human_review"]["ai_assisted_snapshot"]["output"] == ai_record.corrected_output
    assert reviewed.provenance["human_review"]["ai_assisted_snapshot"]["canonical_skill_ids"] == ["python"]


def test_explicit_ai_review_rejection_records_human_decision_and_preserves_ai_output(tmp_path, monkeypatch):
    source = tmp_path / "jobs.jsonl"
    _input(source)
    candidate = build_candidate_examples(source)[0].model_copy(update={"split": "validation"})
    candidates = tmp_path / "validation.jsonl"
    candidates.write_text(candidate.model_dump_json() + "\n", encoding="utf-8")
    ai_record = _ai_assisted_record(candidate)
    annotations = tmp_path / "annotations.jsonl"
    annotations.write_text(ai_record.model_dump_json() + "\n", encoding="utf-8")
    answers = iter(["r", "human-reviewer", "Pseudo-label is not supported."])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    review_candidates(candidates, annotations, candidate_ids=[candidate.example_id])
    rejected = load_annotations(annotations)[candidate.example_id]
    assert rejected.reviewer_decision == ReviewStatus.REJECTED
    assert rejected.corrected_output == ai_record.corrected_output
    assert rejected.provenance["ai_assisted"] == ai_record.provenance["ai_assisted"]
    assert rejected.provenance["human_review"]["decision"] == "reject"
    assert rejected.provenance["human_review"]["ai_assisted_snapshot"]["output"] == ai_record.corrected_output
    assert "Pseudo-label is not supported." in rejected.review_notes


def test_targeted_review_rejects_unknown_ids_without_initializing_annotations(tmp_path):
    source = tmp_path / "jobs.jsonl"
    _input(source)
    candidate = build_candidate_examples(source)[0]
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text(candidate.model_dump_json() + "\n", encoding="utf-8")
    annotations = tmp_path / "annotations.jsonl"
    with pytest.raises(ValueError, match="not present in the supplied candidates file"):
        review_candidates(candidates, annotations, candidate_ids=["not-a-candidate"])
    assert not annotations.exists()


def test_review_cli_accepts_repeatable_candidate_ids(monkeypatch):
    captured = {}
    monkeypatch.setattr("future_skills.annotate.review", lambda candidates, annotations, *, candidate_ids=None: captured.update(ids=candidate_ids))
    monkeypatch.setattr("sys.argv", ["workflow", "review", "--candidate-id", "one", "--candidate-id", "two"])
    assert workflow.main() == 0
    assert captured["ids"] == ["one", "two"]


def test_review_cli_reports_ids_missing_from_candidates_file(tmp_path, monkeypatch, capsys):
    source = tmp_path / "jobs.jsonl"
    _input(source)
    candidate = build_candidate_examples(source)[0]
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text(candidate.model_dump_json() + "\n", encoding="utf-8")
    annotations = tmp_path / "annotations.jsonl"
    monkeypatch.setattr("sys.argv", [
        "workflow", "review", "--candidates", str(candidates), "--annotations", str(annotations),
        "--candidate-id", "missing-id",
    ])
    with pytest.raises(SystemExit) as error:
        workflow.main()
    assert error.value.code == 2
    assert "not present in the supplied candidates file" in capsys.readouterr().err
    assert not annotations.exists()


def test_ai_pre_review_sets_distinct_provenance_and_keeps_exact_relevant_evidence(tmp_path):
    source = tmp_path / "jobs.jsonl"
    source.write_text(json.dumps({
        "record_id": "r1", "source": "ashby", "source_job_id": "j1", "company": "OpenAI",
        "title": "Software Engineer", "description": "About OpenAI: an AI research company. About the role: Build Python services and deploy Docker containers. Required qualifications: Python programming experience.",
    }) + "\n")
    candidate = build_candidate_examples(source)[0].model_copy(update={"split": "validation"})
    candidates = tmp_path / "validation.jsonl"
    candidates.write_text(candidate.model_dump_json() + "\n")
    annotations = tmp_path / "annotations.jsonl"
    annotations.write_text(annotation_from_candidate(candidate).model_dump_json() + "\n")

    result = ai_pre_review_validation(candidates, annotations, system_id="test-system")
    record = load_annotations(annotations)[candidate.example_id]
    assert result["processed"] == 1
    assert record.reviewer_decision == ReviewStatus.AI_ASSISTED
    assert record.reviewer is None
    assert record.split == "validation"
    assert record.provenance["ai_assisted"]["system_id"] == "test-system"
    assert record.provenance["ai_assisted"]["pseudo_label"] is True
    assert record.provenance["ai_assisted"]["independent_human_review"] is False
    assert "artificial-intelligence" not in record.canonical_skill_ids
    assert "python" in record.canonical_skill_ids
    assert all(item["evidence"] in record.provenance["user_content"] for item in record.corrected_output["skills"])
    assert (tmp_path / "annotations.jsonl.before-ai-assisted-review.bak").exists()


def test_ai_pre_review_preserves_existing_human_record_verbatim(tmp_path):
    source = tmp_path / "jobs.jsonl"
    first = {"record_id": "r1", "source": "ashby", "source_job_id": "j1", "company": "OpenAI", "title": "Engineer", "description": "About the role: Build Python services. Required qualifications: Python experience."}
    second = {**first, "record_id": "r2", "source_job_id": "j2"}
    source.write_text(json.dumps(first) + "\n" + json.dumps(second) + "\n")
    candidates = [item.model_copy(update={"split": "validation"}) for item in build_candidate_examples(source)]
    candidate_path = tmp_path / "validation.jsonl"
    candidate_path.write_text("".join(item.model_dump_json() + "\n" for item in candidates))
    human = annotation_from_candidate(candidates[0]).model_copy(update={"reviewer_decision": ReviewStatus.REVIEWED, "reviewer": "human-1", "review_notes": "preserve"})
    pending = annotation_from_candidate(candidates[1])
    human_line = human.model_dump_json()
    annotations = tmp_path / "annotations.jsonl"
    annotations.write_text(human_line + "\n" + pending.model_dump_json() + "\n")
    ai_pre_review_validation(candidate_path, annotations, system_id="test-system")
    result = annotations.read_text().splitlines()
    assert human_line in result
    assert load_annotations(annotations)[candidates[0].example_id].review_notes == "preserve"


def test_ai_assisted_status_rejects_missing_provenance_reviewer_and_bad_evidence(tmp_path):
    source = tmp_path / "jobs.jsonl"
    _input(source)
    candidate = build_candidate_examples(source)[0].model_copy(update={"split": "validation"})
    record = annotation_from_candidate(candidate).model_copy(update={
        "reviewer_decision": ReviewStatus.AI_ASSISTED,
        "corrected_output": {"skills": [{"name": "Python", "canonical_id": "python", "evidence": "fabricated"}], "unresolved_skills": []},
        "canonical_skill_ids": ["python"],
        "provenance": {"source_job_id": candidate.source_job_id, "user_content": "Python"},
    })
    with pytest.raises(ValueError, match="system_id"):
        validate_annotation(record)
    valid_ai = record.model_copy(update={"provenance": {"source_job_id": candidate.source_job_id, "user_content": "Python", "ai_assisted": {"system_id": "s", "timestamp": "now", "method": "m", "pseudo_label": True}}})
    with pytest.raises(ValueError, match="exact substring"):
        validate_annotation(valid_ai)
    bad_taxonomy = valid_ai.model_copy(update={"canonical_skill_ids": ["made-up"], "corrected_output": {"skills": [{"name": "X", "canonical_id": "made-up", "evidence": "Python"}], "unresolved_skills": []}})
    with pytest.raises(ValueError, match="Unsupported"):
        validate_annotation(bad_taxonomy)


def test_ai_export_is_separate_from_human_export_and_checks_leakage(tmp_path):
    source = tmp_path / "jobs.jsonl"
    _input(source)
    candidate = build_candidate_examples(source)[0].model_copy(update={"split": "validation"})
    ai_source = tmp_path / "ai_jobs.jsonl"
    ai_row = json.loads(source.read_text().splitlines()[0])
    ai_row.update({"record_id": "record-ai", "source_job_id": "job-ai"})
    ai_source.write_text(json.dumps(ai_row) + "\n")
    ai_candidate = build_candidate_examples(ai_source)[0].model_copy(update={"split": "validation"})
    candidates = tmp_path / "validation.jsonl"
    candidates.write_text(candidate.model_dump_json() + "\n" + ai_candidate.model_dump_json() + "\n")
    human = annotation_from_candidate(candidate).model_copy(update={"reviewer_decision": ReviewStatus.REVIEWED, "reviewer": "human-1"})
    ai = annotation_from_candidate(ai_candidate).model_copy(update={
        "reviewer_decision": ReviewStatus.AI_ASSISTED,
        "reviewer": None,
        "corrected_output": ai_candidate.proposed_output,
        "provenance": {**annotation_from_candidate(ai_candidate).provenance, "ai_assisted": {"system_id": "s", "timestamp": "t", "method": "m", "pseudo_label": True, "independent_human_review": False}},
    })
    annotations = tmp_path / "annotations.jsonl"
    annotations.write_text(human.model_dump_json() + "\n" + ai.model_dump_json() + "\n")
    human_out = tmp_path / "human.jsonl"
    ai_out = tmp_path / "ai.jsonl"
    assert export_training_data(candidates, annotations, human_out, split="validation")["exported"] == 1
    assert export_ai_assisted_data(candidates, annotations, ai_out)["exported"] == 1
    ai_exported = json.loads(ai_out.read_text().splitlines()[0])
    assert ai_exported["human_review_status"] == "ai_assisted"
    assert ai_exported["provenance"]["ai_assisted"]["pseudo_label"] is True
    assert export_ai_assisted_data(candidates, annotations, tmp_path / "leaked.jsonl", excluded_ids={ai_candidate.source_job_id})["exported"] == 0
    assert export_ai_assisted_data(candidates, annotations, tmp_path / "id-leaked.jsonl", excluded_ids={ai_candidate.example_id})["exported"] == 0
    assert export_ai_assisted_data(candidates, annotations, tmp_path / "company-leaked.jsonl", excluded_companies={"Example"})["exported"] == 0


def test_ai_assisted_report_counts_candidates_and_human_separately(tmp_path):
    path = tmp_path / "annotations.jsonl"
    base = AnnotationRecord(example_id="a", source_job_id="j1", company="OpenAI", title="Role", task_type=TaskType.SKILL_EXTRACTION, split="validation", provenance={"source_job_id": "j1"})
    ai = base.model_copy(update={"example_id": "b", "source_job_id": "j2", "reviewer_decision": ReviewStatus.AI_ASSISTED, "provenance": {"source_job_id": "j2", "ai_assisted": {"pseudo_label": True, "uncertain": True}}})
    human = base.model_copy(update={"example_id": "c", "source_job_id": "j3", "reviewer_decision": ReviewStatus.REVIEWED, "reviewer": "human"})
    path.write_text("\n".join(item.model_dump_json() for item in (base, ai, human)) + "\n")
    report = quality_report(path, 3)
    assert report["candidate_examples"] == 1
    assert report["ai_assisted_examples"] == 1
    assert report["human_reviewed_examples"] == 1
    assert report["ai_assisted_uncertain_examples"] == 1
    assert report["ai_assisted_labels_are_human_verified"] is False
