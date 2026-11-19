# Test execution evidence

Executed during preparation of the supporting-document package on 2026-11-14.

- `pnpm test`: 49 tests passed across 6 test files.
- `PYTHONPATH=ml/skill-intelligence .venv/bin/python -m pytest forecasting/tests ml/skill-intelligence/collection/tests ml/skill-intelligence/future_skills/tests ml/skill-intelligence/scripts/test_inference.py ml/skill-intelligence/tests/test_ml_pipeline.py`: 66 tests passed.

An initial Python invocation without the package path failed during test collection (`ModuleNotFoundError: collection`); rerunning with the repository's ML package directory on `PYTHONPATH` collected and passed the complete set. This is documented to keep the verification record reproducible.
