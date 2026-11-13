from __future__ import annotations

import argparse
import json
import math
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .deduplicate import deduplicate_jobs
from .export import export_jobs
from .http import PublicApiError
from .models import CollectionIssue, CollectionResult, NormalizedJob, RegistryEntry
from .normalize import normalize_job
from .sources import fetch_ashby, fetch_greenhouse, fetch_lever


FETCHERS = {"greenhouse": fetch_greenhouse, "lever": fetch_lever, "ashby": fetch_ashby}


def load_registry(path: str | Path) -> list[RegistryEntry]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [RegistryEntry.model_validate(item) for item in payload]


def _load_jobs(path: Path) -> dict[tuple[str, str], NormalizedJob]:
    jobs: dict[tuple[str, str], NormalizedJob] = {}
    if not path.exists():
        return jobs
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            job = NormalizedJob.model_validate_json(line)
        except ValueError:
            continue
        jobs[(job.source, job.source_job_id)] = job
    return jobs


def _write_checkpoint(path: Path, *, run_id: str, completed_boards: list[str], jobs: list[NormalizedJob], status: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "run_id": run_id,
        "status": status,
        "completed_boards": completed_boards,
        "jobs": [job.model_dump(mode="json") for job in jobs],
    }, indent=2), encoding="utf-8")


def _rejection_reason(raw: dict[str, Any], minimum_description_length: int) -> str | None:
    if not raw.get("source_job_id") or raw.get("source_job_id") == "None":
        return "missing_source_job_id"
    if not raw.get("title"):
        return "missing_title"
    description = raw.get("description") or ""
    if not description:
        return "empty_description"
    if len(description) < minimum_description_length:
        return "description_below_minimum_length"
    return None


