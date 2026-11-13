# Qwen3-4B fine-tuning guide

The isolated implementation is under `ml/skill-intelligence/`. It is not
connected to the production Next.js application and does not use private
resumes.

## Before training

1. Use a Python 3.11 or 3.12 CUDA environment.
2. Import a permitted genuine job-posting dataset through Phase 2A.
3. Review a representative sample and create a human-reviewed gold set.
4. Confirm the dataset report has non-zero genuine and reviewed examples.
5. Confirm the taxonomy version and source license.

## Kaggle

```bash
git clone <repository>
cd resumeIntel
python3.11 -m venv .venv-qwen
source .venv-qwen/bin/activate
python -m pip install -r ml/skill-intelligence/requirements.txt
python ml/skill-intelligence/scripts/inspect_dataset.py
python ml/skill-intelligence/scripts/prepare_dataset.py
python ml/skill-intelligence/scripts/validate_dataset.py
python ml/skill-intelligence/scripts/create_splits.py
python ml/skill-intelligence/scripts/run_baseline.py
python ml/skill-intelligence/scripts/train_model.py
```

Place permitted source data in the ignored ML data directory or provide a
controlled import path. Do not commit credentials, model weights, datasets, or
adapter checkpoints.

## Lightning AI

Use a GPU Studio with Python 3.11/3.12 and a CUDA-compatible PyTorch build,
then run the same commands from the repository root. Verify GPU name, VRAM,
CUDA version, and BF16 support before training. If the 4-bit 4B configuration
does not fit, use the configured 512-token low-memory profile; do not silently
change the base model.

## Evaluation and export

```bash
python ml/skill-intelligence/scripts/evaluate_model.py
python ml/skill-intelligence/scripts/compare_models.py
python ml/skill-intelligence/scripts/export_adapter.py
python ml/skill-intelligence/scripts/test_inference.py
```

These commands currently produce unavailable reports because the repository
has no gold set or model artifacts. A falling training loss alone is not a
success criterion; held-out extraction, mapping, JSON validity, evidence, and
unsupported-skill metrics must improve without unacceptable regression.
