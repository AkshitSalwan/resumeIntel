from datetime import UTC, datetime
from pathlib import Path

from collection.deduplicate import deduplicate_jobs
from collection.country import resolve_country
from collection.collector import collect
from collection.models import RegistryEntry
from collection.normalize import normalize_job
from collection.sources.ashby import fetch_ashby
from collection.sources.greenhouse import fetch_greenhouse
from collection.sources.lever import fetch_lever


ENTRY = RegistryEntry(
    company="Example", provider="greenhouse", board="example", website="https://example.com", source_url="https://example.test"
)
NOW = datetime(2026, 11, 9, tzinfo=UTC)


def test_greenhouse_mapping_preserves_content_and_metadata():
    payload = {"jobs": [{"id": 1, "title": "Engineer", "content": "&lt;p&gt;Python&lt;/p&gt;", "absolute_url": "https://jobs/1", "updated_at": "2026-01-01T00:00:00Z", "location": {"name": "Remote"}, "departments": [{"name": "Engineering"}], "offices": [{"name": "US"}]}]}
    _, jobs = fetch_greenhouse(ENTRY, fetch=lambda _: payload)
    assert jobs[0]["description"] == "Python"
    assert jobs[0]["source_job_id"] == "1"
    assert jobs[0]["source_metadata"]["departments"][0]["name"] == "Engineering"


def test_lever_paginates_until_short_page():
    calls = []
    def fetch(url):
        calls.append(url)
        return [{"id": str(len(calls)), "text": "Engineer", "descriptionPlain": "Python", "hostedUrl": "https://jobs"}] if len(calls) == 1 else []
    _, jobs = fetch_lever(ENTRY.model_copy(update={"provider": "lever", "board": "example"}), fetch=fetch, page_size=1)
    assert len(calls) == 2
    assert len(jobs) == 1


def test_ashby_mapping_keeps_compensation_and_workplace():
    payload = {"jobs": [{"id": "a", "title": "Engineer", "descriptionPlain": "Python", "location": "Remote", "publishedAt": "2026-01-01T00:00:00Z", "workplaceType": "Remote", "jobUrl": "https://jobs", "compensation": {"currency": "USD"}}]}
    _, jobs = fetch_ashby(ENTRY.model_copy(update={"provider": "ashby"}), fetch=lambda _: payload)
    assert jobs[0]["workplace_type"] == "Remote"
    assert jobs[0]["compensation"]["currency"] == "USD"


def test_deduplication_is_source_first_and_cross_source_conservative():
    one = normalize_job({"source": "greenhouse", "source_job_id": "1", "company": "A", "title": "Engineer", "description": "Python"}, ENTRY, NOW)
    duplicate = one.model_copy(update={"last_seen_at": NOW})
    same_title_other_id = one.model_copy(update={"source_job_id": "2", "record_id": "different"})
    unique, count = deduplicate_jobs([one, duplicate, same_title_other_id])
    assert len(unique) == 2
    assert count == 1


def test_normalization_preserves_first_observation():
    first = normalize_job({"source": "greenhouse", "source_job_id": "1", "company": "A", "title": "Engineer", "description": "Python"}, ENTRY, NOW)
    later = normalize_job({"source": "greenhouse", "source_job_id": "1", "company": "A", "title": "Engineer", "description": "Python"}, ENTRY, NOW.replace(day=10), previous=first)
    assert later.first_seen_at == first.first_seen_at
    assert later.last_seen_at == NOW.replace(day=10)


def test_country_resolution_requires_explicit_unambiguous_evidence():
    assert resolve_country("London, UK").country == "United Kingdom"
    assert resolve_country("New York, US").method == "curated_alias"
    assert resolve_country("Remote - UK / US").country is None
    assert resolve_country("Toronto").country is None


def test_greenhouse_date_semantics_keep_update_date_separate():
    payload = {"jobs": [{"id": 1, "title": "Engineer", "content": "A full description", "updated_at": "2026-01-01T00:00:00Z"}]}
    _, jobs = fetch_greenhouse(ENTRY, fetch=lambda _: payload)
    assert jobs[0]["published_at"] is None
    assert jobs[0]["source_updated_at"] == NOW.replace(year=2026, month=1, day=1)
    assert jobs[0]["source_metadata"]["source_updated_at_raw"] == "2026-01-01T00:00:00Z"


def test_collection_rejects_empty_and_short_descriptions_and_exports_consistently(tmp_path, monkeypatch):
    import collection.collector as collector_module

    entry = ENTRY.model_copy(update={"board": "board"})
    payload = {
        "jobs": [
            {"id": 1, "title": "Short", "content": "too short"},
            {"id": 2, "title": "Empty", "content": ""},
            {"id": 3, "title": "Valid", "content": "x" * 300, "absolute_url": "https://jobs/3"},
        ]
    }
    monkeypatch.setitem(collector_module.FETCHERS, "greenhouse", lambda _: (payload, [
        {"source": "greenhouse", "source_job_id": "1", "company": "Example", "title": "Short", "description": "too short"},
        {"source": "greenhouse", "source_job_id": "2", "company": "Example", "title": "Empty", "description": ""},
        {"source": "greenhouse", "source_job_id": "3", "company": "Example", "title": "Valid", "description": "x" * 300, "job_url": "https://jobs/3"},
    ]))
    result = collect([entry], tmp_path, max_records=10, rate_limit_seconds=0, minimum_description_length=300)
    assert len(result.normalized) == 1
    report = result.report
    assert report["records_rejected"] == 2
    assert report["stage_accounting"]["records_exported"] == 1
    assert (tmp_path / "normalized/jobs.jsonl").read_text().count("\n") == 1


def test_collection_resume_uses_running_checkpoint(tmp_path, monkeypatch):
    import collection.collector as collector_module

    first = normalize_job({"source": "greenhouse", "source_job_id": "1", "company": "Example", "title": "Engineer", "description": "x" * 300}, ENTRY, NOW)
    checkpoint = tmp_path / "reports/collection_checkpoint.json"
    checkpoint.parent.mkdir()
    checkpoint.write_text(__import__("json").dumps({
        "run_id": "resume-run", "status": "running", "completed_boards": ["greenhouse:done"],
        "jobs": [first.model_dump(mode="json")],
    }))
    second_entry = ENTRY.model_copy(update={"board": "next"})
    monkeypatch.setitem(collector_module.FETCHERS, "greenhouse", lambda _: ({}, [
        {"source": "greenhouse", "source_job_id": "2", "company": "Example", "title": "Engineer 2", "description": "y" * 300},
    ]))
    result = collect([ENTRY.model_copy(update={"board": "done"}), second_entry], tmp_path, max_records=2, rate_limit_seconds=0)
    assert {job.source_job_id for job in result.normalized} == {"1", "2"}
