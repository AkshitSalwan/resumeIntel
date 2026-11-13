from __future__ import annotations

import importlib.metadata
import sys


PINNED_RUNTIME_VERSIONS = {
    "torch": "2.6.0",
    "transformers": "4.51.3",
    "peft": "0.15.2",
    "bitsandbytes": "0.45.5",
    "accelerate": "1.6.0",
}


def inspect_runtime_packages() -> dict[str, object]:
    versions: dict[str, str] = {}
    errors: list[str] = []
    for package, expected in PINNED_RUNTIME_VERSIONS.items():
        try:
            installed = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            errors.append(f"{package} is not installed (expected {expected}).")
            continue
        versions[package] = installed
        if installed.split("+", 1)[0] != expected:
            errors.append(f"{package} version {installed} does not match pinned {expected}.")
    supported_python = (3, 11) <= sys.version_info[:2] < (3, 13)
    if not supported_python:
        errors.append(f"Python {sys.version_info.major}.{sys.version_info.minor} is unsupported; use Python 3.11 or 3.12.")
    return {"versions": versions, "errors": errors, "valid": not errors}


def inspect_hardware() -> dict[str, object]:
    try:
        import torch
    except ImportError:
        return {"torch_available": False, "cuda": False, "reason": "Install the isolated ML requirements first."}
    cuda = bool(torch.cuda.is_available())
    result: dict[str, object] = {
        "torch_available": True,
        "torch_version": torch.__version__,
        "cuda": cuda,
        "cuda_version": torch.version.cuda,
        "bf16_supported": bool(cuda and torch.cuda.is_bf16_supported()),
        "devices": [],
    }
    if cuda:
        result["devices"] = [
            {
                "index": index,
                "name": torch.cuda.get_device_name(index),
                "memory_gb": round(torch.cuda.get_device_properties(index).total_memory / 1024**3, 2),
                "compute_capability": torch.cuda.get_device_capability(index),
            }
            for index in range(torch.cuda.device_count())
        ]
    return result


def require_training_hardware() -> dict[str, object]:
    runtime = inspect_runtime_packages()
    if not runtime["valid"]:
        raise RuntimeError("Training runtime preflight failed: " + "; ".join(runtime["errors"]))
    hardware = inspect_hardware()
    if not hardware.get("cuda"):
        raise RuntimeError("QLoRA training requires a CUDA GPU; no compatible CUDA device was detected.")
    if not hardware.get("devices"):
        raise RuntimeError("CUDA is available but no GPU device was enumerated.")
    for device in hardware["devices"]:
        if tuple(device["compute_capability"]) < (6, 0):
            raise RuntimeError(f"GPU {device['name']} compute capability is below the supported NF4 threshold 6.0.")
    if not hardware.get("cuda_version"):
        raise RuntimeError("PyTorch does not report a CUDA runtime; reinstall the CUDA-enabled pinned PyTorch build.")
    try:
        cuda_version = tuple(int(part) for part in str(hardware["cuda_version"]).split(".")[:2])
    except ValueError as error:
        raise RuntimeError(f"Unrecognized PyTorch CUDA version: {hardware['cuda_version']}") from error
    if cuda_version < (11, 7) or cuda_version > (12, 6):
        raise RuntimeError(f"PyTorch CUDA {hardware['cuda_version']} is outside the supported bitsandbytes 0.45.5 range (11.7-12.6).")

    # Exercise a small NF4 kernel so a CPU-only or mismatched bitsandbytes wheel
    # is caught before the model is loaded or Trainer is created.
    import torch
    import bitsandbytes as bnb

    probe = torch.randn((32, 32), device="cuda")
    try:
        bnb.functional.quantize_4bit(probe, quant_type="nf4")
        torch.cuda.synchronize()
        bnb.optim.PagedAdamW8bit
    except Exception as error:
        raise RuntimeError(f"bitsandbytes CUDA/NF4 preflight failed: {error}") from error
    finally:
        del probe
        torch.cuda.empty_cache()
    hardware["runtime_packages"] = runtime["versions"]
    return hardware