def collect(
    registry: list[RegistryEntry],
    output_root: str | Path,
    max_records: int = 1000,
    rate_limit_seconds: float = 1.0,
    *,
    max_records_per_company: int | None = 250,
    max_records_per_source: int | None = 1000,
    minimum_description_length: int = 300,
    checkpoint_interval: int = 100,
    resume: bool = True,
) -> CollectionResult:
    root = Path(output_root)
    raw_dir = root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = root / "reports"
    collected_at = datetime.now(UTC)
    checkpoint_path = reports_dir / "collection_checkpoint.json"
    run_id = f"{collected_at.strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    previous_jobs = _load_jobs(root / "normalized" / "jobs.jsonl")
    jobs_by_key = dict(previous_jobs)
    completed_boards: list[str] = []
    if resume and checkpoint_path.exists():
        try:
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            if checkpoint.get("status") == "running":
                run_id = str(checkpoint["run_id"])
                completed_boards = [str(board) for board in checkpoint.get("completed_boards", [])]
                for item in checkpoint.get("jobs", []):
                    job = NormalizedJob.model_validate(item)
                    jobs_by_key[(job.source, job.source_job_id)] = job
        except (OSError, ValueError, TypeError, KeyError):
            pass

    issues: list[CollectionIssue] = []
    raw_files: list[str] = []
    fetched = 0
    parsed = 0
    rejected = Counter()
    stage_by_board: dict[str, dict[str, Any]] = {}
    source_counts = Counter(job.source for job in jobs_by_key.values())
    company_counts = Counter(job.company for job in jobs_by_key.values())
    target_remaining = max(0, max_records - len(jobs_by_key))

    for entry in registry:
        board_key = f"{entry.provider}:{entry.board}"
        if board_key in completed_boards:
            continue
        if target_remaining <= 0:
            break
        try:
            payload, raw_jobs = FETCHERS[entry.provider](entry)
            raw_path = raw_dir / f"{entry.provider}-{entry.board}-{run_id}.json"
            raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            raw_files.append(str(raw_path))
            fetched += len(raw_jobs)
            parsed += len(raw_jobs)
            board_stats = {"discovered": len(raw_jobs), "fetched": len(raw_jobs), "parsed": len(raw_jobs), "rejected": {}, "normalized": 0, "unique": 0, "exported": 0}
            candidates: list[dict[str, Any]] = []
            for raw in raw_jobs:
                reason = _rejection_reason(raw, minimum_description_length)
                if reason:
                    rejected[reason] += 1
                    board_stats["rejected"][reason] = board_stats["rejected"].get(reason, 0) + 1
                    continue
                candidates.append({**raw, "collection_run_id": run_id})
            company_quota = max_records_per_company if max_records_per_company is not None else math.ceil(max_records / max(1, len(registry)))
            source_quota = max_records_per_source if max_records_per_source is not None else max_records
            for raw in candidates:
                key = (entry.provider, str(raw["source_job_id"]))
                if key in jobs_by_key:
                    jobs_by_key[key] = normalize_job(raw, entry, collected_at, previous=jobs_by_key[key])
                    continue
                if target_remaining <= 0 or company_counts[entry.company] >= company_quota or source_counts[entry.provider] >= source_quota:
                    rejected["collection_cap_reached"] += 1
                    board_stats["rejected"]["collection_cap_reached"] = board_stats["rejected"].get("collection_cap_reached", 0) + 1
                    continue
                jobs_by_key[key] = normalize_job(raw, entry, collected_at)
                company_counts[entry.company] += 1
                source_counts[entry.provider] += 1
                target_remaining -= 1
                board_stats["normalized"] += 1
                if board_stats["normalized"] % checkpoint_interval == 0:
                    _write_checkpoint(checkpoint_path, run_id=run_id, completed_boards=completed_boards, jobs=list(jobs_by_key.values()), status="running")
            board_stats["unique"] = len(jobs_by_key)
            board_stats["exported"] = len(jobs_by_key)
            stage_by_board[board_key] = board_stats
            completed_boards.append(board_key)
            _write_checkpoint(checkpoint_path, run_id=run_id, completed_boards=completed_boards, jobs=list(jobs_by_key.values()), status="running")
        except (PublicApiError, KeyError, ValueError, TypeError, OSError) as error:
            issues.append(CollectionIssue(source=entry.provider, board=entry.board, status=getattr(error, "status", None), error=str(error), retryable=getattr(error, "retryable", False)))
        time.sleep(rate_limit_seconds)

    unique, duplicate_count = deduplicate_jobs(list(jobs_by_key.values()))
    from .validate import quality_report
    report = quality_report(
        fetched=fetched,
        parsed=parsed,
        jobs=unique,
        duplicate_count=duplicate_count,
        issues=issues,
        stage_accounting={"boards": stage_by_board, "records_rejected": dict(rejected), "records_normalized": len(unique), "records_exported": len(unique)},
        run_id=run_id,
        minimum_description_length=minimum_description_length,
    )
    paths = export_jobs(unique, report, root)
    _write_checkpoint(checkpoint_path, run_id=run_id, completed_boards=completed_boards, jobs=unique, status="complete")
    return CollectionResult(fetched=fetched, normalized=unique, issues=issues, raw_files=raw_files + paths, report=report)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect public job postings from official ATS APIs.")
    parser.add_argument("--registry", type=Path, default=Path(__file__).with_name("registry.json"))
    parser.add_argument("--output-root", type=Path, default=Path(__file__).parents[1] / "data/job-postings")
    parser.add_argument("--max-records", type=int, default=1000)
    parser.add_argument("--max-records-per-company", type=int)
    parser.add_argument("--max-records-per-source", type=int)
    parser.add_argument("--minimum-description-length", type=int, default=300)
    parser.add_argument("--checkpoint-interval", type=int, default=100)
    parser.add_argument("--rate-limit-seconds", type=float, default=1.0)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()
    result = collect(
        load_registry(args.registry),
        args.output_root,
        max_records=max(1, args.max_records),
        rate_limit_seconds=max(0.0, args.rate_limit_seconds),
        max_records_per_company=args.max_records_per_company,
        max_records_per_source=args.max_records_per_source,
        minimum_description_length=max(0, args.minimum_description_length),
        checkpoint_interval=max(1, args.checkpoint_interval),
        resume=not args.no_resume,
    )
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
