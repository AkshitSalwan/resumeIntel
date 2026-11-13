# Future Skills Intelligence

This package is isolated from the numerical forecasting engine. It reuses the
canonical taxonomy in `forecasting.taxonomy.skill_dictionary` and the genuine
500-posting normalized collection.

## AI-assisted validation pre-review

AI pre-review labels use the distinct `ai_assisted` status and are pseudo-labels,
not independent ground truth. They have no human reviewer identity, are excluded
from the existing human-reviewed exporter, and are exported to a separate file.
They must not be used to report human-verified accuracy.

From `ml/skill-intelligence`, run:

```bash
python -m future_skills.workflow ai-pre-review-validation
python -m future_skills.workflow export-validation-ai
python -m future_skills.workflow report \
  --candidates future_skills/data/validation.jsonl \
  --annotations future_skills/data/validation_annotations.jsonl \
  --output future_skills/data/validation_ai_pre_review_report.json
```

Human-reviewed validation examples remain available through the separate
`export-validation` command and `validation_sft.jsonl` output.

## Prepare candidate data

```bash
PYTHONPATH=../..:. python -m future_skills.prepare \
  --input data/job-postings/normalized/jobs.jsonl \
  --output-dir future_skills/data
```

The command creates provenance-rich Qwen chat JSONL files. Current labels are
`candidate` weak dictionary matches only. They are not human-reviewed or gold
labels. Company-grouped splits prevent postings from the same company from
appearing in multiple splits. Future-outcome training remains disabled because
the dataset does not contain sufficient historical outcome windows.

Tasks requiring reviewed evidence (relationships, trend interpretation,
emerging classification, and career intelligence) are not fabricated from
weak labels. Add reviewed examples to separate files and mark reviewer
provenance before using them for evaluation or training.

## Human annotation workflow

Export the training candidates for review:

```bash
PYTHONPATH=../..:. python -m future_skills.workflow export-annotations \
  --candidates future_skills/data/train.jsonl \
  --output future_skills/data/train_annotations.jsonl \
  --csv future_skills/data/train_annotations.csv
```

Review interactively, with progress saved after every decision:

```bash
PYTHONPATH=../..:. python -m future_skills.annotate \
  --candidates future_skills/data/train.jsonl \
  --annotations future_skills/data/train_reviews.jsonl
```

Use the held-out test split for gold review; do not annotate training records
as gold:

```bash
PYTHONPATH=../..:. python -m future_skills.workflow export-annotations \
  --candidates future_skills/data/test.jsonl \
  --output future_skills/data/test_annotations.jsonl
PYTHONPATH=../..:. python -m future_skills.annotate \
  --candidates future_skills/data/test.jsonl \
  --annotations future_skills/data/test_reviews.jsonl
PYTHONPATH=../..:. python -m future_skills.workflow export-gold \
  --annotations future_skills/data/test_reviews.jsonl \
  --training future_skills/data/train.jsonl \
  --output future_skills/data/gold.jsonl
```

Generate the quality report:

```bash
PYTHONPATH=../..:. python -m future_skills.workflow report \
  --candidates future_skills/data/train.jsonl \
  --annotations future_skills/data/train_reviews.jsonl \
  --gold future_skills/data/gold.jsonl \
  --training future_skills/data/train.jsonl \
  --output future_skills/data/annotation_report.json
```

No records are automatically promoted to reviewed or gold. Gold export rejects
training overlap and company split leakage. Mapping accuracy remains `null`
until reviewers provide independent corrected labels; weak labels are never
used as human ground truth.

### Skill taxonomy and corrections

The shared canonical taxonomy lives in `forecasting/taxonomy/skill_dictionary.py`.
The initial taxonomy covers programming, AI/ML, data engineering, cloud and
infrastructure, cybersecurity, emerging technology, and business/commercial
skills. Business/commercial concepts added for this workflow are `sales`,
`account-management`, `business-development`, `customer-retention`, and
`revenue-growth`. Their aliases are defined beside each canonical skill.

When correcting an extraction, the reviewer CLI searches canonical names and
aliases, displays the canonical ID and aliases, and asks for evidence quoted
from the job description. `Go` requires nearby programming context (or the
unambiguous `Golang` spelling); go-to-market/GTM language alone does not match.
Corrections are stored in the human annotation file separately from candidate
extractions and retain the reviewer's choice and evidence.

Check training readiness only from the reviewed/gold report:

```bash
PYTHONPATH=../..:. python -m future_skills.train \
  --dataset-report future_skills/data/annotation_report.json \
  --min-reviewed-training 50 \
  --min-gold-evaluation 20
```

## Model and inference

`config/future_skills.json` records the intended Qwen3-4B QLoRA configuration:
NF4 double quantization, rank 16, alpha 32, dropout 0.05, gradient
accumulation 8, and sequence length 1024. Training requires an NVIDIA GPU and
the isolated requirements in `ml/skill-intelligence/requirements.txt`.

The inference boundary is disabled by default. It requires
`RESUMEINTEL_FUTURE_SKILLS_ENABLED=true` and a validated adapter or configured
Ollama endpoint; it never falls back to an unvalidated base model. The
Next.js status endpoint is `/api/future-skills/status`. This module does not
alter the numerical forecast endpoints or their readiness gate.

Ollama is optional and must be validated only after adapter compatibility and
GGUF conversion have been tested. The Hugging Face adapter remains the
canonical training artifact.
