# Future Skills Intelligence architecture

The Qwen system is isolated under
[`ml/skill-intelligence/future_skills`](../ml/skill-intelligence/future_skills/).
It reuses the canonical taxonomy in
[`forecasting/taxonomy/skill_dictionary.py`](../forecasting/taxonomy/skill_dictionary.py),
the normalized ATS collection, and the existing QLoRA hardware/configuration
scaffolding. It does not replace the statistical forecasting engine or change
the numerical forecast readiness gate.

The preparation flow creates weak, provenance-rich skill-extraction candidates
from the 500 genuine postings. Company-grouped splits are written to
`future_skills/data/`; no examples are marked human-reviewed or gold. Evidence
interpretation, relationship reasoning, emerging classification, and career
intelligence require separately reviewed evidence and are not fabricated.

Inference is behind `RESUMEINTEL_FUTURE_SKILLS_ENABLED` and requires a validated
adapter or explicitly configured Ollama endpoint. The service rejects
unvalidated fallbacks and requires evidence or an explicit
insufficient-evidence result. The authenticated status endpoint is
`/api/future-skills/status`; numerical forecast endpoints remain unchanged.

Training is intentionally blocked until a human-reviewed gold set and an
NVIDIA-compatible runtime are available. The intended configuration is
Qwen3-4B-Instruct-2507 with Unsloth, Transformers, PEFT, TRL,
BitsAndBytes, NF4 double quantization, LoRA rank 16/alpha 32, and sequence
length 1024. No adapter, GGUF, Ollama model, or evaluation result is claimed
as present.
