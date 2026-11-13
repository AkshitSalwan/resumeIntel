from __future__ import annotations

import json
import hashlib
from pathlib import Path

from _bootstrap import ROOT
from future_skills.train import _validate_gold_data
from future_skills.annotation import _safe_write
from src.evaluation.metrics import extraction_metrics


def _predict(adapter_dir: Path, records: list[dict], base_model: str) -> list[dict]:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    tokenizer = AutoTokenizer.from_pretrained(adapter_dir)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=compute_dtype,
    )
    model = AutoModelForCausalLM.from_pretrained(base_model, quantization_config=quantization_config, torch_dtype=compute_dtype, device_map="auto")
    model = PeftModel.from_pretrained(model, adapter_dir)
    predictions = []
    model.eval()
    with torch.inference_mode():
        for record in records:
            messages = record["messages"]
            prompt = tokenizer.apply_chat_template(messages[:-1], tokenize=True, add_generation_prompt=True, return_tensors="pt").to(model.device)
            generated = model.generate(prompt, max_new_tokens=512, do_sample=False, pad_token_id=tokenizer.pad_token_id)
            raw = tokenizer.decode(generated[0][prompt.shape[-1]:], skip_special_tokens=True)
            try:
                output = json.loads(raw)
            except json.JSONDecodeError:
                output = {}
            skills = output.get("skills", []) if isinstance(output, dict) else []
            predictions.append({"skills": skills if isinstance(skills, list) else [], "canonical_skill_ids": [str(item["canonical_id"]) for item in skills if isinstance(item, dict) and item.get("canonical_id")]})
    return predictions


def _gold_prediction_records(gold_records: list[dict], candidates_by_id: dict[str, dict]) -> list[dict]:
    """Build inference prompts from held-out source postings, never gold labels."""
    prompts = []
    for record in gold_records:
        candidate = candidates_by_id.get(record.get("example_id"))
        if candidate is None:
            raise ValueError(f"Gold candidate text is missing: {record.get('example_id')}")
        messages = candidate.get("messages")
        if not isinstance(messages, list) or [message.get("role") for message in messages] != ["system", "user", "assistant"]:
            raise ValueError(f"Gold candidate has invalid chat messages: {record.get('example_id')}")
        prompts.append({"example_id": record["example_id"], "messages": messages})
    return prompts


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate a trained adapter on the held-out gold set once.")
    parser.add_argument("--adapter", type=Path, default=ROOT / "artifacts" / "future_skills" / "adapter")
    parser.add_argument("--gold", type=Path, default=ROOT / "future_skills" / "data" / "gold.jsonl")
    parser.add_argument("--candidates", type=Path, default=ROOT / "future_skills" / "data" / "test.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "future_skills" / "gold_metrics.json")
    parser.add_argument("--base-model", default="Qwen/Qwen3-4B-Instruct-2507")
    args = parser.parse_args()

    if not args.adapter.is_dir():
        raise FileNotFoundError(f"Adapter directory not found: {args.adapter}")
    gold, errors = _validate_gold_data(args.gold)
    if errors:
        raise ValueError("Gold dataset validation failed: " + "; ".join(errors))
    raw_records = [json.loads(line) for line in args.gold.read_text(encoding="utf-8").splitlines() if line.strip()]
    candidate_rows = [json.loads(line) for line in args.candidates.read_text(encoding="utf-8").splitlines() if line.strip()]
    candidate_by_id = {row.get("example_id"): row for row in candidate_rows}
    missing_candidates = [record.example_id for record in gold if record.example_id not in candidate_by_id]
    if missing_candidates:
        raise ValueError(f"Gold candidate text is missing for {len(missing_candidates)} example(s).")
    invalid_gold_reference_evidence = []
    for record in gold:
        candidate = candidate_by_id[record.example_id]
        if str(candidate.get("source_job_id")) != str(record.source_job_id):
            raise ValueError(f"Gold candidate source_job_id mismatch: {record.example_id}")
        if (candidate.get("source_companies") or [None])[0] != record.company:
            raise ValueError(f"Gold candidate company mismatch: {record.example_id}")
        user_text = next(message["content"] for message in candidate["messages"] if message["role"] == "user")
        target = record.corrected_output or record.proposed_output
        skills = target.get("skills", []) if isinstance(target, dict) else []
        ids = [skill.get("canonical_id") for skill in skills if isinstance(skill, dict)]
        if len(ids) != len(skills) or set(ids) != set(record.canonical_skill_ids) or len(ids) != len(set(ids)):
            raise ValueError(f"Gold labels have invalid canonical IDs: {record.example_id}")
        if any(not isinstance(skill.get("evidence"), str) or skill["evidence"] not in user_text for skill in skills):
            invalid_gold_reference_evidence.append(record.example_id)
    predictions = _predict(args.adapter, _gold_prediction_records(raw_records, candidate_by_id), args.base_model)
    references = []
    user_texts = []
    for record in raw_records:
        target = record.get("corrected_output") or record.get("proposed_output") or {}
        references.append({"canonical_skill_ids": record.get("canonical_skill_ids", []), "skills": target.get("skills", [])})
        candidate_messages = candidate_by_id[record["example_id"]]["messages"]
        user_texts.append(next(message["content"] for message in candidate_messages if message["role"] == "user"))
    metrics = extraction_metrics(references, predictions, user_texts)
    result = {
        "status": "complete",
        "dataset": "gold",
        "gold_examples": len(gold),
        "metrics": metrics,
        "gold_reference_integrity": {
            "examples_with_non_substring_reference_evidence": len(invalid_gold_reference_evidence),
            "affected_example_ids": invalid_gold_reference_evidence,
            "note": "Reference evidence issues are reported separately; extraction metrics are not scored against evidence snippets.",
        },
        "gold_used_for_training_or_selection": False,
        "adapter": str(args.adapter),
        "base_model": args.base_model,
    }
    _safe_write(args.output, json.dumps(result, indent=2))
    metadata_path = args.adapter.parent / "training_metadata.json"
    if metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["gold_evaluation_performed"] = True
        metadata["gold_metrics"] = metrics
        metadata["gold_reference_integrity"] = result["gold_reference_integrity"]
        metadata.setdefault("dataset_counts", {})["gold"] = len(gold)
        metadata.setdefault("dataset_sha256", {})["gold"] = hashlib.sha256(args.gold.read_bytes()).hexdigest()
        metadata.setdefault("split_information", {})["gold"] = "test held out for final evaluation"
        _safe_write(metadata_path, json.dumps(metadata, indent=2), backup_suffix=".before-gold-evaluation.bak")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
