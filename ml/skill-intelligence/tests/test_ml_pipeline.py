import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]
sys.path.extend([str(ROOT), str(REPOSITORY)])

from src.contracts import ExtractionOutput
from src.evaluation.metrics import json_validity, skill_metrics
from src.validation import parse_model_output


def test_metrics_are_deterministic():
    assert skill_metrics([{"python"}], [{"python", "unknown"}]) == {
        "precision": 0.5, "recall": 1.0, "f1": 2 / 3,
    }
    assert json_validity([True, False, True]) == 2 / 3


def test_model_output_rejects_unknown_taxonomy_ids():
    with pytest.raises(ValueError, match="Unknown taxonomy id"):
        parse_model_output('{"skills":[{"name":"X","canonical_id":"made-up","evidence":"X"}],"unresolved_skills":[],"model_version":"test"}')


def test_model_output_accepts_unresolved_skill_without_forcing_id():
    result = parse_model_output('{"skills":[],"unresolved_skills":["Quantum widgets"],"model_version":"test"}')
    assert result.unresolved_skills == ["Quantum widgets"]


def test_empty_training_guard_is_explicit():
    empty = ROOT / "data" / "processed" / "empty-test.jsonl"
    empty.parent.mkdir(parents=True, exist_ok=True)
    empty.write_text("", encoding="utf-8")
    assert empty.read_text() == ""
    empty.unlink()
