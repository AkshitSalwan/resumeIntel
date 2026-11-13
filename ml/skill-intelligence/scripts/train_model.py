from __future__ import annotations

import json
import argparse
from pathlib import Path

from _bootstrap import ROOT
from future_skills.train import training_gate
from src.training.hardware import inspect_hardware
from src.training.train import preflight_model_loading, train


def main() -> int:
    parser = argparse.ArgumentParser(description="Run or preflight Future Skills QLoRA training on CUDA.")
    parser.add_argument("--check-only", action="store_true", help="Validate CUDA, pinned runtime, tokenizer, Qwen model weights, NF4, and PEFT without training.")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--resume-from-checkpoint")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    train_file = ROOT / "future_skills" / "data" / "train_sft.jsonl"
    validation_file = ROOT / "future_skills" / "data" / "validation_sft.jsonl"
    gold_file = ROOT / "future_skills" / "data" / "gold.jsonl"
    report_file = ROOT / "future_skills" / "data" / "annotation_report.json"
    output_dir = args.output_dir or ROOT / "artifacts" / "future_skills"

    gate = training_gate(
        report_file,
        training_data_path=train_file,
        validation_data_path=validation_file,
        gold_data_path=gold_file,
    )
    print(json.dumps({"training_gate": gate}, indent=2))

    if gate.get("status") != "ready_for_gpu_runtime":
        print("Training blocked: dataset readiness checks failed.")
        return 2

    hardware = inspect_hardware()
    print(json.dumps({"hardware": hardware}, indent=2))

    if not hardware.get("cuda"):
        print("Training requires a CUDA GPU. Run this script in Kaggle with GPU enabled.")
        return 2

    if args.check_only:
        result = preflight_model_loading(args.config)
        print(json.dumps({"model_preflight": result}, indent=2))
        return 0

    metadata = train(
        train_file=train_file,
        validation_file=validation_file,
        output_dir=output_dir,
        config_path=args.config,
        resume_from_checkpoint=args.resume_from_checkpoint,
    )
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
