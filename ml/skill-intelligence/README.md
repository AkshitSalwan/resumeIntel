# Qwen3-4B skill intelligence

This is an isolated, GPU-oriented QLoRA pipeline for structured skill
extraction. It does not forecast future demand and does not use private
ResumeIntel data.

## Environment

Use Python 3.11 or 3.12 in Kaggle or Lightning AI. Install the pinned
requirements only in this isolated environment:

```bash
python3.11 -m venv .venv-qwen
source .venv-qwen/bin/activate
python -m pip install -r ml/skill-intelligence/requirements.txt
```

The pins are a starting compatibility set, not evidence that a training run
has succeeded. `scripts/train_model.py` performs hardware and data checks before
launching training.

## Future Skills training workflow

The current source files contain 56 reviewed training examples (Airbnb and
Anthropic), 5 human-reviewed validation annotations, 112 separately marked
AI-assisted validation pseudo-labels, and 29 held-out Stripe gold examples.
`validation_ai_sft.jsonl` is separate and is never accepted by the human
validation gate or passed to training. Training is currently blocked until at
least 10 independently human-reviewed examples are exported to
`validation_sft.jsonl`. The gold set must remain unused for training,
checkpoint choice, and tuning.

Run dataset review/export and readiness checks locally from the
`ml/skill-intelligence` directory. These commands do not need ML/GPU
dependencies:

```bash
python -m future_skills.workflow review \
  --candidates future_skills/data/validation.jsonl \
  --annotations future_skills/data/validation_annotations.jsonl
python -m future_skills.workflow export-validation \
  --candidates future_skills/data/validation.jsonl \
  --annotations future_skills/data/validation_annotations.jsonl \
  --output future_skills/data/validation_sft.jsonl
python -m future_skills.train \
  --dataset-report future_skills/data/annotation_report.json \
  --training-data future_skills/data/train_sft.jsonl \
  --validation-data future_skills/data/validation_sft.jsonl \
  --gold-data future_skills/data/gold.jsonl
```

The minimum reviewed validation count defaults to 10 and is configurable with
`--min-reviewed-validation`; train and gold thresholds are configurable too.
The gate separately reports training readiness and final-evaluation readiness.
No `validation_sft.jsonl` is checked in until the human review/export step is
performed.

For GPU training, use the pinned Python 3.11/3.12 environment in Kaggle with
GPU enabled. Upload the reviewed `train_sft.jsonl`, `validation_sft.jsonl`,
`gold.jsonl`, `test.jsonl`, and the matching annotation report. Never substitute
`validation_ai_sft.jsonl` for the human-reviewed validation file.

### Kaggle runbook

Attach the project files (or a versioned dataset containing them) to a Kaggle
notebook, enable **GPU** in notebook settings, and set internet access on so the
public Qwen checkpoint can be downloaded. In the examples below, replace
`/kaggle/working/resumeIntel` with the extracted project directory if it differs.

```bash
cd /kaggle/working/resumeIntel/ml/skill-intelligence
python --version  # use Python 3.11 or 3.12
python -m pip install -r requirements.txt
python -m future_skills.train \
  --dataset-report future_skills/data/annotation_report.json \
  --training-data future_skills/data/train_sft.jsonl \
  --validation-data future_skills/data/validation_sft.jsonl \
  --gold-data future_skills/data/gold.jsonl
python scripts/train_model.py --check-only
python scripts/train_model.py
```

The readiness command requires 50 reviewed training, 10 reviewed validation,
and 20 gold examples by default. Thresholds can be lowered or raised explicitly
for an audit, but the 56/29 set sizes do not bypass missing human validation.
The runtime preflight checks pinned library versions, CUDA, GPU compute
capability, a small bitsandbytes NF4 kernel, Qwen3 config, tokenizer chat
template, base model weight loading, and PEFT trainable parameters before
training starts. The QLoRA config uses NF4, double quantization, LoRA rank 16,
and gradient checkpointing. Devices at or below 20 GB use sequence length 512
and gradient accumulation 4; larger devices use sequence length 1024 and
accumulation 8. CUDA support and actual available Kaggle VRAM still depend on
the accelerator assigned to the notebook.

Epoch checkpoints under `artifacts/future_skills/checkpoints/` include Trainer
state and optimizer state. To resume, preserve the Kaggle output directory and
pass the checkpoint path:

```bash
python scripts/train_model.py \
  --resume-from-checkpoint artifacts/future_skills/checkpoints/checkpoint-<step>
```

After training, run final gold evaluation and bundle the adapter and reports:

```bash
python scripts/evaluate_model.py \
  --adapter artifacts/future_skills/adapter \
  --gold future_skills/data/gold.jsonl \
  --candidates future_skills/data/test.jsonl \
  --output artifacts/future_skills/gold_metrics.json
python scripts/export_adapter.py
```

Training loss and validation loss/extraction metrics are written to
`training_metrics.json`; gold metrics are written separately to
`gold_metrics.json` and added to `training_metadata.json` only after final
evaluation. Gold reference-evidence mismatches are reported as an integrity
warning; the existing gold labels are not edited. The export command creates
`artifacts/future_skills/future_skills_adapter.zip` and
`artifacts/model_manifest.json`. Download or commit the Kaggle notebook output
to preserve these artifacts. No Unsloth or TRL APIs are used; training uses the
pinned Transformers `Trainer`, PEFT, and bitsandbytes implementations.

## Workflow

```bash
python ml/skill-intelligence/scripts/inspect_dataset.py
python ml/skill-intelligence/scripts/prepare_dataset.py
python ml/skill-intelligence/scripts/validate_dataset.py
python ml/skill-intelligence/scripts/create_splits.py
python ml/skill-intelligence/scripts/run_baseline.py
python ml/skill-intelligence/scripts/train_model.py
python ml/skill-intelligence/scripts/evaluate_model.py
python ml/skill-intelligence/scripts/export_adapter.py
python ml/skill-intelligence/scripts/test_inference.py
```

Training requires a genuine dataset report, a reviewed gold set, CUDA, and
enough VRAM for the selected 4-bit 4B configuration. The service boundary is
deliberately separate from the Next.js application.
