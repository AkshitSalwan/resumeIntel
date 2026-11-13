from __future__ import annotations


def load_model(*, adapter_path: str | None = None, merged_model: bool = False) -> tuple[object, object]:
    """Load only after the caller has explicitly supplied a real model artifact."""
    if not adapter_path and not merged_model:
        raise RuntimeError("No adapter or explicitly requested merged model was supplied.")
    raise NotImplementedError("Model loading requires a validated GPU/CPU runtime and downloaded model artifacts.")
