from __future__ import annotations

import json
import zipfile
from pathlib import Path

from _bootstrap import ROOT


def main() -> int:
    artifact_dir = ROOT / "artifacts" / "future_skills"
    adapter_dir = artifact_dir / "adapter"
    manifest_path = ROOT / "artifacts" / "model_manifest.json"
    if not adapter_dir.is_dir():
        manifest = {
            "status": "unavailable",
            "base_model": "Qwen/Qwen3-4B-Instruct-2507",
            "message": "No adapter checkpoint exists; export was not run.",
        }
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps(manifest, indent=2))
        return 2

    bundle = artifact_dir / "future_skills_adapter.zip"
    included: list[str] = []
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(adapter_dir.rglob("*")):
            if path.is_file():
                relative = path.relative_to(artifact_dir)
                archive.write(path, relative.as_posix())
                included.append(relative.as_posix())
        for name in (
            "training_config.json",
            "training_metrics.json",
            "training_log_history.json",
            "training_metadata.json",
            "gold_metrics.json",
        ):
            path = artifact_dir / name
            if path.is_file():
                archive.write(path, name)
                included.append(name)

    metadata_path = artifact_dir / "training_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
    manifest = {
        "status": "exported",
        "base_model": metadata.get("base_model", "Qwen/Qwen3-4B-Instruct-2507"),
        "adapter_path": str(adapter_dir),
        "bundle_path": str(bundle),
        "included_artifacts": included,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
