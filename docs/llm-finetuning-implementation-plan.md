# Qwen3-4B skill extraction implementation plan

## Verified repository facts

- The application is Next.js 16 App Router with a Supabase-authenticated dashboard.
- Phase 2A/2B live under `forecasting/` and use Pydantic, pandas, pytest, and
  optional matplotlib.
- The canonical skill taxonomy is
  `forecasting/taxonomy/skill_dictionary.py`; this plan reuses it rather than
  creating a second taxonomy.
- `forecasting/data/{raw,processed,normalized,exports}` contain placeholders
  only. No genuine job-posting dataset has been imported.
- Existing fixtures are synthetic unit-test inputs and are excluded from
  training and evaluation datasets.
- The repository's current Python interpreter is 3.14.3. The ML environment
  therefore remains separate and targets Python 3.11 or 3.12 because CUDA,
  bitsandbytes, and model wheels must be validated on the target GPU runtime.

## Implementation boundary

This phase adds dataset contracts, weak-label preparation, split/leakage
checks, evaluation metrics, inference schema validation, and QLoRA launch
configuration. It does not download model weights, train a model, access
private resumes, or alter the production Next.js application.

The pipeline stops with an explicit unavailable/insufficient-data report when
no genuine postings and human-reviewed gold examples are supplied. Automatic
taxonomy matches are marked as weak labels and are never presented as
human-verified ground truth.

## Execution order

1. Import a permitted, posting-level dataset through Phase 2A.
2. Inspect and validate provenance, dates, duplicates, and taxonomy coverage.
3. Review a representative sample and place gold examples in the isolated
   evaluation input directory.
4. Create temporal or deterministic group-aware splits.
5. Run the base-model baseline on the gold set.
6. Confirm a compatible Python 3.11/3.12 CUDA environment and GPU memory.
7. Run QLoRA only after the dataset report and hardware checks pass.
8. Evaluate the adapter on the unchanged held-out gold set before considering
   any integration.
