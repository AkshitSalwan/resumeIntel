from __future__ import annotations


def memory_snapshot() -> dict[str, object]:
    try:
        import torch
    except ImportError:
        return {"available": False}
    if not torch.cuda.is_available():
        return {"available": False, "cuda": False}
    return {
        "available": True,
        "allocated_bytes": torch.cuda.memory_allocated(),
        "reserved_bytes": torch.cuda.memory_reserved(),
    }
