from __future__ import annotations

import os
from dataclasses import dataclass

from .schemas import FutureSkillsOutput, ModelConfig, TaskType


class FutureSkillsUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class InferenceRequest:
    task_type: TaskType
    evidence: list[dict[str, object]]
    prompt: str


def load_config() -> ModelConfig:
    return ModelConfig(
        enabled=os.getenv("RESUMEINTEL_FUTURE_SKILLS_ENABLED", "false").lower() == "true",
        adapter_path=os.getenv("RESUMEINTEL_FUTURE_SKILLS_ADAPTER"),
        model_version=os.getenv("RESUMEINTEL_FUTURE_SKILLS_MODEL_VERSION", "untrained"),
        ollama_endpoint=os.getenv("RESUMEINTEL_FUTURE_SKILLS_OLLAMA_ENDPOINT"),
        inference_timeout_seconds=float(os.getenv("RESUMEINTEL_FUTURE_SKILLS_TIMEOUT", "30")),
    )


def infer(request: InferenceRequest, *, config: ModelConfig | None = None) -> FutureSkillsOutput:
    settings = config or load_config()
    if not settings.enabled:
        raise FutureSkillsUnavailable("Future Skills Intelligence is disabled by configuration.")
    if not settings.adapter_path and not settings.ollama_endpoint:
        raise FutureSkillsUnavailable("No validated adapter or Ollama endpoint is configured.")
    raise FutureSkillsUnavailable("A validated model runtime is not installed; no unvalidated fallback is permitted.")
