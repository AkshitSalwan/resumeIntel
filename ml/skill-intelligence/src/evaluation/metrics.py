from __future__ import annotations

from collections.abc import Iterable


def skill_metrics(expected: Iterable[set[str]], predicted: Iterable[set[str]]) -> dict[str, float]:
    expected_sets, predicted_sets = list(expected), list(predicted)
    true_positive = sum(len(actual & guess) for actual, guess in zip(expected_sets, predicted_sets))
    false_positive = sum(len(guess - actual) for actual, guess in zip(expected_sets, predicted_sets))
    false_negative = sum(len(actual - guess) for actual, guess in zip(expected_sets, predicted_sets))
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
    }


def json_validity(valid: Iterable[bool]) -> float:
    values = list(valid)
    return sum(values) / len(values) if values else 0.0


def extraction_metrics(references: Iterable[dict], predictions: Iterable[dict], user_texts: Iterable[str]) -> dict[str, float | int]:
    refs, preds, texts = list(references), list(predictions), list(user_texts)
    count = min(len(refs), len(preds), len(texts))
    ref_ids = [set(str(item) for item in row.get("canonical_skill_ids", [])) for row in refs[:count]]
    pred_ids = [set(str(item) for item in row.get("canonical_skill_ids", [])) for row in preds[:count]]
    result = skill_metrics(ref_ids, pred_ids)
    evidence_items = 0
    valid_evidence = 0
    for prediction, text in zip(preds[:count], texts[:count]):
        for skill in prediction.get("skills", []) if isinstance(prediction, dict) else []:
            evidence_items += 1
            quote = skill.get("evidence") if isinstance(skill, dict) else None
            valid_evidence += int(isinstance(quote, str) and bool(quote) and quote in text)
    result.update({
        "examples": count,
        "evidence_validity": valid_evidence / evidence_items if evidence_items else 0.0,
        "evidence_items": evidence_items,
    })
    return result
